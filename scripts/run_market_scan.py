#!/usr/bin/env python3
"""
AI Sniper - Market Scan 실행 스크립트 (Phase 9.5)
신규 종목 발굴 + 추천 검증 시스템

Usage:
    python scripts/run_market_scan.py                        # 기본 (KOSPI)
    python scripts/run_market_scan.py --market KOSPI --pdf   # KOSPI + PDF
    python scripts/run_market_scan.py --market ALL --aegis   # 전체시장 + AEGIS
    python scripts/run_market_scan.py --date 20251128        # 특정 날짜

Output:
    - reports/new_stock/aegis_picks.json
    - reports/new_stock/신규종목추천.pdf
    - DB: new_stock_recommendations 테이블
"""
import asyncio
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from io import BytesIO

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.aegis.discovery import OpportunityFinder, RecommendationTracker


async def run_scan(
    target_date: str = None,
    market: str = "KOSPI",
    use_aegis: bool = False,
    generate_pdf: bool = False,
    save_to_db: bool = True
):
    """마켓 스캔 실행"""
    print("=" * 60)
    print("🎯 AI Sniper - 신규 종목 발굴 (Phase 9.5)")
    print(f"   시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   대상일: {target_date or '최근 거래일'}")
    print(f"   시장: {market}")
    print(f"   AEGIS 분석: {'활성화' if use_aegis else '비활성화'}")
    print("=" * 60)

    # OpportunityFinder 실행
    finder = OpportunityFinder(market=market)
    results = await finder.find_opportunities(
        target_date=target_date,
        use_aegis=use_aegis
    )

    # 결과 출력
    print("\n" + finder.get_summary())

    # JSON 저장 (새 경로)
    json_path = save_json_report(finder)

    # DB 저장
    if save_to_db and results:
        tracker = RecommendationTracker()
        await tracker.save_recommendations(results)
        await tracker.disconnect()
        print("   💾 DB 저장 완료")

    # PDF 생성
    if generate_pdf and results:
        pdf_path = await generate_enhanced_pdf(finder, tracker if save_to_db else None)
        print(f"📄 PDF 저장: {pdf_path}")

    print("\n" + "=" * 60)
    print("✅ AI Sniper 완료")
    print("=" * 60)

    return results


def save_json_report(finder: OpportunityFinder) -> str:
    """JSON 리포트 저장 (새 경로: reports/new_stock/)"""
    output_dir = Path(__file__).parent.parent / "reports" / "new_stock"
    output_dir.mkdir(parents=True, exist_ok=True)

    json_file = output_dir / "aegis_picks.json"

    report = finder.report
    report_dict = {
        "scan_date": report.scan_date,
        "market": finder.market,
        "total_scanned": report.total_scanned,
        "candidates_filtered": report.candidates_filtered,
        "deep_analyzed": report.deep_analyzed,
        "generated_at": report.generated_at,
        "recommendations": [
            {
                "code": r.code,
                "name": r.name,
                "market": r.market,
                "current_price": r.current_price,
                "change_rate": r.change_rate,
                "aegis_score": r.aegis_score,
                "scanner_score": r.scanner_score,
                "key_reasons": r.key_reasons,
                "technical_score": r.technical_score,
                "supply_score": r.supply_score,
            }
            for r in finder.results
        ]
    }

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(report_dict, f, ensure_ascii=False, indent=2)

    print(f"💾 JSON 저장: {json_file}")
    return str(json_file)


async def generate_enhanced_pdf(finder: OpportunityFinder, tracker: RecommendationTracker = None) -> str:
    """개선된 PDF 리포트 생성 (3섹션)"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
        PageBreak, HRFlowable
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # 폰트 등록
    font_path = Path(__file__).parent.parent / "fonts" / "NanumGothic.ttf"
    if font_path.exists():
        try:
            pdfmetrics.registerFont(TTFont('NanumGothic', str(font_path)))
            font_name = 'NanumGothic'
        except Exception:
            font_name = 'Helvetica'
    else:
        font_name = 'Helvetica'

    # 출력 경로
    output_dir = Path(__file__).parent.parent / "reports" / "new_stock"
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / "신규종목추천.pdf"

    # PDF 생성
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=15*mm,
        leftMargin=15*mm,
        topMargin=15*mm,
        bottomMargin=15*mm
    )

    styles = getSampleStyleSheet()

    # 커스텀 스타일
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontName=font_name,
        fontSize=18,
        spaceAfter=10,
        textColor=colors.HexColor('#1a1a2e')
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontName=font_name,
        fontSize=14,
        spaceBefore=15,
        spaceAfter=8,
        textColor=colors.HexColor('#16213e')
    )
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        leading=14
    )
    small_style = ParagraphStyle(
        'Small',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#555555')
    )

    elements = []
    report = finder.report

    # ========== 섹션 1: 제목 + 요약 ==========
    title = f"🎯 AI Sniper 신규종목추천"
    elements.append(Paragraph(title, title_style))

    subtitle = f"{report.scan_date} | {finder.market} | {report.generated_at}"
    elements.append(Paragraph(subtitle, small_style))
    elements.append(Spacer(1, 5*mm))

    # 요약 박스
    summary_data = [
        ['스캔 대상', '1차 필터', '심층 분석', '최종 추천'],
        [f'{report.total_scanned:,}개', f'{report.candidates_filtered}개',
         f'{report.deep_analyzed}개', f'{len(report.recommendations)}개']
    ]
    summary_table = Table(summary_data, colWidths=[40*mm, 40*mm, 40*mm, 40*mm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8f4f8')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, 1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 8*mm))

    # ========== 섹션 2: 추천 종목 테이블 ==========
    elements.append(Paragraph("📊 오늘의 추천 종목 (Top 5)", heading_style))

    table_data = [['순위', '종목명', '현재가', '등락률', 'AEGIS', '핵심 근거']]
    for i, r in enumerate(finder.results[:5], 1):
        reasons = ", ".join(r.key_reasons[:2]) if r.key_reasons else "-"
        change_str = f"+{r.change_rate:.1f}%" if r.change_rate >= 0 else f"{r.change_rate:.1f}%"
        table_data.append([
            str(i),
            r.name,
            f"{r.current_price:,}",
            change_str,
            f"{r.aegis_score:.1f}",
            reasons[:20]
        ])

    main_table = Table(table_data, colWidths=[12*mm, 35*mm, 28*mm, 22*mm, 18*mm, 55*mm])
    main_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('ALIGN', (-1, 1), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
    ]))
    elements.append(main_table)
    elements.append(Spacer(1, 10*mm))

    # ========== 섹션 3: 종목별 상세 분석 ==========
    elements.append(Paragraph("📝 종목별 상세 분석", heading_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cccccc')))

    for i, r in enumerate(finder.results[:5], 1):
        # 종목 헤더
        header = f"▶ {i}. {r.name} ({r.code}) - {r.market}"
        elements.append(Paragraph(header, ParagraphStyle(
            'StockHeader',
            parent=normal_style,
            fontSize=11,
            fontName=font_name,
            spaceBefore=8,
            spaceAfter=4,
            textColor=colors.HexColor('#1a1a2e')
        )))

        # 가격 정보
        change_str = f"+{r.change_rate:.1f}%" if r.change_rate >= 0 else f"{r.change_rate:.1f}%"
        price_line = f"현재가: {r.current_price:,}원 | 등락률: {change_str} | AEGIS: {r.aegis_score:.1f}"
        elements.append(Paragraph(price_line, small_style))

        # 추천 근거
        if r.key_reasons:
            reasons_text = "🔍 추천 근거: " + " / ".join(r.key_reasons)
            elements.append(Paragraph(reasons_text, small_style))

        # 세부 점수
        scores_text = f"기술점수: {r.technical_score:.1f} | 수급점수: {r.supply_score:.1f}"
        elements.append(Paragraph(scores_text, small_style))

        elements.append(Spacer(1, 3*mm))

    # ========== 섹션 4: 과거 추천 검증 ==========
    if tracker:
        try:
            await tracker.connect()
            completed = await tracker.get_completed_recommendations(limit=10)
            summary = await tracker.get_performance_summary(days=14)

            if completed:
                elements.append(PageBreak())
                elements.append(Paragraph("📈 과거 추천 검증 (최근 2주)", heading_style))

                verify_data = [['추천일', '종목명', '추천가', '최종가', '수익률', '상태']]
                for rec in completed[:10]:
                    ret = rec.get('final_return', 0) or 0
                    ret_str = f"+{ret:.1f}%" if ret >= 0 else f"{ret:.1f}%"
                    verify_data.append([
                        str(rec.get('rec_date', '-')),
                        rec.get('stock_name', '-'),
                        f"{rec.get('recommended_price', 0):,}",
                        f"{rec.get('final_price', 0):,}",
                        ret_str,
                        'D+14 ✓'
                    ])

                verify_table = Table(verify_data, colWidths=[25*mm, 35*mm, 28*mm, 28*mm, 22*mm, 22*mm])
                verify_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3436')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, -1), font_name),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
                ]))
                elements.append(verify_table)

                # 검증 요약
                elements.append(Spacer(1, 5*mm))
                summary_text = f"📊 검증 요약: 평균 수익률 {summary.avg_return:.1f}%, 승률 {summary.win_rate:.0f}% ({summary.completed}건 완료)"
                elements.append(Paragraph(summary_text, normal_style))

        except Exception as e:
            print(f"   ⚠️ 검증 데이터 조회 실패: {e}")

    # ========== 면책 조항 ==========
    elements.append(Spacer(1, 15*mm))
    disclaimer = "⚠️ 본 리포트는 참고용이며, 투자 판단의 책임은 투자자 본인에게 있습니다. AI 분석은 과거 데이터 기반이며 미래 수익을 보장하지 않습니다."
    elements.append(Paragraph(disclaimer, ParagraphStyle(
        'Disclaimer',
        parent=small_style,
        fontSize=8,
        textColor=colors.HexColor('#888888')
    )))

    doc.build(elements)
    return str(pdf_path)


def main():
    parser = argparse.ArgumentParser(description='AI Sniper - 신규 종목 발굴 (Phase 9.5)')
    parser.add_argument('--date', type=str, help='스캔 날짜 (YYYYMMDD)')
    parser.add_argument('--market', type=str, default='KOSPI',
                        choices=['KOSPI', 'KOSDAQ', 'ALL'],
                        help='대상 시장 (기본: KOSPI)')
    parser.add_argument('--aegis', action='store_true', help='AEGIS 심층 분석 활성화')
    parser.add_argument('--pdf', action='store_true', help='PDF 리포트 생성')
    parser.add_argument('--no-db', action='store_true', help='DB 저장 비활성화')

    args = parser.parse_args()

    asyncio.run(run_scan(
        target_date=args.date,
        market=args.market,
        use_aegis=args.aegis,
        generate_pdf=args.pdf,
        save_to_db=not args.no_db
    ))


if __name__ == "__main__":
    main()
