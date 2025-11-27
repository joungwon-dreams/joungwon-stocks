"""
Phase 4: 피드백 루프 & 증분 재분석
피드백 유형별 최소 범위만 재실행

목표:
- 단일 종목 재분석: ~30초
- 필터 조건 변경: ~5분
- 데이터 새로고침: ~7분
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

import sys
sys.path.insert(0, '.')
from 신규종목추천.config.settings import settings
from 신규종목추천.src.utils.database import db
from 신규종목추천.src.phase1 import Phase1AFilter, Phase1BFilter
from 신규종목추천.src.phase2 import BatchCollector, GeminiBatchAnalyzer, CollectedData
from 신규종목추천.src.phase3 import ValueScorer

logger = logging.getLogger(__name__)


class IncrementalRunner:
    """
    피드백 기반 증분 재분석기

    핵심: 전체 파이프라인 재실행 없이 필요한 Phase만 실행
    """

    def __init__(self):
        self.filter_1a = Phase1AFilter()
        self.filter_1b = Phase1BFilter()
        self.analyzer = GeminiBatchAnalyzer()
        self.scorer = ValueScorer()

    async def handle_feedback(
        self,
        feedback_type: str,
        params: Dict = None
    ) -> Dict[str, Any]:
        """
        피드백 유형에 따라 최소 범위만 재실행

        Args:
            feedback_type: 피드백 유형
                - 'reanalyze_stock': 특정 종목만 AI 재분석
                - 'change_filter': 필터 조건 변경 → Phase 1부터
                - 'refresh_data': 데이터 새로고침 → Phase 2A부터
                - 'full': 전체 재실행
            params: 피드백 파라미터

        Returns:
            업데이트된 추천 결과
        """
        params = params or {}
        start_time = datetime.now()

        logger.info(f"피드백 처리 시작: {feedback_type}")

        if feedback_type == 'reanalyze_stock':
            result = await self._reanalyze_single(params.get('code'))

        elif feedback_type == 'change_filter':
            result = await self._run_from_phase1(params.get('new_filters', {}))

        elif feedback_type == 'refresh_data':
            codes = params.get('codes')
            result = await self._run_from_phase2a(codes)

        elif feedback_type == 'exclude_stock':
            result = await self._exclude_stock(params.get('code'), params.get('reason'))

        elif feedback_type == 'full':
            result = await self._run_full_pipeline()

        else:
            raise ValueError(f"Unknown feedback type: {feedback_type}")

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"피드백 처리 완료: {elapsed:.1f}초")

        return result

    async def _reanalyze_single(self, code: str) -> Dict:
        """
        단일 종목 AI 재분석 (~30초)

        기존 수집 데이터 사용, AI만 재분석
        """
        if not code:
            raise ValueError("종목 코드가 필요합니다")

        logger.info(f"단일 종목 재분석: {code}")

        # 1. 기존 추천 데이터 로드
        existing = await self._load_existing_recommendation(code)
        if not existing:
            raise ValueError(f"기존 추천 데이터 없음: {code}")

        # 2. 기존 수집 데이터 로드
        collected = await self._load_collected_data(code)

        # 3. AI 재분석
        stock_data = dict(existing)
        analyzed = await self.analyzer.analyze_single(stock_data, collected)

        # 4. 점수 재계산
        scored = await self.scorer.score_all([analyzed])
        result = scored[0] if scored else analyzed

        # 5. 피드백 이력 저장
        await self._save_feedback(
            code=code,
            feedback_type='reanalyze',
            before_grade=existing.get('ai_grade'),
            after_grade=result.get('ai_grade'),
            before_score=existing.get('final_score'),
            after_score=result.get('final_score'),
        )

        return {
            'code': code,
            'updated': True,
            'before': {'grade': existing.get('ai_grade'), 'score': existing.get('final_score')},
            'after': {'grade': result.get('ai_grade'), 'score': result.get('final_score')},
        }

    async def _run_from_phase1(self, new_filters: Dict) -> Dict:
        """
        필터 조건 변경 시 Phase 1부터 재실행 (~5분)
        """
        batch_id = str(uuid.uuid4())
        logger.info(f"Phase 1부터 재실행 (batch_id: {batch_id})")

        # 필터 설정 업데이트
        if new_filters:
            for key, value in new_filters.items():
                if hasattr(self.filter_1a.config, key):
                    setattr(self.filter_1a.config, key, value)
                if hasattr(self.filter_1b.config, key):
                    setattr(self.filter_1b.config, key, value)

        # 실행 이력 시작
        await self._start_run_history(batch_id, 'incremental', new_filters)

        # Phase 1
        candidates_1a = await self.filter_1a.filter(batch_id)
        candidates_1b = await self.filter_1b.filter(candidates_1a, batch_id)

        # Phase 2
        async with BatchCollector() as collector:
            collected = await collector.collect_all(candidates_1b)

        analyzed = await self.analyzer.analyze_batch(candidates_1b, collected)

        # Phase 3
        results = await self.scorer.score_all(analyzed, batch_id)

        return {
            'batch_id': batch_id,
            'filter_changed': new_filters,
            'total_candidates': len(results),
            'top_picks': results[:10],
        }

    async def _run_from_phase2a(self, codes: List[str] = None) -> Dict:
        """
        데이터 새로고침 시 Phase 2A부터 재실행 (~7분)
        """
        batch_id = str(uuid.uuid4())
        logger.info(f"Phase 2A부터 재실행 (batch_id: {batch_id})")

        # 코드가 없으면 최근 추천 종목 사용
        if not codes:
            codes = await self._get_latest_recommendation_codes()

        if not codes:
            raise ValueError("재분석할 종목이 없습니다")

        # 기존 Phase 1 결과 로드
        candidates = await self._load_phase1_results(codes)

        # 실행 이력 시작
        await self._start_run_history(batch_id, 'refresh')

        # Phase 2A: 데이터 재수집
        async with BatchCollector() as collector:
            # 캐시 무시하고 강제 수집
            collected = await collector.collect_all(candidates)

        # Phase 2B: AI 분석
        analyzed = await self.analyzer.analyze_batch(candidates, collected)

        # Phase 3: 스코어링
        results = await self.scorer.score_all(analyzed, batch_id)

        return {
            'batch_id': batch_id,
            'refreshed_count': len(results),
            'top_picks': results[:10],
        }

    async def _exclude_stock(self, code: str, reason: str = None) -> Dict:
        """특정 종목 제외 처리"""
        if not code:
            raise ValueError("종목 코드가 필요합니다")

        # 최근 추천에서 해당 종목 제외 마킹
        query = """
        UPDATE smart_recommendations
        SET ai_grade = 'X', ai_risk_factor = $2
        WHERE stock_code = $1
          AND recommendation_date = CURRENT_DATE
        """

        await db.execute(query, code, f"제외됨: {reason or '사용자 요청'}")

        # 피드백 이력 저장
        await self._save_feedback(
            code=code,
            feedback_type='exclude',
            reason=reason,
        )

        return {'code': code, 'excluded': True, 'reason': reason}

    async def _run_full_pipeline(self) -> Dict:
        """전체 파이프라인 재실행"""
        from 신규종목추천.run import SmartValueFinder
        runner = SmartValueFinder()
        return await runner.run()

    async def _load_existing_recommendation(self, code: str) -> Optional[Dict]:
        """기존 추천 데이터 로드"""
        query = """
        SELECT *
        FROM smart_recommendations
        WHERE stock_code = $1
        ORDER BY recommendation_date DESC, created_at DESC
        LIMIT 1
        """
        return await db.fetchrow(query, code)

    async def _load_collected_data(self, code: str) -> CollectedData:
        """수집 데이터 로드"""
        query = """
        SELECT data_type, title, sentiment, target_price, rating, firm_name, raw_data
        FROM smart_collected_data
        WHERE stock_code = $1
          AND expires_at > NOW()
        ORDER BY collected_at DESC
        """

        rows = await db.fetch(query, code)

        collected = CollectedData(stock_code=code)

        for row in rows:
            if row['data_type'] == 'news':
                collected.news.append({
                    'title': row['title'],
                    'sentiment': row['sentiment'],
                })
            elif row['data_type'] == 'consensus':
                if row['raw_data']:
                    collected.consensus = row['raw_data']

        return collected

    async def _get_latest_recommendation_codes(self) -> List[str]:
        """최근 추천 종목 코드 조회"""
        query = """
        SELECT DISTINCT stock_code
        FROM smart_recommendations
        WHERE recommendation_date = (
            SELECT MAX(recommendation_date) FROM smart_recommendations
        )
        ORDER BY final_score DESC
        LIMIT 50
        """
        rows = await db.fetch(query)
        return [r['stock_code'] for r in rows]

    async def _load_phase1_results(self, codes: List[str]) -> List[Dict]:
        """Phase 1 결과 로드"""
        query = """
        SELECT
            sr.stock_code,
            sr.stock_name,
            sr.pbr, sr.per, sr.market_cap, sr.volume, sr.close_price,
            sr.rsi_14, sr.disparity_20, sr.disparity_60,
            sr.pension_net_buy, sr.institution_net_buy,
            sr.quant_score
        FROM smart_recommendations sr
        WHERE sr.stock_code = ANY($1)
        ORDER BY sr.recommendation_date DESC
        """
        rows = await db.fetch(query, codes)

        # 중복 제거 (종목당 최신 1건)
        seen = set()
        results = []
        for r in rows:
            if r['stock_code'] not in seen:
                seen.add(r['stock_code'])
                results.append(dict(r))

        return results

    async def _start_run_history(
        self,
        batch_id: str,
        run_type: str,
        filter_config: Dict = None
    ) -> None:
        """실행 이력 시작"""
        query = """
        INSERT INTO smart_run_history (batch_id, run_type, filter_config, status)
        VALUES ($1, $2, $3, 'running')
        """
        import json
        await db.execute(
            query,
            batch_id,
            run_type,
            json.dumps(filter_config) if filter_config else None
        )

    async def _save_feedback(self, code: str, feedback_type: str, **kwargs) -> None:
        """피드백 이력 저장"""
        query = """
        INSERT INTO smart_feedback (
            stock_code, feedback_type, feedback_reason,
            before_grade, after_grade, before_score, after_score
        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        """
        await db.execute(
            query,
            code,
            feedback_type,
            kwargs.get('reason'),
            kwargs.get('before_grade'),
            kwargs.get('after_grade'),
            kwargs.get('before_score'),
            kwargs.get('after_score'),
        )


async def main():
    """테스트 실행"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    await db.connect()

    try:
        runner = IncrementalRunner()

        # 테스트 1: 필터 조건 변경
        print("\n=== 테스트: 필터 조건 변경 ===")
        result = await runner.handle_feedback(
            'change_filter',
            {'new_filters': {'pbr_max': 0.8, 'per_max': 12}}
        )
        print(f"결과: {result.get('total_candidates', 0)}개 종목")

        # 테스트 2: 특정 종목 재분석 (있는 경우)
        if result.get('top_picks'):
            code = result['top_picks'][0]['stock_code']
            print(f"\n=== 테스트: {code} 재분석 ===")
            reanalyze_result = await runner.handle_feedback(
                'reanalyze_stock',
                {'code': code}
            )
            print(f"결과: {reanalyze_result}")

    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
