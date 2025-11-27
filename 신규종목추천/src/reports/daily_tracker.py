"""
일일 주가 추적기

추천 종목의 현재가를 매일 기록하고 추적합니다.
"""
import asyncio
import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')
from 신규종목추천.src.utils.database import db


class DailyPriceTracker:
    """일일 주가 추적기"""

    def __init__(self):
        self.tracking_dir = Path('/Users/wonny/Dev/joungwon.stocks/reports/new_stock/tracking')
        self.tracking_dir.mkdir(parents=True, exist_ok=True)

    async def record_daily_prices(self, batch_id: str = None, grades: List[str] = None) -> Dict:
        """
        추천 종목의 현재가를 기록 (S/A 등급만)

        Args:
            batch_id: 특정 배치 ID (None이면 최근 30일 내 모든 배치)
            grades: 추적할 등급 리스트 (기본: ['S', 'A'])

        Returns:
            기록 결과
        """
        if grades is None:
            grades = ['S', 'A']  # 기본: S/A 등급만

        # 추적 대상 종목 조회 (S/A 등급만)
        if batch_id:
            recommendations = await self._get_batch_recommendations(batch_id, grades)
        else:
            recommendations = await self._get_recent_recommendations(days=30, grades=grades)

        if not recommendations:
            return {'recorded': 0, 'message': '추적할 종목이 없습니다'}

        # 현재가 조회 및 기록
        recorded = 0
        today = date.today()

        for rec in recommendations:
            stock_code = rec['stock_code']

            # daily_ohlcv에서 최신 가격 조회
            current_price = await self._get_current_price(stock_code)

            if current_price:
                # smart_price_tracking 테이블에 기록
                await self._record_price(
                    recommendation_id=rec['id'],
                    stock_code=stock_code,
                    stock_name=rec['stock_name'],
                    rec_date=rec['recommendation_date'],
                    rec_price=rec['close_price'],
                    rec_grade=rec['ai_grade'],
                    track_date=today,
                    track_price=current_price
                )
                recorded += 1

        return {
            'recorded': recorded,
            'total': len(recommendations),
            'date': str(today)
        }

    async def _get_batch_recommendations(self, batch_id: str, grades: List[str] = None) -> List[Dict]:
        """특정 배치의 추천 종목 조회 (등급 필터링)"""
        if grades is None:
            grades = ['S', 'A']

        query = """
        SELECT id, stock_code, stock_name, recommendation_date,
               close_price, ai_grade, final_score
        FROM smart_recommendations
        WHERE batch_id = $1
        AND ai_grade = ANY($2)
        ORDER BY
            CASE ai_grade WHEN 'S' THEN 1 WHEN 'A' THEN 2 ELSE 3 END,
            final_score DESC
        """
        return await db.fetch(query, batch_id, grades)

    async def _get_recent_recommendations(self, days: int = 30, grades: List[str] = None) -> List[Dict]:
        """최근 N일 내 추천 종목 조회 (등급 필터링)"""
        if grades is None:
            grades = ['S', 'A']

        cutoff_date = date.today() - timedelta(days=days)
        query = """
        SELECT id, stock_code, stock_name, recommendation_date,
               close_price, ai_grade, final_score, batch_id
        FROM smart_recommendations
        WHERE recommendation_date >= $1
        AND ai_grade = ANY($2)
        ORDER BY recommendation_date DESC,
            CASE ai_grade WHEN 'S' THEN 1 WHEN 'A' THEN 2 ELSE 3 END,
            final_score DESC
        """
        return await db.fetch(query, cutoff_date, grades)

    async def _get_current_price(self, stock_code: str) -> Optional[int]:
        """종목의 최신 가격 조회"""
        query = """
        SELECT close
        FROM daily_ohlcv
        WHERE stock_code = $1
        ORDER BY date DESC
        LIMIT 1
        """
        result = await db.fetchrow(query, stock_code)
        return result['close'] if result else None

    async def _record_price(self, recommendation_id: int, stock_code: str,
                           stock_name: str, rec_date: date, rec_price: int,
                           rec_grade: str, track_date: date, track_price: int):
        """가격 기록 저장"""
        # 수익률 계산
        return_rate = ((track_price - rec_price) / rec_price) * 100 if rec_price > 0 else 0
        days_held = (track_date - rec_date).days

        # UPSERT: 같은 날짜에 이미 기록이 있으면 업데이트
        query = """
        INSERT INTO smart_price_tracking
            (recommendation_id, stock_code, stock_name, rec_date, rec_price,
             rec_grade, track_date, track_price, return_rate, days_held)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        ON CONFLICT (recommendation_id, track_date)
        DO UPDATE SET
            track_price = EXCLUDED.track_price,
            return_rate = EXCLUDED.return_rate,
            updated_at = NOW()
        """
        await db.execute(query, recommendation_id, stock_code, stock_name,
                        rec_date, rec_price, rec_grade, track_date,
                        track_price, return_rate, days_held)

    async def get_tracking_summary(self, batch_id: str = None) -> Dict:
        """
        추적 현황 요약

        Returns:
            등급별/기간별 수익률 요약
        """
        if batch_id:
            condition = "sr.batch_id = $1"
            params = [batch_id]
        else:
            condition = "sr.recommendation_date >= $1"
            params = [date.today() - timedelta(days=30)]

        query = f"""
        WITH latest_tracking AS (
            SELECT DISTINCT ON (recommendation_id)
                recommendation_id, track_price, return_rate, days_held, track_date
            FROM smart_price_tracking
            ORDER BY recommendation_id, track_date DESC
        )
        SELECT
            sr.ai_grade,
            COUNT(*) as count,
            AVG(lt.return_rate) as avg_return,
            MIN(lt.return_rate) as min_return,
            MAX(lt.return_rate) as max_return,
            AVG(lt.days_held) as avg_days_held,
            COUNT(CASE WHEN lt.return_rate > 0 THEN 1 END) as winners,
            COUNT(CASE WHEN lt.return_rate <= 0 THEN 1 END) as losers
        FROM smart_recommendations sr
        JOIN latest_tracking lt ON sr.id = lt.recommendation_id
        WHERE {condition}
        GROUP BY sr.ai_grade
        ORDER BY sr.ai_grade
        """
        return await db.fetch(query, *params)

    async def get_stock_tracking_history(self, stock_code: str) -> List[Dict]:
        """특정 종목의 추적 이력"""
        query = """
        SELECT
            spt.track_date,
            spt.track_price,
            spt.return_rate,
            spt.days_held,
            sr.recommendation_date,
            sr.close_price as rec_price,
            sr.ai_grade
        FROM smart_price_tracking spt
        JOIN smart_recommendations sr ON spt.recommendation_id = sr.id
        WHERE spt.stock_code = $1
        ORDER BY spt.track_date DESC
        """
        return await db.fetch(query, stock_code)

    async def get_daily_price_history(self, recommendation_id: int) -> List[Dict]:
        """특정 추천의 일별 가격 이력"""
        query = """
        SELECT track_date, track_price, return_rate, days_held
        FROM smart_price_tracking
        WHERE recommendation_id = $1
        ORDER BY track_date ASC
        """
        return await db.fetch(query, recommendation_id)

    async def generate_tracking_markdown(self, batch_id: str = None, grades: List[str] = None) -> str:
        """
        추적 현황 마크다운 리포트 생성 (S/A 등급만 + 핵심재료 전체 표시 + 일별 추적)

        Args:
            batch_id: 배치 ID
            grades: 포함할 등급 리스트 (기본: ['S', 'A'])

        Returns:
            마크다운 형식의 리포트
        """
        if grades is None:
            grades = ['S', 'A']

        # 최신 배치 ID 조회
        if not batch_id:
            query = """
            SELECT DISTINCT batch_id, recommendation_date
            FROM smart_recommendations
            ORDER BY recommendation_date DESC, batch_id DESC
            LIMIT 1
            """
            result = await db.fetchrow(query)
            if result:
                batch_id = result['batch_id']

        if not batch_id:
            return "# 추적 데이터 없음\n\n추천 데이터가 없습니다."

        # 추천 종목 + 최신 추적 데이터 조회 (S/A 등급만)
        query = """
        WITH latest_tracking AS (
            SELECT DISTINCT ON (recommendation_id)
                recommendation_id, track_price, return_rate, days_held, track_date
            FROM smart_price_tracking
            ORDER BY recommendation_id, track_date DESC
        )
        SELECT
            sr.id,
            sr.stock_code,
            sr.stock_name,
            sr.recommendation_date,
            sr.close_price as rec_price,
            sr.ai_grade,
            sr.final_score,
            sr.ai_key_material,
            sr.ai_risk_factor,
            sr.ai_buy_point,
            sr.ai_policy_alignment,
            COALESCE(lt.track_price, sr.close_price) as current_price,
            COALESCE(lt.return_rate, 0) as return_rate,
            COALESCE(lt.days_held, 0) as days_held,
            lt.track_date
        FROM smart_recommendations sr
        LEFT JOIN latest_tracking lt ON sr.id = lt.recommendation_id
        WHERE sr.batch_id = $1
        AND sr.ai_grade = ANY($2)
        ORDER BY
            CASE sr.ai_grade WHEN 'S' THEN 1 WHEN 'A' THEN 2 ELSE 3 END,
            sr.final_score DESC
        """
        stocks = await db.fetch(query, batch_id, grades)

        if not stocks:
            return f"# S/A 등급 종목 없음\n\n배치 {batch_id}에 S/A 등급 종목이 없습니다."

        # 마크다운 생성
        rec_date = stocks[0]['recommendation_date']
        md = f"""# 신규종목 추적 대시보드

**추천일**: {rec_date}
**배치 ID**: {batch_id}
**생성 시각**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**총 종목수**: {len(stocks)}개

---

## 📊 등급별 현황

| 등급 | 종목수 | 평균 수익률 | 승률 |
|:---:|:---:|:---:|:---:|
"""
        # 등급별 통계
        grade_stats = {}
        for s in stocks:
            grade = s['ai_grade'] or 'N/A'
            if grade not in grade_stats:
                grade_stats[grade] = {'count': 0, 'returns': [], 'winners': 0}
            grade_stats[grade]['count'] += 1
            grade_stats[grade]['returns'].append(s['return_rate'] or 0)
            if (s['return_rate'] or 0) > 0:
                grade_stats[grade]['winners'] += 1

        for grade in ['S', 'A', 'B', 'C', 'D']:
            if grade in grade_stats:
                stats = grade_stats[grade]
                avg_ret = sum(stats['returns']) / len(stats['returns'])
                win_rate = stats['winners'] / stats['count'] * 100
                md += f"| {grade} | {stats['count']} | {avg_ret:+.2f}% | {win_rate:.1f}% |\n"

        # 수익률 분포
        returns = [s['return_rate'] or 0 for s in stocks]
        if returns:
            md += f"""
---

## 📉 수익률 분포

- **최고 수익**: {max(returns):+.2f}%
- **최저 수익**: {min(returns):+.2f}%
- **평균 수익**: {sum(returns)/len(returns):+.2f}%
- **승률**: {sum(1 for r in returns if r > 0)/len(returns)*100:.1f}%
"""

        md += """
---

## 📈 종목별 상세 추적

"""
        # 종목별 상세 (핵심재료 전체 표시)
        for i, s in enumerate(stocks, 1):
            return_emoji = "🟢" if (s['return_rate'] or 0) > 0 else "🔴" if (s['return_rate'] or 0) < -3 else "⚪"

            md += f"""### {i}. {s['stock_name']} ({s['stock_code']})

| 항목 | 값 |
|:---|:---|
| **등급** | {s['ai_grade'] or '-'} |
| **점수** | {s['final_score']:.1f} |
| **추천가** | {s['rec_price']:,}원 |
| **현재가** | {s['current_price']:,}원 |
| **수익률** | {return_emoji} {s['return_rate'] or 0:+.2f}% |
| **경과일** | {s['days_held'] or 0}일 |

**📌 핵심재료**:
{s['ai_key_material'] or '-'}

**🎯 매수포인트**:
{s['ai_buy_point'] or '-'}

**📋 정책관련성**:
{s['ai_policy_alignment'] or '-'}

**⚠️ 리스크 요인**:
{s['ai_risk_factor'] or '-'}

"""
            # 일별 가격 추적 이력 조회
            price_history = await self.get_daily_price_history(s['id'])
            if price_history and len(price_history) > 1:
                md += """**📊 일별 가격 추적**:
| 날짜 | 가격 | 수익률 | 경과일 |
|:---:|---:|---:|:---:|
"""
                for ph in price_history[-10:]:  # 최근 10일만
                    ret_emoji = "🟢" if ph['return_rate'] > 0 else "🔴" if ph['return_rate'] < -3 else "⚪"
                    md += f"| {ph['track_date']} | {ph['track_price']:,} | {ret_emoji} {ph['return_rate']:+.2f}% | {ph['days_held']}일 |\n"

            md += "\n---\n\n"

        # 실패 종목 요약
        failed = [s for s in stocks if (s['return_rate'] or 0) <= -5]
        if failed:
            md += """## ⚠️ 주의 필요 종목 (손실 -5% 이상)

| 종목명 | 등급 | 수익률 | 핵심재료 |
|:---|:---:|:---:|:---|
"""
            for s in failed:
                md += f"| {s['stock_name']} | {s['ai_grade']} | {s['return_rate']:+.2f}% | {s['ai_key_material'] or '-'} |\n"

        md += """
---

## 📝 분석 가이드

### 리뷰 체크리스트
- [ ] 성공 종목: 어떤 재료가 작동했는가?
- [ ] 실패 종목: 놓친 리스크는 무엇인가?
- [ ] AI 등급과 실제 성과의 상관관계 분석
- [ ] 개선할 점 기록

### Phase 4 AI 회고 실행
```bash
python 신규종목추천/run_phase4.py --retrospective-only
```

---

*본 리포트는 자동 생성되었습니다. 투자 판단은 본인 책임입니다.*
"""

        return md

    async def save_tracking_report(self, batch_id: str = None) -> str:
        """추적 리포트 저장"""
        md_content = await self.generate_tracking_markdown(batch_id)

        # 파일명 생성
        today = date.today().strftime('%Y-%m-%d')
        timestamp = datetime.now().strftime('%H%M')
        filename = f"추적현황_{today}_{timestamp}.md"
        filepath = self.tracking_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)

        print(f"✅ 추적 리포트 저장: {filepath}")
        return str(filepath)


async def create_tracking_table():
    """smart_price_tracking 테이블 생성"""
    query = """
    CREATE TABLE IF NOT EXISTS smart_price_tracking (
        id SERIAL PRIMARY KEY,
        recommendation_id INTEGER REFERENCES smart_recommendations(id),
        stock_code VARCHAR(10) NOT NULL,
        stock_name VARCHAR(100),
        rec_date DATE NOT NULL,
        rec_price INTEGER NOT NULL,
        rec_grade CHAR(1),
        track_date DATE NOT NULL,
        track_price INTEGER NOT NULL,
        return_rate NUMERIC(8,2),
        days_held INTEGER,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW(),
        UNIQUE(recommendation_id, track_date)
    );

    CREATE INDEX IF NOT EXISTS idx_price_tracking_stock ON smart_price_tracking(stock_code);
    CREATE INDEX IF NOT EXISTS idx_price_tracking_date ON smart_price_tracking(track_date);
    CREATE INDEX IF NOT EXISTS idx_price_tracking_rec_id ON smart_price_tracking(recommendation_id);
    """
    await db.execute(query)
    print("✅ smart_price_tracking 테이블 생성 완료")


async def main():
    """테스트 실행"""
    await db.connect()

    try:
        # 테이블 생성
        await create_tracking_table()

        # 주가 추적
        tracker = DailyPriceTracker()
        result = await tracker.record_daily_prices()
        print(f"\n📈 주가 기록: {result['recorded']}/{result['total']}건")

        # 리포트 생성
        report_path = await tracker.save_tracking_report()
        print(f"📄 리포트: {report_path}")

    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
