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
    """추천 리포트 PDF 생성기 (NewStockPDFGenerator 래퍼)"""

    def __init__(self, output_dir: str = None):
        # PDF 출력 경로 고정
        self.output_dir = "/Users/wonny/Dev/joungwon.stocks/reports/new_stock/daily"

    async def generate_markdown(
        self,
        results: List[Dict],
        batch_id: str = None
    ) -> str:
        """
        PDF 형식 리포트 생성 (NewStockPDFGenerator 사용)

        Returns:
            리포트 파일 경로
        """
        import os
        from 신규종목추천.src.reports.pdf_generator import NewStockPDFGenerator

        os.makedirs(self.output_dir, exist_ok=True)
        filepath = f"{self.output_dir}/신규종목추천.pdf"

        # S/A 등급 종목 확인
        top_picks = [r for r in results if r.get('ai_grade') in ['S', 'A']] if results else []

        if top_picks:
            # S/A 등급 종목이 있으면 NewStockPDFGenerator로 상세 리포트 생성
            try:
                generator = NewStockPDFGenerator()
                pdf_path = await generator.generate_daily_report(batch_id=batch_id)
                if pdf_path:
                    # 생성된 파일을 고정 경로로 복사
                    import shutil
                    shutil.copy(pdf_path, filepath)
                    logger.info(f"PDF 리포트 생성 (상세): {filepath}")
                    return filepath
            except Exception as e:
                logger.error(f"NewStockPDFGenerator 실패: {e}")

        # S/A 등급이 없거나 생성 실패 시 추적 리포트 생성
        return await self._generate_tracking_report(filepath, batch_id)

    async def _generate_tracking_report(self, filepath: str, batch_id: str = None) -> str:
        """신규 추천 없을 때 추적 종목 + 히스토리 리포트 생성"""
        import os
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm, cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        # 폰트 등록
        font_path = "/Users/wonny/Dev/joungwon.stocks/fonts/NanumGothic.ttf"
        font_bold_path = "/Users/wonny/Dev/joungwon.stocks/fonts/NanumGothicBold.ttf"

        try:
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('NanumGothic', font_path))
            if os.path.exists(font_bold_path):
                pdfmetrics.registerFont(TTFont('NanumGothicBold', font_bold_path))
        except:
            pass

        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )

        # 스타일 설정
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontName='NanumGothicBold' if os.path.exists(font_bold_path) else 'Helvetica-Bold',
            fontSize=24,
            spaceAfter=12,
            alignment=1
        )
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontName='NanumGothic' if os.path.exists(font_path) else 'Helvetica',
            fontSize=14,
            spaceAfter=20,
            alignment=1
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontName='NanumGothicBold' if os.path.exists(font_bold_path) else 'Helvetica-Bold',
            fontSize=14,
            spaceBefore=12,
            spaceAfter=8
        )
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontName='NanumGothic' if os.path.exists(font_path) else 'Helvetica',
            fontSize=10,
            spaceAfter=6
        )
        no_result_style = ParagraphStyle(
            'NoResultStyle',
            parent=styles['Normal'],
            fontName='NanumGothicBold' if os.path.exists(font_bold_path) else 'Helvetica-Bold',
            fontSize=18,
            spaceAfter=20,
            alignment=1,
            textColor=colors.gray
        )

        story = []
        now = datetime.now()

        # 제목
        story.append(Paragraph("신규종목추천 리포트", title_style))
        story.append(Paragraph(f"{now.strftime('%Y-%m-%d %H:%M:%S')}", date_style))
        story.append(Spacer(1, 10*mm))
        story.append(Paragraph("오늘 신규추천종목 없음", no_result_style))
        story.append(Spacer(1, 10*mm))

        # 추적 중인 종목 조회 (최근 7일 S/A 등급)
        tracking_query = """
        SELECT DISTINCT ON (sr.stock_code)
            sr.id, sr.stock_code, sr.stock_name, sr.recommendation_date,
            sr.ai_grade, sr.final_score, sr.close_price, sr.ai_key_material
        FROM smart_recommendations sr
        WHERE sr.ai_grade IN ('S', 'A')
          AND sr.recommendation_date >= CURRENT_DATE - INTERVAL '7 days'
        ORDER BY sr.stock_code, sr.recommendation_date DESC
        """
        tracking_stocks = await db.fetch(tracking_query)

        if tracking_stocks:
            story.append(Paragraph("추적 중인 종목 (최근 7일 S/A등급)", heading_style))

            for t in tracking_stocks:
                # 종목 헤더
                grade_color = '#FF6B6B' if t['ai_grade'] == 'S' else '#4ECDC4'
                header = f"<b>{t['stock_name']}</b> ({t['stock_code']}) - <font color='{grade_color}'><b>{t['ai_grade']}등급</b></font>"
                story.append(Paragraph(header, normal_style))

                # 기본 정보 테이블
                rec_date = t['recommendation_date']
                rec_date_str = rec_date.strftime('%Y-%m-%d') if hasattr(rec_date, 'strftime') else str(rec_date)

                info_data = [
                    ['추천일', rec_date_str, '추천가', f"{t['close_price']:,}원"],
                    ['최종점수', f"{t['final_score']:.1f}", '', '']
                ]
                info_table = Table(info_data, colWidths=[50, 80, 50, 80])
                info_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), 'NanumGothic' if os.path.exists(font_path) else 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8E8E8')),
                    ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#E8E8E8')),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ]))
                story.append(info_table)

                # 핵심재료
                if t.get('ai_key_material'):
                    story.append(Paragraph(f"<b>핵심재료:</b> {t['ai_key_material']}", normal_style))

                # 일별 가격 추적
                tracking_data_query = """
                SELECT track_date, track_price, return_rate, days_held
                FROM smart_price_tracking
                WHERE recommendation_id = $1
                ORDER BY track_date ASC
                """
                price_history = await db.fetch(tracking_data_query, t['id'])

                if price_history:
                    story.append(Paragraph("<b>일별 가격 추적:</b>", normal_style))
                    track_data = [['날짜', '가격', '수익률', '경과일']]
                    for ph in price_history[-7:]:
                        track_date = ph['track_date']
                        track_date_str = track_date.strftime('%m/%d') if hasattr(track_date, 'strftime') else str(track_date)[:5]
                        ret_color = 'red' if ph['return_rate'] < 0 else 'blue'
                        track_data.append([
                            track_date_str,
                            f"{ph['track_price']:,}",
                            f"{ph['return_rate']:+.2f}%",
                            f"{ph['days_held']}일"
                        ])

                    track_table = Table(track_data, colWidths=[50, 70, 60, 40])
                    track_table.setStyle(TableStyle([
                        ('FONTNAME', (0, 0), (-1, -1), 'NanumGothic' if os.path.exists(font_path) else 'Helvetica'),
                        ('FONTSIZE', (0, 0), (-1, -1), 8),
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#D5E8D4')),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ]))
                    story.append(track_table)

                story.append(Spacer(1, 5*mm))
                story.append(Paragraph("─" * 50, normal_style))
                story.append(Spacer(1, 3*mm))

        # 히스토리 섹션
        history_query = """
        SELECT recommendation_date, stock_code, stock_name, ai_grade, final_score, rank_in_batch
        FROM smart_recommendations
        WHERE ai_grade IN ('S', 'A')
          AND recommendation_date >= CURRENT_DATE - INTERVAL '14 days'
        ORDER BY recommendation_date DESC, rank_in_batch
        """
        history = await db.fetch(history_query)

        if history:
            story.append(PageBreak())
            story.append(Paragraph("추천 히스토리 (최근 14일)", heading_style))

            history_data = [['추천일', '종목명', '등급', '점수']]
            for h in history[:15]:
                rec_date = h['recommendation_date']
                rec_date_str = rec_date.strftime('%Y-%m-%d') if hasattr(rec_date, 'strftime') else str(rec_date)
                history_data.append([
                    rec_date_str,
                    h['stock_name'][:10],
                    h['ai_grade'],
                    f"{h['final_score']:.1f}"
                ])

            history_table = Table(history_data, colWidths=[80, 90, 40, 50])
            history_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#455A64')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'NanumGothicBold' if os.path.exists(font_bold_path) else 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'NanumGothic' if os.path.exists(font_path) else 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ECEFF1')]),
            ]))
            story.append(history_table)

        if not tracking_stocks and not history:
            story.append(Paragraph("추천 히스토리가 없습니다.", normal_style))

        # 면책조항
        story.append(Spacer(1, 15*mm))
        disclaimer_style = ParagraphStyle(
            'Disclaimer',
            parent=styles['Normal'],
            fontName='NanumGothic' if os.path.exists(font_path) else 'Helvetica',
            fontSize=8,
            textColor=colors.gray,
            alignment=1
        )
        story.append(Paragraph("본 리포트는 AI 분석 결과이며, 투자 판단은 본인 책임입니다.", disclaimer_style))

        doc.build(story)
        logger.info(f"추적 리포트 생성: {filepath}")
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
