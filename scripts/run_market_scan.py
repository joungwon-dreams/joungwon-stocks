#!/usr/bin/env python3
"""
AI Sniper - Market Scan 실행 스크립트
Phase 9: 신규 종목 발굴 시스템

Usage:
    python scripts/run_market_scan.py                    # 기본 실행 (Scanner만)
    python scripts/run_market_scan.py --aegis            # AEGIS 심층 분석 포함
    python scripts/run_market_scan.py --date 20251128    # 특정 날짜 스캔
    python scripts/run_market_scan.py --pdf              # PDF 리포트 생성

Output:
    - reports/new_stock/daily/aegis_picks.json
    - reports/new_stock/daily/신규종목추천.pdf (--pdf 옵션)
"""
import asyncio
import argparse
import sys
from datetime import datetime
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.aegis.discovery import MarketScanner, OpportunityFinder


async def run_scan(
    target_date: str = None,
    use_aegis: bool = False,
    generate_pdf: bool = False
):
    """마켓 스캔 실행"""
    print("=" * 60)
    print("🎯 AI Sniper - 신규 종목 발굴")
    print(f"   시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   대상일: {target_date or '최근 거래일'}")
    print(f"   AEGIS 분석: {'활성화' if use_aegis else '비활성화'}")
    print("=" * 60)

    # OpportunityFinder 실행
    finder = OpportunityFinder()
    results = await finder.find_opportunities(
        target_date=target_date,
        use_aegis=use_aegis
    )

    # 결과 출력
    print("\n" + finder.get_summary())

    # JSON 저장
    json_path = finder.save_report()

    # PDF 생성 (옵션)
    if generate_pdf and results:
        pdf_path = await generate_pdf_report(finder)
        print(f"📄 PDF 저장: {pdf_path}")

    print("\n" + "=" * 60)
    print("✅ AI Sniper 완료")
    print("=" * 60)

    return results


async def generate_pdf_report(finder: OpportunityFinder) -> str:
    """PDF 리포트 생성"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # 폰트 등록
    font_path = Path(__file__).parent.parent / "fonts" / "NanumGothic.ttf"
    if font_path.exists():
        pdfmetrics.registerFont(TTFont('NanumGothic', str(font_path)))
        font_name = 'NanumGothic'
    else:
        font_name = 'Helvetica'

    # 출력 경로
    output_dir = Path(__file__).parent.parent / "reports" / "new_stock" / "daily"
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
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Title'],
        fontName=font_name,
        fontSize=18,
        spaceAfter=20
    )
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10
    )

    elements = []

    # 제목
    report = finder.report
    title = f"🎯 AI Sniper 추천 종목 ({report.scan_date})"
    elements.append(Paragraph(title, title_style))

    # 요약 정보
    summary = f"""
    스캔 대상: {report.total_scanned:,}개 종목<br/>
    1차 필터: {report.candidates_filtered}개 통과<br/>
    심층 분석: {report.deep_analyzed}개<br/>
    최종 추천: {len(report.recommendations)}개<br/>
    생성 시각: {report.generated_at}
    """
    elements.append(Paragraph(summary, normal_style))
    elements.append(Spacer(1, 10*mm))

    # 추천 종목 테이블
    table_data = [
        ['순위', '종목명', '현재가', '등락률', 'AEGIS', '핵심 근거']
    ]

    for i, r in enumerate(finder.results, 1):
        reasons = ", ".join(r.key_reasons[:2]) if r.key_reasons else "-"
        table_data.append([
            str(i),
            r.name,
            f"{r.current_price:,}",
            f"{r.change_rate:+.2f}%",
            f"{r.aegis_score:.1f}",
            reasons
        ])

    table = Table(table_data, colWidths=[15*mm, 40*mm, 30*mm, 25*mm, 20*mm, 50*mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
    ]))
    elements.append(table)

    # 면책 조항
    elements.append(Spacer(1, 15*mm))
    disclaimer = """
    ⚠️ 본 리포트는 참고용이며, 투자 판단의 책임은 투자자 본인에게 있습니다.
    AI 분석은 과거 데이터 기반이며 미래 수익을 보장하지 않습니다.
    """
    elements.append(Paragraph(disclaimer, normal_style))

    doc.build(elements)
    return str(pdf_path)


def main():
    parser = argparse.ArgumentParser(description='AI Sniper - 신규 종목 발굴')
    parser.add_argument('--date', type=str, help='스캔 날짜 (YYYYMMDD)')
    parser.add_argument('--aegis', action='store_true', help='AEGIS 심층 분석 활성화')
    parser.add_argument('--pdf', action='store_true', help='PDF 리포트 생성')

    args = parser.parse_args()

    asyncio.run(run_scan(
        target_date=args.date,
        use_aegis=args.aegis,
        generate_pdf=args.pdf
    ))


if __name__ == "__main__":
    main()
