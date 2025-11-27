"""
Phase 1B: 기술적 지표 필터
200개 → 50개로 축소

목표: ~30초 내 실행
방법: DB에서 OHLCV 배치 로드 → Pandas로 지표 계산
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np

import sys
sys.path.insert(0, '.')
from 신규종목추천.config.settings import settings
from 신규종목추천.src.utils.database import db

logger = logging.getLogger(__name__)


class Phase1BFilter:
    """
    기술적 지표 기반 2차 필터

    필터 조건:
    1. RSI(14): 30 ~ 60 (과매수/과매도 아닌 구간)
    2. 이격도(20일): <= 105% (20일선 대비 5% 이하)
    3. 이격도(60일): <= 110% (60일선 대비 10% 이하)
    4. 수급: 연기금 또는 기관 순매수 > 0
    """

    def __init__(self, config=None):
        self.config = config or settings.phase1b

    async def filter(
        self,
        candidates: List[Dict[str, Any]],
        batch_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        Phase 1B 필터 실행

        Args:
            candidates: Phase 1A 결과 (200개)
            batch_id: 배치 식별자

        Returns:
            기술적 조건 통과한 종목 리스트 (50개 이하)
        """
        if not candidates:
            logger.warning("Phase 1B: 입력 후보가 없습니다")
            return []

        start_time = datetime.now()
        codes = [c['stock_code'] for c in candidates]

        logger.info(f"Phase 1B 시작: {len(codes)}개 종목 기술적 분석")
        logger.info(f"필터 조건: RSI({self.config.rsi_min}~{self.config.rsi_max}), "
                   f"이격도20<={self.config.disparity_20_max}, "
                   f"이격도60<={self.config.disparity_60_max}")

        # 1. OHLCV 데이터 배치 로드
        ohlcv_data = await self._load_batch_ohlcv(codes, self.config.ohlcv_days)
        logger.info(f"OHLCV 로드 완료: {len(ohlcv_data)}개 종목")

        # 2. 수급 데이터 배치 로드
        supply_data = await self._load_batch_supply_demand(codes, days=20)
        logger.info(f"수급 데이터 로드 완료: {len(supply_data)}개 종목")

        # 3. 종목별 기술적 지표 계산 및 필터링
        results = []
        candidates_dict = {c['stock_code']: c for c in candidates}

        for code in codes:
            df = ohlcv_data.get(code)
            if df is None or len(df) < 20:  # 최소 20일 데이터만 필요 (60 → 20 완화)
                logger.debug(f"{code}: OHLCV 데이터 부족 ({len(df) if df is not None else 0}일)")
                continue

            # 기술적 지표 계산
            indicators = self._calculate_indicators(df)
            if indicators is None:
                continue

            rsi = indicators['rsi']
            disparity_20 = indicators['disparity_20']
            disparity_60 = indicators['disparity_60']

            # 수급 데이터
            supply = supply_data.get(code, {})
            pension_net = supply.get('pension_net_buy', 0)
            institution_net = supply.get('institution_net_buy', 0)
            foreign_net = supply.get('foreign_net_buy', 0)

            # 필터 조건 체크
            rsi_pass = self.config.rsi_min <= rsi <= self.config.rsi_max
            disparity_20_pass = disparity_20 <= self.config.disparity_20_max
            disparity_60_pass = disparity_60 <= self.config.disparity_60_max

            # 수급 조건: 연기금 또는 기관 순매수
            if self.config.require_institutional_buy:
                supply_pass = pension_net > 0 or institution_net > 0
            else:
                supply_pass = True

            # ========== 모멘텀 필터 (NEW) ==========
            volume_surge = indicators.get('volume_surge_ratio', 0)
            trading_value = indicators.get('trading_value', 0)
            ma_alignment = indicators.get('ma_alignment', False)
            high_52w_ratio = indicators.get('high_52w_ratio', 0)
            breakout_20d = indicators.get('breakout_20d', False)
            intraday_range = indicators.get('intraday_range', 0)
            avg_5d_range = indicators.get('avg_5d_range', 0)
            has_bullish_candle = indicators.get('has_bullish_candle', False)
            price_change_3d = indicators.get('price_change_3d', 0)

            # 모멘텀 점수 계산 (0~100)
            momentum_score = self._calculate_momentum_score(
                volume_surge_ratio=volume_surge,
                trading_value=trading_value,
                ma_alignment=ma_alignment,
                high_52w_ratio=high_52w_ratio,
                breakout_20d=breakout_20d,
                intraday_range=intraday_range,
                avg_5d_range=avg_5d_range,
                has_bullish_candle=has_bullish_candle,
                price_change_3d=price_change_3d,
            )

            # 모멘텀 필터 모드
            if self.config.momentum_filter_mode == 'strict':
                # 엄격 모드: 모든 조건 충족 필요
                momentum_pass = (
                    volume_surge >= self.config.volume_surge_ratio or
                    trading_value >= self.config.min_trading_value
                ) and (
                    ma_alignment or breakout_20d
                ) and (
                    avg_5d_range >= self.config.min_5d_avg_range or has_bullish_candle
                )
            else:
                # 유연 모드: 모멘텀 점수 30점 이상 OR 기존 조건 충족
                momentum_pass = momentum_score >= 30 or (volume_surge >= 1.5 or price_change_3d >= 5)

            if rsi_pass and disparity_20_pass and disparity_60_pass and supply_pass and momentum_pass:
                # 원본 데이터와 병합
                original = candidates_dict.get(code, {})

                # 통합 점수 계산 (정량 40% + 모멘텀 60%)
                quant_score = self._calculate_quant_score(
                    original.get('pbr', 1),
                    rsi,
                    pension_net,
                    institution_net
                )
                total_score = quant_score * 0.4 + momentum_score * 0.6

                result = {
                    **original,
                    'rsi_14': round(rsi, 2),
                    'disparity_20': round(disparity_20, 2),
                    'disparity_60': round(disparity_60, 2),
                    'ma_5': int(indicators['ma_5']),
                    'ma_20': int(indicators['ma_20']),
                    'ma_60': int(indicators['ma_60']),
                    'pension_net_buy': pension_net,
                    'institution_net_buy': institution_net,
                    'foreign_net_buy': foreign_net,
                    # 모멘텀 지표 (NEW)
                    'volume_surge_ratio': round(volume_surge, 2),
                    'trading_value': int(trading_value),
                    'ma_alignment': ma_alignment,
                    'high_52w_ratio': round(high_52w_ratio, 3),
                    'breakout_20d': breakout_20d,
                    'intraday_range': round(intraday_range, 2),
                    'avg_5d_range': round(avg_5d_range, 2),
                    'has_bullish_candle': has_bullish_candle,
                    'price_change_3d': round(price_change_3d, 2),
                    'momentum_score': round(momentum_score, 2),
                    'quant_score': round(quant_score, 2),
                    'total_score': round(total_score, 2),
                }
                results.append(result)

        # 통합 점수 기준 정렬 후 상위 N개 (모멘텀 60% 반영)
        results.sort(key=lambda x: x['total_score'], reverse=True)
        results = results[:self.config.max_candidates]

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Phase 1B 완료: {len(results)}개 종목 선정 ({elapsed:.2f}초)")

        # 캐시 테이블 업데이트
        if batch_id:
            await self._update_candidates(batch_id, results)

        return results

    async def _load_batch_ohlcv(
        self,
        codes: List[str],
        days: int
    ) -> Dict[str, pd.DataFrame]:
        """
        여러 종목의 OHLCV 데이터를 1회 쿼리로 로드

        Args:
            codes: 종목 코드 리스트
            days: 조회 기간 (일)

        Returns:
            종목코드 -> DataFrame 딕셔너리
        """
        query = f"""
            SELECT
                stock_code,
                date as trade_date,
                open as open_price,
                high as high_price,
                low as low_price,
                close as close_price,
                volume
            FROM daily_ohlcv
            WHERE stock_code = ANY($1)
              AND date >= CURRENT_DATE - INTERVAL '{days} days'
            ORDER BY stock_code, date ASC
        """

        rows = await db.fetch(query, codes)

        if not rows:
            return {}

        # DataFrame으로 변환
        df = pd.DataFrame(rows)

        # 종목별로 그룹화
        result = {}
        for code, group in df.groupby('stock_code'):
            result[code] = group.reset_index(drop=True)

        return result

    async def _load_batch_supply_demand(
        self,
        codes: List[str],
        days: int = 20
    ) -> Dict[str, Dict]:
        """
        수급 데이터 배치 로드

        stock_supply_demand 테이블 컬럼:
        - pension_net: 연기금 순매수
        - institution_net: 기관 순매수
        - foreigner_net: 외국인 순매수
        - individual_net: 개인 순매수

        Returns:
            종목코드 -> 수급 데이터 딕셔너리
        """
        query = f"""
            SELECT
                stock_code,
                SUM(COALESCE(pension_net, 0)) as pension_net_buy,
                SUM(COALESCE(institution_net, 0)) as institution_net_buy,
                SUM(COALESCE(foreigner_net, 0)) as foreign_net_buy,
                SUM(COALESCE(individual_net, 0)) as individual_net_buy,
                COUNT(DISTINCT CASE WHEN (pension_net > 0 OR institution_net > 0) THEN date END) as net_buy_days
            FROM stock_supply_demand
            WHERE stock_code = ANY($1)
              AND date >= CURRENT_DATE - INTERVAL '{days} days'
            GROUP BY stock_code
        """

        try:
            rows = await db.fetch(query, codes)
            return {r['stock_code']: dict(r) for r in rows}
        except Exception as e:
            logger.warning(f"수급 데이터 조회 실패: {e}")
            # 빈 데이터 반환 (수급 조건 통과시킴)
            return {}

    def _calculate_indicators(self, df: pd.DataFrame) -> Optional[Dict[str, float]]:
        """
        기술적 지표 계산 (모멘텀 지표 추가)

        Args:
            df: OHLCV DataFrame (20일 이상)

        Returns:
            지표 딕셔너리 또는 None
        """
        if len(df) < 20:
            return None

        close = df['close_price'].astype(float)
        high = df['high_price'].astype(float)
        low = df['low_price'].astype(float)
        open_price = df['open_price'].astype(float)
        volume = df['volume'].astype(float)
        current_price = close.iloc[-1]

        # RSI(14) 계산
        rsi = self._calculate_rsi(close, period=14)

        # 이동평균
        ma_5 = close.rolling(5).mean().iloc[-1]
        ma_20 = close.rolling(20).mean().iloc[-1]
        ma_60 = close.rolling(60).mean().iloc[-1] if len(df) >= 60 else ma_20

        if pd.isna(ma_20) or ma_20 == 0:
            return None

        # 이격도
        disparity_20 = (current_price / ma_20) * 100
        disparity_60 = (current_price / ma_60) * 100 if ma_60 and ma_60 != 0 else disparity_20

        # ========== 모멘텀 지표 (NEW) ==========

        # 1. 거래량 활력 (Volume Dynamics)
        vol_ma_5 = volume.rolling(5).mean().iloc[-1]
        current_volume = volume.iloc[-1]
        volume_surge_ratio = current_volume / vol_ma_5 if vol_ma_5 > 0 else 0

        # 거래대금 (당일)
        trading_value = current_price * current_volume

        # 2. 추세 돌파 (Trend & Breakout)
        # 정배열 여부: 주가 > 5일선 > 20일선
        ma_alignment = current_price > ma_5 > ma_20 if not pd.isna(ma_5) else False

        # 52주 고가 대비 위치
        high_52w = high.max() if len(df) >= 52 else high.rolling(min(len(df), 52)).max().iloc[-1]
        high_52w_ratio = current_price / high_52w if high_52w > 0 else 0

        # 20일 고가 돌파 여부
        high_20d = high.rolling(20).max().iloc[-2] if len(df) >= 21 else high.max()
        breakout_20d = current_price > high_20d

        # 3. 변동성 (Volatility)
        # 일중 변동폭 (당일)
        intraday_range = ((high.iloc[-1] - low.iloc[-1]) / open_price.iloc[-1]) * 100 if open_price.iloc[-1] > 0 else 0

        # 5일 평균 변동폭
        daily_ranges = ((high - low) / open_price * 100).replace([np.inf, -np.inf], 0)
        avg_5d_range = daily_ranges.tail(5).mean()

        # 장대양봉 여부 (최근 3일 내 3% 이상 상승 양봉)
        price_changes = ((close - open_price) / open_price * 100).tail(3)
        has_bullish_candle = any(price_changes > 3.0)

        # 3일 가격 변화율
        price_change_3d = ((close.iloc[-1] - close.iloc[-4]) / close.iloc[-4] * 100) if len(df) >= 4 else 0

        return {
            'rsi': rsi,
            'ma_5': ma_5,
            'ma_20': ma_20,
            'ma_60': ma_60 or ma_20,
            'disparity_20': disparity_20,
            'disparity_60': disparity_60,
            # 모멘텀 지표
            'volume_surge_ratio': volume_surge_ratio,
            'trading_value': trading_value,
            'ma_alignment': ma_alignment,
            'high_52w_ratio': high_52w_ratio,
            'breakout_20d': breakout_20d,
            'intraday_range': intraday_range,
            'avg_5d_range': avg_5d_range,
            'has_bullish_candle': has_bullish_candle,
            'price_change_3d': price_change_3d,
        }

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """RSI 계산"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain.iloc[-1] / loss.iloc[-1] if loss.iloc[-1] != 0 else 0
        rsi = 100 - (100 / (1 + rs))

        return rsi if not pd.isna(rsi) else 50.0

    def _calculate_momentum_score(
        self,
        volume_surge_ratio: float,
        trading_value: float,
        ma_alignment: bool,
        high_52w_ratio: float,
        breakout_20d: bool,
        intraday_range: float,
        avg_5d_range: float,
        has_bullish_candle: bool,
        price_change_3d: float,
    ) -> float:
        """
        모멘텀 점수 계산 (0-100)

        구성:
        - 거래량 활력: 30점
        - 추세 돌파: 40점
        - 변동성: 30점
        """
        score = 0.0

        # ========== 1. 거래량 활력 (30점) ==========
        # 거래량 급증 (최대 20점)
        if volume_surge_ratio >= 3.0:
            score += 20
        elif volume_surge_ratio >= 2.0:
            score += 15
        elif volume_surge_ratio >= 1.5:
            score += 10
        elif volume_surge_ratio >= 1.2:
            score += 5

        # 거래대금 (최대 10점)
        if trading_value >= 50_000_000_000:  # 500억 이상
            score += 10
        elif trading_value >= 20_000_000_000:  # 200억 이상
            score += 7
        elif trading_value >= 10_000_000_000:  # 100억 이상
            score += 5
        elif trading_value >= 5_000_000_000:  # 50억 이상
            score += 3

        # ========== 2. 추세 돌파 (40점) ==========
        # 정배열 (15점)
        if ma_alignment:
            score += 15

        # 52주 고가 근접 (최대 15점)
        if high_52w_ratio >= 0.95:  # 신고가 근접
            score += 15
        elif high_52w_ratio >= 0.90:
            score += 12
        elif high_52w_ratio >= 0.85:
            score += 8
        elif high_52w_ratio >= 0.80:
            score += 5

        # 20일 고가 돌파 (10점)
        if breakout_20d:
            score += 10

        # ========== 3. 변동성 (30점) ==========
        # 일중 변동폭 (최대 10점)
        if intraday_range >= 5.0:
            score += 10
        elif intraday_range >= 3.0:
            score += 7
        elif intraday_range >= 2.0:
            score += 5

        # 5일 평균 변동폭 (최대 10점)
        if avg_5d_range >= 4.0:
            score += 10
        elif avg_5d_range >= 2.5:
            score += 7
        elif avg_5d_range >= 1.5:
            score += 4

        # 장대양봉 (5점)
        if has_bullish_candle:
            score += 5

        # 3일 가격 변화 (최대 5점)
        if price_change_3d >= 10:
            score += 5
        elif price_change_3d >= 5:
            score += 3
        elif price_change_3d >= 3:
            score += 1

        return min(100, score)

    def _calculate_quant_score(
        self,
        pbr: float,
        rsi: float,
        pension_net: int,
        institution_net: int
    ) -> float:
        """
        정량 점수 계산 (0-100)

        구성:
        - PBR 깊이: 40점
        - RSI 위치: 20점
        - 수급 강도: 40점
        """
        score = 0.0

        # Decimal to float 변환
        pbr = float(pbr) if pbr else 0.0
        rsi = float(rsi) if rsi else 50.0
        pension_net = int(pension_net) if pension_net else 0
        institution_net = int(institution_net) if institution_net else 0

        # PBR 점수 (낮을수록 높은 점수)
        if pbr > 0:
            pbr_score = max(0.0, 50.0 - pbr * 40.0)  # PBR 0.2 = 42점, PBR 1.0 = 10점
            score += pbr_score * 0.4

        # RSI 점수 (40~50 구간이 최적)
        if 40 <= rsi <= 50:
            score += 20
        elif 35 <= rsi <= 55:
            score += 15
        elif 30 <= rsi <= 60:
            score += 10

        # 수급 점수
        total_institutional = pension_net + institution_net
        if total_institutional > 10_000_000_000:  # 100억 이상
            score += 40
        elif total_institutional > 5_000_000_000:  # 50억 이상
            score += 30
        elif total_institutional > 1_000_000_000:  # 10억 이상
            score += 20
        elif total_institutional > 0:
            score += 10

        return round(min(100, score), 2)

    async def _update_candidates(self, batch_id: str, candidates: List[Dict]) -> None:
        """Phase 1B 결과를 캐시 테이블에 업데이트"""
        if not candidates:
            return

        query = """
        UPDATE smart_phase1_candidates
        SET
            rsi_14 = $3,
            disparity_20 = $4,
            disparity_60 = $5,
            pension_net_buy = $6,
            institution_net_buy = $7,
            quant_score = $8,
            phase1b_passed = TRUE
        WHERE batch_id = $1 AND stock_code = $2
        """

        args_list = [
            (
                batch_id,
                c['stock_code'],
                c.get('rsi_14'),
                c.get('disparity_20'),
                c.get('disparity_60'),
                c.get('pension_net_buy', 0),
                c.get('institution_net_buy', 0),
                c.get('quant_score', 0),
            )
            for c in candidates
        ]

        await db.executemany(query, args_list)
        logger.info(f"Phase 1B 결과 업데이트: {len(candidates)}개")


async def main():
    """테스트 실행"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    from 신규종목추천.src.phase1.filter_phase1a import Phase1AFilter

    await db.connect()

    try:
        # Phase 1A 실행
        filter_1a = Phase1AFilter()
        candidates_1a = await filter_1a.filter()

        print(f"\n=== Phase 1A 결과: {len(candidates_1a)}개 종목 ===\n")

        # Phase 1B 실행
        filter_1b = Phase1BFilter()
        candidates_1b = await filter_1b.filter(candidates_1a)

        print(f"\n=== Phase 1B 결과: {len(candidates_1b)}개 종목 ===")
        for i, c in enumerate(candidates_1b[:20], 1):
            print(f"{i:2}. {c['stock_code']} {c.get('stock_name', ''):<12} "
                  f"PBR:{c.get('pbr', 0):.2f} RSI:{c.get('rsi_14', 0):.1f} "
                  f"이격20:{c.get('disparity_20', 0):.1f}% "
                  f"수급:{c.get('pension_net_buy', 0) + c.get('institution_net_buy', 0):,.0f} "
                  f"점수:{c.get('quant_score', 0):.1f}")

    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
