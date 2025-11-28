#!/usr/bin/env python3
"""
PROJECT AEGIS - Signal Verification Script
============================================
AEGIS 신호의 정확도를 추적하고 검증하는 스크립트

기능:
1. aegis_signal_history에서 미검증 신호 조회
2. 신호 발생 후 1시간/1일 가격 변화 계산
3. 승/패 판정 및 DB 업데이트
4. 검증 결과 리포트 출력

실행: python scripts/verify_aegis_signals.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg


# 데이터베이스 설정
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'stock_investment_db',
    'user': 'wonny'
}

# 검증 기준
VERIFICATION_CONFIG = {
    'min_hours_for_1h': 1,      # 1시간 검증에 필요한 최소 시간
    'min_hours_for_1d': 24,     # 1일 검증에 필요한 최소 시간
    'success_threshold_pct': 0.5,  # 성공 판정 기준 (0.5% 이상 수익)
}


class AegisSignalVerifier:
    """AEGIS 신호 검증기"""

    def __init__(self):
        self.conn = None

    async def connect(self):
        """DB 연결"""
        self.conn = await asyncpg.connect(**DB_CONFIG)

    async def disconnect(self):
        """DB 연결 종료"""
        if self.conn:
            await self.conn.close()

    async def get_unverified_signals(self) -> list:
        """미검증 신호 조회"""
        query = """
            SELECT id, stock_code, stock_name, signal_type, signal_score,
                   current_price, recorded_at, result_1h, result_1d
            FROM aegis_signal_history
            WHERE is_success IS NULL
              AND recorded_at < NOW() - INTERVAL '1 hour'
            ORDER BY recorded_at ASC
        """
        return await self.conn.fetch(query)

    async def get_price_at_time(self, stock_code: str, target_time: datetime) -> int | None:
        """특정 시간의 가격 조회 (min_ticks에서)"""
        # target_time 근처 ±30분 범위에서 가장 가까운 가격 조회
        query = """
            SELECT price, timestamp,
                   ABS(EXTRACT(EPOCH FROM (timestamp - $2))) as time_diff
            FROM min_ticks
            WHERE stock_code = $1
              AND timestamp BETWEEN $2 - INTERVAL '30 minutes' AND $2 + INTERVAL '30 minutes'
            ORDER BY time_diff ASC
            LIMIT 1
        """
        row = await self.conn.fetchrow(query, stock_code, target_time)
        if row:
            return int(row['price'])
        return None

    async def get_latest_price(self, stock_code: str) -> int | None:
        """최신 가격 조회"""
        query = """
            SELECT price FROM min_ticks
            WHERE stock_code = $1
            ORDER BY timestamp DESC
            LIMIT 1
        """
        row = await self.conn.fetchrow(query, stock_code)
        if row:
            return int(row['price'])
        return None

    def calculate_return_pct(self, entry_price: int, current_price: int) -> float:
        """수익률 계산"""
        if entry_price == 0:
            return 0.0
        return ((current_price - entry_price) / entry_price) * 100

    def judge_success(self, signal_type: str, return_pct: float) -> bool:
        """성공 여부 판정

        STRONG_BUY/BUY: 가격 상승 시 성공
        STRONG_SELL/SELL: 가격 하락 시 성공
        """
        threshold = VERIFICATION_CONFIG['success_threshold_pct']

        if signal_type in ['STRONG_BUY', 'BUY', '강매수', '매수']:
            return return_pct >= threshold  # 매수 신호 → 가격 상승 = 성공
        elif signal_type in ['STRONG_SELL', 'SELL', '강매도', '매도']:
            return return_pct <= -threshold  # 매도 신호 → 가격 하락 = 성공
        return False

    async def verify_signal(self, signal: dict) -> dict:
        """개별 신호 검증"""
        result = {
            'id': signal['id'],
            'stock_code': signal['stock_code'],
            'stock_name': signal['stock_name'],
            'signal_type': signal['signal_type'],
            'entry_price': signal['current_price'],
            'recorded_at': signal['recorded_at'],
            'result_1h': signal['result_1h'],
            'result_1d': signal['result_1d'],
            'is_success': None,
            'needs_update': False
        }

        now = datetime.now()
        hours_elapsed = (now - signal['recorded_at']).total_seconds() / 3600

        # 1시간 후 검증 (아직 안 한 경우)
        if result['result_1h'] is None and hours_elapsed >= VERIFICATION_CONFIG['min_hours_for_1h']:
            target_time = signal['recorded_at'] + timedelta(hours=1)
            price_1h = await self.get_price_at_time(signal['stock_code'], target_time)

            if price_1h is None:
                # 1시간 후 데이터 없으면 최신 가격 사용
                price_1h = await self.get_latest_price(signal['stock_code'])

            if price_1h:
                result['result_1h'] = self.calculate_return_pct(signal['current_price'], price_1h)
                result['needs_update'] = True

        # 1일 후 검증 (아직 안 한 경우)
        if result['result_1d'] is None and hours_elapsed >= VERIFICATION_CONFIG['min_hours_for_1d']:
            target_time = signal['recorded_at'] + timedelta(hours=24)
            price_1d = await self.get_price_at_time(signal['stock_code'], target_time)

            if price_1d is None:
                # 24시간 후 데이터 없으면 최신 가격 사용
                price_1d = await self.get_latest_price(signal['stock_code'])

            if price_1d:
                result['result_1d'] = self.calculate_return_pct(signal['current_price'], price_1d)
                result['needs_update'] = True

        # 최종 성공 여부 판정 (1일 결과 기준, 없으면 1시간 기준)
        if result['result_1d'] is not None:
            result['is_success'] = self.judge_success(signal['signal_type'], result['result_1d'])
        elif result['result_1h'] is not None:
            result['is_success'] = self.judge_success(signal['signal_type'], result['result_1h'])

        return result

    async def update_verification(self, result: dict):
        """검증 결과 DB 업데이트"""
        query = """
            UPDATE aegis_signal_history
            SET result_1h = COALESCE($2, result_1h),
                result_1d = COALESCE($3, result_1d),
                is_success = $4,
                verified_at = NOW()
            WHERE id = $1
        """
        await self.conn.execute(
            query,
            result['id'],
            result['result_1h'],
            result['result_1d'],
            result['is_success']
        )

    async def get_verification_stats(self) -> dict:
        """검증 통계 조회"""
        query = """
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN is_success = true THEN 1 END) as success,
                COUNT(CASE WHEN is_success = false THEN 1 END) as fail,
                COUNT(CASE WHEN is_success IS NULL THEN 1 END) as pending,
                AVG(result_1h) as avg_1h,
                AVG(result_1d) as avg_1d,
                signal_type
            FROM aegis_signal_history
            GROUP BY signal_type
            ORDER BY signal_type
        """
        return await self.conn.fetch(query)

    async def run_verification(self):
        """검증 실행"""
        print("=" * 60)
        print("  PROJECT AEGIS - Signal Verification")
        print("=" * 60)
        print(f"\n⏰ 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        await self.connect()

        try:
            # 미검증 신호 조회
            signals = await self.get_unverified_signals()
            print(f"\n📋 미검증 신호: {len(signals)}건")

            if not signals:
                print("   → 검증할 신호가 없습니다.")
            else:
                # 각 신호 검증
                updated_count = 0
                for signal in signals:
                    result = await self.verify_signal(signal)

                    if result['needs_update']:
                        await self.update_verification(result)
                        updated_count += 1

                        status = "✅" if result['is_success'] else "❌" if result['is_success'] is False else "⏳"
                        r1h = f"{result['result_1h']:+.2f}%" if result['result_1h'] else "-"
                        r1d = f"{result['result_1d']:+.2f}%" if result['result_1d'] else "-"

                        print(f"   {status} {result['stock_name']} ({result['signal_type']})")
                        print(f"      진입가: {result['entry_price']:,}원 | 1H: {r1h} | 1D: {r1d}")

                print(f"\n📝 업데이트: {updated_count}건")

            # 통계 출력
            print("\n" + "=" * 60)
            print("  📊 검증 통계")
            print("=" * 60)

            stats = await self.get_verification_stats()

            total_success = 0
            total_fail = 0
            total_all = 0

            for row in stats:
                signal_type = row['signal_type']
                total = row['total']
                success = row['success'] or 0
                fail = row['fail'] or 0
                pending = row['pending'] or 0
                avg_1h = row['avg_1h'] or 0
                avg_1d = row['avg_1d'] or 0

                win_rate = (success / (success + fail) * 100) if (success + fail) > 0 else 0

                total_success += success
                total_fail += fail
                total_all += total

                print(f"\n   [{signal_type}]")
                print(f"   총 {total}건 | 성공 {success} | 실패 {fail} | 대기 {pending}")
                print(f"   승률: {win_rate:.1f}% | 평균1H: {avg_1h:+.2f}% | 평균1D: {avg_1d:+.2f}%")

            # 전체 통계
            overall_win_rate = (total_success / (total_success + total_fail) * 100) if (total_success + total_fail) > 0 else 0
            print(f"\n{'─'*60}")
            print(f"   📈 전체 승률: {overall_win_rate:.1f}% ({total_success}승 / {total_fail}패)")
            print("=" * 60)

        finally:
            await self.disconnect()


async def main():
    """메인 함수"""
    verifier = AegisSignalVerifier()
    await verifier.run_verification()


if __name__ == '__main__':
    asyncio.run(main())
