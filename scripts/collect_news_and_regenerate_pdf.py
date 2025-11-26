#!/usr/bin/env python3
"""
30분마다 뉴스 및 공시 수집 후 PDF 재생성
- 네이버 뉴스 크롤링
- DART 전자공시 조회
- PDF 뉴스 섹션 업데이트 후 재생성
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
import aiohttp
from bs4 import BeautifulSoup

# .env 파일 로드 (cron 환경에서 필수)
from dotenv import load_dotenv
load_dotenv('/Users/wonny/Dev/joungwon.stocks/.env')

sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')
from src.config.database import db


class NewsCollectorAndPDFGenerator:
    def __init__(self):
        self.log_file = Path('/Users/wonny/Dev/joungwon.stocks/logs/news_collection.log')
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log(self, message: str):
        """로그 메시지 출력"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)

        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_msg + '\n')

    async def get_holdings(self):
        """보유 종목 목록 조회"""
        query = """
            SELECT stock_code, stock_name
            FROM stock_assets
            WHERE quantity > 0
            ORDER BY total_value DESC
        """
        return await db.fetch(query)

    async def collect_naver_news(self, stock_code: str, stock_name: str):
        """네이버 뉴스 수집"""
        try:
            url = f"https://finance.naver.com/item/news_news.naver?code={stock_code}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}) as response:
                    if response.status != 200:
                        self.log(f"⚠️  {stock_name}: 네이버 뉴스 조회 실패 (HTTP {response.status})")
                        return []

                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    news_list = []
                    news_items = soup.select('.newsList .relation_lst li')[:10]  # 최근 10개

                    for item in news_items:
                        try:
                            title_tag = item.select_one('a')
                            if not title_tag:
                                continue

                            title = title_tag.get_text(strip=True)
                            link = title_tag.get('href', '')

                            # 날짜 파싱
                            date_tag = item.select_one('.date')
                            date_str = date_tag.get_text(strip=True) if date_tag else ''

                            # 언론사
                            press_tag = item.select_one('.info')
                            press = press_tag.get_text(strip=True) if press_tag else '네이버금융'

                            news_list.append({
                                'title': title,
                                'link': f"https://finance.naver.com{link}" if link.startswith('/') else link,
                                'date': date_str,
                                'press': press,
                                'source': 'naver'
                            })

                        except Exception as e:
                            self.log(f"⚠️  뉴스 항목 파싱 오류: {e}")
                            continue

                    return news_list

        except Exception as e:
            self.log(f"❌ {stock_name} 네이버 뉴스 수집 오류: {e}")
            return []

    async def collect_dart_disclosures(self, stock_code: str, stock_name: str):
        """DART 전자공시 조회 (간단 버전)"""
        try:
            # DART API는 API 키 필요 - 여기서는 네이버 금융의 공시 탭 크롤링
            url = f"https://finance.naver.com/item/news_notice.naver?code={stock_code}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}) as response:
                    if response.status != 200:
                        self.log(f"⚠️  {stock_name}: 공시 조회 실패 (HTTP {response.status})")
                        return []

                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    disclosures = []
                    items = soup.select('.tb_cont tbody tr')[:5]  # 최근 5개

                    for item in items:
                        try:
                            title_tag = item.select_one('td.title a')
                            if not title_tag:
                                continue

                            title = title_tag.get_text(strip=True)
                            link = title_tag.get('href', '')

                            # 날짜
                            date_tag = item.select_one('td.date')
                            date_str = date_tag.get_text(strip=True) if date_tag else ''

                            disclosures.append({
                                'title': title,
                                'link': f"https://finance.naver.com{link}" if link.startswith('/') else link,
                                'date': date_str,
                                'source': 'dart'
                            })

                        except Exception as e:
                            self.log(f"⚠️  공시 항목 파싱 오류: {e}")
                            continue

                    return disclosures

        except Exception as e:
            self.log(f"❌ {stock_name} DART 공시 수집 오류: {e}")
            return []

    async def save_news_to_db(self, stock_code: str, news_list: list):
        """뉴스 데이터를 DB에 저장"""
        if not news_list:
            return 0

        saved_count = 0

        for news in news_list:
            try:
                # 중복 체크 (제목 + 날짜)
                check_query = """
                    SELECT COUNT(*) as cnt
                    FROM news
                    WHERE stock_code = $1 AND title = $2
                """
                result = await db.fetchrow(check_query, stock_code, news['title'])

                if result['cnt'] > 0:
                    continue  # 이미 존재하는 뉴스

                # 삽입
                insert_query = """
                    INSERT INTO news (
                        stock_code, title, url, content,
                        published_at, source, created_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP)
                """

                # published_at 파싱 (간단 버전)
                published_at = datetime.now() - timedelta(hours=1)  # 임시

                await db.execute(
                    insert_query,
                    stock_code,
                    news['title'],
                    news['link'],
                    '',  # content는 비워둠
                    published_at,
                    news.get('source', 'naver')
                )

                saved_count += 1

            except Exception as e:
                self.log(f"⚠️  뉴스 저장 오류: {e}")
                continue

        return saved_count

    async def regenerate_pdf_for_stock(self, stock_code: str, stock_name: str):
        """특정 종목의 PDF 재생성 (뉴스 섹션 업데이트)"""
        try:
            self.log(f"📄 {stock_name} PDF 재생성 시작...")

            # PDF 생성 스크립트 호출
            # 실제로는 scripts/gemini/generate_single_report.py 등을 사용
            import subprocess

            result = subprocess.run(
                [
                    '/Users/wonny/Dev/joungwon.stocks/venv/bin/python',
                    '/Users/wonny/Dev/joungwon.stocks/scripts/gemini/generate_single_report.py',
                    stock_code
                ],
                capture_output=True,
                text=True,
                timeout=300  # 5분 타임아웃
            )

            if result.returncode == 0:
                self.log(f"✅ {stock_name} PDF 재생성 완료")
                return True
            else:
                self.log(f"❌ {stock_name} PDF 재생성 실패: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.log(f"⏱️  {stock_name} PDF 생성 시간 초과 (5분)")
            return False
        except Exception as e:
            self.log(f"❌ {stock_name} PDF 재생성 오류: {e}")
            return False

    async def process_all_holdings(self):
        """모든 보유 종목 처리"""
        self.log("=" * 80)
        self.log("📰 30분 뉴스 수집 및 PDF 재생성 시작")
        self.log("=" * 80)

        # 시간 제한 체크 (04:00 ~ 18:00만 허용)
        now = datetime.now()
        current_hour = now.hour

        if current_hour < 4 or current_hour >= 18:
            # 다음 실행 가능 시각 계산
            if current_hour >= 18:
                # 18시 이후면 내일 04시
                next_available = (now + timedelta(days=1)).replace(hour=4, minute=0, second=0)
            else:
                # 04시 이전이면 오늘 04시
                next_available = now.replace(hour=4, minute=0, second=0)

            self.log(f"⚠️  실행 시간 제한: 04:00 ~ 18:00만 허용됩니다.")
            self.log(f"   현재 시각: {now.strftime('%Y-%m-%d %H:%M:%S')}")
            self.log(f"   다음 실행 가능 시각: {next_available.strftime('%Y-%m-%d %H:%M:%S')}")
            self.log("=" * 80)
            return

        await db.connect()

        try:
            # 보유 종목 조회
            holdings = await self.get_holdings()

            if not holdings:
                self.log("📭 보유 종목이 없습니다.")
                return

            self.log(f"📊 총 {len(holdings)}개 종목 처리 중...\n")

            total_news = 0
            total_disclosures = 0
            pdf_success = 0
            pdf_fail = 0

            for row in holdings:
                stock_code = row['stock_code']
                stock_name = row['stock_name']

                self.log(f"\n{'='*60}")
                self.log(f"📈 {stock_name}({stock_code}) 처리 중...")
                self.log(f"{'='*60}")

                # 1. 네이버 뉴스 수집
                self.log(f"1️⃣ 네이버 뉴스 수집...")
                news_list = await self.collect_naver_news(stock_code, stock_name)
                self.log(f"   수집: {len(news_list)}건")

                # 2. DART 공시 수집
                self.log(f"2️⃣ DART 공시 수집...")
                disclosures = await self.collect_dart_disclosures(stock_code, stock_name)
                self.log(f"   수집: {len(disclosures)}건")

                # 3. DB 저장
                self.log(f"3️⃣ 데이터베이스 저장...")
                saved_news = await self.save_news_to_db(stock_code, news_list + disclosures)
                self.log(f"   저장: {saved_news}건 (중복 제외)")

                total_news += len(news_list)
                total_disclosures += len(disclosures)

                # 4. PDF 재생성 (새 뉴스가 있는 경우에만)
                if saved_news > 0:
                    self.log(f"4️⃣ PDF 재생성 ({saved_news}건의 새 뉴스)")
                    success = await self.regenerate_pdf_for_stock(stock_code, stock_name)

                    if success:
                        pdf_success += 1
                    else:
                        pdf_fail += 1
                else:
                    self.log(f"4️⃣ PDF 재생성 건너뜀 (새 뉴스 없음)")

                # API 호출 제한 방지
                await asyncio.sleep(2)

            # 최종 요약
            self.log(f"\n{'='*80}")
            self.log(f"📊 수집 완료 요약:")
            self.log(f"   뉴스: {total_news}건")
            self.log(f"   공시: {total_disclosures}건")
            self.log(f"   PDF 재생성 성공: {pdf_success}개")
            self.log(f"   PDF 재생성 실패: {pdf_fail}개")
            self.log("=" * 80)

        except Exception as e:
            self.log(f"❌ 처리 오류: {e}")
            import traceback
            self.log(traceback.format_exc())

        finally:
            await db.disconnect()


async def main():
    """메인 함수"""
    collector = NewsCollectorAndPDFGenerator()
    await collector.process_all_holdings()


if __name__ == '__main__':
    asyncio.run(main())
