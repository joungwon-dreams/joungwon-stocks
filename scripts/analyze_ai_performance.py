"""
AI Performance Analysis Script
보유종목 AI 피드백 성과 분석

사용법:
    python scripts/analyze_ai_performance.py           # 최근 7일
    python scripts/analyze_ai_performance.py --days 30 # 최근 30일
    python scripts/analyze_ai_performance.py --weekly  # 주간 리포트 생성
"""
import asyncio
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Any

import sys
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')
from src.config.database import db


async def get_overall_stats(days: int = 7) -> Dict[str, Any]:
    """전체 AI 판단 통계"""
    query = """
        SELECT
            COUNT(*) as total_decisions,
            SUM(CASE WHEN is_verified THEN 1 ELSE 0 END) as verified_count,
            SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) as correct_count,
            AVG(CASE WHEN is_verified THEN
                CASE WHEN was_correct THEN 1.0 ELSE 0.0 END
            END) * 100 as accuracy,
            AVG(CASE WHEN is_verified THEN next_day_return END) as avg_return,
            AVG(confidence) as avg_confidence
        FROM portfolio_ai_history
        WHERE report_date >= CURRENT_DATE - $1 * INTERVAL '1 day'
    """
    result = await db.fetchrow(query, days)
    return dict(result) if result else {}


async def get_recommendation_breakdown(days: int = 7) -> List[Dict]:
    """추천 유형별 성과"""
    query = """
        SELECT
            recommendation,
            COUNT(*) as count,
            SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) as correct,
            AVG(CASE WHEN is_verified THEN
                CASE WHEN was_correct THEN 1.0 ELSE 0.0 END
            END) * 100 as accuracy,
            AVG(CASE WHEN is_verified THEN next_day_return END) as avg_return
        FROM portfolio_ai_history
        WHERE report_date >= CURRENT_DATE - $1 * INTERVAL '1 day'
          AND is_verified = TRUE
        GROUP BY recommendation
        ORDER BY count DESC
    """
    results = await db.fetch(query, days)
    return [dict(r) for r in results]


async def get_stock_breakdown(days: int = 7) -> List[Dict]:
    """종목별 성과"""
    query = """
        SELECT
            p.stock_code,
            s.stock_name,
            COUNT(*) as decisions,
            SUM(CASE WHEN p.was_correct THEN 1 ELSE 0 END) as correct,
            AVG(CASE WHEN p.is_verified THEN
                CASE WHEN p.was_correct THEN 1.0 ELSE 0.0 END
            END) * 100 as accuracy,
            AVG(CASE WHEN p.is_verified THEN p.next_day_return END) as avg_return
        FROM portfolio_ai_history p
        LEFT JOIN stocks s ON p.stock_code = s.stock_code
        WHERE p.report_date >= CURRENT_DATE - $1 * INTERVAL '1 day'
          AND p.is_verified = TRUE
        GROUP BY p.stock_code, s.stock_name
        ORDER BY decisions DESC
    """
    results = await db.fetch(query, days)
    return [dict(r) for r in results]


async def get_daily_trend(days: int = 7) -> List[Dict]:
    """일별 성과 추이"""
    query = """
        SELECT
            report_date,
            COUNT(*) as decisions,
            SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) as correct,
            AVG(next_day_return) as avg_return
        FROM portfolio_ai_history
        WHERE report_date >= CURRENT_DATE - $1 * INTERVAL '1 day'
          AND is_verified = TRUE
        GROUP BY report_date
        ORDER BY report_date DESC
    """
    results = await db.fetch(query, days)
    return [dict(r) for r in results]


async def get_recent_decisions(limit: int = 10) -> List[Dict]:
    """최근 AI 판단 내역"""
    query = """
        SELECT
            p.report_date,
            p.stock_code,
            s.stock_name,
            p.recommendation,
            p.confidence,
            p.market_price,
            p.next_day_price,
            p.next_day_return,
            p.was_correct,
            p.is_verified
        FROM portfolio_ai_history p
        LEFT JOIN stocks s ON p.stock_code = s.stock_code
        ORDER BY p.report_date DESC, p.created_at DESC
        LIMIT $1
    """
    results = await db.fetch(query, limit)
    return [dict(r) for r in results]


def print_report(days: int, overall: Dict, by_rec: List, by_stock: List,
                 daily: List, recent: List):
    """콘솔 리포트 출력"""
    rec_map = {
        'BUY_MORE': '추가매수',
        'HOLD': '관망',
        'SELL': '매도',
        'CUT_LOSS': '손절'
    }

    print("\n" + "=" * 70)
    print(f"🤖 AI 피드백 성과 분석 리포트 (최근 {days}일)")
    print("=" * 70)

    # 전체 통계
    print("\n📊 전체 통계")
    print("-" * 40)
    total = overall.get('total_decisions', 0) or 0
    verified = overall.get('verified_count', 0) or 0
    correct = overall.get('correct_count', 0) or 0
    accuracy = overall.get('accuracy', 0) or 0
    avg_return = overall.get('avg_return', 0) or 0
    avg_conf = overall.get('avg_confidence', 0) or 0

    print(f"  총 판단 수: {total}건")
    print(f"  검증 완료: {verified}건")
    print(f"  적중: {correct}건")
    print(f"  적중률: {accuracy:.1f}%")
    print(f"  평균 수익률: {avg_return:+.2f}%")
    print(f"  평균 신뢰도: {avg_conf*100:.1f}%")

    # 추천 유형별
    if by_rec:
        print("\n📈 추천 유형별 성과")
        print("-" * 40)
        print(f"  {'유형':<10} {'건수':>6} {'적중':>6} {'적중률':>8} {'평균수익':>10}")
        print(f"  {'-'*10} {'-'*6} {'-'*6} {'-'*8} {'-'*10}")
        for r in by_rec:
            rec_kr = rec_map.get(r['recommendation'], r['recommendation'])
            cnt = r['count'] or 0
            cor = r['correct'] or 0
            acc = r['accuracy'] or 0
            ret = r['avg_return'] or 0
            print(f"  {rec_kr:<10} {cnt:>6} {cor:>6} {acc:>7.1f}% {ret:>+9.2f}%")

    # 종목별
    if by_stock:
        print("\n🏢 종목별 성과")
        print("-" * 40)
        print(f"  {'종목명':<12} {'건수':>6} {'적중':>6} {'적중률':>8} {'평균수익':>10}")
        print(f"  {'-'*12} {'-'*6} {'-'*6} {'-'*8} {'-'*10}")
        for s in by_stock[:10]:  # 상위 10개
            name = (s['stock_name'] or s['stock_code'])[:10]
            cnt = s['decisions'] or 0
            cor = s['correct'] or 0
            acc = s['accuracy'] or 0
            ret = s['avg_return'] or 0
            print(f"  {name:<12} {cnt:>6} {cor:>6} {acc:>7.1f}% {ret:>+9.2f}%")

    # 일별 추이
    if daily:
        print("\n📅 일별 추이")
        print("-" * 40)
        print(f"  {'날짜':<12} {'건수':>6} {'적중':>6} {'평균수익':>10}")
        print(f"  {'-'*12} {'-'*6} {'-'*6} {'-'*10}")
        for d in daily[:7]:  # 최근 7일
            date = d['report_date'].strftime('%Y-%m-%d') if d['report_date'] else '-'
            cnt = d['decisions'] or 0
            cor = d['correct'] or 0
            ret = d['avg_return'] or 0
            print(f"  {date:<12} {cnt:>6} {cor:>6} {ret:>+9.2f}%")

    # 최근 판단
    if recent:
        print("\n🕐 최근 AI 판단")
        print("-" * 40)
        for r in recent[:5]:
            date = r['report_date'].strftime('%m/%d') if r['report_date'] else '-'
            name = (r['stock_name'] or r['stock_code'])[:8]
            rec = rec_map.get(r['recommendation'], '?')[:4]
            conf = (r['confidence'] or 0) * 100
            ret = r['next_day_return'] or 0
            result = '✅' if r['was_correct'] else '❌' if r['is_verified'] else '⏳'
            print(f"  {date} {name:<8} {rec:<4} 신뢰:{conf:>3.0f}% 결과:{ret:>+5.2f}% {result}")

    print("\n" + "=" * 70)
    print(f"생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")


async def generate_weekly_report() -> str:
    """주간 리포트 마크다운 생성"""
    days = 7
    overall = await get_overall_stats(days)
    by_rec = await get_recommendation_breakdown(days)
    by_stock = await get_stock_breakdown(days)
    daily = await get_daily_trend(days)

    rec_map = {
        'BUY_MORE': '추가매수',
        'HOLD': '관망',
        'SELL': '매도',
        'CUT_LOSS': '손절'
    }

    now = datetime.now()
    week_start = (now - timedelta(days=6)).strftime('%Y-%m-%d')
    week_end = now.strftime('%Y-%m-%d')

    md = f"""---
created: {now.strftime('%Y-%m-%d %H:%M:%S')}
tags: [report, ai-performance, weekly]
---

# AI 피드백 주간 성과 리포트

**기간**: {week_start} ~ {week_end}

## 전체 요약

| 지표 | 값 |
|:---|---:|
| 총 판단 수 | {overall.get('total_decisions', 0) or 0}건 |
| 검증 완료 | {overall.get('verified_count', 0) or 0}건 |
| 적중 | {overall.get('correct_count', 0) or 0}건 |
| **적중률** | **{overall.get('accuracy', 0) or 0:.1f}%** |
| 평균 수익률 | {overall.get('avg_return', 0) or 0:+.2f}% |
| 평균 신뢰도 | {(overall.get('avg_confidence', 0) or 0)*100:.1f}% |

## 추천 유형별 성과

| 유형 | 건수 | 적중 | 적중률 | 평균수익 |
|:---|---:|---:|---:|---:|
"""

    for r in by_rec:
        rec_kr = rec_map.get(r['recommendation'], r['recommendation'])
        md += f"| {rec_kr} | {r['count'] or 0} | {r['correct'] or 0} | {r['accuracy'] or 0:.1f}% | {r['avg_return'] or 0:+.2f}% |\n"

    md += """
## 종목별 성과

| 종목 | 건수 | 적중 | 적중률 | 평균수익 |
|:---|---:|---:|---:|---:|
"""

    for s in by_stock[:10]:
        name = (s['stock_name'] or s['stock_code'])[:10]
        md += f"| {name} | {s['decisions'] or 0} | {s['correct'] or 0} | {s['accuracy'] or 0:.1f}% | {s['avg_return'] or 0:+.2f}% |\n"

    md += """
## 일별 추이

| 날짜 | 건수 | 적중 | 평균수익 |
|:---|---:|---:|---:|
"""

    for d in daily:
        date = d['report_date'].strftime('%Y-%m-%d') if d['report_date'] else '-'
        md += f"| {date} | {d['decisions'] or 0} | {d['correct'] or 0} | {d['avg_return'] or 0:+.2f}% |\n"

    md += f"""
---

*생성 시각: {now.strftime('%Y-%m-%d %H:%M:%S')}*
"""

    return md


async def main():
    parser = argparse.ArgumentParser(description='AI Performance Analysis')
    parser.add_argument('--days', type=int, default=7, help='분석 기간 (일)')
    parser.add_argument('--weekly', action='store_true', help='주간 리포트 생성')
    args = parser.parse_args()

    await db.connect()
    try:
        if args.weekly:
            # 주간 리포트 마크다운 생성
            md_content = await generate_weekly_report()

            # 파일 저장
            from pathlib import Path
            report_dir = Path('/Users/wonny/Dev/joungwon.stocks/reports/ai_performance')
            report_dir.mkdir(parents=True, exist_ok=True)

            filename = f"weekly_{datetime.now().strftime('%Y%m%d')}.md"
            filepath = report_dir / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(md_content)

            print(f"✅ 주간 리포트 생성: {filepath}")
            print(md_content)
        else:
            # 콘솔 리포트
            overall = await get_overall_stats(args.days)
            by_rec = await get_recommendation_breakdown(args.days)
            by_stock = await get_stock_breakdown(args.days)
            daily = await get_daily_trend(args.days)
            recent = await get_recent_decisions(10)

            print_report(args.days, overall, by_rec, by_stock, daily, recent)

    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
