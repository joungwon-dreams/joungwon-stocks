"""
신규종목추천 시스템 설정
"""
import os
from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class DatabaseConfig:
    """데이터베이스 설정"""
    host: str = os.getenv('DB_HOST', 'localhost')
    port: int = int(os.getenv('DB_PORT', '5432'))
    database: str = os.getenv('DB_NAME', 'stock_investment_db')
    user: str = os.getenv('DB_USER', 'wonny')
    password: str = os.getenv('DB_PASSWORD', '')

    @property
    def dsn(self) -> str:
        if self.password:
            return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        return f"postgresql://{self.user}@{self.host}:{self.port}/{self.database}"


@dataclass
class Phase1AConfig:
    """Phase 1A: SQL 기반 1차 필터 설정"""
    # 밸류에이션 필터 (완화: 모멘텀 종목 포함)
    pbr_min: float = 0.1
    pbr_max: float = 1.5  # 0.5 → 1.5 완화 (성장주 포함)
    per_min: float = 1.0
    per_max: float = 20.0  # 15 → 20 완화 (적정 성장성)

    # 유동성 필터
    min_volume: int = 50_000  # 최소 5만주 (유동성 확보)
    min_market_cap: int = 50_000_000_000  # 최소 500억 (코스닥 기준)

    # 거래대금 필터 (Phase 1A SQL에서 사용)
    min_trading_value: int = 5_000_000_000  # 최소 50억원 거래대금

    # 시장 필터
    include_kosdaq: bool = False  # 코스닥 제외 (KOSPI만)

    # 결과 제한
    max_candidates: int = 300  # 200 → 300 (모멘텀 필터용 풀 확대)


@dataclass
class Phase1BConfig:
    """Phase 1B: 기술적 지표 필터 설정 (모멘텀 강화)"""
    # RSI 필터
    rsi_min: float = 20.0
    rsi_max: float = 80.0
    rsi_period: int = 14

    # 이격도 필터
    disparity_20_max: float = 115.0
    disparity_60_max: float = 120.0

    # 수급 필터 (연기금 또는 기관 순매수)
    require_institutional_buy: bool = False

    # OHLCV 데이터 기간
    ohlcv_days: int = 60

    # ========== 모멘텀 필터 (NEW) ==========
    # 거래량 활력 (Volume Dynamics)
    volume_surge_ratio: float = 2.0  # 5일 평균 대비 200% 이상 급증
    min_trading_value: int = 5_000_000_000  # 최소 거래대금 50억원
    volume_turnover_min: float = 0.5  # 최소 거래회전율 0.5%

    # 추세 돌파 (Trend & Breakout)
    require_ma_alignment: bool = True  # 정배열 필수 (주가 > 20일선)
    high_52w_proximity: float = 0.85  # 52주 고가 대비 85% 이상
    breakout_20d_high: bool = True  # 20일 고가 돌파 여부 체크

    # 변동성 (Volatility)
    min_intraday_range: float = 2.5  # 일중 변동폭 최소 2.5%
    min_5d_avg_range: float = 2.0  # 5일 평균 변동폭 최소 2.0%
    require_bullish_candle: bool = True  # 최근 3일 내 장대양봉(3%+) 필요

    # 필터 모드: 'strict' (모든 조건 AND) or 'flexible' (일부 OR)
    momentum_filter_mode: str = 'flexible'

    # 결과 제한
    max_candidates: int = 100


@dataclass
class Phase2AConfig:
    """Phase 2A: 배치 데이터 수집 설정"""
    # 캐시 설정
    cache_ttl_hours: int = 6

    # Rate Limit (calls per minute)
    rate_limits: Dict[str, int] = field(default_factory=lambda: {
        'naver_api': 30,
        'daum_api': 30,
        'fnguide': 12,
        'wise_report': 12,
        'securities': 12,
        'news': 12,
    })

    # 수집할 뉴스 개수
    news_limit: int = 10

    # 수집할 리포트 개수
    report_limit: int = 5


@dataclass
class Phase2BConfig:
    """Phase 2B: Gemini AI 분석 설정"""
    api_key: str = os.getenv('GEMINI_API_KEY', '')
    model_name: str = 'gemini-2.0-flash'

    # 배치 설정
    batch_size: int = 5
    rate_delay_seconds: int = 10  # API 호출 간격

    # 프롬프트 설정
    max_tokens: int = 4096
    temperature: float = 0.3


@dataclass
class Phase3Config:
    """Phase 3: 스코어링 설정"""
    # 점수 가중치
    quant_weight: float = 0.4
    qual_weight: float = 0.6

    # AI 등급별 점수
    grade_scores: Dict[str, int] = field(default_factory=lambda: {
        'S': 100,
        'A': 80,
        'B': 60,
        'C': 40,
        'D': 20,
    })


@dataclass
class Settings:
    """전체 설정"""
    db: DatabaseConfig = field(default_factory=DatabaseConfig)
    phase1a: Phase1AConfig = field(default_factory=Phase1AConfig)
    phase1b: Phase1BConfig = field(default_factory=Phase1BConfig)
    phase2a: Phase2AConfig = field(default_factory=Phase2AConfig)
    phase2b: Phase2BConfig = field(default_factory=Phase2BConfig)
    phase3: Phase3Config = field(default_factory=Phase3Config)

    # 로깅
    log_level: str = 'INFO'
    log_dir: str = '신규종목추천/logs'

    # 리포트 출력
    report_dir: str = 'reports/new_stock'


# 전역 설정 인스턴스
settings = Settings()
