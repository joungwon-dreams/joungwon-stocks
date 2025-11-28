# PROJECT AEGIS 현재 상태

> Last Updated: 2025-11-28 14:30

## 개요
PROJECT AEGIS는 한국 주식 시장을 위한 AI 기반 자동 매매 시스템입니다.
- **목표**: 월 3~5% 수익률, 리스크 관리 중심
- **투자금**: 1억원
- **전략**: 퀀트 기반 스윙 트레이딩 + 멀티 전략 앙상블

## 파일 구조
```
src/aegis/
├── __init__.py                    # v0.1.0
├── analysis/
│   ├── indicators.py              # VWAP, RSI, MA 기술 지표
│   ├── signal.py                  # 점수 기반 신호 생성 (-3 ~ +3)
│   └── backtest/
│       ├── engine.py              # BacktestEngine (리스크 관리 통합)
│       ├── strategy.py            # AegisSwingStrategy, MeanReversionStrategy
│       └── performance.py         # PerformanceMonitor, TradeRecord
├── risk/
│   ├── manager.py                 # RiskManager (ATR, Kelly, 포지션 사이징)
│   └── circuit_breaker.py         # CircuitBreaker (일일 손실/거래 제한)
└── ensemble/
    ├── regime.py                  # MarketRegimeClassifier (BULL/BEAR/SIDEWAY)
    ├── registry.py                # StrategyRegistry
    └── orchestrator.py            # StrategyOrchestrator (앙상블 엔진)
```

## 완료된 Phase
| Phase | 내용 | 완료일 |
|-------|------|--------|
| 0 | 기술 지표 + 신호 생성 | 2025-11-28 |
| 1 | 백테스팅 프레임워크 | 2025-11-28 |
| 2 | 리스크 관리 시스템 | 2025-11-28 |
| 3 | 멀티 전략 앙상블 | 2025-11-28 |

## 핵심 설정
```python
# 신호 점수 체계 (-3 ~ +3)
MA 정배열: +1, 역배열: -1
VWAP 지지: +1, 이탈: -1
RSI < 30: +1, RSI > 70: -1

# 리스크 설정
max_capital_per_trade_pct = 0.20  # 20%
risk_per_trade_pct = 0.02         # 2%
atr_multiplier = 2.0              # ATR × 2 손절
max_daily_loss_pct = 0.02         # -2% 일일 한도
max_daily_trades = 10             # 10회 제한

# 레짐 분류
BULL: MA(20) > MA(60) + 2%
BEAR: MA(20) < MA(60) - 2%
SIDEWAY: 그 외
```

## 백테스트 결과 (한국전력 250일)
| 전략 | 수익률 | 거래수 | 승률 | MDD |
|------|--------|--------|------|-----|
| Swing Only | +27.63% | 1 | 100% | 4.96% |
| Mean Reversion | +1.66% | 2 | 100% | 0.11% |
| Ensemble | +1.57% | 10 | 70% | 1.01% |

## 다음 단계
- Phase 3.5: 가중치 최적화 (Grid Search)
- Phase 4: AI 예측 모델 (LSTM)
- Phase 5: 자동매매 + 대시보드

## 관련 문서
- `docs/AI_COLLABORATION_LOG.md` - Claude & Gemini 협업 로그
- `docs/SYSTEM_EVOLUTION_DESIGN_SPEC.md` - 전체 설계 명세
