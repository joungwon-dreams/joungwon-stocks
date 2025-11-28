"""
Final Signal Validator - Phase 6
Veto System (문지기)

핵심 기능:
- Hard Cutoff (과락) 규칙 적용
- Liquidity Check (유동성 트랩 방지)
- Market Panic 모드 감지
- Disclosure Risk 강제 매도
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging


class ValidationDecision(Enum):
    """검증 결정"""
    PASS = "pass"              # 통과 - 매매 가능
    BLOCK_BUY = "block_buy"    # 매수 금지
    BLOCK_SELL = "block_sell"  # 매도 금지 (희귀)
    FORCE_SELL = "force_sell"  # 강제 매도
    HOLD_ONLY = "hold_only"    # 보유만 가능 (신규 매수 금지)


class BlockReason(Enum):
    """차단 사유"""
    FUNDAMENTAL_RISK = "fundamental_risk"      # 펀더멘털 과락
    MARKET_PANIC = "market_panic"              # 시장 폭락
    LIQUIDITY_TRAP = "liquidity_trap"          # 유동성 부족
    DISCLOSURE_HALT = "disclosure_halt"        # 거래정지 공시
    CALENDAR_CRITICAL = "calendar_critical"    # Critical 경제 이벤트
    OVERHEATED_MARKET = "overheated_market"    # 시장 과열
    HIGH_VOLATILITY = "high_volatility"        # 과도한 변동성


@dataclass
class ValidationResult:
    """검증 결과"""
    decision: ValidationDecision
    reasons: List[BlockReason]
    details: Dict[str, Any]

    # 원본 점수 (참고용)
    original_signal: str
    original_score: float

    # 조정된 점수 (Veto 적용 후)
    adjusted_score: Optional[float]
    adjusted_signal: Optional[str]

    # 경고 메시지
    warnings: List[str]

    # 메타데이터
    validated_at: str


class FinalSignalValidator:
    """
    최종 신호 검증기 (문지기)

    Phase 6 Spec:
    - 모든 점수 계산 후 마지막에 호출
    - Hard Cutoff 규칙으로 위험 신호 차단
    - 유동성/시장 상황 기반 Veto
    """

    # Hard Cutoff 임계값
    THRESHOLDS = {
        'fundamental_min': -2.0,      # 펀더멘털 과락 기준
        'market_panic': -2.0,         # 시장 폭락 기준
        'liquidity_min_krw': 10_000_000_000,  # 최소 거래대금 (100억)
        'vix_extreme': 35.0,          # VIX 극단적 공포
        'volatility_max': 15.0,       # 일일 변동성 최대 (%)
    }

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    async def validate(
        self,
        ticker: str,
        fusion_result: Any,  # FusionResult
        avg_traded_value_5d: float,  # 5일 평균 거래대금 (원)
        daily_volatility: Optional[float] = None,  # 일일 변동성 (%)
    ) -> ValidationResult:
        """
        최종 신호 검증

        Args:
            ticker: 종목코드
            fusion_result: FusionEngine의 분석 결과
            avg_traded_value_5d: 5일 평균 거래대금
            daily_volatility: 일일 변동성 (%)

        Returns:
            ValidationResult: 검증 결과
        """
        self.logger.info(f"Validating signal for {ticker}")

        reasons: List[BlockReason] = []
        warnings: List[str] = []
        details: Dict[str, Any] = {}

        # 원본 정보 저장
        original_signal = fusion_result.signal.value
        original_score = fusion_result.final_score

        # === 1. Trading Halt 체크 (최우선) ===
        if fusion_result.trading_halt:
            return ValidationResult(
                decision=ValidationDecision.FORCE_SELL,
                reasons=[BlockReason.DISCLOSURE_HALT],
                details={'halt_reason': fusion_result.halt_reason},
                original_signal=original_signal,
                original_score=original_score,
                adjusted_score=None,
                adjusted_signal='force_sell',
                warnings=['Trading Halt detected - Force Sell required'],
                validated_at=datetime.now().isoformat()
            )

        # === 2. Fundamental Risk 체크 ===
        if fusion_result.fundamental_score < self.THRESHOLDS['fundamental_min']:
            reasons.append(BlockReason.FUNDAMENTAL_RISK)
            details['fundamental_score'] = fusion_result.fundamental_score
            warnings.append(
                f"Fundamental score ({fusion_result.fundamental_score:.2f}) "
                f"below threshold ({self.THRESHOLDS['fundamental_min']})"
            )

        # === 3. Market Panic 체크 ===
        if fusion_result.market_context_score < self.THRESHOLDS['market_panic']:
            reasons.append(BlockReason.MARKET_PANIC)
            details['market_context_score'] = fusion_result.market_context_score
            warnings.append(
                f"Market in panic mode (score: {fusion_result.market_context_score:.2f})"
            )

        # === 4. Liquidity Trap 체크 ===
        if avg_traded_value_5d < self.THRESHOLDS['liquidity_min_krw']:
            reasons.append(BlockReason.LIQUIDITY_TRAP)
            details['avg_traded_value_5d'] = avg_traded_value_5d
            details['min_required'] = self.THRESHOLDS['liquidity_min_krw']
            warnings.append(
                f"Low liquidity: {avg_traded_value_5d/1e8:.1f}억 "
                f"(min: {self.THRESHOLDS['liquidity_min_krw']/1e8:.0f}억)"
            )

        # === 5. Calendar Critical 체크 ===
        calendar_risk = fusion_result.details.get('calendar_risk_level', 'low')
        if calendar_risk == 'critical':
            reasons.append(BlockReason.CALENDAR_CRITICAL)
            details['calendar_risk'] = calendar_risk
            details['calendar_warning'] = fusion_result.details.get('calendar_warning')
            warnings.append(
                f"Critical calendar event: {fusion_result.details.get('calendar_warning')}"
            )

        # === 6. VIX Extreme 체크 ===
        fear_greed = fusion_result.details.get('fear_greed_score', 50)
        market_condition = fusion_result.details.get('market_condition', 'neutral')
        if market_condition in ['panic', 'fear']:
            reasons.append(BlockReason.OVERHEATED_MARKET)
            details['market_condition'] = market_condition
            details['fear_greed_score'] = fear_greed
            warnings.append(f"Market in {market_condition} mode (F&G: {fear_greed})")

        # === 7. High Volatility 체크 ===
        if daily_volatility and daily_volatility > self.THRESHOLDS['volatility_max']:
            reasons.append(BlockReason.HIGH_VOLATILITY)
            details['daily_volatility'] = daily_volatility
            warnings.append(
                f"High volatility: {daily_volatility:.1f}% "
                f"(max: {self.THRESHOLDS['volatility_max']}%)"
            )

        # === 결정 로직 ===
        decision = self._determine_decision(reasons, original_signal)
        adjusted_score, adjusted_signal = self._adjust_signal(
            decision, original_score, original_signal, reasons
        )

        return ValidationResult(
            decision=decision,
            reasons=reasons,
            details=details,
            original_signal=original_signal,
            original_score=original_score,
            adjusted_score=adjusted_score,
            adjusted_signal=adjusted_signal,
            warnings=warnings,
            validated_at=datetime.now().isoformat()
        )

    def _determine_decision(
        self,
        reasons: List[BlockReason],
        original_signal: str
    ) -> ValidationDecision:
        """결정 로직"""
        if not reasons:
            return ValidationDecision.PASS

        # 강제 매도 케이스
        if BlockReason.DISCLOSURE_HALT in reasons:
            return ValidationDecision.FORCE_SELL

        # 매수 금지 케이스 (Hard Block)
        hard_block_reasons = {
            BlockReason.FUNDAMENTAL_RISK,
            BlockReason.LIQUIDITY_TRAP,
        }
        if reasons and hard_block_reasons.intersection(reasons):
            return ValidationDecision.BLOCK_BUY

        # 신규 매수 금지 (Soft Block - 보유는 가능)
        soft_block_reasons = {
            BlockReason.MARKET_PANIC,
            BlockReason.CALENDAR_CRITICAL,
            BlockReason.OVERHEATED_MARKET,
            BlockReason.HIGH_VOLATILITY,
        }
        if reasons and soft_block_reasons.intersection(reasons):
            # 기존 보유는 괜찮지만 신규 매수는 금지
            if original_signal in ['strong_buy', 'buy']:
                return ValidationDecision.HOLD_ONLY
            return ValidationDecision.PASS

        return ValidationDecision.PASS

    def _adjust_signal(
        self,
        decision: ValidationDecision,
        original_score: float,
        original_signal: str,
        reasons: List[BlockReason]
    ) -> Tuple[Optional[float], Optional[str]]:
        """신호 조정"""
        if decision == ValidationDecision.PASS:
            return original_score, original_signal

        if decision == ValidationDecision.FORCE_SELL:
            return -999.0, 'force_sell'

        if decision == ValidationDecision.BLOCK_BUY:
            # 매수 신호였다면 hold로 변경
            if original_signal in ['strong_buy', 'buy']:
                return 0.0, 'hold'
            return original_score, original_signal

        if decision == ValidationDecision.HOLD_ONLY:
            # 매수 신호를 hold로 강제 변경
            if original_signal in ['strong_buy', 'buy']:
                return 0.0, 'hold'
            return original_score, original_signal

        return original_score, original_signal

    def get_liquidity_grade(self, avg_traded_value: float) -> str:
        """유동성 등급 반환"""
        if avg_traded_value >= 100_000_000_000:  # 1000억 이상
            return "A"  # 최우량
        elif avg_traded_value >= 50_000_000_000:  # 500억 이상
            return "B"  # 우량
        elif avg_traded_value >= 10_000_000_000:  # 100억 이상
            return "C"  # 보통
        elif avg_traded_value >= 5_000_000_000:   # 50억 이상
            return "D"  # 주의
        else:
            return "F"  # 거래 불가

    def should_reduce_position(self, validation_result: ValidationResult) -> bool:
        """포지션 축소 권고 여부"""
        risky_conditions = {
            BlockReason.MARKET_PANIC,
            BlockReason.CALENDAR_CRITICAL,
            BlockReason.HIGH_VOLATILITY,
        }
        return bool(risky_conditions.intersection(validation_result.reasons))


# Singleton instance
_validator_instance: Optional[FinalSignalValidator] = None


def get_signal_validator() -> FinalSignalValidator:
    """Get singleton FinalSignalValidator instance"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = FinalSignalValidator()
    return _validator_instance
