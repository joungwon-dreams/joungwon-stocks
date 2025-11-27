#!/usr/bin/env python3
"""
1-Minute Real-time Stock Data Collector + Dashboard PDF Generator
Fetches current price, volume, bid/ask data for all holdings
Runs every minute via cron during trading hours (08:50-16:00 KST)

네이버 금융 웹 스크래핑을 통해 실시간 현재가, 등락률, 거래량, 호가 정보 수집
+ 수집 후 realtime_dashboard.pdf 자동 생성
"""
import asyncio
import sys
from datetime import datetime, time
from pathlib import Path
import asyncpg

# Add project root to path
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

# Dashboard PDF 생성 모듈 임포트
from scripts.generate_realtime_dashboard_terminal_style import (
    get_all_holdings,
    get_stock_detail_data,
    create_pdf
)

# Direct database connection (settings 의존성 제거)
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'stock_investment_db',
    'user': 'wonny'
}


class RealtimeDataCollector:
    """실시간 주식 데이터 수집기"""

    def __init__(self):
        # 거래 시간: 08:50 - 16:00
        self.trading_hours = {
            'start': time(8, 50),    # 08:50
            'end': time(16, 0)       # 16:00
        }
        # 전체 실행 시간: 05:00 - 21:00
        self.active_hours = {
            'start': time(5, 0),     # 05:00
            'end': time(21, 0)       # 21:00
        }

    def is_active_hours(self) -> bool:
        """현재 시간이 활성 시간인지 확인 (05:00-21:00)"""
        now = datetime.now().time()
        return self.active_hours['start'] <= now <= self.active_hours['end']

    def is_trading_hours(self) -> bool:
        """현재 시간이 거래 시간인지 확인 (08:50-16:00)"""
        now = datetime.now().time()
        return self.trading_hours['start'] <= now <= self.trading_hours['end']

    async def get_holdings(self, conn):
        """보유 종목 목록 조회"""
        query = """
            SELECT stock_code, stock_name
            FROM stock_assets
            WHERE quantity > 0
            ORDER BY stock_code
        """
        return await conn.fetch(query)

    async def fetch_realtime_data(self, stock_code: str):
        """
        네이버 금융에서 실시간 현재가 수집 (BeautifulSoup 사용 - 정적 HTML 파싱)

        Returns:
            dict: {
                'price': 현재가,
                'change_rate': 등락률,
                'volume': 거래량,
                'bid_price': 매수호가,
                'ask_price': 매도호가,
                'bid_volume': 매수잔량,
                'ask_volume': 매도잔량
            }
        """
        try:
            import aiohttp
            from bs4 import BeautifulSoup
            import re

            url = f"https://finance.naver.com/item/main.naver?code={stock_code}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}) as response:
                    if response.status != 200:
                        print(f"⚠️  {stock_code}: HTTP {response.status}")
                        return None

                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # <dd>현재가 60,800 전일대비 상승 2,800 플러스 4.83 퍼센트</dd> 파싱
                    dd_tags = soup.find_all('dd')
                    price = 0
                    change_rate = 0.0
                    volume = 0

                    for dd in dd_tags:
                        text = dd.get_text(strip=True)

                        # 현재가 파싱
                        if text.startswith('현재가'):
                            # "현재가 60,800 전일대비 상승 2,800 플러스 4.83 퍼센트"
                            numbers = re.findall(r'[\d,]+', text)
                            if numbers:
                                price = int(numbers[0].replace(',', ''))

                            # 등락률 파싱
                            if '상승' in text or '하락' in text:
                                rate_match = re.search(r'([\d.]+)\s*퍼센트', text)
                                if rate_match:
                                    change_rate = float(rate_match.group(1))
                                    if '하락' in text:
                                        change_rate = -change_rate

                        # 거래량 파싱
                        if text.startswith('거래량'):
                            # "거래량 1,234,567"
                            vol_match = re.search(r'거래량\s*([\d,]+)', text)
                            if vol_match:
                                volume = int(vol_match.group(1).replace(',', ''))

                    if price == 0:
                        print(f"⚠️  {stock_code}: 현재가 파싱 실패")
                        return None

                    # 호가 정보는 JavaScript로 로딩되므로 현재는 0으로 설정
                    # 추후 한국투자증권 API로 대체 권장
                    data = {
                        'price': price,
                        'change_rate': change_rate,
                        'volume': volume,
                        'bid_price': 0,  # iframe 내 동적 로딩
                        'ask_price': 0,  # iframe 내 동적 로딩
                        'bid_volume': 0,  # iframe 내 동적 로딩
                        'ask_volume': 0   # iframe 내 동적 로딩
                    }

                    return data

        except Exception as e:
            print(f"❌ Error fetching {stock_code}: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def save_to_db(self, conn, stock_code: str, data: dict):
        """min_ticks 테이블에 데이터 저장"""
        try:
            query = """
                INSERT INTO min_ticks
                    (stock_code, timestamp, price, change_rate, volume,
                     bid_price, ask_price, bid_volume, ask_volume, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, CURRENT_TIMESTAMP)
            """

            await conn.execute(
                query,
                stock_code,
                datetime.now(),
                data['price'],
                data['change_rate'],
                data['volume'],
                data['bid_price'],
                data['ask_price'],
                data['bid_volume'],
                data['ask_volume']
            )

            return True

        except Exception as e:
            print(f"⚠️  DB save error for {stock_code}: {e}")
            return False

    async def collect_all(self):
        """모든 보유 종목의 실시간 데이터 수집"""
        print(f"\n{'='*60}")
        print(f"🕐 1분 데이터 수집 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")

        # 활성 시간 확인 (05:00-21:00)
        if not self.is_active_hours():
            print("⏸️  활성 시간이 아닙니다 (05:00-21:00). 수집을 건너뜁니다.")
            return

        # 거래 시간 여부 표시
        if self.is_trading_hours():
            print("📊 거래 시간 (08:50-16:00) - 활발한 데이터 수집")
        else:
            print("🌙 거래 시간 외 - 제한적 데이터 수집")

        # 데이터베이스 연결
        conn = await asyncpg.connect(**DB_CONFIG)

        try:
            # 보유 종목 목록 조회
            holdings = await self.get_holdings(conn)

            if not holdings:
                print("📭 보유 종목이 없습니다.")
                return

            print(f"📊 총 {len(holdings)}개 종목 데이터 수집 중...\n")

            success_count = 0
            fail_count = 0

            # 각 종목별 데이터 수집
            for row in holdings:
                stock_code = row['stock_code']
                stock_name = row['stock_name']

                # 실시간 데이터 조회
                data = await self.fetch_realtime_data(stock_code)

                if data:
                    # 데이터베이스 저장
                    saved = await self.save_to_db(conn, stock_code, data)

                    if saved:
                        print(f"✅ {stock_name}({stock_code}): "
                              f"{data['price']:,}원 "
                              f"({data['change_rate']:+.2f}%) "
                              f"거래량: {data['volume']:,}")
                        success_count += 1
                    else:
                        fail_count += 1
                else:
                    print(f"❌ {stock_name}({stock_code}): 데이터 수집 실패")
                    fail_count += 1

                # API 호출 제한 방지 (초당 10건 제한)
                await asyncio.sleep(0.5)

            print(f"\n{'='*60}")
            print(f"✅ 수집 완료: 성공 {success_count}건, 실패 {fail_count}건")
            print(f"{'='*60}\n")

            # 데이터 수집 성공 시 대시보드 PDF 생성
            if success_count > 0:
                await self.generate_dashboard_pdf()

        except Exception as e:
            print(f"❌ 전체 수집 오류: {e}")
            import traceback
            traceback.print_exc()

        finally:
            # 데이터베이스 연결 해제
            await conn.close()

    async def generate_dashboard_pdf(self):
        """실시간 대시보드 PDF 생성"""
        try:
            print(f"\n📊 대시보드 PDF 생성 중...")

            # 출력 디렉토리
            output_dir = Path('/Users/wonny/Dev/joungwon.stocks/reports')
            output_dir.mkdir(exist_ok=True)

            # 보유 종목 목록 조회
            holdings = await get_all_holdings()

            if not holdings:
                print("   ⚠️  보유 종목이 없습니다.")
                return

            # 각 종목별 상세 데이터 수집
            # create_pdf는 (stock_code, stock_name, data) 튜플 리스트를 기대
            all_data = []
            for row in holdings:
                stock_code = row['stock_code']
                stock_name = row['stock_name']
                try:
                    data = await get_stock_detail_data(stock_code, stock_name)
                    if data:
                        # (stock_code, stock_name, data) 튜플로 변환
                        all_data.append((stock_code, stock_name, data))
                except Exception as e:
                    print(f"   ⚠️  {stock_name} 데이터 조회 실패: {e}")
                    continue

            if not all_data:
                print("   ⚠️  수집된 데이터가 없습니다.")
                return

            # PDF 생성
            output_path = output_dir / 'realtime_dashboard.pdf'
            create_pdf(all_data, str(output_path))

            print(f"   ✅ 대시보드 PDF 생성 완료: {output_path}")

        except Exception as e:
            print(f"   ❌ 대시보드 PDF 생성 오류: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """메인 함수"""
    collector = RealtimeDataCollector()
    await collector.collect_all()


if __name__ == '__main__':
    # 로그 파일 생성 (선택사항)
    log_dir = Path('/Users/wonny/Dev/joungwon.stocks/logs')
    log_dir.mkdir(exist_ok=True)

    # asyncio 실행
    asyncio.run(main())
