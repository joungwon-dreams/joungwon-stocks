#!/usr/bin/env python3
"""
InvestmentReporter - Phase 9.5 AI 투자 리포트 생성기
추천 종목에 대한 상세 투자 분석 리포트를 Gemini AI로 생성

포함 내용:
- 핵심 투자 포인트
- 기술적/수급/재료 분석
- 향후 시나리오 (긍정/부정)
- 대응 전략 (목표가/손절가)
"""
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from src.gemini.client import GeminiClient
from .finder import DiscoveryResult


@dataclass
class InvestmentReport:
    """투자 분석 리포트"""
    stock_code: str
    stock_name: str

    # AI 분석 결과
    executive_summary: str = ""  # 핵심 요약
    investment_points: List[str] = None  # 투자 포인트
    technical_analysis: str = ""  # 기술적 분석
    supply_analysis: str = ""  # 수급 분석
    catalyst_analysis: str = ""  # 재료/모멘텀 분석

    # 시나리오
    bull_scenario: str = ""  # 긍정 시나리오
    bear_scenario: str = ""  # 부정 시나리오

    # 대응 전략
    target_price: int = 0  # 목표가
    stop_loss: int = 0  # 손절가
    strategy: str = ""  # 매매 전략

    # 메타
    generated_at: str = ""
    raw_response: str = ""

    def __post_init__(self):
        if self.investment_points is None:
            self.investment_points = []


class InvestmentReporter:
    """
    AI 투자 리포트 생성기
    Gemini를 활용한 상세 분석 리포트 생성
    """

    def __init__(self):
        self.gemini = GeminiClient()
        self.reports: Dict[str, InvestmentReport] = {}

    async def generate_report(
        self,
        result: DiscoveryResult,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> InvestmentReport:
        """
        추천 종목에 대한 상세 투자 리포트 생성

        Args:
            result: OpportunityFinder에서 나온 추천 종목
            additional_data: 추가 데이터 (뉴스, 공시 등)

        Returns:
            InvestmentReport
        """
        prompt = self._build_prompt(result, additional_data)

        try:
            response = await self.gemini.generate_content(prompt)
            if not response:
                return self._create_fallback_report(result)

            report = self._parse_response(result, response)
            self.reports[result.code] = report
            return report

        except Exception as e:
            print(f"   ⚠️ AI 리포트 생성 실패 ({result.name}): {e}")
            return self._create_fallback_report(result)

    async def generate_batch_reports(
        self,
        results: List[DiscoveryResult],
        max_reports: int = 5
    ) -> List[InvestmentReport]:
        """
        여러 종목에 대한 리포트 일괄 생성

        Args:
            results: 추천 종목 리스트
            max_reports: 최대 리포트 수 (API 비용 절감)

        Returns:
            리포트 리스트
        """
        reports = []
        targets = results[:max_reports]

        print(f"\n📝 AI 투자 리포트 생성 중... ({len(targets)}개)")

        for i, r in enumerate(targets, 1):
            print(f"   [{i}/{len(targets)}] {r.name}...")
            report = await self.generate_report(r)
            reports.append(report)

            # Rate limiting (Gemini API 제한)
            if i < len(targets):
                await asyncio.sleep(1)

        print(f"   ✅ 리포트 생성 완료")
        return reports

    def _build_prompt(
        self,
        result: DiscoveryResult,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """AI 분석 프롬프트 생성"""

        # 기본 정보
        badge_info = f"[{result.badge}] " if result.badge else ""
        reasons = ", ".join(result.key_reasons) if result.key_reasons else "없음"

        prompt = f"""당신은 한국 주식 전문 애널리스트입니다. 다음 종목에 대한 상세 투자 분석 리포트를 작성해주세요.

## 분석 대상
- 종목명: {badge_info}{result.name} ({result.code})
- 시장: {result.market}
- 현재가: {result.current_price:,}원
- 등락률: {result.change_rate:+.1f}%

## AEGIS 분석 점수
- 종합 점수: {result.aegis_score:.1f}점
- 기술적 점수: {result.technical_score:.1f}점
- 수급 점수: {result.supply_score:.1f}점

## 선정 근거
{reasons}

## 요청 사항
다음 형식으로 상세 분석 리포트를 작성해주세요:

### 1. 핵심 요약 (2-3문장)
이 종목을 왜 주목해야 하는지 핵심 포인트를 요약

### 2. 투자 포인트 (3개)
- 포인트 1: [구체적 근거]
- 포인트 2: [구체적 근거]
- 포인트 3: [구체적 근거]

### 3. 기술적 분석
현재 차트 패턴, 이평선 배열, RSI 등 기술적 관점 분석

### 4. 수급 분석
외국인/기관 매매 동향 및 수급 관점 분석

### 5. 재료/모멘텀
업종 동향, 뉴스, 이슈 등 주가 움직임에 영향을 줄 수 있는 요인

### 6. 시나리오 분석
- 긍정 시나리오: [조건과 예상 주가]
- 부정 시나리오: [리스크 요인과 예상 주가]

### 7. 매매 전략
- 목표가: [가격]원 (현재가 대비 +X%)
- 손절가: [가격]원 (현재가 대비 -X%)
- 전략: [구체적인 매매 전략 제안]

분석은 객관적이고 구체적으로 작성하되, 투자 결정에 실질적으로 도움이 되도록 해주세요.
"""
        return prompt

    def _parse_response(
        self,
        result: DiscoveryResult,
        response: str
    ) -> InvestmentReport:
        """AI 응답 파싱"""
        report = InvestmentReport(
            stock_code=result.code,
            stock_name=result.name,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            raw_response=response
        )

        lines = response.split('\n')
        current_section = ""
        section_content = []

        for line in lines:
            line = line.strip()

            # 섹션 헤더 감지
            if line.startswith("### 1.") or "핵심 요약" in line:
                if current_section and section_content:
                    self._apply_section(report, current_section, section_content)
                current_section = "summary"
                section_content = []
            elif line.startswith("### 2.") or "투자 포인트" in line:
                if current_section and section_content:
                    self._apply_section(report, current_section, section_content)
                current_section = "points"
                section_content = []
            elif line.startswith("### 3.") or "기술적 분석" in line:
                if current_section and section_content:
                    self._apply_section(report, current_section, section_content)
                current_section = "technical"
                section_content = []
            elif line.startswith("### 4.") or "수급 분석" in line:
                if current_section and section_content:
                    self._apply_section(report, current_section, section_content)
                current_section = "supply"
                section_content = []
            elif line.startswith("### 5.") or "재료" in line or "모멘텀" in line:
                if current_section and section_content:
                    self._apply_section(report, current_section, section_content)
                current_section = "catalyst"
                section_content = []
            elif line.startswith("### 6.") or "시나리오" in line:
                if current_section and section_content:
                    self._apply_section(report, current_section, section_content)
                current_section = "scenario"
                section_content = []
            elif line.startswith("### 7.") or "매매 전략" in line:
                if current_section and section_content:
                    self._apply_section(report, current_section, section_content)
                current_section = "strategy"
                section_content = []
            elif line and not line.startswith("###"):
                section_content.append(line)

        # 마지막 섹션 처리
        if current_section and section_content:
            self._apply_section(report, current_section, section_content)

        # 목표가/손절가 추출
        self._extract_prices(report, result.current_price)

        return report

    def _apply_section(
        self,
        report: InvestmentReport,
        section: str,
        content: List[str]
    ):
        """섹션 내용 적용"""
        text = "\n".join(content).strip()

        if section == "summary":
            report.executive_summary = text
        elif section == "points":
            # 투자 포인트 파싱
            points = []
            for line in content:
                if line.startswith("-") or line.startswith("•"):
                    points.append(line.lstrip("-•").strip())
            report.investment_points = points if points else [text]
        elif section == "technical":
            report.technical_analysis = text
        elif section == "supply":
            report.supply_analysis = text
        elif section == "catalyst":
            report.catalyst_analysis = text
        elif section == "scenario":
            # 긍정/부정 시나리오 분리
            bull_lines = []
            bear_lines = []
            current = None
            for line in content:
                if "긍정" in line:
                    current = "bull"
                elif "부정" in line:
                    current = "bear"
                elif current == "bull":
                    bull_lines.append(line)
                elif current == "bear":
                    bear_lines.append(line)
            report.bull_scenario = "\n".join(bull_lines).strip()
            report.bear_scenario = "\n".join(bear_lines).strip()
        elif section == "strategy":
            report.strategy = text

    def _extract_prices(self, report: InvestmentReport, current_price: int):
        """목표가/손절가 추출"""
        import re

        # 전략 텍스트에서 가격 추출
        text = report.strategy + " " + report.raw_response

        # 목표가 패턴
        target_patterns = [
            r'목표가[:\s]*(\d{1,3}(?:,\d{3})*)\s*원',
            r'목표\s*가격[:\s]*(\d{1,3}(?:,\d{3})*)\s*원',
        ]
        for pattern in target_patterns:
            match = re.search(pattern, text)
            if match:
                report.target_price = int(match.group(1).replace(',', ''))
                break

        # 손절가 패턴
        stop_patterns = [
            r'손절가[:\s]*(\d{1,3}(?:,\d{3})*)\s*원',
            r'손절\s*가격[:\s]*(\d{1,3}(?:,\d{3})*)\s*원',
        ]
        for pattern in stop_patterns:
            match = re.search(pattern, text)
            if match:
                report.stop_loss = int(match.group(1).replace(',', ''))
                break

        # 기본값 설정 (추출 실패시)
        if report.target_price == 0:
            report.target_price = int(current_price * 1.05)  # +5%
        if report.stop_loss == 0:
            report.stop_loss = int(current_price * 0.97)  # -3%

    def _create_fallback_report(self, result: DiscoveryResult) -> InvestmentReport:
        """AI 실패시 기본 리포트"""
        return InvestmentReport(
            stock_code=result.code,
            stock_name=result.name,
            executive_summary=f"{result.name}은(는) AEGIS 분석 결과 {result.aegis_score:.1f}점을 기록하여 추천 대상으로 선정되었습니다.",
            investment_points=result.key_reasons[:3] if result.key_reasons else ["분석 데이터 부족"],
            technical_analysis=f"기술적 점수: {result.technical_score:.1f}점",
            supply_analysis=f"수급 점수: {result.supply_score:.1f}점",
            catalyst_analysis="상세 분석 불가",
            bull_scenario=f"목표가 {int(result.current_price * 1.05):,}원 도달 시 +5% 수익",
            bear_scenario=f"손절가 {int(result.current_price * 0.97):,}원 이탈 시 -3% 손실",
            target_price=int(result.current_price * 1.05),
            stop_loss=int(result.current_price * 0.97),
            strategy="기술적/수급 지표 확인 후 분할 매수 권장",
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

    def get_full_analysis_text(self, report: InvestmentReport) -> str:
        """PDF용 전체 분석 텍스트"""
        points_text = "\n".join([f"• {p}" for p in report.investment_points]) if report.investment_points else "없음"

        return f"""📌 핵심 요약
{report.executive_summary}

💡 투자 포인트
{points_text}

📊 기술적 분석
{report.technical_analysis}

📈 수급 분석
{report.supply_analysis}

🎯 재료/모멘텀
{report.catalyst_analysis}

🔮 시나리오 분석
[긍정] {report.bull_scenario}
[부정] {report.bear_scenario}

⚡ 매매 전략
목표가: {report.target_price:,}원 | 손절가: {report.stop_loss:,}원
{report.strategy}
"""


# CLI 테스트
if __name__ == "__main__":
    from .finder import DiscoveryResult

    async def test():
        reporter = InvestmentReporter()

        # 테스트 데이터
        test_result = DiscoveryResult(
            code="005930",
            name="삼성전자",
            market="KOSPI",
            current_price=70000,
            change_rate=1.5,
            scanner_score=2.0,
            aegis_score=2.5,
            technical_score=1.5,
            supply_score=1.0,
            key_reasons=["이평선 정배열", "외인 순매수", "골든크로스"]
        )

        report = await reporter.generate_report(test_result)
        print(reporter.get_full_analysis_text(report))

    asyncio.run(test())
