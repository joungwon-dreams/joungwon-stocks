#!/usr/bin/env python3
"""
MarketScanner - Phase 9 AI Sniper
전체 시장에서 후보 종목을 1차 필터링

Filters:
- 유동성: 거래대금 100억 이상
- 기술적: RSI, 이평선, 골든크로스
- 수급: 외인/기관 순매수
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import pandas as pd
import numpy as np

from pykrx import stock as pykrx


@dataclass
class CandidateStock:
    """후보 종목 데이터"""
    code: str
    name: str
    market: str  # KOSPI / KOSDAQ
    current_price: int
    change_rate: float
    volume: int
    traded_value: int  # 거래대금

    # Technical indicators
    rsi_14: float = 0.0
    ma_5: float = 0.0
    ma_20: float = 0.0
    ma_60: float = 0.0
    golden_cross: bool = False

    # Supply/Demand
    foreigner_net: int = 0
    institution_net: int = 0

    # Scoring
    technical_score: float = 0.0
    supply_score: float = 0.0
    total_score: float = 0.0

    filter_reasons: List[str] = field(default_factory=list)


class MarketScanner:
    """
    전체 시장 스캐너
    KOSPI/KOSDAQ 전 종목 중 유망 후보군 필터링

    Args:
        market: 대상 시장 ("KOSPI", "KOSDAQ", "ALL")
    """

    # 필터링 기준
    MIN_TRADED_VALUE = 10_000_000_000  # 100억 원
    MIN_PRICE = 1000  # 1000원 이상 (동전주 제외)
    MAX_CANDIDATES = 50  # 최대 후보 수

    # 지원 시장
    VALID_MARKETS = ["KOSPI", "KOSDAQ", "ALL"]

    def __init__(self, market: str = "KOSPI"):
        """
        Args:
            market: 대상 시장 ("KOSPI", "KOSDAQ", "ALL")
        """
        if market.upper() not in self.VALID_MARKETS:
            raise ValueError(f"Invalid market: {market}. Use one of {self.VALID_MARKETS}")
        self.market = market.upper()
        self.candidates: List[CandidateStock] = []
        self.scan_date: Optional[str] = None

    async def scan_market(self, target_date: Optional[str] = None) -> List[CandidateStock]:
        """
        전체 시장 스캔 실행

        Args:
            target_date: 스캔 날짜 (YYYYMMDD), None이면 최근 거래일

        Returns:
            필터링된 후보 종목 리스트
        """
        self.scan_date = target_date or self._get_latest_trading_date()
        market_label = self.market if self.market != "ALL" else "KOSPI+KOSDAQ"
        print(f"📡 Market Scan 시작: {self.scan_date} ({market_label})")

        # 1. 전 종목 리스트 가져오기
        all_stocks = await self._get_all_stocks()
        print(f"   전체 종목 수: {len(all_stocks)}")

        # 2. 기본 필터링 (유동성)
        liquid_stocks = await self._filter_by_liquidity(all_stocks)
        print(f"   유동성 필터 통과: {len(liquid_stocks)}")

        # 3. 기술적 지표 계산
        candidates = await self._calculate_technical_indicators(liquid_stocks)
        print(f"   기술적 분석 완료: {len(candidates)}")

        # 4. 수급 데이터 추가
        candidates = await self._add_supply_demand(candidates)
        print(f"   수급 분석 완료: {len(candidates)}")

        # 5. 종합 스코어링 및 정렬
        scored_candidates = self._calculate_scores(candidates)

        # 6. 상위 N개 선정
        self.candidates = sorted(
            scored_candidates,
            key=lambda x: x.total_score,
            reverse=True
        )[:self.MAX_CANDIDATES]

        print(f"✅ 최종 후보: {len(self.candidates)}개")
        return self.candidates

    def _get_latest_trading_date(self) -> str:
        """최근 거래일 조회"""
        today = datetime.now()
        for i in range(7):
            check_date = (today - timedelta(days=i)).strftime("%Y%m%d")
            try:
                df = pykrx.get_market_ohlcv(check_date, market="KOSPI")
                if len(df) > 0:
                    return check_date
            except Exception:
                continue
        return today.strftime("%Y%m%d")

    def _get_target_markets(self) -> List[str]:
        """스캔 대상 시장 목록 반환"""
        if self.market == "ALL":
            return ["KOSPI", "KOSDAQ"]
        return [self.market]

    async def _get_all_stocks(self) -> List[Dict[str, Any]]:
        """대상 시장의 전 종목 리스트"""
        all_stocks = []
        target_markets = self._get_target_markets()

        for market in target_markets:
            try:
                tickers = pykrx.get_market_ticker_list(self.scan_date, market=market)
                for ticker in tickers:
                    name = pykrx.get_market_ticker_name(ticker)
                    all_stocks.append({
                        "code": ticker,
                        "name": name,
                        "market": market
                    })
            except Exception as e:
                print(f"   ⚠️ {market} 종목 조회 실패: {e}")

        return all_stocks

    async def _filter_by_liquidity(self, stocks: List[Dict]) -> List[Dict]:
        """유동성 필터 (거래대금 기준)"""
        filtered = []
        target_markets = self._get_target_markets()

        # OHLCV 데이터 조회
        for market in target_markets:
            try:
                df = pykrx.get_market_ohlcv(self.scan_date, market=market)
                # pykrx 컬럼: 시가, 고가, 저가, 종가, 거래량, 거래대금, 등락률, 시가총액
                # 인덱스: 티커

                for stock in stocks:
                    if stock["market"] != market:
                        continue

                    code = stock["code"]
                    if code in df.index:
                        row = df.loc[code]
                        traded_value = int(row['거래대금'])
                        close_price = int(row['종가'])

                        # 필터 조건
                        if traded_value >= self.MIN_TRADED_VALUE and close_price >= self.MIN_PRICE:
                            stock.update({
                                "current_price": close_price,
                                "change_rate": float(row['등락률']),
                                "volume": int(row['거래량']),
                                "traded_value": traded_value
                            })
                            filtered.append(stock)
            except Exception as e:
                print(f"   ⚠️ {market} OHLCV 조회 실패: {e}")

        return filtered

    async def _calculate_technical_indicators(self, stocks: List[Dict]) -> List[CandidateStock]:
        """기술적 지표 계산 (RSI, MA, 골든크로스)"""
        candidates = []

        # 과거 60일 데이터 필요
        start_date = (datetime.strptime(self.scan_date, "%Y%m%d") - timedelta(days=90)).strftime("%Y%m%d")

        for stock in stocks:
            try:
                code = stock["code"]
                df = pykrx.get_market_ohlcv(start_date, self.scan_date, code)

                if len(df) < 20:
                    continue

                # RSI 계산
                rsi = self._calculate_rsi(df['종가'], 14)

                # 이동평균
                ma_5 = df['종가'].rolling(5).mean().iloc[-1]
                ma_20 = df['종가'].rolling(20).mean().iloc[-1]
                ma_60 = df['종가'].rolling(60).mean().iloc[-1] if len(df) >= 60 else ma_20

                # 골든크로스 체크 (5일선이 20일선 상향돌파)
                prev_ma_5 = df['종가'].rolling(5).mean().iloc[-2] if len(df) > 5 else ma_5
                prev_ma_20 = df['종가'].rolling(20).mean().iloc[-2] if len(df) > 20 else ma_20
                golden_cross = (prev_ma_5 <= prev_ma_20) and (ma_5 > ma_20)

                candidate = CandidateStock(
                    code=code,
                    name=stock["name"],
                    market=stock["market"],
                    current_price=stock["current_price"],
                    change_rate=stock["change_rate"],
                    volume=stock["volume"],
                    traded_value=stock["traded_value"],
                    rsi_14=rsi,
                    ma_5=ma_5,
                    ma_20=ma_20,
                    ma_60=ma_60,
                    golden_cross=golden_cross
                )
                candidates.append(candidate)

            except Exception as e:
                continue  # 개별 종목 오류는 스킵

        return candidates

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """RSI 계산"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0

    async def _add_supply_demand(self, candidates: List[CandidateStock]) -> List[CandidateStock]:
        """수급 데이터 추가 (외인/기관 순매수)"""
        try:
            # 투자자별 거래 데이터
            for market in ["KOSPI", "KOSDAQ"]:
                df = pykrx.get_market_net_purchases_of_equities(
                    self.scan_date, self.scan_date, market=market
                )

                if df.empty:
                    continue

                df = df.reset_index()

                for candidate in candidates:
                    if candidate.market != market:
                        continue

                    if candidate.code in df['종목코드'].values if '종목코드' in df.columns else False:
                        row = df[df['종목코드'] == candidate.code].iloc[0]
                        candidate.foreigner_net = int(row.get('외국인', 0))
                        candidate.institution_net = int(row.get('기관', 0))

        except Exception as e:
            print(f"   ⚠️ 수급 데이터 조회 실패: {e}")

        return candidates

    def _calculate_scores(self, candidates: List[CandidateStock]) -> List[CandidateStock]:
        """종합 스코어 계산"""
        for c in candidates:
            # 기술적 점수 (0~3점)
            tech_score = 0.0
            reasons = []

            # RSI 기반 점수
            if c.rsi_14 < 30:
                tech_score += 1.0
                reasons.append("RSI 과매도")
            elif c.rsi_14 < 40:
                tech_score += 0.5
                reasons.append("RSI 저점")
            elif c.rsi_14 > 70:
                tech_score -= 0.5
                reasons.append("RSI 과매수")

            # 이평선 정배열
            if c.current_price > c.ma_5 > c.ma_20:
                tech_score += 0.5
                reasons.append("이평선 정배열")
            elif c.current_price > c.ma_20 > c.ma_60:
                tech_score += 0.3
                reasons.append("중기 상승추세")

            # 골든크로스
            if c.golden_cross:
                tech_score += 1.0
                reasons.append("골든크로스")

            c.technical_score = tech_score

            # 수급 점수 (0~2점)
            supply_score = 0.0

            if c.foreigner_net > 0:
                supply_score += 0.5
                reasons.append("외인 순매수")
            if c.institution_net > 0:
                supply_score += 0.5
                reasons.append("기관 순매수")
            if c.foreigner_net > 0 and c.institution_net > 0:
                supply_score += 0.5
                reasons.append("외인+기관 동반매수")

            c.supply_score = supply_score

            # 총점
            c.total_score = tech_score + supply_score
            c.filter_reasons = reasons

        return candidates

    def get_summary(self) -> str:
        """스캔 결과 요약"""
        if not self.candidates:
            return "스캔 결과 없음"

        lines = [
            f"📊 Market Scan 결과 ({self.scan_date})",
            f"━" * 50,
            f"{'순위':<4} {'종목명':<12} {'현재가':>10} {'등락률':>8} {'점수':>6}",
            f"━" * 50,
        ]

        for i, c in enumerate(self.candidates[:20], 1):
            lines.append(
                f"{i:<4} {c.name:<12} {c.current_price:>10,} {c.change_rate:>7.2f}% {c.total_score:>6.1f}"
            )

        return "\n".join(lines)


# CLI 실행
if __name__ == "__main__":
    async def main():
        scanner = MarketScanner()
        await scanner.scan_market()
        print(scanner.get_summary())

    asyncio.run(main())
