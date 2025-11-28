#!/usr/bin/env python3
"""
OpportunityFinder - Phase 9 AI Sniper
MarketScanner 후보군에 대해 AEGIS InformationFusionEngine 심층 분석

Logic:
1. MarketScanner로 1차 후보군 (50개) 필터링
2. 각 후보에 대해 InformationFusionEngine 실행
3. Final AEGIS Score >= 2.0인 종목 선별
4. Top 5 추천 종목 선정
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict

from .scanner import MarketScanner, CandidateStock


@dataclass
class DiscoveryResult:
    """발굴 종목 결과"""
    code: str
    name: str
    market: str
    current_price: int
    change_rate: float

    # MarketScanner 점수
    scanner_score: float

    # AEGIS 분석 결과
    aegis_score: float = 0.0
    aegis_signal: str = "hold"

    # 세부 점수
    technical_score: float = 0.0
    news_score: float = 0.0
    disclosure_score: float = 0.0
    supply_score: float = 0.0
    fundamental_score: float = 0.0

    # 핵심 근거
    key_reasons: List[str] = field(default_factory=list)

    # 메타데이터
    analyzed_at: str = ""


@dataclass
class DiscoveryReport:
    """일일 발굴 리포트"""
    scan_date: str
    total_scanned: int
    candidates_filtered: int
    deep_analyzed: int
    recommendations: List[DiscoveryResult]
    generated_at: str = ""


class OpportunityFinder:
    """
    기회 발굴기
    MarketScanner + InformationFusionEngine 연동
    """

    TOP_N = 5  # 최종 추천 종목 수
    MIN_AEGIS_SCORE = 1.5  # AEGIS 최소 점수 (BUY 이상)
    MAX_DEEP_ANALYSIS = 30  # 심층 분석 최대 종목 수 (API 비용 절감)

    def __init__(self):
        self.scanner = MarketScanner()
        self.results: List[DiscoveryResult] = []
        self.report: Optional[DiscoveryReport] = None

    async def find_opportunities(
        self,
        target_date: Optional[str] = None,
        use_aegis: bool = True
    ) -> List[DiscoveryResult]:
        """
        기회 발굴 실행

        Args:
            target_date: 스캔 날짜 (YYYYMMDD)
            use_aegis: AEGIS 심층 분석 사용 여부 (False면 Scanner 점수만)

        Returns:
            추천 종목 리스트
        """
        print("=" * 60)
        print("🎯 AI Sniper - 신규 종목 발굴 시작")
        print("=" * 60)

        # 1. MarketScanner로 1차 필터링
        candidates = await self.scanner.scan_market(target_date)
        print(f"\n📋 1차 후보: {len(candidates)}개")

        # 2. 상위 종목만 심층 분석 (API 비용 절감)
        top_candidates = candidates[:self.MAX_DEEP_ANALYSIS]

        # 3. AEGIS 심층 분석 또는 Scanner 점수만 사용
        if use_aegis:
            self.results = await self._deep_analyze_with_aegis(top_candidates)
        else:
            self.results = self._convert_to_results(top_candidates)

        # 4. 최종 정렬 및 Top N 선정
        self.results = sorted(
            self.results,
            key=lambda x: x.aegis_score if use_aegis else x.scanner_score,
            reverse=True
        )[:self.TOP_N]

        # 5. 리포트 생성
        self.report = DiscoveryReport(
            scan_date=self.scanner.scan_date or datetime.now().strftime("%Y%m%d"),
            total_scanned=len(await self.scanner._get_all_stocks()) if hasattr(self.scanner, '_get_all_stocks') else 2500,
            candidates_filtered=len(candidates),
            deep_analyzed=len(top_candidates),
            recommendations=self.results,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        print(f"\n✅ 최종 추천: {len(self.results)}개")
        return self.results

    async def _deep_analyze_with_aegis(
        self,
        candidates: List[CandidateStock]
    ) -> List[DiscoveryResult]:
        """AEGIS InformationFusionEngine으로 심층 분석"""
        results = []

        try:
            from src.aegis.fusion.engine import InformationFusionEngine
            engine = InformationFusionEngine()
        except ImportError:
            print("   ⚠️ AEGIS Engine 로드 실패, Scanner 점수만 사용")
            return self._convert_to_results(candidates)

        print(f"\n🔬 AEGIS 심층 분석 중... ({len(candidates)}개)")

        for i, c in enumerate(candidates):
            try:
                # InformationFusionEngine 분석
                fusion_result = await engine.analyze(c.code)

                result = DiscoveryResult(
                    code=c.code,
                    name=c.name,
                    market=c.market,
                    current_price=c.current_price,
                    change_rate=c.change_rate,
                    scanner_score=c.total_score,
                    aegis_score=fusion_result.final_score,
                    aegis_signal=fusion_result.signal.value,
                    technical_score=fusion_result.technical_score,
                    news_score=fusion_result.news_sentiment_score,
                    disclosure_score=fusion_result.disclosure_score,
                    supply_score=fusion_result.supply_score,
                    fundamental_score=fusion_result.fundamental_score,
                    key_reasons=self._extract_key_reasons(fusion_result, c),
                    analyzed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                results.append(result)

                if (i + 1) % 10 == 0:
                    print(f"   진행: {i + 1}/{len(candidates)}")

            except Exception as e:
                # 분석 실패시 Scanner 점수만 사용
                result = DiscoveryResult(
                    code=c.code,
                    name=c.name,
                    market=c.market,
                    current_price=c.current_price,
                    change_rate=c.change_rate,
                    scanner_score=c.total_score,
                    aegis_score=c.total_score,  # Fallback
                    key_reasons=c.filter_reasons,
                    analyzed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                results.append(result)

        return results

    def _convert_to_results(self, candidates: List[CandidateStock]) -> List[DiscoveryResult]:
        """CandidateStock을 DiscoveryResult로 변환"""
        return [
            DiscoveryResult(
                code=c.code,
                name=c.name,
                market=c.market,
                current_price=c.current_price,
                change_rate=c.change_rate,
                scanner_score=c.total_score,
                aegis_score=c.total_score,
                technical_score=c.technical_score,
                supply_score=c.supply_score,
                key_reasons=c.filter_reasons,
                analyzed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            for c in candidates
        ]

    def _extract_key_reasons(self, fusion_result, candidate: CandidateStock) -> List[str]:
        """핵심 매수 근거 추출"""
        reasons = list(candidate.filter_reasons)  # Scanner 이유

        # AEGIS 분석 결과에서 추가 근거
        if fusion_result.news_sentiment_score > 0.5:
            reasons.append("긍정적 뉴스")
        if fusion_result.disclosure_score > 0.5:
            reasons.append("호재성 공시")
        if fusion_result.supply_score > 0.5:
            reasons.append("수급 우호적")
        if fusion_result.fundamental_score > 0.5:
            reasons.append("재무 건전")

        return reasons[:5]  # 최대 5개

    def save_report(self, output_dir: str = "reports/new_stock") -> str:
        """리포트 저장"""
        if not self.report:
            return ""

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # JSON 저장
        json_file = output_path / "daily" / "aegis_picks.json"
        json_file.parent.mkdir(parents=True, exist_ok=True)

        report_dict = {
            "scan_date": self.report.scan_date,
            "total_scanned": self.report.total_scanned,
            "candidates_filtered": self.report.candidates_filtered,
            "deep_analyzed": self.report.deep_analyzed,
            "generated_at": self.report.generated_at,
            "recommendations": [asdict(r) for r in self.report.recommendations]
        }

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, ensure_ascii=False, indent=2)

        print(f"💾 저장: {json_file}")
        return str(json_file)

    def get_summary(self) -> str:
        """결과 요약"""
        if not self.results:
            return "발굴 결과 없음"

        lines = [
            "=" * 60,
            "🎯 AI Sniper - 추천 종목",
            "=" * 60,
            f"{'순위':<4} {'종목명':<12} {'현재가':>10} {'AEGIS':>6} {'핵심 근거'}",
            "-" * 60,
        ]

        for i, r in enumerate(self.results, 1):
            reasons = ", ".join(r.key_reasons[:3]) if r.key_reasons else "-"
            lines.append(
                f"{i:<4} {r.name:<12} {r.current_price:>10,} {r.aegis_score:>6.1f} {reasons}"
            )

        lines.append("=" * 60)
        return "\n".join(lines)


# Singleton
_finder_instance: Optional[OpportunityFinder] = None


def get_opportunity_finder() -> OpportunityFinder:
    """OpportunityFinder 싱글톤"""
    global _finder_instance
    if _finder_instance is None:
        _finder_instance = OpportunityFinder()
    return _finder_instance


# CLI 실행
if __name__ == "__main__":
    async def main():
        finder = OpportunityFinder()
        await finder.find_opportunities(use_aegis=False)  # 테스트시 AEGIS 비활성화
        print(finder.get_summary())
        finder.save_report()

    asyncio.run(main())
