#!/usr/bin/env python3
"""
5-Minute Realtime Dashboard PDF Generator
매 5분마다 보유종목 대시보드 PDF 생성
Runs every 5 minutes via cron (05:00-21:00 KST)
"""
import asyncio
import sys
from datetime import datetime, time
from pathlib import Path

# Add project root to path
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

# Import from the main script
from scripts.generate_realtime_dashboard_terminal_style import (
    get_all_holdings,
    get_stock_detail_data,
    create_pdf
)


class DashboardGenerator:
    """5분 주기 대시보드 PDF 생성기"""

    def __init__(self):
        # 거래 시간: 08:50 - 16:00
        self.trading_hours = {
            'start': time(8, 50),
            'end': time(16, 0)
        }

    def is_trading_hours(self) -> bool:
        """현재 시간이 거래 시간인지 확인 (08:50-16:00)"""
        now = datetime.now().time()
        return self.trading_hours['start'] <= now <= self.trading_hours['end']

    async def generate_dashboard(self):
        """대시보드 PDF 생성"""
        print(f"\n{'='*80}")
        print(f"📊 5분 주기 대시보드 PDF 생성: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")

        # 거래 시간 확인
        if not self.is_trading_hours():
            print("⏸️  거래 시간이 아닙니다 (08:50-16:00). 생성을 건너뜁니다.")
            return

        try:
            # 출력 디렉토리
            output_dir = Path('/Users/wonny/Dev/joungwon.stocks/reports')
            output_dir.mkdir(parents=True, exist_ok=True)

            # 보유종목 목록 조회 (평가금액 높은 순)
            print("📡 보유종목 목록 조회 중...")
            holdings = await get_all_holdings()

            if not holdings:
                print("📭 보유 종목이 없습니다.")
                return

            print(f"✅ {len(holdings)}개 종목 발견\n")

            # 각 종목별 상세 데이터 수집
            holdings_data = []
            for row in holdings:
                stock_code = row['stock_code']
                stock_name = row['stock_name']
                print(f"   📊 {stock_name}({stock_code}) 데이터 수집 중...")

                data = await get_stock_detail_data(stock_code, stock_name, limit_count=20)
                holdings_data.append((stock_code, stock_name, data))

            print(f"\n✅ 모든 종목 데이터 수집 완료\n")

            # PDF 생성
            output_path = output_dir / 'realtime_dashboard.pdf'
            print(f"📄 PDF 생성 중: {output_path}")
            create_pdf(holdings_data, output_path)

            print(f"\n{'='*80}")
            print(f"✅ 완료! PDF 경로: {output_path}")
            print(f"{'='*80}\n")

        except Exception as e:
            print(f"❌ 대시보드 생성 오류: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """메인 함수"""
    generator = DashboardGenerator()
    await generator.generate_dashboard()


if __name__ == '__main__':
    # 로그 디렉토리 생성
    log_dir = Path('/Users/wonny/Dev/joungwon.stocks/logs')
    log_dir.mkdir(exist_ok=True)

    # asyncio 실행
    asyncio.run(main())
