"""
Phase 1A: SQL 기반 1차 필터
2,500개 종목 → 200개로 즉시 축소

목표: <1초 내 실행
방법: 100% SQL 기반, Fetcher 호출 없음
"""
import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime
import uuid

import sys
sys.path.insert(0, '.')
from 신규종목추천.config.settings import settings
from 신규종목추천.src.utils.database import db

logger = logging.getLogger(__name__)


class Phase1AFilter:
    """
    SQL 기반 1차 필터

    필터 조건:
    1. PBR: 0.2 ~ 1.0 (저평가)
    2. PER: 3 ~ 15 (적정 수익성)
    3. 거래량: 10만주 이상 (유동성)
    4. 시총: 1000억 이상 (안정성)
    """

    def __init__(self, config=None):
        self.config = config or settings.phase1a

    async def filter(self, batch_id: str = None) -> List[Dict[str, Any]]:
        """
        Phase 1A 필터 실행

        Args:
            batch_id: 배치 식별자 (None이면 자동 생성)

        Returns:
            필터 통과 종목 리스트
        """
        batch_id = batch_id or str(uuid.uuid4())
        start_time = datetime.now()

        logger.info(f"Phase 1A 시작 - batch_id: {batch_id}")
        market_filter = "KOSPI, KOSDAQ" if self.config.include_kosdaq else "KOSPI만"
        logger.info(f"필터 조건: PBR({self.config.pbr_min}~{self.config.pbr_max}), "
                   f"PER({self.config.per_min}~{self.config.per_max}), "
                   f"거래량>{self.config.min_volume:,}, 시총>{self.config.min_market_cap:,}, "
                   f"시장: {market_filter}")

        # 메인 필터 쿼리
        # - daily_ohlcv 컬럼: date, open, high, low, close, volume
        # - stock_fundamentals 컬럼: pbr, per, market_cap

        # 시장 필터 설정
        if self.config.include_kosdaq:
            market_condition = "s.market IN ('KOSPI', 'KOSDAQ')"
        else:
            market_condition = "s.market = 'KOSPI'"

        query = f"""
        WITH latest_prices AS (
            -- 최근 거래일의 OHLCV 데이터
            SELECT DISTINCT ON (stock_code)
                stock_code,
                close as close_price,
                volume,
                date as trade_date
            FROM daily_ohlcv
            WHERE date >= CURRENT_DATE - INTERVAL '5 days'
            ORDER BY stock_code, date DESC
        ),
        fundamentals AS (
            -- stock_fundamentals 테이블에서 밸류에이션 데이터 (stocks와 조인)
            SELECT
                s.stock_code,
                s.stock_name,
                s.market,
                s.sector,
                COALESCE(sf.pbr, 0) as pbr,
                COALESCE(sf.per, 0) as per,
                COALESCE(sf.market_cap, 0) as market_cap
            FROM stocks s
            LEFT JOIN stock_fundamentals sf ON s.stock_code = sf.stock_code
            WHERE s.is_delisted = FALSE
              AND {market_condition}
        )
        SELECT
            f.stock_code,
            f.stock_name,
            f.market,
            f.sector,
            f.pbr,
            f.per,
            f.market_cap,
            lp.close_price,
            lp.volume,
            lp.trade_date
        FROM fundamentals f
        JOIN latest_prices lp ON f.stock_code = lp.stock_code
        WHERE
            -- 밸류에이션 필터
            f.pbr BETWEEN $1 AND $2
            AND f.per BETWEEN $3 AND $4
            -- 유동성 필터
            AND lp.volume >= $5
            -- 시총 필터
            AND (f.market_cap >= $6 OR f.market_cap = 0)
        ORDER BY f.pbr ASC, f.per ASC
        LIMIT $7
        """

        try:
            candidates = await db.fetch(
                query,
                self.config.pbr_min,
                self.config.pbr_max,
                self.config.per_min,
                self.config.per_max,
                self.config.min_volume,
                self.config.min_market_cap,
                self.config.max_candidates
            )

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"Phase 1A 완료: {len(candidates)}개 종목 선정 ({elapsed:.2f}초)")

            # Phase 1 캐시 테이블에 저장
            await self._save_candidates(batch_id, candidates)

            return candidates

        except Exception as e:
            logger.error(f"Phase 1A 필터 실패: {e}")
            raise

    async def filter_with_fallback(self, batch_id: str = None) -> List[Dict[str, Any]]:
        """
        PBR/PER가 stocks 테이블에 없는 경우 collected_data에서 조회하는 대체 로직

        Returns:
            필터 통과 종목 리스트
        """
        batch_id = batch_id or str(uuid.uuid4())
        start_time = datetime.now()

        logger.info(f"Phase 1A (Fallback) 시작 - batch_id: {batch_id}")

        # 시장 필터 설정
        if self.config.include_kosdaq:
            market_condition = "s.market IN ('KOSPI', 'KOSDAQ')"
        else:
            market_condition = "s.market = 'KOSPI'"

        # collected_data 또는 stock_opinions 테이블에서 PBR/PER 조회
        query = f"""
        WITH latest_prices AS (
            SELECT DISTINCT ON (stock_code)
                stock_code,
                close_price,
                volume,
                trade_date
            FROM daily_ohlcv
            WHERE trade_date >= CURRENT_DATE - INTERVAL '5 days'
            ORDER BY stock_code, trade_date DESC
        ),
        valuations AS (
            -- collected_data에서 최신 밸류에이션 데이터
            SELECT DISTINCT ON (stock_code)
                stock_code,
                (data_content->>'pbr')::DECIMAL as pbr,
                (data_content->>'per')::DECIMAL as per,
                (data_content->>'market_cap')::BIGINT as market_cap
            FROM collected_data
            WHERE data_type = 'valuation'
              AND collected_at >= CURRENT_DATE - INTERVAL '7 days'
            ORDER BY stock_code, collected_at DESC
        ),
        stock_info AS (
            SELECT
                s.stock_code,
                s.stock_name,
                s.market,
                s.sector,
                COALESCE(s.pbr, v.pbr, 0) as pbr,
                COALESCE(s.per, v.per, 0) as per,
                COALESCE(s.market_cap, v.market_cap, 0) as market_cap
            FROM stocks s
            LEFT JOIN valuations v ON s.stock_code = v.stock_code
            WHERE s.is_delisted = FALSE
              AND {market_condition}
        )
        SELECT
            si.stock_code,
            si.stock_name,
            si.market,
            si.sector,
            si.pbr,
            si.per,
            si.market_cap,
            lp.close_price,
            lp.volume,
            lp.trade_date
        FROM stock_info si
        JOIN latest_prices lp ON si.stock_code = lp.stock_code
        WHERE
            si.pbr BETWEEN $1 AND $2
            AND si.per BETWEEN $3 AND $4
            AND lp.volume >= $5
        ORDER BY si.pbr ASC, si.per ASC
        LIMIT $6
        """

        try:
            candidates = await db.fetch(
                query,
                self.config.pbr_min,
                self.config.pbr_max,
                self.config.per_min,
                self.config.per_max,
                self.config.min_volume,
                self.config.max_candidates
            )

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"Phase 1A (Fallback) 완료: {len(candidates)}개 종목 선정 ({elapsed:.2f}초)")

            await self._save_candidates(batch_id, candidates)
            return candidates

        except Exception as e:
            logger.error(f"Phase 1A Fallback 필터 실패: {e}")
            raise

    async def _save_candidates(self, batch_id: str, candidates: List[Dict]) -> None:
        """Phase 1A 결과를 캐시 테이블에 저장"""
        if not candidates:
            return

        query = """
        INSERT INTO smart_phase1_candidates
            (batch_id, stock_code, stock_name, pbr, per, market_cap, volume, close_price, phase1a_passed)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, TRUE)
        ON CONFLICT (batch_id, stock_code) DO UPDATE SET
            pbr = EXCLUDED.pbr,
            per = EXCLUDED.per,
            market_cap = EXCLUDED.market_cap,
            volume = EXCLUDED.volume,
            close_price = EXCLUDED.close_price,
            phase1a_passed = TRUE
        """

        args_list = [
            (
                batch_id,
                c['stock_code'],
                c['stock_name'],
                c.get('pbr'),
                c.get('per'),
                c.get('market_cap'),
                c.get('volume'),
                c.get('close_price'),
            )
            for c in candidates
        ]

        await db.executemany(query, args_list)
        logger.info(f"Phase 1A 결과 저장: {len(candidates)}개")


async def main():
    """테스트 실행"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    await db.connect()

    try:
        filter_1a = Phase1AFilter()
        candidates = await filter_1a.filter()

        print(f"\n=== Phase 1A 결과: {len(candidates)}개 종목 ===")
        for i, c in enumerate(candidates[:10], 1):
            print(f"{i:2}. {c['stock_code']} {c['stock_name']:<12} "
                  f"PBR:{c['pbr']:.2f} PER:{c['per']:.1f} "
                  f"거래량:{c['volume']:,}")

        if len(candidates) > 10:
            print(f"... 외 {len(candidates) - 10}개")

    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
