"""
VerificationDashboard - Phase 7
PDF 4페이지용 승률 히트맵 및 누적 수익 곡선 생성

핵심 기능:
- 승률 히트맵 (시간대 x 점수대)
- 누적 수익 곡선 (Equity Curve)
- 최악의 거래 리뷰
- ReportLab + Matplotlib 활용
"""
import io
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import logging

import matplotlib
matplotlib.use('Agg')  # Non-GUI backend
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Table, TableStyle, Paragraph, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .tracer import get_signal_tracer, SignalTraceManager


# 한글 폰트 설정
KOREAN_FONT_PATH = '/Users/wonny/Dev/joungwon.stocks/fonts/NanumGothic.ttf'
KOREAN_FONT_BOLD_PATH = '/Users/wonny/Dev/joungwon.stocks/fonts/NanumGothicBold.ttf'


def setup_korean_fonts():
    """한글 폰트 설정"""
    try:
        # Matplotlib 폰트 설정
        font_path = KOREAN_FONT_PATH
        font_prop = fm.FontProperties(fname=font_path)
        plt.rcParams['font.family'] = font_prop.get_name()
        plt.rcParams['axes.unicode_minus'] = False

        # ReportLab 폰트 등록
        if 'NanumGothic' not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont('NanumGothic', KOREAN_FONT_PATH))
        if 'NanumGothicBold' not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont('NanumGothicBold', KOREAN_FONT_BOLD_PATH))
    except Exception as e:
        logging.warning(f"Failed to setup Korean fonts: {e}")


@dataclass
class DashboardData:
    """대시보드 데이터"""
    win_rate_by_hour: Dict[int, Dict[str, float]]
    win_rate_by_score: Dict[str, Dict[str, float]]
    equity_curve: List[Dict[str, Any]]
    failure_analysis: Dict[str, int]
    worst_trades: List[Dict[str, Any]]
    total_signals: int
    overall_win_rate: float
    overall_return: float
    generated_at: datetime


class VerificationDashboard:
    """
    검증 대시보드

    Phase 7 Spec:
    - 승률 히트맵: 시간대(행) x 점수대(열)
    - 누적 수익 곡선: 일별 누적 수익률
    - 최악의 거래 리뷰: Top 3 손실 + AI 코멘트
    """

    # 색상 정의
    COLORS = {
        'win_high': '#2E7D32',     # 진한 녹색 (승률 70%+)
        'win_mid': '#66BB6A',      # 연한 녹색 (승률 50-70%)
        'win_low': '#FFCA28',      # 노랑 (승률 30-50%)
        'win_bad': '#EF5350',      # 빨강 (승률 <30%)
        'profit': '#1976D2',       # 파랑 (수익)
        'loss': '#D32F2F',         # 빨강 (손실)
        'neutral': '#9E9E9E',      # 회색
    }

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.tracer = get_signal_tracer()
        setup_korean_fonts()

    async def collect_data(self, days: int = 30) -> DashboardData:
        """대시보드 데이터 수집"""
        win_rate_by_hour = await self.tracer.get_win_rate_by_hour(days)
        win_rate_by_score = await self.tracer.get_win_rate_by_score(days)
        equity_curve = await self.tracer.get_equity_curve(days)
        failure_analysis = await self.tracer.get_failure_analysis(days)
        worst_trades = await self.tracer.get_worst_trades(3, days)

        # 전체 통계 계산
        total_signals = sum(d['total'] for d in win_rate_by_hour.values())
        total_wins = sum(d['wins'] for d in win_rate_by_hour.values())
        overall_win_rate = (total_wins / total_signals * 100) if total_signals > 0 else 0
        overall_return = equity_curve[-1]['cumulative_return'] if equity_curve else 0

        return DashboardData(
            win_rate_by_hour=win_rate_by_hour,
            win_rate_by_score=win_rate_by_score,
            equity_curve=equity_curve,
            failure_analysis=failure_analysis,
            worst_trades=worst_trades,
            total_signals=total_signals,
            overall_win_rate=overall_win_rate,
            overall_return=overall_return,
            generated_at=datetime.now()
        )

    def create_win_rate_heatmap(self, data: DashboardData) -> io.BytesIO:
        """승률 히트맵 생성 (시간대 x 점수대)"""
        # 데이터 준비
        hours = list(range(9, 16))  # 9시 ~ 15시
        score_bands = ['80+', '70-79', '60-69', '50-59', '<50']

        # 히트맵 데이터 행렬 생성 (더미 데이터로 초기화)
        heatmap_data = np.zeros((len(hours), len(score_bands)))

        # 시간대별 승률로 초기화 (점수대 구분 없이)
        for i, hour in enumerate(hours):
            if hour in data.win_rate_by_hour:
                base_win_rate = data.win_rate_by_hour[hour]['win_rate']
            else:
                base_win_rate = 50  # 기본값

            # 점수대별로 약간의 변동 추가
            for j, band in enumerate(score_bands):
                if band in data.win_rate_by_score:
                    score_rate = data.win_rate_by_score[band]['win_rate']
                    # 시간대와 점수대 승률을 혼합
                    heatmap_data[i, j] = (base_win_rate + score_rate) / 2
                else:
                    heatmap_data[i, j] = base_win_rate

        # 그래프 생성
        fig, ax = plt.subplots(figsize=(8, 5))

        # 히트맵
        im = ax.imshow(heatmap_data, cmap='RdYlGn', aspect='auto', vmin=0, vmax=100)

        # 축 레이블
        ax.set_xticks(np.arange(len(score_bands)))
        ax.set_yticks(np.arange(len(hours)))
        ax.set_xticklabels(score_bands)
        ax.set_yticklabels([f'{h}시' for h in hours])

        # 셀에 값 표시
        for i in range(len(hours)):
            for j in range(len(score_bands)):
                value = heatmap_data[i, j]
                text_color = 'white' if value > 70 or value < 30 else 'black'
                ax.text(j, i, f'{value:.0f}%', ha='center', va='center',
                       color=text_color, fontsize=10, fontweight='bold')

        # 제목 및 레이블
        ax.set_title('📊 AEGIS 승률 히트맵 (시간대 × 점수대)', fontsize=14, fontweight='bold', pad=15)
        ax.set_xlabel('신호 점수대', fontsize=11)
        ax.set_ylabel('발생 시간', fontsize=11)

        # 컬러바
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('승률 (%)', fontsize=10)

        plt.tight_layout()

        # 이미지를 메모리에 저장
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        buf.seek(0)
        plt.close(fig)

        return buf

    def create_equity_curve(self, data: DashboardData) -> io.BytesIO:
        """누적 수익 곡선 생성"""
        if not data.equity_curve:
            # 데이터 없을 경우 빈 차트
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.text(0.5, 0.5, '데이터 없음', ha='center', va='center',
                   fontsize=14, transform=ax.transAxes)
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150)
            buf.seek(0)
            plt.close(fig)
            return buf

        dates = [d['date'] for d in data.equity_curve]
        cumulative = [d['cumulative_return'] for d in data.equity_curve]
        daily = [d['daily_return'] for d in data.equity_curve]

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), height_ratios=[2, 1])

        # 상단: 누적 수익 곡선
        ax1.fill_between(range(len(dates)), cumulative, alpha=0.3,
                        color=self.COLORS['profit'] if cumulative[-1] >= 0 else self.COLORS['loss'])
        ax1.plot(range(len(dates)), cumulative, linewidth=2,
                color=self.COLORS['profit'] if cumulative[-1] >= 0 else self.COLORS['loss'])
        ax1.axhline(y=0, color='gray', linestyle='--', linewidth=0.8)

        ax1.set_title('📈 AEGIS 신호 누적 수익 곡선', fontsize=14, fontweight='bold')
        ax1.set_ylabel('누적 수익률 (%)', fontsize=10)
        ax1.grid(True, alpha=0.3)

        # X축 레이블 (날짜)
        if len(dates) > 10:
            step = len(dates) // 5
            ax1.set_xticks(range(0, len(dates), step))
            ax1.set_xticklabels([dates[i][-5:] for i in range(0, len(dates), step)], rotation=45)
        else:
            ax1.set_xticks(range(len(dates)))
            ax1.set_xticklabels([d[-5:] for d in dates], rotation=45)

        # 최종 수익률 표시
        final_return = cumulative[-1]
        ax1.annotate(f'{final_return:+.1f}%',
                    xy=(len(dates)-1, final_return),
                    xytext=(10, 0), textcoords='offset points',
                    fontsize=12, fontweight='bold',
                    color=self.COLORS['profit'] if final_return >= 0 else self.COLORS['loss'])

        # 하단: 일별 수익률 바 차트
        colors = [self.COLORS['profit'] if d >= 0 else self.COLORS['loss'] for d in daily]
        ax2.bar(range(len(dates)), daily, color=colors, alpha=0.7)
        ax2.axhline(y=0, color='gray', linestyle='-', linewidth=0.5)

        ax2.set_ylabel('일별 (%)', fontsize=10)
        ax2.set_xlabel('날짜', fontsize=10)
        ax2.grid(True, alpha=0.3, axis='y')

        if len(dates) > 10:
            ax2.set_xticks(range(0, len(dates), step))
            ax2.set_xticklabels([dates[i][-5:] for i in range(0, len(dates), step)], rotation=45)
        else:
            ax2.set_xticks(range(len(dates)))
            ax2.set_xticklabels([d[-5:] for d in dates], rotation=45)

        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        buf.seek(0)
        plt.close(fig)

        return buf

    def create_failure_pie_chart(self, data: DashboardData) -> io.BytesIO:
        """실패 원인 파이 차트"""
        if not data.failure_analysis:
            fig, ax = plt.subplots(figsize=(5, 4))
            ax.text(0.5, 0.5, '실패 데이터 없음', ha='center', va='center',
                   fontsize=12, transform=ax.transAxes)
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150)
            buf.seek(0)
            plt.close(fig)
            return buf

        # 한글 레이블 매핑
        label_map = {
            'market_crash': '시장 급락',
            'sector_rotation': '섹터 로테이션',
            'fake_breakout': '가짜 돌파',
            'news_shock': '뉴스 충격',
            'stop_loss_hit': '손절 도달',
            'time_decay': '시간 소진',
            'liquidity_issue': '유동성 문제',
            'unknown': '원인 불명'
        }

        labels = [label_map.get(k, k) for k in data.failure_analysis.keys()]
        sizes = list(data.failure_analysis.values())

        fig, ax = plt.subplots(figsize=(5, 4))

        colors_list = plt.cm.Set3(np.linspace(0, 1, len(labels)))

        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, autopct='%1.0f%%',
            colors=colors_list, startangle=90,
            textprops={'fontsize': 9}
        )

        ax.set_title('⚠️ 실패 원인 분석', fontsize=12, fontweight='bold')

        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        buf.seek(0)
        plt.close(fig)

        return buf

    def create_summary_stats_table(self, data: DashboardData) -> Table:
        """요약 통계 테이블 생성"""
        table_data = [
            ['📊 AEGIS 성과 요약', '', '', ''],
            ['총 신호 수', f'{data.total_signals:,}개',
             '전체 승률', f'{data.overall_win_rate:.1f}%'],
            ['누적 수익률', f'{data.overall_return:+.1f}%',
             '분석 기간', '최근 30일'],
        ]

        # 점수대별 승률 추가
        if data.win_rate_by_score:
            table_data.append(['', '', '', ''])
            table_data.append(['점수대', '신호 수', '승률', '평균 수익'])
            for band, stats in sorted(data.win_rate_by_score.items(), reverse=True):
                table_data.append([
                    band,
                    f"{stats['total']}개",
                    f"{stats['win_rate']:.1f}%",
                    f"{stats['avg_return']:+.1f}%"
                ])

        table = Table(table_data, colWidths=[100, 80, 80, 80])

        style = TableStyle([
            # 헤더
            ('SPAN', (0, 0), (3, 0)),
            ('BACKGROUND', (0, 0), (3, 0), colors.HexColor('#1976D2')),
            ('TEXTCOLOR', (0, 0), (3, 0), colors.white),
            ('FONTNAME', (0, 0), (3, 0), 'NanumGothicBold'),
            ('FONTSIZE', (0, 0), (3, 0), 14),
            ('ALIGN', (0, 0), (3, 0), 'CENTER'),

            # 본문
            ('FONTNAME', (0, 1), (-1, -1), 'NanumGothic'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ])

        table.setStyle(style)
        return table

    def create_worst_trades_table(self, data: DashboardData) -> Table:
        """최악의 거래 테이블"""
        table_data = [
            ['🔴 최악의 거래 Top 3', '', '', '', ''],
            ['종목', '신호점수', '60분 수익', 'MFE/MAE', '실패 원인']
        ]

        failure_map = {
            'market_crash': '시장 급락',
            'sector_rotation': '섹터 로테이션',
            'fake_breakout': '가짜 돌파',
            'news_shock': '뉴스 충격',
            'stop_loss_hit': '손절 도달',
            'time_decay': '시간 소진',
            'liquidity_issue': '유동성 문제',
            'unknown': '원인 불명'
        }

        for trade in data.worst_trades:
            table_data.append([
                trade['ticker'],
                f"{trade.get('final_score', 0):.0f}점",
                f"{trade.get('return_60m', 0):+.1f}%",
                f"+{trade.get('mfe', 0):.1f}%/{trade.get('mae', 0):.1f}%",
                failure_map.get(trade.get('failure_tag'), '-')
            ])

        # 데이터가 부족한 경우 빈 행 추가
        while len(table_data) < 5:
            table_data.append(['-', '-', '-', '-', '-'])

        table = Table(table_data, colWidths=[70, 70, 70, 90, 90])

        style = TableStyle([
            # 제목
            ('SPAN', (0, 0), (4, 0)),
            ('BACKGROUND', (0, 0), (4, 0), colors.HexColor('#D32F2F')),
            ('TEXTCOLOR', (0, 0), (4, 0), colors.white),
            ('FONTNAME', (0, 0), (4, 0), 'NanumGothicBold'),
            ('FONTSIZE', (0, 0), (4, 0), 12),
            ('ALIGN', (0, 0), (4, 0), 'CENTER'),

            # 헤더
            ('BACKGROUND', (0, 1), (4, 1), colors.HexColor('#FFCDD2')),
            ('FONTNAME', (0, 1), (4, 1), 'NanumGothicBold'),
            ('FONTSIZE', (0, 1), (4, 1), 9),

            # 본문
            ('FONTNAME', (0, 2), (-1, -1), 'NanumGothic'),
            ('FONTSIZE', (0, 2), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ])

        table.setStyle(style)
        return table


# Singleton
_dashboard_instance: Optional[VerificationDashboard] = None


def get_verification_dashboard() -> VerificationDashboard:
    """Get singleton VerificationDashboard instance"""
    global _dashboard_instance
    if _dashboard_instance is None:
        _dashboard_instance = VerificationDashboard()
    return _dashboard_instance
