"""
신규종목추천 PDF 리포트 생성기

추천 종목 리포트를 PDF로 생성하고,
일일 주가 추적 정보를 포함합니다.
"""
import asyncio
import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import matplotlib.pyplot as plt
from matplotlib import rcParams
import numpy as np

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')
from 신규종목추천.src.utils.database import db

# 한글 폰트 설정
rcParams['font.family'] = 'AppleGothic'
rcParams['axes.unicode_minus'] = False

try:
    pdfmetrics.registerFont(TTFont('AppleGothic', '/System/Library/Fonts/Supplemental/AppleGothic.ttf'))
except:
    pass


class NewStockPDFGenerator:
    """신규종목추천 PDF 생성기"""

    def __init__(self):
        self.report_date = datetime.now()
        self.output_dir = Path('/Users/wonny/Dev/joungwon.stocks/reports/new_stock/daily')
        self.tracking_dir = Path('/Users/wonny/Dev/joungwon.stocks/reports/new_stock/tracking')
        self.chart_dir = Path('/Users/wonny/Dev/joungwon.stocks/reports/new_stock/charts')

        for d in [self.output_dir, self.tracking_dir, self.chart_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self._setup_styles()

    def _setup_styles(self):
        """PDF 스타일 설정"""
        self.styles = getSampleStyleSheet()

        self.styles.add(ParagraphStyle(
            name='KoreanTitle',
            fontName='AppleGothic',
            fontSize=18,
            leading=22,
            alignment=TA_CENTER,
            spaceAfter=12
        ))

        self.styles.add(ParagraphStyle(
            name='KoreanHeading',
            fontName='AppleGothic',
            fontSize=14,
            leading=18,
            spaceBefore=12,
            spaceAfter=6
        ))

        self.styles.add(ParagraphStyle(
            name='KoreanSubHeading',
            fontName='AppleGothic',
            fontSize=11,
            leading=14,
            spaceBefore=8,
            spaceAfter=4,
            textColor=colors.HexColor('#1E3A5F')
        ))

        self.styles.add(ParagraphStyle(
            name='KoreanBody',
            fontName='AppleGothic',
            fontSize=10,
            leading=14
        ))

        self.styles.add(ParagraphStyle(
            name='KoreanSmall',
            fontName='AppleGothic',
            fontSize=8,
            leading=11,
            textColor=colors.grey
        ))

        self.styles.add(ParagraphStyle(
            name='KoreanDetail',
            fontName='AppleGothic',
            fontSize=9,
            leading=12,
            leftIndent=10
        ))

    async def generate_daily_report(self, batch_id: str = None, grades: List[str] = None) -> str:
        """
        일일 추천 종목 PDF 리포트 생성 (S/A 등급만)

        Args:
            batch_id: 배치 ID (None이면 최신 배치)
            grades: 포함할 등급 리스트 (기본: ['S', 'A'])

        Returns:
            생성된 PDF 파일 경로
        """
        if grades is None:
            grades = ['S', 'A']  # 기본: S/A 등급만

        # 최신 배치 조회
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
            raise ValueError("추천 데이터가 없습니다")

        # 추천 종목 조회 (S/A 등급만)
        recommendations = await self._get_recommendations(batch_id, grades)

        if not recommendations:
            # S/A 등급 없으면 메시지 출력하고 None 리턴
            print(f"❌ S/A 등급 종목이 없습니다 (배치: {batch_id})")
            return None

        # PDF 생성
        date_str = self.report_date.strftime('%Y-%m-%d')
        time_str = self.report_date.strftime('%H%M')
        filename = f"신규종목추천_{date_str}_{time_str}.pdf"
        filepath = self.output_dir / filename

        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            leftMargin=1.5*cm,
            rightMargin=1.5*cm,
            topMargin=1.5*cm,
            bottomMargin=1.5*cm
        )

        elements = []

        # 1. 헤더
        elements.extend(self._create_header(recommendations))

        # 2. 등급별 요약
        elements.extend(self._create_grade_summary(recommendations))

        # 3. Top 10 요약
        elements.extend(self._create_top10_summary(recommendations))

        # 4. 종목별 상세 분석 (전체)
        elements.extend(await self._create_full_detailed_analysis(recommendations))

        # 5. 지난주 실패 분석 (Phase 4 피드백)
        elements.extend(await self._create_failure_analysis())

        # 6. 등급 분포
        elements.extend(self._create_grade_distribution(recommendations))

        # PDF 빌드
        doc.build(elements)

        print(f"✅ PDF 생성: {filepath}")
        return str(filepath)

    async def _get_recommendations(self, batch_id: str, grades: List[str] = None) -> List[Dict]:
        """추천 종목 조회 (등급 필터링)"""
        if grades is None:
            grades = ['S', 'A']

        query = """
        SELECT
            id,
            stock_code,
            stock_name,
            recommendation_date,
            pbr,
            per,
            close_price,
            rsi_14,
            ai_grade,
            ai_confidence,
            ai_key_material,
            ai_policy_alignment,
            ai_buy_point,
            ai_risk_factor,
            quant_score,
            qual_score,
            final_score,
            rank_in_batch
        FROM smart_recommendations
        WHERE batch_id = $1
        AND ai_grade = ANY($2)
        ORDER BY
            CASE ai_grade WHEN 'S' THEN 1 WHEN 'A' THEN 2 ELSE 3 END,
            final_score DESC
        """
        return await db.fetch(query, batch_id, grades)

    async def _get_price_history(self, recommendation_id: int) -> List[Dict]:
        """종목의 일별 가격 추적 이력 조회"""
        query = """
        SELECT track_date, track_price, return_rate, days_held
        FROM smart_price_tracking
        WHERE recommendation_id = $1
        ORDER BY track_date ASC
        """
        return await db.fetch(query, recommendation_id)

    def _create_header(self, recommendations: List[Dict]) -> List:
        """헤더 섹션"""
        elements = []

        # 제목
        title = Paragraph("신규종목 AI 추천 리포트", self.styles['KoreanTitle'])
        elements.append(title)

        # 날짜 및 요약 정보
        rec_date = recommendations[0]['recommendation_date'] if recommendations else date.today()
        summary = f"""
        <b>생성일시:</b> {self.report_date.strftime('%Y-%m-%d %H:%M')} |
        <b>추천일:</b> {rec_date} |
        <b>총 추천종목:</b> {len(recommendations)}개
        """
        elements.append(Paragraph(summary, self.styles['KoreanBody']))
        elements.append(Spacer(1, 0.5*cm))

        return elements

    def _create_grade_summary(self, recommendations: List[Dict]) -> List:
        """등급별 요약"""
        elements = []

        elements.append(Paragraph("📊 등급별 현황", self.styles['KoreanHeading']))

        # 등급 카운트
        grade_counts = {'S': 0, 'A': 0, 'B': 0, 'C': 0, 'D': 0}
        for rec in recommendations:
            grade = rec.get('ai_grade', 'D')
            if grade in grade_counts:
                grade_counts[grade] += 1

        total = len(recommendations)
        data = [['등급', 'S', 'A', 'B', 'C', 'D', '합계']]
        data.append([
            '종목수',
            str(grade_counts['S']),
            str(grade_counts['A']),
            str(grade_counts['B']),
            str(grade_counts['C']),
            str(grade_counts['D']),
            str(total)
        ])

        table = Table(data, colWidths=[2*cm]*7)
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'AppleGothic'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A5F')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 0.5*cm))

        return elements

    def _create_top10_summary(self, recommendations: List[Dict]) -> List:
        """Top 10 요약 테이블"""
        elements = []

        elements.append(Paragraph("📈 Top 10 추천 종목", self.styles['KoreanHeading']))

        # 테이블 데이터
        data = [['순위', '종목명', '등급', '점수', 'PBR', 'PER', '현재가']]

        for i, rec in enumerate(recommendations[:10], 1):
            pbr = rec.get('pbr') or 0
            per = rec.get('per') or 0
            data.append([
                str(i),
                rec['stock_name'],
                rec.get('ai_grade', '-'),
                f"{rec.get('final_score', 0):.1f}",
                f"{pbr:.2f}" if pbr else '-',
                f"{per:.1f}" if per else '-',
                f"{rec.get('close_price', 0):,}"
            ])

        table = Table(data, colWidths=[1*cm, 3.5*cm, 1*cm, 1.5*cm, 1.5*cm, 1.5*cm, 2.5*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'AppleGothic'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A5F')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 0.5*cm))

        return elements

    async def _create_full_detailed_analysis(self, recommendations: List[Dict]) -> List:
        """전체 종목 상세 분석 (핵심재료 전체 표시 + 일별 추적)"""
        elements = []

        elements.append(PageBreak())
        elements.append(Paragraph("📋 종목별 상세 분석", self.styles['KoreanTitle']))
        elements.append(Spacer(1, 0.5*cm))

        for i, rec in enumerate(recommendations, 1):
            # 종목 헤더
            grade_color = {
                'S': '#FF6B6B', 'A': '#4ECDC4', 'B': '#45B7D1',
                'C': '#96CEB4', 'D': '#FFEAA7'
            }.get(rec.get('ai_grade', 'D'), '#FFEAA7')

            header = f"<b>{i}. {rec['stock_name']}</b> ({rec['stock_code']}) - <font color='{grade_color}'><b>{rec.get('ai_grade', '-')}등급</b></font>"
            elements.append(Paragraph(header, self.styles['KoreanSubHeading']))

            # 지표 테이블
            pbr = rec.get('pbr') or 0
            per = rec.get('per') or 0
            rsi = rec.get('rsi_14') or 0
            metrics_data = [
                ['점수', 'PBR', 'PER', 'RSI', '현재가'],
                [
                    f"{rec.get('final_score', 0):.1f}",
                    f"{pbr:.2f}" if pbr else '-',
                    f"{per:.1f}" if per else '-',
                    f"{rsi:.1f}" if rsi else '-',
                    f"{rec.get('close_price', 0):,}원"
                ]
            ]

            metrics_table = Table(metrics_data, colWidths=[2.5*cm]*5)
            metrics_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'AppleGothic'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E8E8E8')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(metrics_table)
            elements.append(Spacer(1, 0.2*cm))

            # 핵심재료 (전체)
            key_material = rec.get('ai_key_material') or '-'
            elements.append(Paragraph(f"<b>📌 핵심재료:</b>", self.styles['KoreanDetail']))
            elements.append(Paragraph(key_material, self.styles['KoreanDetail']))
            elements.append(Spacer(1, 0.1*cm))

            # 매수포인트 (전체)
            buy_point = rec.get('ai_buy_point') or '-'
            elements.append(Paragraph(f"<b>🎯 매수포인트:</b>", self.styles['KoreanDetail']))
            elements.append(Paragraph(buy_point, self.styles['KoreanDetail']))
            elements.append(Spacer(1, 0.1*cm))

            # 정책관련성 (전체)
            policy = rec.get('ai_policy_alignment') or '-'
            elements.append(Paragraph(f"<b>📋 정책관련성:</b>", self.styles['KoreanDetail']))
            elements.append(Paragraph(policy, self.styles['KoreanDetail']))
            elements.append(Spacer(1, 0.1*cm))

            # 리스크 요인 (전체)
            risk = rec.get('ai_risk_factor') or '-'
            elements.append(Paragraph(f"<b>⚠️ 리스크 요인:</b>", self.styles['KoreanDetail']))
            elements.append(Paragraph(risk, self.styles['KoreanDetail']))

            # 일별 가격 추적 이력
            price_history = await self._get_price_history(rec['id'])
            if price_history and len(price_history) > 0:
                elements.append(Spacer(1, 0.2*cm))
                elements.append(Paragraph(f"<b>📊 일별 가격 추적:</b>", self.styles['KoreanDetail']))

                tracking_data = [['날짜', '가격', '수익률', '경과일']]
                for ph in price_history[-7:]:  # 최근 7일
                    ret_str = f"{ph['return_rate']:+.2f}%"
                    tracking_data.append([
                        str(ph['track_date']),
                        f"{ph['track_price']:,}",
                        ret_str,
                        f"{ph['days_held']}일"
                    ])

                tracking_table = Table(tracking_data, colWidths=[3*cm, 2.5*cm, 2*cm, 1.5*cm])
                tracking_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), 'AppleGothic'),
                    ('FONTSIZE', (0, 0), (-1, -1), 7),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#D5E8D4')),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ]))
                elements.append(tracking_table)

            elements.append(Spacer(1, 0.3*cm))

            # 구분선
            elements.append(Paragraph("─" * 60, self.styles['KoreanSmall']))
            elements.append(Spacer(1, 0.2*cm))

            # 페이지 브레이크 (10개마다)
            if i % 8 == 0 and i < len(recommendations):
                elements.append(PageBreak())

        return elements

    async def _create_failure_analysis(self) -> List:
        """지난주 실패 분석 섹션 (Phase 4 피드백)"""
        elements = []

        # 지난 7일간 손실 종목 조회 (-5% 이하)
        query = """
        WITH latest_tracking AS (
            SELECT DISTINCT ON (recommendation_id)
                recommendation_id, track_price, return_rate, days_held, track_date
            FROM smart_price_tracking
            WHERE track_date >= CURRENT_DATE - INTERVAL '7 days'
            ORDER BY recommendation_id, track_date DESC
        )
        SELECT
            sr.stock_code,
            sr.stock_name,
            sr.ai_grade,
            sr.close_price as rec_price,
            sr.ai_key_material,
            sr.ai_risk_factor,
            sr.recommendation_date,
            lt.track_price,
            lt.return_rate,
            lt.days_held
        FROM smart_recommendations sr
        JOIN latest_tracking lt ON sr.id = lt.recommendation_id
        WHERE lt.return_rate <= -5
        ORDER BY lt.return_rate ASC
        LIMIT 10
        """
        failed_stocks = await db.fetch(query)

        if not failed_stocks:
            return elements  # 실패 종목 없으면 섹션 생략

        elements.append(PageBreak())
        elements.append(Paragraph("⚠️ 지난주 실패 분석 (Phase 4 피드백)", self.styles['KoreanTitle']))
        elements.append(Spacer(1, 0.3*cm))

        elements.append(Paragraph(
            "손실 -5% 이상 종목의 원인 분석입니다. 향후 추천 정확도 개선에 활용됩니다.",
            self.styles['KoreanSmall']
        ))
        elements.append(Spacer(1, 0.3*cm))

        # 실패 종목 요약 테이블
        summary_data = [['종목명', '등급', '추천가', '현재가', '수익률', '경과일']]
        for stock in failed_stocks:
            summary_data.append([
                stock['stock_name'][:8],
                stock['ai_grade'] or '-',
                f"{stock['rec_price']:,}",
                f"{stock['track_price']:,}",
                f"{stock['return_rate']:+.1f}%",
                f"{stock['days_held']}일"
            ])

        summary_table = Table(summary_data, colWidths=[3*cm, 1*cm, 2*cm, 2*cm, 1.5*cm, 1.5*cm])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'AppleGothic'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#C0392B')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FADBD8')]),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 0.5*cm))

        # 종목별 실패 원인 분석
        elements.append(Paragraph("📋 실패 원인 분석", self.styles['KoreanSubHeading']))
        elements.append(Spacer(1, 0.2*cm))

        for i, stock in enumerate(failed_stocks[:5], 1):  # 상위 5개만 상세 분석
            header = f"<b>{i}. {stock['stock_name']}</b> ({stock['stock_code']}) - <font color='red'>{stock['return_rate']:+.1f}%</font>"
            elements.append(Paragraph(header, self.styles['KoreanDetail']))

            # 추천 당시 핵심재료
            key_material = stock.get('ai_key_material') or '정보 없음'
            elements.append(Paragraph(f"<b>추천 당시 핵심재료:</b> {key_material[:100]}...", self.styles['KoreanSmall']))

            # 리스크 요인 (사전 경고 확인)
            risk_factor = stock.get('ai_risk_factor') or '정보 없음'
            elements.append(Paragraph(f"<b>사전 경고 리스크:</b> {risk_factor[:100]}...", self.styles['KoreanSmall']))

            # 교훈 (간단한 분석)
            lesson = "리스크 요인이 현실화되었을 가능성 높음. 향후 해당 패턴 경계 필요."
            elements.append(Paragraph(f"<b>교훈:</b> {lesson}", self.styles['KoreanSmall']))

            elements.append(Spacer(1, 0.2*cm))

        # 개선 제안
        elements.append(Spacer(1, 0.3*cm))
        elements.append(Paragraph("🎯 개선 제안", self.styles['KoreanSubHeading']))
        suggestions = """
        1. 리스크 요인이 명확한 종목은 등급 하향 검토<br/>
        2. 거래량 급감 시 조기 손절 기준 강화<br/>
        3. 테마 과열 종목 필터링 기준 추가<br/>
        4. AI 등급과 실제 성과 간 상관관계 재분석
        """
        elements.append(Paragraph(suggestions, self.styles['KoreanSmall']))

        return elements

    def _create_grade_distribution(self, recommendations: List[Dict]) -> List:
        """등급 분포 (마지막 페이지)"""
        elements = []

        elements.append(PageBreak())
        elements.append(Paragraph("📊 등급 분포 요약", self.styles['KoreanHeading']))

        # 등급 카운트
        grade_counts = {'S': 0, 'A': 0, 'B': 0, 'C': 0, 'D': 0}
        for rec in recommendations:
            grade = rec.get('ai_grade', 'D')
            if grade in grade_counts:
                grade_counts[grade] += 1

        total = len(recommendations)
        data = [['등급', 'S', 'A', 'B', 'C', 'D', '합계']]
        data.append([
            '종목수',
            str(grade_counts['S']),
            str(grade_counts['A']),
            str(grade_counts['B']),
            str(grade_counts['C']),
            str(grade_counts['D']),
            str(total)
        ])
        data.append([
            '비율',
            f"{grade_counts['S']/total*100:.1f}%" if total > 0 else '0%',
            f"{grade_counts['A']/total*100:.1f}%" if total > 0 else '0%',
            f"{grade_counts['B']/total*100:.1f}%" if total > 0 else '0%',
            f"{grade_counts['C']/total*100:.1f}%" if total > 0 else '0%',
            f"{grade_counts['D']/total*100:.1f}%" if total > 0 else '0%',
            '100%'
        ])

        table = Table(data, colWidths=[2*cm]*7)
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'AppleGothic'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A5F')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))

        elements.append(table)

        # 면책 조항
        elements.append(Spacer(1, 1*cm))
        disclaimer = """
        <b>면책 조항:</b><br/>
        본 리포트는 AI 분석 결과이며, 투자 판단은 본인 책임입니다.<br/>
        과거 성과가 미래 수익을 보장하지 않습니다.<br/>
        투자 전 반드시 자체 분석을 수행하시기 바랍니다.
        """
        elements.append(Paragraph(disclaimer, self.styles['KoreanSmall']))

        return elements


async def main():
    """테스트 실행"""
    await db.connect()

    try:
        generator = NewStockPDFGenerator()
        pdf_path = await generator.generate_daily_report()
        print(f"\n✅ PDF 생성 완료: {pdf_path}")
    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
