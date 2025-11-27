"""
Phase 3: 최종 스코어링 & 결과 저장
정량 40% + 정성 60% 통합 점수 계산

목표: <1분 내 실행
"""
import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime
import uuid
import json

import sys
sys.path.insert(0, '.')
from 신규종목추천.config.settings import settings
from 신규종목추천.src.utils.database import db

logger = logging.getLogger(__name__)


class ValueScorer:
    """
    최종 가치 점수 계산기

    점수 구성:
    - 정량 점수 (40%): PBR 깊이, RSI 위치, 수급 강도
    - 정성 점수 (60%): AI 등급, 신뢰도
    """

    def __init__(self, config=None):
        self.config = config or settings.phase3

    async def score_all(
        self,
        candidates: List[Dict[str, Any]],
        batch_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        전체 후보 종목 스코어링 및 저장

        Args:
            candidates: Phase 2B 결과 (AI 분석 완료)
            batch_id: 배치 식별자

        Returns:
            최종 점수가 계산된 종목 리스트 (정렬됨)
        """
        if not candidates:
            return []

        batch_id = batch_id or str(uuid.uuid4())
        start_time = datetime.now()

        logger.info(f"Phase 3 시작: {len(candidates)}개 종목 스코어링")

        results = []

        for stock in candidates:
            # 정량 점수 (Phase 1B에서 이미 계산됨)
            quant_score = stock.get('quant_score', 0)

            # 정성 점수 계산
            qual_score = self._calculate_qual_score(stock)

            # 최종 점수 계산
            final_score = (
                quant_score * self.config.quant_weight +
                qual_score * self.config.qual_weight
            )

            result = {
                **stock,
                'quant_score': round(quant_score, 2),
                'qual_score': round(qual_score, 2),
                'final_score': round(final_score, 2),
                'batch_id': batch_id,
            }
            results.append(result)

        # 최종 점수 기준 정렬
        results.sort(key=lambda x: x['final_score'], reverse=True)

        # 순위 부여
        for i, r in enumerate(results, 1):
            r['rank_in_batch'] = i

        # DB 저장
        await self._save_recommendations(results)

        # 실행 이력 업데이트
        await self._update_run_history(batch_id, len(results))

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Phase 3 완료: {len(results)}개 종목 저장 ({elapsed:.2f}초)")

        return results

    def _calculate_qual_score(self, stock: Dict) -> float:
        """
        정성 점수 계산 (0-100)

        구성:
        - AI 등급 기본 점수
        - 신뢰도(confidence) 가중
        """
        ai_grade = stock.get('ai_grade', 'C')
        ai_confidence = stock.get('ai_confidence', 0.5)

        # 등급별 기본 점수
        grade_score = self.config.grade_scores.get(ai_grade, 40)

        # 신뢰도 가중 (0.5~1.0 범위를 0.7~1.0으로 스케일링)
        confidence_factor = 0.7 + (ai_confidence * 0.3)

        qual_score = grade_score * confidence_factor

        return min(100, qual_score)

    async def _save_recommendations(self, results: List[Dict]) -> None:
        """추천 결과를 DB에 저장"""
        query = """
        INSERT INTO smart_recommendations (
            stock_code, stock_name, recommendation_date, batch_id,
            pbr, per, market_cap, volume, close_price,
            rsi_14, disparity_20, disparity_60, ma_20, ma_60,
            pension_net_buy, institution_net_buy, foreign_net_buy,
            quant_score,
            news_count, news_sentiment, report_count,
            avg_target_price, consensus_buy, consensus_hold, consensus_sell,
            ai_grade, ai_confidence, ai_key_material, ai_policy_alignment,
            ai_buy_point, ai_risk_factor, ai_raw_response,
            qual_score, final_score, rank_in_batch
        ) VALUES (
            $1, $2, CURRENT_DATE, $3,
            $4, $5, $6, $7, $8,
            $9, $10, $11, $12, $13,
            $14, $15, $16,
            $17,
            $18, $19, $20,
            $21, $22, $23, $24,
            $25, $26, $27, $28,
            $29, $30, $31,
            $32, $33, $34
        )
        ON CONFLICT (stock_code, recommendation_date, batch_id) DO UPDATE SET
            ai_grade = EXCLUDED.ai_grade,
            ai_confidence = EXCLUDED.ai_confidence,
            qual_score = EXCLUDED.qual_score,
            final_score = EXCLUDED.final_score,
            rank_in_batch = EXCLUDED.rank_in_batch,
            updated_at = NOW()
        """

        for r in results:
            try:
                # 컨센서스 데이터 추출
                consensus = r.get('consensus', {})

                await db.execute(
                    query,
                    r['stock_code'],
                    r.get('stock_name', ''),
                    r.get('batch_id'),
                    # 기본 정량 데이터
                    r.get('pbr'),
                    r.get('per'),
                    r.get('market_cap'),
                    r.get('volume'),
                    r.get('close_price'),
                    # 기술적 지표
                    r.get('rsi_14'),
                    r.get('disparity_20'),
                    r.get('disparity_60'),
                    r.get('ma_20'),
                    r.get('ma_60'),
                    # 수급
                    r.get('pension_net_buy', 0),
                    r.get('institution_net_buy', 0),
                    r.get('foreign_net_buy', 0),
                    # 정량 점수
                    r.get('quant_score'),
                    # 뉴스/리포트
                    len(r.get('news', [])) if isinstance(r.get('news'), list) else 0,
                    r.get('news_sentiment'),
                    len(r.get('reports', [])) if isinstance(r.get('reports'), list) else 0,
                    # 컨센서스
                    consensus.get('avg_target_price'),
                    consensus.get('buy', 0),
                    consensus.get('hold', 0),
                    consensus.get('sell', 0),
                    # AI 분석
                    r.get('ai_grade'),
                    r.get('ai_confidence'),
                    r.get('ai_key_material'),
                    r.get('ai_policy_alignment'),
                    r.get('ai_buy_point'),
                    r.get('ai_risk_factor'),
                    json.dumps(r.get('ai_raw_response', {})),
                    # 최종 점수
                    r.get('qual_score'),
                    r.get('final_score'),
                    r.get('rank_in_batch'),
                )
            except Exception as e:
                logger.error(f"추천 저장 실패 {r['stock_code']}: {e}")

        logger.info(f"smart_recommendations 테이블에 {len(results)}개 저장")

    async def _update_run_history(self, batch_id: str, scored_count: int) -> None:
        """실행 이력 업데이트"""
        query = """
        UPDATE smart_run_history
        SET
            phase3_scored = $2,
            phase3_completed_at = NOW(),
            finished_at = NOW(),
            status = 'completed'
        WHERE batch_id = $1
        """

        try:
            await db.execute(query, batch_id, scored_count)
        except Exception as e:
            logger.debug(f"실행 이력 업데이트 실패: {e}")


class ReportGenerator:
    """추천 리포트 생성기"""

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or settings.report_dir

    async def generate_markdown(
        self,
        results: List[Dict],
        batch_id: str = None
    ) -> str:
        """
        마크다운 형식 리포트 생성

        Returns:
            리포트 파일 경로
        """
        today = datetime.now().strftime('%Y-%m-%d')
        time_str = datetime.now().strftime('%H%M')

        report = f"""# 신규종목추천 리포트

**생성일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**배치 ID**: {batch_id or 'N/A'}
**추천 종목 수**: {len(results)}개

---

## 📊 Top 10 추천 종목

| 순위 | 종목 | AI등급 | 최종점수 | 정량 | 정성 | 핵심 포인트 |
|:---:|:---:|:---:|:---:|:---:|:---:|:---|
"""

        for r in results[:10]:
            report += f"| {r['rank_in_batch']} | {r.get('stock_name', r['stock_code'])} | **{r.get('ai_grade', 'N/A')}** | {r['final_score']:.1f} | {r['quant_score']:.1f} | {r['qual_score']:.1f} | {r.get('ai_key_material', '')[:30]}... |\n"

        report += """
---

## 📈 S/A 등급 종목 상세

"""

        for r in results:
            if r.get('ai_grade') in ['S', 'A']:
                report += f"""### {r.get('stock_name', r['stock_code'])} ({r['stock_code']})

- **AI 등급**: {r.get('ai_grade')} (신뢰도: {r.get('ai_confidence', 0):.0%})
- **최종 점수**: {r['final_score']:.1f}점 (정량 {r['quant_score']:.1f} + 정성 {r['qual_score']:.1f})

**정량 지표**
- PBR: {r.get('pbr', 'N/A')}, PER: {r.get('per', 'N/A')}
- RSI(14): {r.get('rsi_14', 'N/A')}
- 연기금 순매수: {r.get('pension_net_buy', 0):,}원
- 기관 순매수: {r.get('institution_net_buy', 0):,}원

**AI 분석**
- 핵심 재료: {r.get('ai_key_material', 'N/A')}
- 정책 관련: {r.get('ai_policy_alignment', 'N/A')}
- 매수 포인트: {r.get('ai_buy_point', 'N/A')}
- 리스크: {r.get('ai_risk_factor', 'N/A')}

---

"""

        report += f"""
## 📊 등급 분포

| 등급 | 종목 수 | 비율 |
|:---:|:---:|:---:|
"""

        # 등급별 집계
        grade_counts = {}
        for r in results:
            grade = r.get('ai_grade', 'N/A')
            grade_counts[grade] = grade_counts.get(grade, 0) + 1

        for grade in ['S', 'A', 'B', 'C', 'D']:
            count = grade_counts.get(grade, 0)
            pct = (count / len(results) * 100) if results else 0
            report += f"| {grade} | {count} | {pct:.1f}% |\n"

        report += f"""
---

*본 리포트는 AI 분석 결과이며, 투자 판단은 본인 책임입니다.*
"""

        # 파일 저장
        import os
        os.makedirs(self.output_dir, exist_ok=True)
        filepath = f"{self.output_dir}/추천종목_{today}_{time_str}.md"

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"리포트 생성: {filepath}")
        return filepath


async def main():
    """테스트 실행"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    from 신규종목추천.src.phase1 import Phase1AFilter, Phase1BFilter
    from 신규종목추천.src.phase2 import BatchCollector, GeminiBatchAnalyzer

    await db.connect()

    try:
        batch_id = str(uuid.uuid4())

        # Phase 1
        filter_1a = Phase1AFilter()
        candidates_1a = await filter_1a.filter(batch_id)

        filter_1b = Phase1BFilter()
        candidates_1b = await filter_1b.filter(candidates_1a, batch_id)

        # 테스트용 5개만
        test_candidates = candidates_1b[:5]

        # Phase 2
        async with BatchCollector() as collector:
            collected = await collector.collect_all(test_candidates)

        analyzer = GeminiBatchAnalyzer()
        analyzed = await analyzer.analyze_batch(test_candidates, collected)

        # Phase 3
        scorer = ValueScorer()
        results = await scorer.score_all(analyzed, batch_id)

        print(f"\n=== Phase 3 결과: {len(results)}개 종목 ===\n")
        for r in results:
            print(f"{r['rank_in_batch']:2}. {r['stock_code']} {r.get('stock_name', ''):<10} "
                  f"등급:{r.get('ai_grade', 'N/A')} "
                  f"점수:{r['final_score']:.1f} "
                  f"(정량:{r['quant_score']:.1f} 정성:{r['qual_score']:.1f})")

        # 리포트 생성
        reporter = ReportGenerator()
        filepath = await reporter.generate_markdown(results, batch_id)
        print(f"\n리포트 저장: {filepath}")

    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
