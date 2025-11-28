#!/usr/bin/env python3
"""
일일 매매 성과 리포트 PDF 생성 - Phase 8

구성:
- Page 1: 오늘의 손익 요약, 자산 추이 그래프
- Page 2: 포트폴리오 파이차트, 매매 일지(Trade Log)
- Page 3: 주간/월간 누적 성과 (캘린더 형태)

저장 경로: reports/performance/YYYY-MM-DD_Daily_Report.pdf
실행 시점: 장 마감 후 (15:40~)
"""
import asyncio
import os
import sys
import tempfile
from datetime import datetime, date, timedelta
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

from src.config.database import db
from src.reporting.performance.analyzer import (
    DailyPerformanceAnalyzer,
    DailySummary,
    get_performance_analyzer,
)

# 한글 폰트 설정
FONT_PATH = '/System/Library/Fonts/Supplemental/AppleGothic.ttf'
pdfmetrics.registerFont(TTFont('AppleGothic', FONT_PATH))
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

# 색상 정의
COLOR_RED = colors.Color(0.8, 0.1, 0.1)      # 상승/이익
COLOR_BLUE = colors.Color(0.1, 0.1, 0.8)     # 하락/손실
COLOR_GREEN = colors.Color(0.1, 0.6, 0.1)    # 긍정
COLOR_GRAY = colors.Color(0.5, 0.5, 0.5)
COLOR_LIGHT_GRAY = colors.Color(0.9, 0.9, 0.9)

# 페이지 설정
PAGE_WIDTH, PAGE_HEIGHT = A4


def format_currency(value: float, show_sign: bool = False) -> str:
    """금액 포맷팅"""
    if value >= 0:
        sign = '+' if show_sign else ''
        return f"{sign}{value:,.0f}"
    else:
        return f"{value:,.0f}"


def format_percent(value: float, show_sign: bool = True) -> str:
    """퍼센트 포맷팅"""
    if value >= 0:
        sign = '+' if show_sign else ''
        return f"{sign}{value:.2f}%"
    else:
        return f"{value:.2f}%"


def get_color_for_value(value: float) -> colors.Color:
    """값에 따른 색상 반환"""
    if value > 0:
        return COLOR_RED
    elif value < 0:
        return COLOR_BLUE
    else:
        return colors.black


class DailyPerformanceReportGenerator:
    """일일 성과 리포트 PDF 생성기"""

    def __init__(self, output_dir: str = 'reports/performance'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate(self, target_date: date = None) -> str:
        """
        일일 성과 리포트 생성

        Args:
            target_date: 대상 날짜 (기본: 오늘)

        Returns:
            생성된 PDF 파일 경로
        """
        if target_date is None:
            target_date = date.today()

        print(f"\n{'='*60}")
        print(f"📊 일일 매매 성과 리포트 생성")
        print(f"   대상 날짜: {target_date}")
        print(f"{'='*60}\n")

        # 1. 성과 분석
        print("📈 성과 데이터 분석 중...")
        analyzer = get_performance_analyzer()
        summary = await analyzer.analyze(target_date)

        # 2. 주간 데이터 조회
        print("📅 주간 데이터 조회 중...")
        weekly_data = await analyzer.get_weekly_summary(target_date)

        # 3. 월간 캘린더 데이터
        print("🗓️ 월간 캘린더 데이터 조회 중...")
        monthly_data = await analyzer.get_monthly_calendar(target_date.year, target_date.month)

        # 4. PDF 생성
        output_path = self.output_dir / f"{target_date.strftime('%Y-%m-%d')}_Daily_Report.pdf"
        print(f"📄 PDF 생성 중: {output_path}")

        self._create_pdf(summary, weekly_data, monthly_data, output_path)

        # 5. DB에 요약 저장
        print("💾 DB에 요약 저장 중...")
        await analyzer.save_summary(summary)

        print(f"\n✅ 리포트 생성 완료: {output_path}")
        return str(output_path)

    def _create_pdf(
        self,
        summary: DailySummary,
        weekly_data: list,
        monthly_data: list,
        output_path: Path
    ):
        """PDF 파일 생성"""
        c = canvas.Canvas(str(output_path), pagesize=A4)

        # Page 1: 오늘의 손익 요약
        self._draw_page1_summary(c, summary)
        c.showPage()

        # Page 2: 포트폴리오 & 매매 일지
        self._draw_page2_portfolio(c, summary)
        c.showPage()

        # Page 3: 주간/월간 캘린더
        self._draw_page3_calendar(c, summary, weekly_data, monthly_data)
        c.showPage()

        c.save()

    def _draw_page1_summary(self, c: canvas.Canvas, summary: DailySummary):
        """Page 1: 오늘의 손익 요약"""
        y = PAGE_HEIGHT - 50

        # 헤더
        c.setFont('AppleGothic', 24)
        c.drawString(50, y, f"📊 일일 매매 성과 리포트")
        y -= 30

        c.setFont('AppleGothic', 14)
        c.setFillColor(COLOR_GRAY)
        c.drawString(50, y, f"{summary.date.strftime('%Y년 %m월 %d일')} ({['월','화','수','목','금','토','일'][summary.date.weekday()]})")
        y -= 50

        # 핵심 지표 박스
        c.setFillColor(colors.black)
        c.setFont('AppleGothic', 12)

        # 총 자산
        self._draw_metric_box(c, 50, y, "총 자산", format_currency(summary.total_asset), "원")
        # 일일 손익
        pnl_color = get_color_for_value(summary.daily_pnl)
        self._draw_metric_box(c, 200, y, "일일 손익", format_currency(summary.daily_pnl, True), "원", pnl_color)
        # 일일 수익률
        self._draw_metric_box(c, 350, y, "일일 수익률", format_percent(summary.daily_pnl_rate), "", pnl_color)
        y -= 100

        # 손익 상세
        c.setFont('AppleGothic', 14)
        c.setFillColor(colors.black)
        c.drawString(50, y, "💰 손익 상세")
        y -= 30

        details_data = [
            ["구분", "금액", "비고"],
            ["실현 손익", format_currency(summary.realized_pnl, True) + "원",
             f"매도 {summary.sell_count}건"],
            ["미실현 손익", format_currency(summary.unrealized_pnl, True) + "원",
             f"보유 {len(summary.holdings)}종목"],
            ["누적 실현 손익", format_currency(summary.cumulative_realized_pnl, True) + "원",
             f"수익률 {format_percent(summary.cumulative_pnl_rate)}"],
        ]

        table = Table(details_data, colWidths=[150, 150, 150])
        table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'AppleGothic', 11),
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_LIGHT_GRAY),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRAY),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        table.wrapOn(c, PAGE_WIDTH, PAGE_HEIGHT)
        table.drawOn(c, 50, y - 100)
        y -= 150

        # 매매 통계
        c.setFont('AppleGothic', 14)
        c.drawString(50, y, "📈 매매 통계")
        y -= 30

        trade_data = [
            ["구분", "건수", "금액"],
            ["매수", f"{summary.buy_count}건", format_currency(summary.buy_amount) + "원"],
            ["매도", f"{summary.sell_count}건", format_currency(summary.sell_amount) + "원"],
            ["총 거래", f"{summary.trade_count}건", "-"],
        ]

        table2 = Table(trade_data, colWidths=[100, 100, 150])
        table2.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'AppleGothic', 11),
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_LIGHT_GRAY),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRAY),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        table2.wrapOn(c, PAGE_WIDTH, PAGE_HEIGHT)
        table2.drawOn(c, 50, y - 100)

        # 승률 표시
        c.setFont('AppleGothic', 12)
        win_rate_text = f"승률: {summary.win_rate:.1f}% ({summary.win_trades}승 {summary.lose_trades}패)"
        c.drawString(300, y - 30, win_rate_text)

        # 시장 지표
        y -= 180
        c.setFont('AppleGothic', 14)
        c.drawString(50, y, "🌏 시장 지표")
        y -= 30

        market_text = []
        if summary.kospi_close:
            kospi_color = "🔴" if summary.kospi_change_rate and summary.kospi_change_rate > 0 else "🔵"
            market_text.append(f"KOSPI: {summary.kospi_close:,.2f} ({format_percent(summary.kospi_change_rate or 0)}) {kospi_color}")
        if summary.kosdaq_close:
            kosdaq_color = "🔴" if summary.kosdaq_change_rate and summary.kosdaq_change_rate > 0 else "🔵"
            market_text.append(f"KOSDAQ: {summary.kosdaq_close:,.2f} ({format_percent(summary.kosdaq_change_rate or 0)}) {kosdaq_color}")

        c.setFont('AppleGothic', 11)
        for i, text in enumerate(market_text):
            c.drawString(50, y - i * 20, text)

        # 푸터
        c.setFont('AppleGothic', 9)
        c.setFillColor(COLOR_GRAY)
        c.drawString(50, 30, f"Generated by AEGIS Trading System | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def _draw_metric_box(
        self,
        c: canvas.Canvas,
        x: float,
        y: float,
        label: str,
        value: str,
        unit: str,
        value_color: colors.Color = colors.black
    ):
        """지표 박스 그리기"""
        # 라벨
        c.setFont('AppleGothic', 10)
        c.setFillColor(COLOR_GRAY)
        c.drawString(x, y + 25, label)

        # 값
        c.setFont('AppleGothic', 18)
        c.setFillColor(value_color)
        c.drawString(x, y, value)

        # 단위
        if unit:
            c.setFont('AppleGothic', 10)
            c.setFillColor(COLOR_GRAY)
            c.drawString(x + len(value) * 12, y, unit)

    def _draw_page2_portfolio(self, c: canvas.Canvas, summary: DailySummary):
        """Page 2: 포트폴리오 & 매매 일지"""
        y = PAGE_HEIGHT - 50

        # 헤더
        c.setFont('AppleGothic', 18)
        c.drawString(50, y, "📦 포트폴리오 현황")
        y -= 40

        # 보유종목 테이블
        if summary.holdings:
            headers = ["종목명", "수량", "평단가", "현재가", "평가금액", "손익", "수익률"]
            data = [headers]

            for h in summary.holdings[:10]:  # 최대 10개
                pnl_str = format_currency(h.unrealized_pnl, True)
                rate_str = format_percent(h.unrealized_pnl_rate)
                data.append([
                    h.stock_name[:8],  # 이름 길이 제한
                    f"{h.quantity:,}",
                    f"{h.avg_buy_price:,.0f}",
                    f"{h.current_price:,.0f}",
                    f"{h.total_value:,.0f}",
                    pnl_str,
                    rate_str,
                ])

            table = Table(data, colWidths=[80, 50, 70, 70, 80, 70, 60])
            table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), 'AppleGothic', 9),
                ('BACKGROUND', (0, 0), (-1, 0), COLOR_LIGHT_GRAY),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRAY),
                ('PADDING', (0, 0), (-1, -1), 5),
            ]))
            table.wrapOn(c, PAGE_WIDTH, PAGE_HEIGHT)
            table.drawOn(c, 50, y - len(data) * 20 - 20)
            y -= len(data) * 20 + 60
        else:
            c.setFont('AppleGothic', 11)
            c.setFillColor(COLOR_GRAY)
            c.drawString(50, y - 20, "보유종목 없음")
            y -= 60

        # 포트폴리오 파이차트
        if summary.holdings:
            y -= 20
            c.setFont('AppleGothic', 14)
            c.setFillColor(colors.black)
            c.drawString(50, y, "📊 자산 배분")
            y -= 10

            chart_path = self._create_pie_chart(summary.holdings)
            if chart_path:
                c.drawImage(chart_path, 50, y - 200, width=250, height=200)
                os.unlink(chart_path)
            y -= 220

        # 매매 일지
        c.setFont('AppleGothic', 14)
        c.setFillColor(colors.black)
        c.drawString(50, y, "📝 매매 일지")
        y -= 30

        if summary.trades:
            headers = ["시간", "종목", "구분", "수량", "단가", "금액", "손익"]
            data = [headers]

            for t in summary.trades[:8]:  # 최대 8개
                trade_type_str = "매수" if t.trade_type == 'BUY' else "매도"
                pnl_str = format_currency(t.realized_pnl, True) if t.realized_pnl else "-"
                data.append([
                    t.trade_time.strftime('%H:%M'),
                    t.stock_name[:6] if t.stock_name else t.stock_code,
                    trade_type_str,
                    f"{t.quantity:,}",
                    f"{t.price:,.0f}",
                    f"{t.amount:,.0f}",
                    pnl_str,
                ])

            table = Table(data, colWidths=[50, 60, 40, 50, 70, 80, 70])
            table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), 'AppleGothic', 9),
                ('BACKGROUND', (0, 0), (-1, 0), COLOR_LIGHT_GRAY),
                ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
                ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRAY),
                ('PADDING', (0, 0), (-1, -1), 5),
            ]))
            table.wrapOn(c, PAGE_WIDTH, PAGE_HEIGHT)
            table.drawOn(c, 50, y - len(data) * 18 - 10)
        else:
            c.setFont('AppleGothic', 11)
            c.setFillColor(COLOR_GRAY)
            c.drawString(50, y - 10, "당일 매매 내역 없음")

        # 푸터
        c.setFont('AppleGothic', 9)
        c.setFillColor(COLOR_GRAY)
        c.drawString(50, 30, "Page 2/3")

    def _draw_page3_calendar(
        self,
        c: canvas.Canvas,
        summary: DailySummary,
        weekly_data: list,
        monthly_data: list
    ):
        """Page 3: 주간/월간 캘린더"""
        y = PAGE_HEIGHT - 50

        # 헤더
        c.setFont('AppleGothic', 18)
        c.drawString(50, y, "📅 성과 캘린더")
        y -= 50

        # 주간 요약
        c.setFont('AppleGothic', 14)
        c.drawString(50, y, f"📈 주간 성과 ({(summary.date - timedelta(days=6)).strftime('%m/%d')} ~ {summary.date.strftime('%m/%d')})")
        y -= 30

        if weekly_data:
            headers = ["날짜", "총자산", "일일손익", "수익률", "거래", "승률"]
            data = [headers]

            for day in weekly_data:
                data.append([
                    day['date'].strftime('%m/%d'),
                    format_currency(float(day.get('total_asset', 0))),
                    format_currency(float(day.get('daily_pnl', 0)), True),
                    format_percent(float(day.get('daily_pnl_rate', 0))),
                    str(day.get('trade_count', 0)),
                    f"{day.get('win_rate', 0):.0f}%",
                ])

            table = Table(data, colWidths=[60, 100, 80, 70, 50, 50])
            table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), 'AppleGothic', 10),
                ('BACKGROUND', (0, 0), (-1, 0), COLOR_LIGHT_GRAY),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRAY),
                ('PADDING', (0, 0), (-1, -1), 6),
            ]))
            table.wrapOn(c, PAGE_WIDTH, PAGE_HEIGHT)
            table.drawOn(c, 50, y - len(data) * 22)
            y -= len(data) * 22 + 40
        else:
            c.setFont('AppleGothic', 11)
            c.setFillColor(COLOR_GRAY)
            c.drawString(50, y, "주간 데이터 없음")
            y -= 40

        # 월간 캘린더
        c.setFont('AppleGothic', 14)
        c.setFillColor(colors.black)
        c.drawString(50, y, f"🗓️ {summary.date.year}년 {summary.date.month}월 손익 캘린더")
        y -= 20

        if monthly_data:
            chart_path = self._create_monthly_calendar(monthly_data, summary.date.year, summary.date.month)
            if chart_path:
                c.drawImage(chart_path, 50, y - 280, width=500, height=280)
                os.unlink(chart_path)

        # AEGIS 신호 성과
        y -= 320
        c.setFont('AppleGothic', 14)
        c.drawString(50, y, "🤖 AEGIS 신호 성과")
        y -= 25

        c.setFont('AppleGothic', 11)
        c.drawString(50, y, f"당일 발생 신호: {summary.aegis_signal_count}건")
        y -= 18
        c.drawString(50, y, f"신호 적중률: {summary.aegis_accuracy:.1f}%")

        # 푸터
        c.setFont('AppleGothic', 9)
        c.setFillColor(COLOR_GRAY)
        c.drawString(50, 30, "Page 3/3 | AEGIS Trading System")

    def _create_pie_chart(self, holdings: list) -> str:
        """포트폴리오 파이차트 생성"""
        try:
            fig, ax = plt.subplots(figsize=(4, 3))

            labels = [h.stock_name[:6] for h in holdings[:6]]
            sizes = [h.total_value for h in holdings[:6]]

            # 나머지 합계
            if len(holdings) > 6:
                labels.append('기타')
                sizes.append(sum(h.total_value for h in holdings[6:]))

            wedges, texts, autotexts = ax.pie(
                sizes, labels=labels, autopct='%1.1f%%',
                startangle=90, textprops={'fontsize': 8}
            )
            ax.set_title('자산 배분', fontsize=10)

            temp_path = tempfile.mktemp(suffix='.png')
            plt.savefig(temp_path, dpi=80, bbox_inches='tight', facecolor='white')
            plt.close(fig)

            return temp_path
        except Exception as e:
            print(f"차트 생성 실패: {e}")
            return None

    def _create_monthly_calendar(self, monthly_data: list, year: int, month: int) -> str:
        """월간 손익 캘린더 생성"""
        try:
            import calendar

            fig, ax = plt.subplots(figsize=(8, 4))

            # 캘린더 데이터 준비
            cal = calendar.Calendar()
            month_days = list(cal.itermonthdates(year, month))

            # 손익 데이터를 딕셔너리로
            pnl_dict = {d['date']: float(d.get('daily_pnl', 0)) for d in monthly_data}

            # 7x6 그리드 (요일 x 주)
            num_weeks = (len(month_days) + 6) // 7

            for week_idx in range(num_weeks):
                for day_idx in range(7):
                    idx = week_idx * 7 + day_idx
                    if idx < len(month_days):
                        day = month_days[idx]
                        x = day_idx
                        y = num_weeks - week_idx - 1

                        # 현재 월의 날짜만 표시
                        if day.month == month:
                            pnl = pnl_dict.get(day, 0)

                            # 색상 결정
                            if pnl > 0:
                                color = '#ffcccc'  # 연한 빨강 (이익)
                            elif pnl < 0:
                                color = '#ccccff'  # 연한 파랑 (손실)
                            else:
                                color = '#f0f0f0'  # 회색 (없음)

                            rect = plt.Rectangle((x, y), 0.95, 0.95, facecolor=color, edgecolor='gray')
                            ax.add_patch(rect)

                            # 날짜 표시
                            ax.text(x + 0.1, y + 0.7, str(day.day), fontsize=8, ha='left')

                            # 손익 표시
                            if pnl != 0:
                                pnl_text = f"{pnl/10000:+.1f}만"
                                text_color = 'red' if pnl > 0 else 'blue'
                                ax.text(x + 0.5, y + 0.3, pnl_text, fontsize=7, ha='center', color=text_color)

            # 요일 헤더
            days_kr = ['월', '화', '수', '목', '금', '토', '일']
            for i, day_name in enumerate(days_kr):
                ax.text(i + 0.5, num_weeks + 0.2, day_name, fontsize=9, ha='center', fontweight='bold')

            ax.set_xlim(-0.1, 7.1)
            ax.set_ylim(-0.1, num_weeks + 0.5)
            ax.set_aspect('equal')
            ax.axis('off')
            ax.set_title(f'{year}년 {month}월 일별 손익', fontsize=11, pad=10)

            temp_path = tempfile.mktemp(suffix='.png')
            plt.savefig(temp_path, dpi=80, bbox_inches='tight', facecolor='white')
            plt.close(fig)

            return temp_path
        except Exception as e:
            print(f"캘린더 생성 실패: {e}")
            return None


async def main():
    """메인 함수"""
    print("\n" + "="*60)
    print("📊 Phase 8: 일일 매매 성과 리포트 생성")
    print("="*60 + "\n")

    # 시간 체크 (선택적 - 장 마감 후에만 실행)
    now = datetime.now()
    # if now.hour < 15 or (now.hour == 15 and now.minute < 40):
    #     print("⚠️ 장 마감 전입니다. 15:40 이후에 실행하세요.")
    #     return

    # DB 연결
    await db.connect()

    try:
        generator = DailyPerformanceReportGenerator()
        output_path = await generator.generate()

        print("\n" + "="*60)
        print(f"✅ 리포트 생성 완료!")
        print(f"   📄 파일: {output_path}")
        print("="*60 + "\n")

    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
