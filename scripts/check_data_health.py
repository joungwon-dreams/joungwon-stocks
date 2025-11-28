#!/usr/bin/env python3
"""
종목별 데이터 수집 현황 체크 및 누락 데이터 재수집 스크립트

사용법:
    python scripts/check_data_health.py           # 현황 체크만
    python scripts/check_data_health.py --fix     # 누락 데이터 재수집 시도
    python scripts/check_data_health.py --report  # 상세 리포트 생성
"""
import asyncio
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import asyncpg

sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'stock_investment_db',
    'user': 'wonny'
}

# 데이터 상태 저장 파일
HEALTH_REPORT_FILE = Path('/Users/wonny/Dev/joungwon.stocks/logs/data_health_report.json')


class DataHealthChecker:
    """종목별 데이터 수집 상태 체크"""

    def __init__(self):
        self.conn = None
        self.report = {
            'check_time': datetime.now().isoformat(),
            'summary': {},
            'stocks': {}
        }

    async def connect(self):
        self.conn = await asyncpg.connect(**DB_CONFIG)

    async def disconnect(self):
        if self.conn:
            await self.conn.close()

    async def get_holdings(self):
        """보유 종목 목록"""
        return await self.conn.fetch('''
            SELECT stock_code, stock_name
            FROM stock_assets
            WHERE quantity > 0
            ORDER BY stock_name
        ''')

    async def check_stock_data(self, stock_code: str, stock_name: str) -> dict:
        """개별 종목 데이터 상태 체크"""
        result = {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'items': {},
            'missing': [],
            'stale': [],
            'ok': []
        }

        today = datetime.now().date()

        # 1. 현재가 (min_ticks) - 오늘 데이터
        price = await self.conn.fetchrow('''
            SELECT price, change_rate, timestamp
            FROM min_ticks
            WHERE stock_code = $1 AND DATE(timestamp) = CURRENT_DATE
            ORDER BY timestamp DESC LIMIT 1
        ''', stock_code)

        if price:
            result['items']['price'] = {
                'status': 'ok',
                'value': f"{price['price']:,}원 ({price['change_rate']:+.2f}%)",
                'time': price['timestamp'].strftime('%H:%M')
            }
            result['ok'].append('price')
        else:
            result['items']['price'] = {'status': 'missing', 'reason': '오늘 데이터 없음'}
            result['missing'].append('price')

        # 2. OHLCV - 최근 데이터 (3일 이내)
        ohlcv = await self.conn.fetchrow('''
            SELECT date, open, high, low, close, volume
            FROM daily_ohlcv
            WHERE stock_code = $1
            ORDER BY date DESC LIMIT 1
        ''', stock_code)

        if ohlcv:
            days_old = (today - ohlcv['date']).days
            if days_old <= 3:
                result['items']['ohlcv'] = {
                    'status': 'ok',
                    'value': f"종가 {ohlcv['close']:,}원",
                    'date': str(ohlcv['date']),
                    'days_old': days_old
                }
                result['ok'].append('ohlcv')
            else:
                result['items']['ohlcv'] = {
                    'status': 'stale',
                    'value': f"종가 {ohlcv['close']:,}원",
                    'date': str(ohlcv['date']),
                    'days_old': days_old,
                    'reason': f'{days_old}일 전 데이터'
                }
                result['stale'].append('ohlcv')
        else:
            result['items']['ohlcv'] = {'status': 'missing', 'reason': '데이터 없음'}
            result['missing'].append('ohlcv')

        # 3. 투자자 수급 (3일 이내)
        trends = await self.conn.fetchrow('''
            SELECT trade_date, individual, "foreign", institutional
            FROM investor_trends
            WHERE stock_code = $1
            ORDER BY trade_date DESC LIMIT 1
        ''', stock_code)

        if trends:
            days_old = (today - trends['trade_date']).days
            foreign_val = trends['foreign'] / 100000000 if trends['foreign'] else 0
            if days_old <= 3:
                result['items']['investor_trends'] = {
                    'status': 'ok',
                    'value': f"외국인 {foreign_val:+.1f}억",
                    'date': str(trends['trade_date']),
                    'days_old': days_old
                }
                result['ok'].append('investor_trends')
            else:
                result['items']['investor_trends'] = {
                    'status': 'stale',
                    'value': f"외국인 {foreign_val:+.1f}억",
                    'date': str(trends['trade_date']),
                    'days_old': days_old,
                    'reason': f'{days_old}일 전 데이터'
                }
                result['stale'].append('investor_trends')
        else:
            result['items']['investor_trends'] = {'status': 'missing', 'reason': '데이터 없음'}
            result['missing'].append('investor_trends')

        # 4. 뉴스 (최근 7일)
        news_count = await self.conn.fetchval('''
            SELECT COUNT(*) FROM news
            WHERE stock_code = $1 AND created_at > NOW() - INTERVAL '7 days'
        ''', stock_code)

        if news_count and news_count > 0:
            result['items']['news'] = {
                'status': 'ok',
                'value': f'{news_count}건',
                'count': news_count
            }
            result['ok'].append('news')
        else:
            result['items']['news'] = {
                'status': 'warning',
                'value': '0건',
                'reason': '최근 7일 뉴스 없음'
            }
            # 뉴스는 없을 수 있으므로 missing이 아닌 warning

        # 5. 컨센서스 (목표가)
        consensus = await self.conn.fetchrow('''
            SELECT target_price, opinion, analyst_count, updated_at
            FROM stock_consensus
            WHERE stock_code = $1
        ''', stock_code)

        if consensus and consensus['target_price']:
            days_old = (datetime.now() - consensus['updated_at']).days if consensus['updated_at'] else 999
            result['items']['consensus'] = {
                'status': 'ok' if days_old <= 30 else 'stale',
                'value': f"목표가 {consensus['target_price']:,}원",
                'opinion': consensus['opinion'],
                'analyst_count': consensus['analyst_count'],
                'days_old': days_old
            }
            if days_old <= 30:
                result['ok'].append('consensus')
            else:
                result['stale'].append('consensus')
        else:
            result['items']['consensus'] = {'status': 'missing', 'reason': '목표가 없음'}
            result['missing'].append('consensus')

        # 6. 재무제표
        financials_count = await self.conn.fetchval('''
            SELECT COUNT(*) FROM stock_financials
            WHERE stock_code = $1
        ''', stock_code)

        if financials_count and financials_count > 0:
            result['items']['financials'] = {
                'status': 'ok',
                'value': f'{financials_count}건',
                'count': financials_count
            }
            result['ok'].append('financials')
        else:
            result['items']['financials'] = {'status': 'missing', 'reason': '데이터 없음'}
            result['missing'].append('financials')

        # 7. 기업개요 (fundamentals)
        fundamentals = await self.conn.fetchrow('''
            SELECT company_summary, per, pbr, eps, dividend_yield, updated_at
            FROM stock_fundamentals
            WHERE stock_code = $1
        ''', stock_code)

        if fundamentals:
            has_summary = bool(fundamentals['company_summary'])
            has_per = fundamentals['per'] is not None
            has_pbr = fundamentals['pbr'] is not None

            missing_items = []
            if not has_summary:
                missing_items.append('기업개요')
            if not has_per:
                missing_items.append('PER')
            if not has_pbr:
                missing_items.append('PBR')

            if not missing_items:
                result['items']['fundamentals'] = {
                    'status': 'ok',
                    'value': f"PER {fundamentals['per']:.1f}, PBR {fundamentals['pbr']:.2f}" if has_per and has_pbr else 'OK',
                    'has_summary': has_summary,
                    'per': fundamentals['per'],
                    'pbr': fundamentals['pbr']
                }
                result['ok'].append('fundamentals')
            else:
                result['items']['fundamentals'] = {
                    'status': 'partial',
                    'value': f"누락: {', '.join(missing_items)}",
                    'missing_items': missing_items,
                    'has_summary': has_summary,
                    'per': fundamentals['per'],
                    'pbr': fundamentals['pbr']
                }
                result['missing'].append('fundamentals_partial')
        else:
            result['items']['fundamentals'] = {'status': 'missing', 'reason': '데이터 없음'}
            result['missing'].append('fundamentals')

        return result

    async def check_all(self):
        """모든 보유 종목 체크"""
        await self.connect()

        try:
            holdings = await self.get_holdings()

            total_ok = 0
            total_missing = 0
            total_stale = 0

            print('=' * 100)
            print(f'📊 보유 종목 데이터 수집 현황 ({datetime.now().strftime("%Y-%m-%d %H:%M:%S")})')
            print('=' * 100)

            for h in holdings:
                code = h['stock_code']
                name = h['stock_name']

                result = await self.check_stock_data(code, name)
                self.report['stocks'][code] = result

                # 상태 아이콘
                if result['missing']:
                    status_icon = '❌'
                    total_missing += 1
                elif result['stale']:
                    status_icon = '⚠️'
                    total_stale += 1
                else:
                    status_icon = '✅'
                    total_ok += 1

                print(f'\n{status_icon} {name} ({code})')
                print('-' * 80)

                # 항목별 상태 출력
                for item_name, item_data in result['items'].items():
                    item_icon = {
                        'ok': '✅',
                        'missing': '❌',
                        'stale': '⏰',
                        'warning': '⚠️',
                        'partial': '🔶'
                    }.get(item_data['status'], '❓')

                    item_label = {
                        'price': '현재가',
                        'ohlcv': 'OHLCV',
                        'investor_trends': '투자자수급',
                        'news': '뉴스',
                        'consensus': '컨센서스',
                        'financials': '재무제표',
                        'fundamentals': '기업개요'
                    }.get(item_name, item_name)

                    value = item_data.get('value', item_data.get('reason', '-'))
                    print(f'  {item_icon} {item_label}: {value}')

                # 누락/오래된 항목 요약
                if result['missing']:
                    print(f'  📋 누락: {", ".join(result["missing"])}')
                if result['stale']:
                    print(f'  📋 갱신필요: {", ".join(result["stale"])}')

            # 전체 요약
            self.report['summary'] = {
                'total': len(holdings),
                'ok': total_ok,
                'missing': total_missing,
                'stale': total_stale
            }

            print('\n' + '=' * 100)
            print('📈 전체 요약')
            print('=' * 100)
            print(f'  총 종목: {len(holdings)}개')
            print(f'  ✅ 정상: {total_ok}개')
            print(f'  ⚠️ 갱신필요: {total_stale}개')
            print(f'  ❌ 누락: {total_missing}개')

            # 리포트 저장
            HEALTH_REPORT_FILE.parent.mkdir(exist_ok=True)
            with open(HEALTH_REPORT_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.report, f, ensure_ascii=False, indent=2, default=str)
            print(f'\n📄 리포트 저장: {HEALTH_REPORT_FILE}')

        finally:
            await self.disconnect()

        return self.report

    async def fix_missing_data(self):
        """누락 데이터 재수집 시도"""
        print('\n' + '=' * 100)
        print('🔧 누락 데이터 재수집 시도')
        print('=' * 100)

        await self.connect()

        try:
            # 기존 리포트 로드
            if HEALTH_REPORT_FILE.exists():
                with open(HEALTH_REPORT_FILE, 'r', encoding='utf-8') as f:
                    self.report = json.load(f)
            else:
                print('❌ 먼저 체크를 실행하세요: python scripts/check_data_health.py')
                return

            for stock_code, stock_data in self.report['stocks'].items():
                if not stock_data['missing'] and not stock_data['stale']:
                    continue

                stock_name = stock_data['stock_name']
                print(f'\n🔹 {stock_name} ({stock_code})')

                # 누락된 데이터 타입별 재수집
                items_to_fix = stock_data['missing'] + stock_data['stale']

                for item in items_to_fix:
                    print(f'  → {item} 재수집 시도...')

                    if item in ['ohlcv', 'investor_trends']:
                        # pykrx로 재수집
                        success = await self._fetch_pykrx_data(stock_code, item)
                        print(f'    {"✅ 성공" if success else "❌ 실패"}')

                    elif item == 'price':
                        # 네이버 현재가 재수집
                        success = await self._fetch_current_price(stock_code)
                        print(f'    {"✅ 성공" if success else "❌ 실패"}')

                    elif item == 'consensus':
                        # 네이버 컨센서스 재수집
                        success = await self._fetch_consensus(stock_code)
                        print(f'    {"✅ 성공" if success else "❌ 실패"}')

                    elif item in ['fundamentals', 'fundamentals_partial']:
                        # 기업개요 재수집
                        success = await self._fetch_fundamentals(stock_code)
                        print(f'    {"✅ 성공" if success else "❌ 실패"}')

                    elif item == 'financials':
                        # 재무제표 재수집 (FnGuide 등에서)
                        success = await self._fetch_financials(stock_code)
                        print(f'    {"✅ 성공" if success else "❌ 실패"}')

                    await asyncio.sleep(0.5)  # Rate limit

        finally:
            await self.disconnect()

    async def _fetch_pykrx_data(self, stock_code: str, data_type: str) -> bool:
        """pykrx로 OHLCV/수급 데이터 수집"""
        try:
            from pykrx import stock as pykrx_stock

            today = datetime.now().strftime('%Y%m%d')
            week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')

            if data_type == 'ohlcv':
                df = pykrx_stock.get_market_ohlcv_by_date(week_ago, today, stock_code)
                if df.empty:
                    return False

                latest = df.iloc[-1]
                latest_date = df.index[-1].to_pydatetime().date()

                await self.conn.execute('''
                    INSERT INTO daily_ohlcv (stock_code, date, open, high, low, close, volume, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, CURRENT_TIMESTAMP)
                    ON CONFLICT (stock_code, date) DO UPDATE SET
                        open = EXCLUDED.open, high = EXCLUDED.high,
                        low = EXCLUDED.low, close = EXCLUDED.close,
                        volume = EXCLUDED.volume
                ''', stock_code, latest_date,
                    int(latest['시가']), int(latest['고가']),
                    int(latest['저가']), int(latest['종가']),
                    int(latest['거래량']))
                return True

            elif data_type == 'investor_trends':
                df = pykrx_stock.get_market_trading_value_by_date(week_ago, today, stock_code)
                if df.empty:
                    return False

                latest = df.iloc[-1]
                latest_date = df.index[-1].to_pydatetime().date()

                await self.conn.execute('''
                    INSERT INTO investor_trends (stock_code, trade_date, individual, "foreign", institutional, collected_at)
                    VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP)
                    ON CONFLICT (stock_code, trade_date) DO UPDATE SET
                        individual = EXCLUDED.individual,
                        "foreign" = EXCLUDED."foreign",
                        institutional = EXCLUDED.institutional
                ''', stock_code, latest_date,
                    int(latest.get('개인', 0)),
                    int(latest.get('외국인', 0)),
                    int(latest.get('기관', 0)))
                return True

            return False

        except Exception as e:
            print(f'    오류: {e}')
            return False

    async def _fetch_current_price(self, stock_code: str) -> bool:
        """네이버에서 현재가 수집"""
        try:
            import aiohttp
            from bs4 import BeautifulSoup
            import re

            url = f"https://finance.naver.com/item/main.naver?code={stock_code}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}) as response:
                    if response.status != 200:
                        return False

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
                        return False

                    await self.conn.execute('''
                        INSERT INTO min_ticks (stock_code, timestamp, price, change_rate, volume,
                            bid_price, ask_price, bid_volume, ask_volume, created_at)
                        VALUES ($1, $2, $3, $4, $5, 0, 0, 0, 0, CURRENT_TIMESTAMP)
                    ''', stock_code, datetime.now(), price, change_rate, volume)

                    return True

        except Exception as e:
            print(f'    오류: {e}')
            return False

    async def _fetch_consensus(self, stock_code: str) -> bool:
        """네이버 컨센서스 수집"""
        try:
            sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')
            from scripts.gemini.naver.consensus import NaverConsensusFetcher

            fetcher = NaverConsensusFetcher()
            data = await fetcher.fetch_consensus(stock_code)

            if not data or not data.get('target_price'):
                return False

            # 콤마 제거 후 정수 변환
            target_price_str = str(data['target_price']).replace(',', '')
            try:
                target_price = int(float(target_price_str))
            except:
                target_price = None

            await self.conn.execute('''
                INSERT INTO stock_consensus (stock_code, target_price, opinion, analyst_count, updated_at)
                VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
                ON CONFLICT (stock_code) DO UPDATE SET
                    target_price = EXCLUDED.target_price,
                    opinion = EXCLUDED.opinion,
                    analyst_count = EXCLUDED.analyst_count,
                    updated_at = CURRENT_TIMESTAMP
            ''', stock_code,
                target_price,
                data.get('opinion', ''),
                data.get('analyst_count', 0) or 0)

            return True

        except Exception as e:
            print(f'    오류: {e}')
            return False

    async def _fetch_financials(self, stock_code: str) -> bool:
        """네이버에서 재무제표 수집"""
        try:
            import aiohttp
            from bs4 import BeautifulSoup
            import re

            url = f"https://finance.naver.com/item/main.naver?code={stock_code}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}) as response:
                    if response.status != 200:
                        return False

                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # 재무정보 테이블 찾기
                    table = soup.select_one('.tb_type1_ifrs')
                    if not table:
                        table = soup.select_one('.tb_type1')

                    if not table:
                        return False

                    # 헤더에서 연도 추출
                    headers = table.select('thead th')
                    years = []
                    for th in headers[1:]:  # 첫 번째는 '주요재무정보'
                        text = th.get_text(strip=True)
                        year_match = re.search(r'(\d{4})', text)
                        if year_match:
                            years.append(year_match.group(1))

                    if not years:
                        return False

                    # 행 데이터 추출
                    rows = table.select('tbody tr')
                    data = {}

                    for row in rows:
                        cells = row.select('td')
                        th = row.select_one('th')
                        if not th or len(cells) < len(years):
                            continue

                        row_name = th.get_text(strip=True)

                        # 매출액, 영업이익, 당기순이익 추출
                        for i, year in enumerate(years):
                            if i >= len(cells):
                                break

                            cell_text = cells[i].get_text(strip=True)
                            # 숫자 추출 (억 단위)
                            num_match = re.search(r'([-]?[\d,]+)', cell_text)
                            if num_match:
                                value = int(num_match.group(1).replace(',', ''))
                            else:
                                value = None

                            if year not in data:
                                data[year] = {}

                            if '매출' in row_name:
                                data[year]['revenue'] = value
                            elif '영업이익' in row_name and '률' not in row_name:
                                data[year]['operating_profit'] = value
                            elif '당기순이익' in row_name or '순이익' in row_name:
                                data[year]['net_profit'] = value

                    # DB 저장
                    saved = 0
                    for year, values in data.items():
                        if not values:
                            continue

                        try:
                            await self.conn.execute('''
                                INSERT INTO stock_financials
                                    (stock_code, fiscal_year, fiscal_quarter, period_type, revenue, operating_profit, net_profit, collected_at)
                                VALUES ($1, $2, NULL, 'yearly', $3, $4, $5, CURRENT_TIMESTAMP)
                                ON CONFLICT (stock_code, period_type, fiscal_year, fiscal_quarter) DO UPDATE SET
                                    revenue = EXCLUDED.revenue,
                                    operating_profit = EXCLUDED.operating_profit,
                                    net_profit = EXCLUDED.net_profit
                            ''', stock_code, int(year),
                                values.get('revenue'),
                                values.get('operating_profit'),
                                values.get('net_profit'))
                            saved += 1
                        except Exception as e:
                            print(f'      재무제표 저장 오류 ({year}): {e}')

                    return saved > 0

        except Exception as e:
            print(f'    오류: {e}')
            return False

    async def _fetch_fundamentals(self, stock_code: str) -> bool:
        """기업개요 수집"""
        try:
            import aiohttp
            from bs4 import BeautifulSoup

            url = f"https://finance.naver.com/item/main.naver?code={stock_code}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}) as response:
                    if response.status != 200:
                        return False

                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # 기업개요 추출
                    summary = ''
                    summary_div = soup.select_one('.summary_info')
                    if summary_div:
                        summary = summary_div.get_text(strip=True)[:500]

                    # PER, PBR 추출 시도
                    per = None
                    pbr = None

                    table = soup.select_one('.aside_invest_info table')
                    if table:
                        rows = table.select('tr')
                        for row in rows:
                            text = row.get_text()
                            if 'PER' in text:
                                import re
                                match = re.search(r'PER.*?([\d.]+)', text)
                                if match:
                                    per = float(match.group(1))
                            if 'PBR' in text:
                                match = re.search(r'PBR.*?([\d.]+)', text)
                                if match:
                                    pbr = float(match.group(1))

                    # DB 업데이트
                    await self.conn.execute('''
                        INSERT INTO stock_fundamentals (stock_code, company_summary, per, pbr, updated_at)
                        VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
                        ON CONFLICT (stock_code) DO UPDATE SET
                            company_summary = COALESCE(EXCLUDED.company_summary, stock_fundamentals.company_summary),
                            per = COALESCE(EXCLUDED.per, stock_fundamentals.per),
                            pbr = COALESCE(EXCLUDED.pbr, stock_fundamentals.pbr),
                            updated_at = CURRENT_TIMESTAMP
                    ''', stock_code, summary if summary else None, per, pbr)

                    return True

        except Exception as e:
            print(f'    오류: {e}')
            return False


async def main():
    parser = argparse.ArgumentParser(description='종목별 데이터 수집 현황 체크')
    parser.add_argument('--fix', action='store_true', help='누락 데이터 재수집 시도')
    parser.add_argument('--report', action='store_true', help='상세 JSON 리포트만 생성')
    args = parser.parse_args()

    checker = DataHealthChecker()

    # 항상 먼저 체크
    await checker.check_all()

    # --fix 옵션 시 재수집 시도
    if args.fix:
        await checker.fix_missing_data()
        # 재수집 후 다시 체크
        print('\n🔄 재수집 후 현황 재체크...')
        checker2 = DataHealthChecker()
        await checker2.check_all()


if __name__ == '__main__':
    asyncio.run(main())
