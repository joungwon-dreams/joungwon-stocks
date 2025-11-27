#!/usr/bin/env python3
"""
Phase 4 실행 스크립트: 수익률 추적, AI 회고, 일일 추적

사용법:
    # 전체 실행 (일일 추적 + 수익률 추적 + AI 회고 + 리포트)
    python 신규종목추천/run_phase4.py

    # 일일 주가 추적만
    python 신규종목추천/run_phase4.py --daily

    # 수익률 추적만 (7/14/30일)
    python 신규종목추천/run_phase4.py --track-only

    # AI 회고만
    python 신규종목추천/run_phase4.py --retrospective-only

    # 추적 대시보드 생성
    python 신규종목추천/run_phase4.py --dashboard

    # PDF 리포트 생성
    python 신규종목추천/run_phase4.py --pdf
"""
import asyncio
import argparse
import logging
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, '.')
from 신규종목추천.src.utils.database import db
from 신규종목추천.src.phase4.profit_tracker import ProfitTracker
from 신규종목추천.src.phase4.retrospective import AIRetrospective
from 신규종목추천.src.reports.daily_tracker import DailyPriceTracker, create_tracking_table
from 신규종목추천.src.reports.pdf_generator import NewStockPDFGenerator


async def run_daily_tracking():
    """일일 주가 추적 실행"""
    # 테이블 생성 확인
    await create_tracking_table()

    tracker = DailyPriceTracker()
    result = await tracker.record_daily_prices()
    return result


async def run_tracking():
    """수익률 추적 실행 (7/14/30일)"""
    tracker = ProfitTracker()
    return await tracker.track_all()


async def run_retrospective(limit: int = 10):
    """AI 회고 분석 실행"""
    retrospective = AIRetrospective()
    return await retrospective.analyze_failures(limit=limit)


async def generate_dashboard():
    """추적 대시보드 마크다운 생성"""
    tracker = DailyPriceTracker()
    report_path = await tracker.save_tracking_report()
    return report_path


async def generate_pdf_report():
    """PDF 리포트 생성"""
    generator = NewStockPDFGenerator()
    pdf_path = await generator.generate_daily_report()
    return pdf_path


async def generate_full_reports():
    """전체 리포트 생성 (성과 + 학습 + 대시보드)"""
    # 1. 성과 리포트
    tracker = ProfitTracker()
    performance_report = await tracker.generate_report()

    # 2. 학습 리포트
    retrospective = AIRetrospective()
    learning_report = await retrospective.generate_learning_report()

    # 3. 통합 리포트 저장
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M')
    report_dir = Path('reports/new_stock/archive')
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f'성과분석_{timestamp}.md'

    full_report = f"""# 신규종목추천 성과 분석 리포트

**생성일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

{performance_report}

---

{learning_report}

---

## 📋 분석 체크리스트

### 놓친 리스크 분석
- [ ] 실패 종목의 공통점은 무엇인가?
- [ ] AI가 예측하지 못한 악재는 무엇인가?
- [ ] 외부 요인 (시장 급락, 섹터 악재) vs 내부 요인 (실적, 경영)

### 실제 원인 파악
- [ ] 뉴스 이벤트 확인
- [ ] 경쟁사 동향 확인
- [ ] 업종 전체 흐름 확인

### 학습 교훈
- [ ] 향후 유사 종목 선별 시 적용할 기준
- [ ] 리스크 평가 강화 포인트
- [ ] AI 프롬프트 개선 사항

### 개선 제안
- [ ] Phase 1 필터 조건 조정
- [ ] Phase 2 AI 평가 기준 개선
- [ ] 추적 기간/기준 조정

---

*이 리포트는 자동 생성되었습니다.*
"""

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(full_report)

    print(f"📊 성과 분석 리포트: {report_path}")

    # 4. 대시보드 생성
    dashboard_path = await generate_dashboard()

    return str(report_path), dashboard_path


async def main(args):
    """메인 실행 함수"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    await db.connect()

    try:
        if args.daily:
            # 일일 주가 추적만
            print("\n" + "="*60)
            print("📈 일일 주가 추적")
            print("="*60)
            results = await run_daily_tracking()
            print(f"\n✅ 기록 완료: {results['recorded']}/{results['total']}건")

        elif args.track_only:
            # 수익률 추적만 (7/14/30일)
            print("\n" + "="*60)
            print("📈 Phase 4A: 수익률 추적 (7/14/30일)")
            print("="*60)
            results = await run_tracking()
            print(f"\n✅ 추적 완료: {results['total_tracked']}건")

        elif args.retrospective_only:
            # AI 회고만
            print("\n" + "="*60)
            print("🔍 Phase 4B: AI 회고 분석")
            print("="*60)
            results = await run_retrospective(limit=args.limit)
            print(f"\n✅ 회고 완료: {results['analyzed_count']}건")

        elif args.dashboard:
            # 대시보드만
            print("\n" + "="*60)
            print("📊 추적 대시보드 생성")
            print("="*60)
            dashboard_path = await generate_dashboard()
            print(f"\n✅ 대시보드 생성: {dashboard_path}")

        elif args.pdf:
            # PDF만
            print("\n" + "="*60)
            print("📄 PDF 리포트 생성")
            print("="*60)
            pdf_path = await generate_pdf_report()
            print(f"\n✅ PDF 생성: {pdf_path}")

        elif args.report:
            # 전체 리포트
            print("\n" + "="*60)
            print("📊 전체 리포트 생성")
            print("="*60)
            report_path, dashboard_path = await generate_full_reports()

        else:
            # 전체 실행
            print("\n" + "="*60)
            print("🚀 Phase 4: 성과 추적 시스템 실행")
            print("="*60)

            # 1. 일일 주가 추적
            print("\n📈 [Step 1] 일일 주가 추적 중...")
            daily_results = await run_daily_tracking()
            print(f"   → {daily_results['recorded']}/{daily_results['total']}건 기록")

            # 2. 수익률 추적 (7/14/30일)
            print("\n📈 [Step 2] 기간별 수익률 추적 중...")
            track_results = await run_tracking()
            print(f"   → {track_results['total_tracked']}건 추적 완료")

            # 3. AI 회고
            print("\n🔍 [Step 3] AI 회고 분석 중...")
            retro_results = await run_retrospective(limit=args.limit)
            print(f"   → {retro_results['analyzed_count']}건 회고 완료")

            # 4. 대시보드 생성
            print("\n📊 [Step 4] 대시보드 생성 중...")
            dashboard_path = await generate_dashboard()

            # 5. PDF 리포트
            print("\n📄 [Step 5] PDF 리포트 생성 중...")
            try:
                pdf_path = await generate_pdf_report()
            except Exception as e:
                print(f"   ⚠️ PDF 생성 실패: {e}")
                pdf_path = "생성 실패"

            # 6. 성과 분석 리포트
            print("\n📊 [Step 6] 성과 분석 리포트 생성 중...")
            report_path, _ = await generate_full_reports()

            # 결과 요약
            print("\n" + "="*60)
            print("✅ Phase 4 완료!")
            print("="*60)
            print(f"\n📁 생성된 파일:")
            print(f"  - 대시보드: {dashboard_path}")
            print(f"  - PDF 리포트: {pdf_path}")
            print(f"  - 성과 분석: {report_path}")

            # 성과 요약 출력
            if track_results.get('summary'):
                print("\n📊 기간별 성과 요약:")
                for period, stats in track_results['summary'].items():
                    print(f"  {period}: {stats['total']}건, "
                          f"평균 {stats['avg_return']:+.2f}%, "
                          f"승률 {stats['win_rate']:.1f}%")

            # AI 회고 요약
            if retro_results.get('common_lessons'):
                print("\n🎓 AI 학습 교훈:")
                for lesson in retro_results['common_lessons'][:3]:
                    print(f"  - {lesson}")

    finally:
        await db.disconnect()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Phase 4: 성과 추적 및 AI 회고')
    parser.add_argument('--daily', action='store_true',
                        help='일일 주가 추적만 실행')
    parser.add_argument('--track-only', action='store_true',
                        help='수익률 추적만 실행 (7/14/30일)')
    parser.add_argument('--retrospective-only', action='store_true',
                        help='AI 회고만 실행')
    parser.add_argument('--dashboard', action='store_true',
                        help='추적 대시보드만 생성')
    parser.add_argument('--pdf', action='store_true',
                        help='PDF 리포트만 생성')
    parser.add_argument('--report', action='store_true',
                        help='전체 리포트만 생성')
    parser.add_argument('--limit', type=int, default=10,
                        help='AI 회고 분석 최대 건수 (기본: 10)')

    args = parser.parse_args()
    asyncio.run(main(args))
