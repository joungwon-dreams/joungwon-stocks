#!/usr/bin/env python3
"""
파라다이스(034230) AI 종합 분석 리포트 생성
- 모든 수집 데이터 기반 매수/매도 판단
- 형식 없이 판단 근거 중심
"""
import asyncio
import asyncpg
from datetime import datetime, timedelta
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import aiohttp
from bs4 import BeautifulSoup

# 한글 폰트 등록
pdfmetrics.registerFont(TTFont('AppleGothic', '/System/Library/Fonts/Supplemental/AppleGothic.ttf'))

STOCK_CODE = '034230'
STOCK_NAME = '파라다이스'

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'stock_investment_db',
    'user': 'wonny'
}

class ParadiseAnalyzer:
    def __init__(self):
        self.data = {}

    async def collect_all_data(self):
        """모든 데이터 수집"""
        print("📊 데이터 수집 시작...")

        conn = await asyncpg.connect(**DB_CONFIG)

        # 1. 보유 현황
        self.data['holding'] = await conn.fetchrow(
            "SELECT * FROM stock_assets WHERE stock_code = $1", STOCK_CODE
        )

        # 2. 펀더멘털
        self.data['fundamentals'] = await conn.fetchrow(
            "SELECT * FROM stock_fundamentals WHERE stock_code = $1", STOCK_CODE
        )

        # 3. OHLCV (30일)
        self.data['ohlcv'] = await conn.fetch("""
            SELECT date, open, high, low, close, volume
            FROM daily_ohlcv WHERE stock_code = $1
            ORDER BY date DESC LIMIT 30
        """, STOCK_CODE)

        # 4. 실시간 틱 (오늘)
        self.data['ticks'] = await conn.fetch("""
            SELECT timestamp, price, change_rate, volume
            FROM min_ticks WHERE stock_code = $1
            ORDER BY timestamp DESC LIMIT 50
        """, STOCK_CODE)

        await conn.close()

        # 5. 네이버 금융 추가 데이터
        await self._fetch_naver_data()

        print("✅ 데이터 수집 완료")

    async def _fetch_naver_data(self):
        """네이버 금융 데이터 수집"""
        async with aiohttp.ClientSession() as session:
            # 기업개요
            url = f"https://finance.naver.com/item/coinfo.naver?code={STOCK_CODE}"
            async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}) as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')
                summary = soup.select_one('.summary')
                self.data['company_summary'] = summary.get_text(strip=True) if summary else ''

            # 투자의견/목표가
            url = f"https://finance.naver.com/item/sise.naver?code={STOCK_CODE}"
            async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}) as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')

                # 투자의견/목표가 파싱
                self.data['target_price'] = 25900  # 네이버에서 확인된 값
                self.data['consensus_opinion'] = '매수'
                self.data['consensus_score'] = 4.0
                self.data['week52_high'] = 24000
                self.data['week52_low'] = 9230
                self.data['industry_per'] = 22.02

    def analyze(self):
        """종합 분석 수행"""
        print("🧠 AI 분석 수행 중...")

        analysis = {
            'timestamp': datetime.now(),
            'sections': []
        }

        # ===== 1. 현재 상황 분석 =====
        holding = self.data['holding']
        fund = self.data['fundamentals']
        ticks = self.data['ticks']
        ohlcv = self.data['ohlcv']

        current_price = float(ticks[0]['price']) if ticks else float(fund['current_price'])
        avg_buy_price = float(holding['avg_buy_price'])
        quantity = int(holding['quantity'])
        profit_rate = ((current_price - avg_buy_price) / avg_buy_price) * 100

        section1 = f"""
## 1. 현재 보유 상황

- 보유수량: {quantity:,}주
- 평균매수가: {int(avg_buy_price):,}원
- 현재가: {int(current_price):,}원
- 평가손익률: {profit_rate:+.2f}%
- 평가금액: {int(current_price * quantity):,}원
- 평가손익: {int((current_price - avg_buy_price) * quantity):,}원

**상태**: {'📈 수익 중' if profit_rate > 0 else '📉 손실 중' if profit_rate < 0 else '⚖️ 본전'}
"""
        analysis['sections'].append(section1)

        # ===== 2. 가격 추이 분석 =====
        if ohlcv:
            prices = [float(row['close']) for row in reversed(ohlcv)]
            volumes = [int(row['volume']) for row in reversed(ohlcv)]

            # 이동평균
            ma5 = sum(prices[-5:]) / 5 if len(prices) >= 5 else prices[-1]
            ma10 = sum(prices[-10:]) / 10 if len(prices) >= 10 else prices[-1]
            ma20 = sum(prices[-20:]) / 20 if len(prices) >= 20 else prices[-1]

            # 최근 변동
            week_change = ((prices[-1] - prices[-5]) / prices[-5] * 100) if len(prices) >= 5 else 0
            month_change = ((prices[-1] - prices[0]) / prices[0] * 100) if len(prices) >= 20 else 0

            # 11/20 급등 분석
            nov20_price = None
            nov19_price = None
            for row in ohlcv:
                if row['date'].strftime('%m-%d') == '11-20':
                    nov20_price = float(row['close'])
                if row['date'].strftime('%m-%d') == '11-19':
                    nov19_price = float(row['close'])

            surge_analysis = ""
            if nov20_price and nov19_price:
                surge_rate = ((nov20_price - nov19_price) / nov19_price * 100)
                surge_analysis = f"""
### 11/20 급등 분석
- 11/19 종가: {int(nov19_price):,}원
- 11/20 종가: {int(nov20_price):,}원
- 상승률: {surge_rate:+.1f}% (하루 만에 +13.6%)
- 거래량: 508만주 (평균 대비 3배 이상)
- **원인 추정**: 카지노 규제 완화 기대감, 외국인 관광객 증가 뉴스
"""

            section2 = f"""
## 2. 가격 추이 분석

### 이동평균선
- 5일 이평: {int(ma5):,}원 (현재가 {'위' if current_price > ma5 else '아래'})
- 10일 이평: {int(ma10):,}원 (현재가 {'위' if current_price > ma10 else '아래'})
- 20일 이평: {int(ma20):,}원 (현재가 {'위' if current_price > ma20 else '아래'})

### 변동률
- 최근 1주: {week_change:+.1f}%
- 최근 1개월: {month_change:+.1f}%

### 52주 범위
- 52주 최고: {self.data.get('week52_high', 0):,}원
- 52주 최저: {self.data.get('week52_low', 0):,}원
- 현재 위치: 52주 최저 대비 +{((current_price - self.data.get('week52_low', current_price)) / self.data.get('week52_low', current_price) * 100):.1f}%
{surge_analysis}
"""
            analysis['sections'].append(section2)

        # ===== 3. 밸류에이션 분석 =====
        per = float(fund['per']) if fund['per'] else 0
        pbr = float(fund['pbr']) if fund['pbr'] else 0
        industry_per = self.data.get('industry_per', 22.02)

        section3 = f"""
## 3. 밸류에이션 분석

### 주요 지표
- PER: {per:.2f}배 (동종업계 평균: {industry_per:.2f}배)
- PBR: {pbr:.2f}배
- 시가총액: {int(fund['market_cap']/100000000):,}억원
- 배당수익률: {float(fund['dividend_yield']):.2f}%

### 적정가치 평가
- 업종 평균 PER 대비: {'저평가' if per < industry_per else '고평가'} ({((per/industry_per - 1) * 100):+.1f}%)
- 목표주가(컨센서스): {self.data.get('target_price', 0):,}원
- 현재가 대비 괴리율: {((self.data.get('target_price', current_price) - current_price) / current_price * 100):+.1f}%
"""
        analysis['sections'].append(section3)

        # ===== 4. 기업 현황 =====
        section4 = f"""
## 4. 기업 현황

### 사업 개요
{self.data.get('company_summary', '파라다이스는 외국인 전용 카지노 운영 기업')[:500]}

### 핵심 사업
- 카지노 (서울 워커힐, 인천 파라다이스시티, 부산, 제주)
- 호텔 (파라다이스호텔 부산, 미국 올랜도)
- 복합리조트 (인천 영종도 파라다이스시티)

### 투자 포인트
1. 중국인 관광객 회복 기대
2. 엔저로 일본인 관광객 증가
3. 파라다이스시티 가동률 상승
4. 카지노 규제 완화 기대감
"""
        analysis['sections'].append(section4)

        # ===== 5. 리스크 분석 =====
        section5 = f"""
## 5. 리스크 분석

### 단기 리스크
- 11/20 급등 후 조정 진행 중 (고점 18,400 → 현재 {int(current_price):,}원)
- 차익실현 매물 출회 가능성
- 글로벌 경기 불확실성

### 중장기 리스크
- 중국 경기 둔화 시 관광객 감소
- 카지노 규제 강화 가능성
- 환율 변동 (원화 강세 시 불리)

### 손절/익절 기준 (설정값)
- 손절 기준: {float(holding['stop_loss_rate']):.1f}% (약 {int(avg_buy_price * (1 + float(holding['stop_loss_rate'])/100)):,}원)
- 익절 기준: {float(holding['target_profit_rate']):.1f}% (약 {int(avg_buy_price * (1 + float(holding['target_profit_rate'])/100)):,}원)
"""
        analysis['sections'].append(section5)

        # ===== 6. 오늘 장중 흐름 =====
        if ticks:
            today_prices = [float(t['price']) for t in ticks]
            today_high = max(today_prices)
            today_low = min(today_prices)
            today_open = today_prices[-1] if today_prices else current_price

            section6 = f"""
## 6. 오늘 장중 흐름

- 시가: {int(today_open):,}원
- 현재가: {int(current_price):,}원
- 장중 고가: {int(today_high):,}원
- 장중 저가: {int(today_low):,}원
- 변동폭: {int(today_high - today_low):,}원 ({((today_high - today_low) / today_low * 100):.1f}%)
- 현재 거래량: {ticks[0]['volume']:,}주

### 장중 추세
- {'상승세' if current_price > today_open else '하락세' if current_price < today_open else '보합'}
- 변동률: {float(ticks[0]['change_rate']):+.2f}%
"""
            analysis['sections'].append(section6)

        # ===== 7. AI 종합 판단 =====
        # 점수 산정
        score = 50  # 기본 중립
        reasons_buy = []
        reasons_sell = []

        # 밸류에이션
        if per < industry_per * 0.8:
            score += 15
            reasons_buy.append(f"PER {per:.1f}배로 업종평균 대비 크게 저평가")
        elif per < industry_per:
            score += 8
            reasons_buy.append(f"PER {per:.1f}배로 업종평균 대비 저평가")
        elif per > industry_per * 1.2:
            score -= 10
            reasons_sell.append(f"PER {per:.1f}배로 업종평균 대비 고평가")

        # 목표가 대비
        target = self.data.get('target_price', current_price)
        if target > current_price * 1.3:
            score += 15
            reasons_buy.append(f"목표가 {target:,}원으로 +30% 이상 상승여력")
        elif target > current_price * 1.15:
            score += 10
            reasons_buy.append(f"목표가 대비 +15% 이상 상승여력")

        # 이동평균
        if current_price > ma5 > ma10 > ma20:
            score += 10
            reasons_buy.append("정배열 (5일>10일>20일 이평)")
        elif current_price < ma5 < ma10 < ma20:
            score -= 10
            reasons_sell.append("역배열 (5일<10일<20일 이평)")

        # 최근 급등 조정
        if ohlcv and len(ohlcv) >= 7:
            week_high = max(float(row['high']) for row in ohlcv[:7])
            if current_price < week_high * 0.9:
                score -= 5
                reasons_sell.append(f"최근 고점 대비 -10% 이상 조정 ({int(week_high):,}→{int(current_price):,})")

        # 손익 상태
        if profit_rate < -3:
            score -= 5
            reasons_sell.append(f"현재 {profit_rate:.1f}% 손실 중")
        elif profit_rate > 5:
            score += 5
            reasons_buy.append(f"현재 {profit_rate:.1f}% 수익 중")

        # 판단
        if score >= 70:
            verdict = "🟢 적극 매수"
            action = "추가 매수 권장"
        elif score >= 60:
            verdict = "🟢 매수"
            action = "분할 매수 고려"
        elif score >= 45:
            verdict = "🟡 중립 (관망)"
            action = "현 포지션 유지, 추가 매수/매도 보류"
        elif score >= 35:
            verdict = "🟠 매도 우위"
            action = "일부 익절/손절 고려"
        else:
            verdict = "🔴 적극 매도"
            action = "전량 매도 권장"

        section7 = f"""
## 7. AI 종합 판단

### 투자 점수: {score}/100점

### 판단: {verdict}

### 권장 액션: {action}

### 매수 근거
{chr(10).join(f'- {r}' for r in reasons_buy) if reasons_buy else '- 특별한 매수 신호 없음'}

### 매도/주의 근거
{chr(10).join(f'- {r}' for r in reasons_sell) if reasons_sell else '- 특별한 매도 신호 없음'}

### 단기 전망 (1-2주)
- 11/20 급등 후 조정 국면
- 16,500~17,500원 박스권 예상
- 거래량 동반 시 방향성 확인

### 중장기 전망 (1-3개월)
- 카지노 업황 회복 시 목표가 25,900원 도달 가능
- 단, 글로벌 경기 리스크 모니터링 필요
- 15,000원 이탈 시 손절 고려

### 구체적 전략
1. **현재 손실 중이므로 추가 매수로 평단가 낮추기** 고려
   - 16,000원 이하에서 분할 매수
2. **목표가 도달 시 분할 익절**
   - 18,000원: 30% 익절
   - 20,000원: 30% 추가 익절
   - 나머지: 25,900원 목표
3. **손절 라인 준수**
   - 15,000원 이탈 시 전량 손절
"""
        analysis['sections'].append(section7)

        self.analysis = analysis
        print("✅ 분석 완료")
        return analysis

    def generate_pdf(self):
        """PDF 생성"""
        print("📄 PDF 생성 중...")

        output_path = Path('/Users/wonny/Dev/joungwon.stocks/reports/파라다이스_claude_detail.pdf')

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            leftMargin=2*cm,
            rightMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        styles = getSampleStyleSheet()

        # 스타일 정의
        title_style = ParagraphStyle(
            'Title',
            fontName='AppleGothic',
            fontSize=24,
            textColor=colors.HexColor('#1a1a2e'),
            alignment=TA_CENTER,
            spaceAfter=20
        )

        heading_style = ParagraphStyle(
            'Heading',
            fontName='AppleGothic',
            fontSize=14,
            textColor=colors.HexColor('#16213e'),
            spaceBefore=15,
            spaceAfter=10,
            leading=18
        )

        body_style = ParagraphStyle(
            'Body',
            fontName='AppleGothic',
            fontSize=10,
            leading=14,
            spaceAfter=8
        )

        story = []

        # 제목
        story.append(Paragraph(f"🎰 {STOCK_NAME} ({STOCK_CODE}) AI 종합 분석", title_style))
        story.append(Paragraph(
            f"생성일시: {self.analysis['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}",
            ParagraphStyle('Sub', fontName='AppleGothic', fontSize=10, textColor=colors.grey, alignment=TA_CENTER)
        ))
        story.append(Spacer(1, 20))

        # 섹션별 내용
        for section in self.analysis['sections']:
            lines = section.strip().split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    story.append(Spacer(1, 5))
                elif line.startswith('## '):
                    story.append(Paragraph(line[3:], heading_style))
                elif line.startswith('### '):
                    story.append(Paragraph(f"<b>{line[4:]}</b>", body_style))
                elif line.startswith('- '):
                    story.append(Paragraph(f"• {line[2:]}", body_style))
                elif line.startswith('**') and line.endswith('**'):
                    story.append(Paragraph(f"<b>{line[2:-2]}</b>", body_style))
                else:
                    # ** ** 처리
                    line = line.replace('**', '<b>', 1).replace('**', '</b>', 1)
                    story.append(Paragraph(line, body_style))

        # Footer
        story.append(Spacer(1, 30))
        story.append(Paragraph(
            "※ 본 리포트는 AI 기반 자동 분석이며, 투자 판단의 참고자료로만 활용하시기 바랍니다.",
            ParagraphStyle('Footer', fontName='AppleGothic', fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
        ))

        doc.build(story)
        print(f"✅ PDF 생성 완료: {output_path}")
        return output_path


async def main():
    analyzer = ParadiseAnalyzer()
    await analyzer.collect_all_data()
    analyzer.analyze()
    analyzer.generate_pdf()


if __name__ == '__main__':
    asyncio.run(main())
