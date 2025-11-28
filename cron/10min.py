#!/usr/bin/env python3
"""
10-Minute Stock Data Collector & PDF Report Generator
매 10분마다 실행되어 실시간 데이터 수집 및 PDF 리포트 재생성

실행 시간: 04:50 ~ 18:00

기능:
1. 04:50 첫 실행: 전일 주가 데이터 수집 (종가, 거래량, 수급)
2. 매 10분: 현재가, 거래량 업데이트 + 뉴스 수집 + PDF 재생성
3. 실패 데이터 재시도 로직
4. 종목별 독립 실행 (한 종목 실패가 다른 종목에 영향 없음)
"""
import asyncio
import sys
import json
from datetime import datetime, time, timedelta
from pathlib import Path
import asyncpg
import aiohttp
from bs4 import BeautifulSoup
import subprocess
import traceback

# .env 파일 로드 (cron 환경에서 필수)
from dotenv import load_dotenv
load_dotenv('/Users/wonny/Dev/joungwon.stocks/.env')

sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

# 프로젝트 경로
PROJECT_ROOT = Path('/Users/wonny/Dev/joungwon.stocks')
LOG_DIR = PROJECT_ROOT / 'logs'
REPORTS_DIR = PROJECT_ROOT / 'reports'
FAILED_DATA_FILE = LOG_DIR / '10min_failed_data.json'

# 데이터베이스 설정
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'stock_investment_db',
    'user': 'wonny'
}


class TenMinuteCollector:
    """10분 데이터 수집기"""

    def __init__(self):
        self.log_file = LOG_DIR / '10min_collection.log'
        LOG_DIR.mkdir(exist_ok=True)
        self.failed_items = self._load_failed_items()

        # 실행 시간 설정
        self.active_hours = {
            'start': time(4, 50),   # 04:50
            'end': time(18, 0)      # 18:00
        }

        # 첫 실행 시간 (전일 데이터 수집)
        self.morning_init_time = time(4, 50)

    def log(self, message: str, level: str = "INFO"):
        """로그 메시지 출력"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] [{level}] {message}"
        print(log_msg)

        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_msg + '\n')

    def _load_failed_items(self) -> dict:
        """이전 실패 항목 로드"""
        if FAILED_DATA_FILE.exists():
            try:
                with open(FAILED_DATA_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {'stocks': {}}

    def _save_failed_items(self):
        """실패 항목 저장"""
        with open(FAILED_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.failed_items, f, ensure_ascii=False, indent=2)

    def _record_failure(self, stock_code: str, data_type: str, error: str):
        """실패 기록"""
        if stock_code not in self.failed_items['stocks']:
            self.failed_items['stocks'][stock_code] = {}

        self.failed_items['stocks'][stock_code][data_type] = {
            'error': str(error)[:200],
            'timestamp': datetime.now().isoformat(),
            'retry_count': self.failed_items['stocks'].get(stock_code, {}).get(data_type, {}).get('retry_count', 0) + 1
        }
        self._save_failed_items()

    def _clear_failure(self, stock_code: str, data_type: str = None):
        """실패 기록 제거"""
        if stock_code in self.failed_items['stocks']:
            if data_type:
                self.failed_items['stocks'][stock_code].pop(data_type, None)
                if not self.failed_items['stocks'][stock_code]:
                    del self.failed_items['stocks'][stock_code]
            else:
                del self.failed_items['stocks'][stock_code]
            self._save_failed_items()

    def is_active_hours(self) -> bool:
        """현재 시간이 활성 시간인지 확인 (04:50-18:00)"""
        now = datetime.now().time()
        return self.active_hours['start'] <= now <= self.active_hours['end']

    def is_morning_init_time(self) -> bool:
        """04:50 첫 실행 시간인지 확인"""
        now = datetime.now().time()
        # 04:50 ~ 05:00 사이면 첫 실행
        return time(4, 50) <= now <= time(5, 0)

    async def get_holdings(self, conn) -> list:
        """보유 종목 목록 조회"""
        query = """
            SELECT stock_code, stock_name
            FROM stock_assets
            WHERE quantity > 0
            ORDER BY stock_code
        """
        return await conn.fetch(query)

    # =========================================================================
    # 데이터 수집 메서드
    # =========================================================================

    async def fetch_current_price(self, stock_code: str) -> dict:
        """네이버 금융에서 현재가 수집"""
        try:
            import re
            url = f"https://finance.naver.com/item/main.naver?code={stock_code}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}) as response:
                    if response.status != 200:
                        return None

                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    price = 0
                    change_rate = 0.0
                    volume = 0

                    dd_tags = soup.find_all('dd')
                    for dd in dd_tags:
                        text = dd.get_text(strip=True)

                        if text.startswith('현재가'):
                            numbers = re.findall(r'[\d,]+', text)
                            if numbers:
                                price = int(numbers[0].replace(',', ''))

                            if '상승' in text or '하락' in text:
                                rate_match = re.search(r'([\d.]+)\s*퍼센트', text)
                                if rate_match:
                                    change_rate = float(rate_match.group(1))
                                    if '하락' in text:
                                        change_rate = -change_rate

                        if text.startswith('거래량'):
                            vol_match = re.search(r'거래량\s*([\d,]+)', text)
                            if vol_match:
                                volume = int(vol_match.group(1).replace(',', ''))

                    if price == 0:
                        return None

                    return {
                        'price': price,
                        'change_rate': change_rate,
                        'volume': volume
                    }

        except Exception as e:
            self.log(f"현재가 수집 오류 ({stock_code}): {e}", "ERROR")
            return None

    async def fetch_yesterday_ohlcv(self, stock_code: str) -> dict:
        """전일 OHLCV 데이터 수집 (pykrx 사용)"""
        try:
            from pykrx import stock as pykrx_stock
            from datetime import date

            # 어제 날짜
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
            today = datetime.now().strftime('%Y%m%d')

            # 최근 5일 데이터 조회 (주말/공휴일 대비)
            df = pykrx_stock.get_market_ohlcv_by_date(
                fromdate=(datetime.now() - timedelta(days=7)).strftime('%Y%m%d'),
                todate=today,
                ticker=stock_code
            )

            if df.empty:
                return None

            # 가장 최근 데이터
            latest = df.iloc[-1]
            latest_date = df.index[-1].to_pydatetime().date()

            return {
                'date': latest_date,
                'open': int(latest['시가']),
                'high': int(latest['고가']),
                'low': int(latest['저가']),
                'close': int(latest['종가']),
                'volume': int(latest['거래량'])
            }

        except Exception as e:
            self.log(f"전일 OHLCV 수집 오류 ({stock_code}): {e}", "ERROR")
            return None

    async def fetch_investor_trends(self, stock_code: str) -> dict:
        """투자자별 수급 데이터 수집 (pykrx 사용)"""
        try:
            from pykrx import stock as pykrx_stock

            today = datetime.now().strftime('%Y%m%d')
            week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')

            df = pykrx_stock.get_market_trading_value_by_date(
                fromdate=week_ago,
                todate=today,
                ticker=stock_code
            )

            if df.empty:
                return None

            # 가장 최근 데이터
            latest = df.iloc[-1]
            latest_date = df.index[-1].to_pydatetime().date()

            return {
                'date': latest_date,
                'individual': int(latest.get('개인', 0)),
                'foreign': int(latest.get('외국인', 0)),
                'institutional': int(latest.get('기관', 0))
            }

        except Exception as e:
            self.log(f"수급 데이터 수집 오류 ({stock_code}): {e}", "ERROR")
            return None

    async def fetch_news(self, stock_code: str, stock_name: str) -> list:
        """네이버 뉴스 수집"""
        try:
            url = f"https://finance.naver.com/item/news_news.naver?code={stock_code}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}) as response:
                    if response.status != 200:
                        return []

                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    news_list = []
                    # 뉴스 테이블에서 항목 추출
                    rows = soup.select('.type5 tbody tr')[:10]

                    for row in rows:
                        try:
                            title_tag = row.select_one('.title a')
                            if not title_tag:
                                continue

                            title = title_tag.get_text(strip=True)
                            link = title_tag.get('href', '')

                            # 날짜
                            date_tag = row.select_one('.date')
                            date_str = date_tag.get_text(strip=True) if date_tag else ''

                            # 언론사
                            info_tag = row.select_one('.info')
                            source = info_tag.get_text(strip=True) if info_tag else 'naver'

                            news_list.append({
                                'title': title,
                                'url': f"https://finance.naver.com{link}" if link.startswith('/') else link,
                                'date': date_str,
                                'source': source
                            })

                        except:
                            continue

                    return news_list

        except Exception as e:
            self.log(f"뉴스 수집 오류 ({stock_code}): {e}", "ERROR")
            return []

    # =========================================================================
    # 데이터 저장 메서드
    # =========================================================================

    async def save_min_tick(self, conn, stock_code: str, data: dict) -> bool:
        """min_ticks 테이블에 저장"""
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
                data.get('change_rate', 0),
                data.get('volume', 0),
                0, 0, 0, 0  # 호가 데이터는 추후 구현
            )
            return True

        except Exception as e:
            self.log(f"min_tick 저장 오류 ({stock_code}): {e}", "ERROR")
            return False

    async def save_daily_ohlcv(self, conn, stock_code: str, data: dict) -> bool:
        """daily_ohlcv 테이블에 저장 (UPSERT)"""
        try:
            query = """
                INSERT INTO daily_ohlcv
                    (stock_code, date, open, high, low, close, volume, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, CURRENT_TIMESTAMP)
                ON CONFLICT (stock_code, date) DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume
            """

            await conn.execute(
                query,
                stock_code,
                data['date'],
                data['open'],
                data['high'],
                data['low'],
                data['close'],
                data['volume']
            )
            return True

        except Exception as e:
            self.log(f"daily_ohlcv 저장 오류 ({stock_code}): {e}", "ERROR")
            return False

    async def save_investor_trends(self, conn, stock_code: str, data: dict) -> bool:
        """investor_trends 테이블에 저장 (UPSERT)"""
        try:
            query = """
                INSERT INTO investor_trends
                    (stock_code, trade_date, individual, "foreign", institutional, created_at)
                VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP)
                ON CONFLICT (stock_code, trade_date) DO UPDATE SET
                    individual = EXCLUDED.individual,
                    "foreign" = EXCLUDED."foreign",
                    institutional = EXCLUDED.institutional
            """

            await conn.execute(
                query,
                stock_code,
                data['date'],
                data['individual'],
                data['foreign'],
                data['institutional']
            )
            return True

        except Exception as e:
            self.log(f"investor_trends 저장 오류 ({stock_code}): {e}", "ERROR")
            return False

    async def save_news(self, conn, stock_code: str, news_list: list) -> int:
        """news 테이블에 저장"""
        saved_count = 0

        for news in news_list:
            try:
                # 중복 체크
                check_query = """
                    SELECT COUNT(*) as cnt FROM news
                    WHERE stock_code = $1 AND title = $2
                """
                result = await conn.fetchrow(check_query, stock_code, news['title'])

                if result['cnt'] > 0:
                    continue

                # 삽입
                insert_query = """
                    INSERT INTO news
                        (stock_code, title, url, source, created_at)
                    VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
                """

                await conn.execute(
                    insert_query,
                    stock_code,
                    news['title'],
                    news.get('url', ''),
                    news.get('source', 'naver')
                )
                saved_count += 1

            except Exception as e:
                self.log(f"뉴스 저장 오류: {e}", "ERROR")
                continue

        return saved_count

    # =========================================================================
    # PDF 생성
    # =========================================================================

    def regenerate_pdf(self, stock_code: str) -> bool:
        """PDF 리포트 재생성"""
        try:
            result = subprocess.run(
                [
                    '/Users/wonny/Dev/joungwon.stocks/venv/bin/python',
                    '/Users/wonny/Dev/joungwon.stocks/scripts/gemini/generate_pdf_report.py',
                    stock_code
                ],
                capture_output=True,
                text=True,
                timeout=180  # 3분 타임아웃
            )

            if result.returncode == 0:
                return True
            else:
                self.log(f"PDF 생성 실패 ({stock_code}): {result.stderr[:200]}", "ERROR")
                return False

        except subprocess.TimeoutExpired:
            self.log(f"PDF 생성 시간 초과 ({stock_code})", "ERROR")
            return False
        except Exception as e:
            self.log(f"PDF 생성 오류 ({stock_code}): {e}", "ERROR")
            return False

    # =========================================================================
    # 메인 실행
    # =========================================================================

    async def process_stock(self, conn, stock_code: str, stock_name: str, is_morning: bool) -> dict:
        """
        개별 종목 처리 (독립 실행 - 다른 종목에 영향 없음)

        Returns:
            dict: {'success': bool, 'details': {...}}
        """
        result = {
            'success': True,
            'price_collected': False,
            'ohlcv_collected': False,
            'trends_collected': False,
            'news_count': 0,
            'pdf_generated': False,
            'errors': []
        }

        try:
            # 1. 현재가 수집
            price_data = await self.fetch_current_price(stock_code)
            if price_data:
                saved = await self.save_min_tick(conn, stock_code, price_data)
                if saved:
                    result['price_collected'] = True
                    self._clear_failure(stock_code, 'price')
                else:
                    self._record_failure(stock_code, 'price', 'DB save failed')
                    result['errors'].append('price_save_failed')
            else:
                self._record_failure(stock_code, 'price', 'Fetch failed')
                result['errors'].append('price_fetch_failed')

            # 2. 04:50 첫 실행 시 전일 데이터 수집
            if is_morning:
                # 전일 OHLCV
                ohlcv_data = await self.fetch_yesterday_ohlcv(stock_code)
                if ohlcv_data:
                    saved = await self.save_daily_ohlcv(conn, stock_code, ohlcv_data)
                    if saved:
                        result['ohlcv_collected'] = True
                        self._clear_failure(stock_code, 'ohlcv')
                else:
                    self._record_failure(stock_code, 'ohlcv', 'Fetch failed')
                    result['errors'].append('ohlcv_fetch_failed')

                # 투자자 수급
                trends_data = await self.fetch_investor_trends(stock_code)
                if trends_data:
                    saved = await self.save_investor_trends(conn, stock_code, trends_data)
                    if saved:
                        result['trends_collected'] = True
                        self._clear_failure(stock_code, 'trends')
                else:
                    self._record_failure(stock_code, 'trends', 'Fetch failed')
                    result['errors'].append('trends_fetch_failed')

            # 3. 실패 데이터 재시도
            stock_failures = self.failed_items['stocks'].get(stock_code, {})
            for data_type, failure_info in list(stock_failures.items()):
                if failure_info.get('retry_count', 0) < 5:  # 최대 5회 재시도
                    self.log(f"재시도 ({stock_code}/{data_type}): {failure_info.get('retry_count', 0) + 1}회차", "INFO")

                    if data_type == 'ohlcv':
                        ohlcv_data = await self.fetch_yesterday_ohlcv(stock_code)
                        if ohlcv_data:
                            await self.save_daily_ohlcv(conn, stock_code, ohlcv_data)
                            self._clear_failure(stock_code, 'ohlcv')

                    elif data_type == 'trends':
                        trends_data = await self.fetch_investor_trends(stock_code)
                        if trends_data:
                            await self.save_investor_trends(conn, stock_code, trends_data)
                            self._clear_failure(stock_code, 'trends')

            # 4. 뉴스 수집
            news_list = await self.fetch_news(stock_code, stock_name)
            if news_list:
                saved_count = await self.save_news(conn, stock_code, news_list)
                result['news_count'] = saved_count

            # 5. PDF 재생성
            pdf_success = self.regenerate_pdf(stock_code)
            result['pdf_generated'] = pdf_success

            if result['errors']:
                result['success'] = False

        except Exception as e:
            result['success'] = False
            result['errors'].append(str(e))
            self.log(f"종목 처리 오류 ({stock_code}): {e}", "ERROR")

        return result

    async def run(self):
        """메인 실행"""
        self.log("=" * 80)
        self.log("📊 10분 데이터 수집 및 PDF 재생성 시작")
        self.log("=" * 80)

        # 시간 체크
        if not self.is_active_hours():
            now = datetime.now()
            if now.time() < self.active_hours['start']:
                next_run = now.replace(hour=4, minute=50, second=0)
            else:
                next_run = (now + timedelta(days=1)).replace(hour=4, minute=50, second=0)

            self.log(f"⏸️  실행 시간 외 (04:50 ~ 18:00)")
            self.log(f"   현재 시각: {now.strftime('%Y-%m-%d %H:%M:%S')}")
            self.log(f"   다음 실행: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            return

        is_morning = self.is_morning_init_time()
        if is_morning:
            self.log("🌅 04:50 첫 실행 - 전일 데이터 수집 포함")

        # DB 연결
        conn = await asyncpg.connect(**DB_CONFIG)

        try:
            # 보유 종목 조회
            holdings = await self.get_holdings(conn)

            if not holdings:
                self.log("📭 보유 종목이 없습니다.")
                return

            self.log(f"📈 총 {len(holdings)}개 종목 처리 중...\n")

            # 결과 집계
            total_results = {
                'success': 0,
                'failed': 0,
                'price_collected': 0,
                'ohlcv_collected': 0,
                'trends_collected': 0,
                'news_total': 0,
                'pdf_generated': 0
            }

            # 각 종목 처리 (독립적)
            for row in holdings:
                stock_code = row['stock_code']
                stock_name = row['stock_name']

                self.log(f"\n{'─'*60}")
                self.log(f"🔹 {stock_name} ({stock_code}) 처리 중...")

                result = await self.process_stock(conn, stock_code, stock_name, is_morning)

                # 결과 로깅
                status = "✅" if result['success'] else "⚠️"
                self.log(f"   {status} 현재가: {'O' if result['price_collected'] else 'X'} | "
                        f"OHLCV: {'O' if result['ohlcv_collected'] else '-'} | "
                        f"수급: {'O' if result['trends_collected'] else '-'} | "
                        f"뉴스: {result['news_count']}건 | "
                        f"PDF: {'O' if result['pdf_generated'] else 'X'}")

                if result['errors']:
                    self.log(f"   ⚠️  오류: {', '.join(result['errors'])}", "WARNING")

                # 집계
                if result['success']:
                    total_results['success'] += 1
                else:
                    total_results['failed'] += 1

                if result['price_collected']:
                    total_results['price_collected'] += 1
                if result['ohlcv_collected']:
                    total_results['ohlcv_collected'] += 1
                if result['trends_collected']:
                    total_results['trends_collected'] += 1
                total_results['news_total'] += result['news_count']
                if result['pdf_generated']:
                    total_results['pdf_generated'] += 1

                # API 호출 제한 방지
                await asyncio.sleep(1)

            # 최종 요약
            self.log(f"\n{'='*80}")
            self.log(f"📊 실행 완료 요약:")
            self.log(f"   성공: {total_results['success']}개 | 실패: {total_results['failed']}개")
            self.log(f"   현재가 수집: {total_results['price_collected']}개")
            if is_morning:
                self.log(f"   OHLCV 수집: {total_results['ohlcv_collected']}개")
                self.log(f"   수급 수집: {total_results['trends_collected']}개")
            self.log(f"   뉴스 저장: {total_results['news_total']}건")
            self.log(f"   PDF 생성: {total_results['pdf_generated']}개")
            self.log("=" * 80)

        except Exception as e:
            self.log(f"❌ 전체 실행 오류: {e}", "ERROR")
            traceback.print_exc()

        finally:
            await conn.close()


async def main():
    """메인 함수"""
    collector = TenMinuteCollector()
    await collector.run()


if __name__ == '__main__':
    asyncio.run(main())
