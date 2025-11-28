#!/usr/bin/env python3
"""
Daily Recommendation Tracking Script (Phase 9.5)
활성 추천 종목의 일일 가격 추적

Usage:
    python scripts/track_recommendations.py              # 오늘 추적
    python scripts/track_recommendations.py --date 20251128  # 특정 날짜

Cron: 매일 18:00 실행 (장 마감 후)
    0 18 * * * python scripts/track_recommendations.py
"""
import asyncio
import argparse
import sys
from datetime import datetime
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.aegis.discovery import RecommendationTracker


async def track_daily(target_date: str = None):
    """일일 추적 실행"""
    print("=" * 60)
    print("📊 신규종목 추천 추적 (Phase 9.5)")
    print(f"   시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   대상일: {target_date or '오늘'}")
    print("=" * 60)

    tracker = RecommendationTracker()

    try:
        # 1. 일일 가격 추적
        tracked_count = await tracker.track_daily_prices(target_date)

        # 2. 성과 요약 출력
        summary = await tracker.get_performance_summary(days=14)

        print("\n📈 추천 성과 요약 (최근 2주)")
        print("-" * 40)
        print(f"   총 추천: {summary.total_recommendations}건")
        print(f"   추적 완료: {summary.completed}건")
        print(f"   활성 추적: {summary.active}건")
        print(f"   평균 수익률: {summary.avg_return:.1f}%")
        print(f"   승률: {summary.win_rate:.0f}%")
        print(f"   최고 수익: {summary.best_return:.1f}%")
        print(f"   최저 수익: {summary.worst_return:.1f}%")
        print("-" * 40)

        # 3. 활성 추천 목록
        active = await tracker.get_active_recommendations()
        if active:
            print("\n📋 활성 추천 종목")
            print("-" * 60)
            print(f"{'종목명':<14} {'추천가':>10} {'현재가':>10} {'수익률':>8} {'D+':>4}")
            print("-" * 60)
            for rec in active:
                current = rec.get('current_price', 0) or 0
                ret = rec.get('cumulative_return', 0) or 0
                day = rec.get('day_number', 0) or 0
                ret_str = f"+{ret:.1f}%" if ret >= 0 else f"{ret:.1f}%"
                print(f"{rec['stock_name']:<14} {rec['recommended_price']:>10,} {current:>10,} {ret_str:>8} {day:>4}")
            print("-" * 60)

    except Exception as e:
        print(f"❌ 추적 오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await tracker.disconnect()

    print("\n" + "=" * 60)
    print("✅ 추적 완료")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='Daily Recommendation Tracking (Phase 9.5)')
    parser.add_argument('--date', type=str, help='추적 날짜 (YYYYMMDD)')

    args = parser.parse_args()
    asyncio.run(track_daily(args.date))


if __name__ == "__main__":
    main()
