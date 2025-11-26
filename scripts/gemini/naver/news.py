import aiohttp
import logging
from typing import List, Dict
import os
from dotenv import load_dotenv
import google.generativeai as genai

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

class NaverNewsFetcher:
    async def fetch_news(self, stock_code: str) -> List[Dict[str, str]]:
        """Fetch real-time news headlines using Naver Mobile API."""
        # Mobile News API
        url = f"https://m.stock.naver.com/api/news/stock/{stock_code}"
        params = {'pageSize': 10, 'page': 1}
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
            'Referer': 'https://m.stock.naver.com/'
        }
        
        news_items = []
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # The API returns a list of sections, each containing 'items'
                        # Structure: [{'items': [...]}, {'items': [...]}]
                        
                        raw_sections = data if isinstance(data, list) else [data]
                        
                        for section in raw_sections:
                            section_items = section.get('items', [])
                            for item in section_items:
                                # Structure: {datetime: '202511251118', title: 'Title', ...}
                                title = item.get('title', '')
                                date_str = item.get('datetime', '')
                                
                                # Format date: 202511251118 -> 2025-11-25 11:18
                                if len(date_str) == 12:
                                    date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} {date_str[8:10]}:{date_str[10:]}"
                                else:
                                    date = date_str
                                    
                                oid = item.get('officeId', '')
                                aid = item.get('articleId', '')
                                
                                # Clean title (remove HTML tags like <b>)
                                title = title.replace('<b>', '').replace('</b>', '').replace('&quot;', '"')
                                
                                office_name = item.get('officeName', '알 수 없음')

                                news_items.append({
                                    'title': title,
                                    'collected_at': date,
                                    'content': title,
                                    'url': f"https://m.stock.naver.com/domestic/stock/{stock_code}/news/view/{oid}/{aid}",
                                    'source': office_name,
                                    'sentiment': None,  # Will be analyzed later
                                    'summary': None     # Will be generated later
                                })
        except Exception as e:
            logger.error(f"Naver news API fetch error: {e}")

        # Analyze sentiment and generate summaries using Gemini
        if GEMINI_API_KEY and news_items:
            news_items = await self._analyze_news_with_gemini(news_items[:10])

        return news_items[:10]

    async def _analyze_news_with_gemini(self, news_items: List[Dict]) -> List[Dict]:
        """Use Gemini AI to analyze sentiment and generate summaries"""
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')

            for item in news_items:
                title = item['title']

                # Create prompt for Gemini
                prompt = f"""
다음 주식 뉴스 제목을 분석해주세요:

제목: {title}

다음 형식으로 답변해주세요:
1. 감성분석: [호재/악재/중립] 중 하나만 선택
2. 요약 (3줄 이내로 핵심만 간단히):
- 첫째줄
- 둘째줄
- 셋째줄

응답 형식:
감성분석: [호재/악재/중립]
요약:
- 요약 1
- 요약 2
- 요약 3
"""

                try:
                    response = model.generate_content(prompt)
                    result_text = response.text.strip()

                    # Parse response
                    sentiment = '중립'
                    summary_lines = []

                    for line in result_text.split('\n'):
                        line = line.strip()
                        if line.startswith('감성분석:'):
                            sentiment_text = line.replace('감성분석:', '').strip()
                            if '호재' in sentiment_text:
                                sentiment = '호재'
                            elif '악재' in sentiment_text:
                                sentiment = '악재'
                            else:
                                sentiment = '중립'
                        elif line.startswith('-') and len(summary_lines) < 3:
                            summary_lines.append(line[1:].strip())

                    item['sentiment'] = sentiment
                    item['summary'] = '\n'.join(summary_lines) if summary_lines else title[:100]

                except Exception as e:
                    logger.error(f"Gemini analysis error for news item: {e}")
                    item['sentiment'] = '중립'
                    item['summary'] = title[:100]

        except Exception as e:
            logger.error(f"Gemini API configuration error: {e}")
            # Fallback: use simple keyword matching
            for item in news_items:
                item['sentiment'] = self._simple_sentiment_analysis(item['title'])
                item['summary'] = item['title'][:100]

        return news_items

    def _simple_sentiment_analysis(self, title: str) -> str:
        """Simple keyword-based sentiment analysis as fallback"""
        positive_keywords = ['상승', '증가', '호실적', '신고가', '매수', '상향', '개선', '성장', '확대', '수주']
        negative_keywords = ['하락', '감소', '악화', '하향', '적자', '손실', '매도', '부진', '감소', '우려']

        title_lower = title.lower()

        pos_count = sum(1 for kw in positive_keywords if kw in title)
        neg_count = sum(1 for kw in negative_keywords if kw in title)

        if pos_count > neg_count:
            return '호재'
        elif neg_count > pos_count:
            return '악재'
            return '중립'

    async def fetch_target_price_news(self, stock_code: str, stock_name: str) -> List[Dict[str, Any]]:
        """
        Fetch news specifically searching for target price updates.
        Uses stock news API and filters by keyword since search API doesn't exist.
        Returns list of dicts with 'firm', 'target_price', 'date', 'title'.
        """
        # Use stock news API instead of search (search endpoint doesn't exist)
        url = f"https://m.stock.naver.com/api/news/stock/{stock_code}"

        results = []
        try:
            async with aiohttp.ClientSession(headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://m.stock.naver.com/'}) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Handle list or dict response
                        raw_sections = data if isinstance(data, list) else [data]
                        
                        for section in raw_sections:
                            items = section.get('items', [])
                            for item in items:
                                title = item.get('title', '')
                                # Parse Broker and Price from title
                                parsed = self._parse_target_price_news(title, stock_name)
                                if parsed:
                                    parsed['date'] = item.get('datetime', '')[:8] # YYYYMMDD
                                    parsed['url'] = f"https://m.stock.naver.com/news/view/{item.get('officeId')}/{item.get('articleId')}"
                                    results.append(parsed)
        except Exception as e:
            logger.error(f"Error fetching target price news: {e}")
            
        return results

    def _parse_target_price_news(self, title: str, stock_name: str) -> Dict[str, Any]:
        import re
        # Clean title (remove HTML tags)
        title = re.sub(r'<[^>]+>', '', title)
        
        # 1. Verify stock name is present
        if stock_name not in title:
            return None

        # 2. Check for other major stocks that might confuse the parser
        # If another stock is mentioned, we need to be careful.
        # For now, if "SK하이닉스" or "삼성전자" is in the title, and we are looking for "한국전력",
        # we might want to skip or check proximity.
        other_stocks = ['삼성전자', 'SK하이닉스', 'LG에너지솔루션', '현대차', '기아', 'POSCO홀딩스', 'NAVER', '카카오']
        for other in other_stocks:
            if other in title and other != stock_name:
                # If another major stock is present, it's risky. 
                # E.g. "SK하이닉스 목표가 상향... 한국전력은 유지" -> parser might grab SK's price.
                # Simple heuristic: Skip if another major stock is found.
                return None
        
        # 3. Extract Price (e.g., 6.2만, 62,000, 6만원)
        # Improved regex to avoid capturing dates or other numbers
        price_match = re.search(r'(\d+(?:[.,]\d+)?)(만|천)?원?', title)
        if not price_match:
            return None
            
        num_str = price_match.group(1).replace(',', '')
        unit = price_match.group(2)
        
        try:
            price = float(num_str)
            if unit == '만':
                price *= 10000
            elif unit == '천':
                price *= 1000
            elif price < 1000: # Assuming unit is '만' if small number found in context of target price
                 price *= 10000
                 
            target_price = int(price)
            
            # Sanity check: Target price shouldn't be too crazy (e.g. < 1000 won for KEPCO is unlikely, > 1,000,000 is unlikely)
            # But this depends on the stock.
            # Let's just rely on the regex for now.
        except:
            return None

        # 4. Extract Broker (Heuristic list of major brokers)
        brokers = ['KB', '신한', '삼성', '미래에셋', '하나', '한국투자', 'NH', '메리츠', '키움', '대신', '유안타', '한화', 'IBK', '교보', '하이', '현대차', '유진', 'DB', '이베스트', 'SK', '신영', '다올', 'BNK', '상상인']
        found_broker = 'Unknown'
        for broker in brokers:
            if broker in title:
                found_broker = broker + '증권' # Normalize
                break
        
        if found_broker == 'Unknown':
            # Try to find words ending in '증권' or '투자'
            broker_match = re.search(r'(\w+(?:증권|투자))', title)
            if broker_match:
                found_broker = broker_match.group(1)
            else:
                return None # Skip if no broker found (might be general news)

        return {
            'firm': found_broker,
            'target_price': target_price,
            'title': title
        }
