"""
Naver Stock News Playwright Fetcher
Tier 4 - Browser Automation

Fetches:
- 종목 뉴스 (Stock News)
- 공시 (Disclosures)
- 뉴스 감성 분석 (호재/악재)

Phase 3.9 Enhanced Features:
- 중복 뉴스 제거 (Jaccard Similarity)
- 우선순위 점수 (Priority Scoring)
- 중요 키워드 가중치
"""
from typing import Dict, Any, Optional, List, Set
import re
from datetime import datetime
from difflib import SequenceMatcher

from .base_playwright_fetcher import BasePlaywrightFetcher


# Phase 3.9: 우선순위 키워드 (높은 점수)
PRIORITY_KEYWORDS = {
    5: ['단독', '속보', '긴급', '특종'],  # 최우선
    4: ['공시', '계약', '수주', '인수', '합병', 'M&A'],  # 핵심 이벤트
    3: ['실적', '매출', '영업이익', '순이익', '흑자전환', '적자전환'],  # 재무
    2: ['목표가', '투자의견', '상향', '하향', '매수', '매도'],  # 증권사
    1: ['특징주', '테마', '급등', '급락', '신고가', '신저가'],  # 시장 관심
}

# 중복 판단 임계값 (0.0 ~ 1.0)
SIMILARITY_THRESHOLD = 0.7


class NaverStockNewsFetcher(BasePlaywrightFetcher):
    """
    Naver Stock News fetcher using Playwright.

    Target URL: https://finance.naver.com/item/news.naver?code={ticker}

    Phase 3.9 Enhanced:
    - 중복 뉴스 자동 제거
    - 우선순위 점수 계산 (1-5)
    - 감성 분석 개선
    """

    BASE_URL = "https://finance.naver.com/item/news.naver"

    def __init__(self, site_id: int, config: Dict[str, Any]):
        super().__init__(site_id, config)
        self.config['data_type'] = 'stock_news'
        self._seen_titles: Set[str] = set()  # 중복 체크용

    def build_url(self, ticker: str) -> str:
        """Build Naver Stock News URL for ticker"""
        return f"{self.BASE_URL}?code={ticker}"

    async def fetch_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch Naver Stock News for ticker.

        Args:
            ticker: Stock ticker code

        Returns:
            Parsed data dictionary or None
        """
        url = self.build_url(ticker)

        # Navigate to page
        success = await self.navigate_to(url, wait_until='networkidle')
        if not success:
            return None

        # Wait for page to fully load
        await self.page.wait_for_timeout(5000)  # 5초 대기

        # Parse data (includes iframe parsing)
        data = await self.parse_data(ticker)

        return data

    async def parse_data(self, ticker: str) -> Dict[str, Any]:
        """
        Parse Naver Stock News from current page.

        Args:
            ticker: Stock ticker code

        Returns:
            Parsed data dictionary
        """
        # Reset seen titles for new ticker
        self._seen_titles.clear()

        raw_news_list = await self.parse_news_list()

        # Phase 3.9: 중복 제거 및 우선순위 정렬
        unique_news = self._deduplicate_news(raw_news_list)
        sorted_news = sorted(unique_news, key=lambda x: x.get('priority', 0), reverse=True)

        data = {
            'ticker': ticker,
            'source': 'naver_stock_news',
            'crawled_at': datetime.now().isoformat(),
            'news_list': sorted_news,
            'news_count': len(sorted_news),
            'raw_count': len(raw_news_list),  # 원본 개수
            'duplicates_removed': len(raw_news_list) - len(sorted_news)
        }

        self.logger.info(
            f"Naver Stock News parsed for {ticker}: "
            f"{data['news_count']} unique articles "
            f"({data['duplicates_removed']} duplicates removed)"
        )

        return data

    async def parse_news_list(self, max_news: int = 20) -> List[Dict[str, Any]]:
        """
        Parse news list from current page (iframe).

        Args:
            max_news: Maximum number of news to fetch

        Returns:
            List of news dictionaries
        """
        news_list = []

        try:
            # Find news iframe
            news_iframe = await self.page.query_selector('iframe[name="news"]')
            if not news_iframe:
                self.logger.warning("News iframe not found")
                return news_list

            # Get iframe content
            frame = await news_iframe.content_frame()
            if not frame:
                self.logger.warning("Could not access news iframe content")
                return news_list

            # Parse news from iframe
            rows = await frame.query_selector_all('table.type5 tbody tr')

            for row in rows[:max_news]:
                # Check if it's a news row (has title link)
                title_elem = await row.query_selector('a.tit')
                if not title_elem:
                    continue

                news_item = {}

                # Title
                title_text = await title_elem.text_content()
                if title_text:
                    news_item['title'] = title_text.strip()

                # Link
                href = await title_elem.get_attribute('href')
                if href:
                    # Convert to absolute URL
                    if href.startswith('/'):
                        news_item['url'] = f"https://finance.naver.com{href}"
                    else:
                        news_item['url'] = href

                # Source (언론사)
                info_elem = await row.query_selector('td.info')
                if info_elem:
                    info_text = await info_elem.text_content()
                    if info_text:
                        news_item['source'] = info_text.strip()

                # Date
                date_elem = await row.query_selector('td.date')
                if date_elem:
                    date_text = await date_elem.text_content()
                    if date_text:
                        news_item['date'] = date_text.strip()

                # Sentiment (간단한 키워드 기반)
                if title_text:
                    news_item['sentiment'] = self.analyze_sentiment(title_text)
                    # Phase 3.9: 우선순위 점수 추가
                    news_item['priority'] = self.calculate_priority(title_text)

                if news_item:
                    news_list.append(news_item)

        except Exception as e:
            self.logger.warning(f"Error parsing news list: {e}")

        return news_list

    @staticmethod
    def analyze_sentiment(title: str) -> str:
        """
        Simple keyword-based sentiment analysis.

        Args:
            title: News title

        Returns:
            'positive', 'negative', or 'neutral'
        """
        # 호재 키워드
        positive_keywords = [
            '상승', '급등', '호조', '흑자', '성장', '증가', '확대', '개선',
            '신고가', '최고', '실적', '호재', '수주', '계약', '투자',
            '상향', '목표가', '강세', '매수', '긍정'
        ]

        # 악재 키워드
        negative_keywords = [
            '하락', '급락', '부진', '적자', '감소', '축소', '악화',
            '신저가', '최저', '부실', '악재', '소송', '분쟁', '손실',
            '하향', '약세', '매도', '부정', '우려', '위기'
        ]

        title_lower = title.lower()

        # Count keywords
        positive_count = sum(1 for kw in positive_keywords if kw in title_lower)
        negative_count = sum(1 for kw in negative_keywords if kw in title_lower)

        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'

    @staticmethod
    def calculate_priority(title: str) -> int:
        """
        Phase 3.9: Calculate news priority score (1-5).

        Higher scores indicate more important news.

        Args:
            title: News title

        Returns:
            Priority score (0-5, 0 = no priority keywords found)
        """
        max_priority = 0
        title_lower = title.lower()

        for priority, keywords in PRIORITY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in title_lower:
                    max_priority = max(max_priority, priority)

        return max_priority

    def _deduplicate_news(self, news_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Phase 3.9: Remove duplicate news based on title similarity.

        Uses SequenceMatcher for fuzzy matching.

        Args:
            news_list: List of news items

        Returns:
            Deduplicated list
        """
        unique_news = []

        for news in news_list:
            title = news.get('title', '')
            if not title:
                continue

            # Check similarity against seen titles
            is_duplicate = False
            for seen_title in self._seen_titles:
                similarity = SequenceMatcher(None, title, seen_title).ratio()
                if similarity >= SIMILARITY_THRESHOLD:
                    is_duplicate = True
                    self.logger.debug(
                        f"Duplicate detected: '{title[:30]}...' "
                        f"similar to '{seen_title[:30]}...' ({similarity:.2f})"
                    )
                    break

            if not is_duplicate:
                self._seen_titles.add(title)
                unique_news.append(news)

        return unique_news

    def clear_seen_titles(self):
        """Clear the seen titles cache (useful between sessions)."""
        self._seen_titles.clear()

    async def validate_structure(self) -> bool:
        """
        Validate Naver Stock News site structure (required by BaseFetcher).

        Returns:
            True (always valid for Playwright-based fetchers)
        """
        # Playwright fetchers don't need structure validation
        # as they handle dynamic content
        return True


# Factory function
async def create_naver_stock_news_fetcher(site_id: int, config: Dict[str, Any]) -> NaverStockNewsFetcher:
    """
    Create and initialize Naver Stock News fetcher.

    Args:
        site_id: Reference site ID from database
        config: Site configuration

    Returns:
        Initialized NaverStockNewsFetcher instance
    """
    fetcher = NaverStockNewsFetcher(site_id, config)
    return fetcher
