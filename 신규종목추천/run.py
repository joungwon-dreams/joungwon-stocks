#!/usr/bin/env python3
"""
신규종목추천 메인 실행 스크립트

전체 파이프라인 실행:
    python 신규종목추천/run.py

피드백 모드:
    python 신규종목추천/run.py --feedback reanalyze --code 005930
    python 신규종목추천/run.py --feedback refresh
    python 신규종목추천/run.py --feedback filter --pbr_max 0.8

옵션:
    --test: 테스트 모드 (5개 종목만)
    --no-ai: AI 분석 스킵 (정량만)
    --report: 마크다운 리포트 생성
"""
import asyncio
import argparse
import logging
from datetime import datetime
import uuid
import os
import sys

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from 신규종목추천.config.settings import settings
from 신규종목추천.src.utils.database import db
from 신규종목추천.src.phase1 import Phase1AFilter, Phase1BFilter
from 신규종목추천.src.phase2 import BatchCollector, GeminiBatchAnalyzer
from 신규종목추천.src.phase3 import ValueScorer, ReportGenerator
from 신규종목추천.src.phase4 import IncrementalRunner

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            f"{settings.log_dir}/run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            encoding='utf-8'
        )
    ]
)
logger = logging.getLogger(__name__)


class SmartValueFinder:
    """
    신규종목추천 메인 파이프라인

    Phase 1A: SQL 기반 1차 필터 (~1초)
    Phase 1B: 기술적 지표 필터 (~30초)
    Phase 2A: 배치 데이터 수집 (~5분)
    Phase 2B: Gemini 배치 분석 (~2.5분)
    Phase 3: 스코어링 & 저장 (~10초)
    """

    def __init__(self, test_mode: bool = False, skip_ai: bool = False):
        self.test_mode = test_mode
        self.skip_ai = skip_ai

        # Phase 컴포넌트
        self.filter_1a = Phase1AFilter()
        self.filter_1b = Phase1BFilter()
        self.analyzer = GeminiBatchAnalyzer()
        self.scorer = ValueScorer()
        self.reporter = ReportGenerator()

    async def run(self) -> dict:
        """
        전체 파이프라인 실행

        Returns:
            실행 결과 딕셔너리
        """
        batch_id = str(uuid.uuid4())
        start_time = datetime.now()

        logger.info("=" * 60)
        logger.info("신규종목추천 파이프라인 시작")
        logger.info(f"Batch ID: {batch_id}")
        logger.info(f"테스트 모드: {self.test_mode}")
        logger.info(f"AI 스킵: {self.skip_ai}")
        logger.info("=" * 60)

        await db.connect()

        try:
            # 실행 이력 시작
            await self._start_run_history(batch_id)

            # ========== Phase 1A: SQL 기반 1차 필터 ==========
            phase1a_start = datetime.now()
            logger.info("\n[Phase 1A] SQL 기반 1차 필터 시작...")

            candidates_1a = await self.filter_1a.filter(batch_id)

            phase1a_elapsed = (datetime.now() - phase1a_start).total_seconds()
            logger.info(f"[Phase 1A] 완료: {len(candidates_1a)}개 종목 ({phase1a_elapsed:.2f}초)")

            if not candidates_1a:
                logger.warning("Phase 1A 필터 결과 없음 - 종료")
                return {'success': False, 'error': 'No candidates from Phase 1A'}

            # ========== Phase 1B: 기술적 지표 필터 ==========
            phase1b_start = datetime.now()
            logger.info("\n[Phase 1B] 기술적 지표 필터 시작...")

            candidates_1b = await self.filter_1b.filter(candidates_1a, batch_id)

            # 테스트 모드: 5개만
            if self.test_mode:
                candidates_1b = candidates_1b[:5]
                logger.info(f"[테스트 모드] {len(candidates_1b)}개로 제한")

            phase1b_elapsed = (datetime.now() - phase1b_start).total_seconds()
            logger.info(f"[Phase 1B] 완료: {len(candidates_1b)}개 종목 ({phase1b_elapsed:.2f}초)")

            await self._update_run_history(batch_id, 'phase1', {
                'phase1a_input': len(candidates_1a) if candidates_1a else 0,
                'phase1a_output': len(candidates_1a),
                'phase1b_output': len(candidates_1b),
            })

            if not candidates_1b:
                logger.warning("Phase 1B 필터 결과 없음 - 종료")
                return {'success': False, 'error': 'No candidates from Phase 1B'}

            # ========== Phase 2A: 배치 데이터 수집 ==========
            phase2a_start = datetime.now()
            logger.info(f"\n[Phase 2A] {len(candidates_1b)}개 종목 데이터 수집 시작...")

            async with BatchCollector() as collector:
                collected = await collector.collect_all(candidates_1b)

            phase2a_elapsed = (datetime.now() - phase2a_start).total_seconds()
            logger.info(f"[Phase 2A] 완료: {len(collected)}개 종목 수집 ({phase2a_elapsed:.1f}초)")

            # ========== Phase 2B: Gemini 배치 분석 ==========
            if self.skip_ai:
                logger.info("\n[Phase 2B] AI 분석 스킵 - 기본 등급 할당")
                analyzed = self.analyzer._assign_default_grades(candidates_1b)
            else:
                phase2b_start = datetime.now()
                logger.info(f"\n[Phase 2B] {len(candidates_1b)}개 종목 AI 분석 시작...")

                analyzed = await self.analyzer.analyze_batch(candidates_1b, collected)

                phase2b_elapsed = (datetime.now() - phase2b_start).total_seconds()
                logger.info(f"[Phase 2B] 완료: {len(analyzed)}개 종목 분석 ({phase2b_elapsed:.1f}초)")

            await self._update_run_history(batch_id, 'phase2', {
                'phase2a_collected': len(collected),
                'phase2b_analyzed': len(analyzed),
            })

            # ========== Phase 3: 스코어링 & 저장 ==========
            phase3_start = datetime.now()
            logger.info(f"\n[Phase 3] {len(analyzed)}개 종목 스코어링 시작...")

            results = await self.scorer.score_all(analyzed, batch_id)

            phase3_elapsed = (datetime.now() - phase3_start).total_seconds()
            logger.info(f"[Phase 3] 완료: {len(results)}개 종목 저장 ({phase3_elapsed:.2f}초)")

            # ========== 리포트 생성 ==========
            report_path = await self.reporter.generate_markdown(results, batch_id)

            # ========== 결과 출력 ==========
            total_elapsed = (datetime.now() - start_time).total_seconds()

            logger.info("\n" + "=" * 60)
            logger.info("신규종목추천 파이프라인 완료")
            logger.info(f"총 소요 시간: {total_elapsed:.1f}초 ({total_elapsed/60:.1f}분)")
            logger.info(f"최종 추천 종목: {len(results)}개")
            logger.info(f"리포트: {report_path}")
            logger.info("=" * 60)

            # 상위 10개 출력
            self._print_top_picks(results[:10])

            # 실행 이력 완료
            await self._update_run_history(batch_id, 'complete', {
                'phase3_scored': len(results),
            })

            return {
                'success': True,
                'batch_id': batch_id,
                'total_candidates': len(results),
                'elapsed_seconds': total_elapsed,
                'report_path': report_path,
                'top_picks': results[:10],
            }

        except Exception as e:
            logger.error(f"파이프라인 실패: {e}", exc_info=True)
            await self._update_run_history(batch_id, 'failed', {'error': str(e)})
            return {'success': False, 'error': str(e)}

        finally:
            await db.disconnect()

    def _print_top_picks(self, picks: list):
        """상위 종목 출력"""
        print("\n" + "=" * 70)
        print("📊 Top 10 추천 종목")
        print("=" * 70)
        print(f"{'순위':^4} {'종목':^12} {'등급':^4} {'점수':^6} {'정량':^6} {'정성':^6} {'핵심 포인트':<30}")
        print("-" * 70)

        for r in picks:
            name = r.get('stock_name', r['stock_code'])[:10]
            print(f"{r['rank_in_batch']:^4} {name:<12} {r.get('ai_grade', 'N/A'):^4} "
                  f"{r['final_score']:>6.1f} {r['quant_score']:>6.1f} {r['qual_score']:>6.1f} "
                  f"{(r.get('ai_key_material', '') or '')[:28]}")

        print("=" * 70)

    async def _start_run_history(self, batch_id: str):
        """실행 이력 시작"""
        query = """
        INSERT INTO smart_run_history (batch_id, run_type, status)
        VALUES ($1, $2, 'running')
        """
        run_type = 'test' if self.test_mode else 'full'
        await db.execute(query, batch_id, run_type)

    async def _update_run_history(self, batch_id: str, phase: str, data: dict):
        """실행 이력 업데이트"""
        if phase == 'phase1':
            query = """
            UPDATE smart_run_history SET
                phase1a_input = $2,
                phase1a_output = $3,
                phase1b_output = $4,
                phase1_completed_at = NOW()
            WHERE batch_id = $1
            """
            await db.execute(query, batch_id,
                           data.get('phase1a_input'),
                           data.get('phase1a_output'),
                           data.get('phase1b_output'))

        elif phase == 'phase2':
            query = """
            UPDATE smart_run_history SET
                phase2a_collected = $2,
                phase2b_analyzed = $3,
                phase2_completed_at = NOW()
            WHERE batch_id = $1
            """
            await db.execute(query, batch_id,
                           data.get('phase2a_collected'),
                           data.get('phase2b_analyzed'))

        elif phase == 'complete':
            query = """
            UPDATE smart_run_history SET
                phase3_scored = $2,
                phase3_completed_at = NOW(),
                finished_at = NOW(),
                status = 'completed'
            WHERE batch_id = $1
            """
            await db.execute(query, batch_id, data.get('phase3_scored'))

        elif phase == 'failed':
            query = """
            UPDATE smart_run_history SET
                finished_at = NOW(),
                status = 'failed',
                error_message = $2
            WHERE batch_id = $1
            """
            await db.execute(query, batch_id, data.get('error'))


async def run_feedback(args):
    """피드백 모드 실행"""
    await db.connect()

    try:
        runner = IncrementalRunner()

        if args.feedback == 'reanalyze':
            if not args.code:
                print("오류: --code 옵션이 필요합니다")
                return

            result = await runner.handle_feedback('reanalyze_stock', {'code': args.code})
            print(f"\n재분석 결과: {result}")

        elif args.feedback == 'refresh':
            codes = args.code.split(',') if args.code else None
            result = await runner.handle_feedback('refresh_data', {'codes': codes})
            print(f"\n새로고침 결과: {result.get('refreshed_count', 0)}개 종목")

        elif args.feedback == 'filter':
            new_filters = {}
            if args.pbr_max:
                new_filters['pbr_max'] = float(args.pbr_max)
            if args.per_max:
                new_filters['per_max'] = float(args.per_max)
            if args.rsi_min:
                new_filters['rsi_min'] = float(args.rsi_min)
            if args.rsi_max:
                new_filters['rsi_max'] = float(args.rsi_max)

            result = await runner.handle_feedback('change_filter', {'new_filters': new_filters})
            print(f"\n필터 변경 결과: {result.get('total_candidates', 0)}개 종목")

        elif args.feedback == 'exclude':
            if not args.code:
                print("오류: --code 옵션이 필요합니다")
                return

            result = await runner.handle_feedback('exclude_stock', {
                'code': args.code,
                'reason': args.reason or '사용자 요청'
            })
            print(f"\n제외 결과: {result}")

    finally:
        await db.disconnect()


def main():
    """메인 진입점"""
    parser = argparse.ArgumentParser(description='신규종목추천 시스템')

    # 기본 옵션
    parser.add_argument('--test', action='store_true', help='테스트 모드 (5개 종목)')
    parser.add_argument('--no-ai', action='store_true', help='AI 분석 스킵')

    # 피드백 옵션
    parser.add_argument('--feedback', choices=['reanalyze', 'refresh', 'filter', 'exclude'],
                       help='피드백 모드')
    parser.add_argument('--code', help='종목 코드 (피드백용)')
    parser.add_argument('--reason', help='제외 사유')

    # 필터 변경 옵션
    parser.add_argument('--pbr_max', help='PBR 최대값')
    parser.add_argument('--per_max', help='PER 최대값')
    parser.add_argument('--rsi_min', help='RSI 최소값')
    parser.add_argument('--rsi_max', help='RSI 최대값')

    args = parser.parse_args()

    # 로그 디렉토리 생성
    os.makedirs(settings.log_dir, exist_ok=True)
    os.makedirs(settings.report_dir, exist_ok=True)

    if args.feedback:
        # 피드백 모드
        asyncio.run(run_feedback(args))
    else:
        # 전체 실행
        finder = SmartValueFinder(test_mode=args.test, skip_ai=args.no_ai)
        result = asyncio.run(finder.run())

        if result.get('success'):
            print(f"\n✅ 완료! 리포트: {result.get('report_path')}")
        else:
            print(f"\n❌ 실패: {result.get('error')}")
            sys.exit(1)


if __name__ == '__main__':
    main()
