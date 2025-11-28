"""
News Sentiment Analyzer - Phase 4
Gemini API를 활용한 뉴스 감성 분석

핵심 기능:
- 실시간 뉴스 수집 및 분석
- Gemini AI를 통한 감성 점수화
- 키워드 기반 빠른 필터링
- 중복 뉴스 제거 (유사도 기반)
"""
import asyncio
import re
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

import aiohttp

# Gemini client
from src.gemini.client import GeminiClient


class NewsSentiment(Enum):
    """뉴스 감성 분류"""
    VERY_POSITIVE = "very_positive"   # +2.0
    POSITIVE = "positive"              # +1.0
    NEUTRAL = "neutral"                # 0.0
    NEGATIVE = "negative"              # -1.0
    VERY_NEGATIVE = "very_negative"   # -2.0


@dataclass
class NewsItem:
    """개별 뉴스 항목"""
    title: str
    content: str
    source: str
    published_at: datetime
    url: str = ""
    sentiment: Optional[NewsSentiment] = None
    sentiment_score: float = 0.0
    keywords: List[str] = field(default_factory=list)
    relevance: float = 1.0


@dataclass
class NewsSentimentResult:
    """뉴스 감성 분석 결과"""
    ticker: str
    score: float  # -2.0 ~ +2.0
    sentiment: NewsSentiment
    news_count: int
    positive_count: int
    negative_count: int
    key_headlines: List[Dict[str, Any]]
    ai_summary: Optional[str]
    analyzed_at: str
    details: Dict[str, Any] = field(default_factory=dict)


class NewsSentimentAnalyzer:
    """
    뉴스 감성 분석기

    Phase 4 Spec:
    - 실시간 뉴스 감성 분석
    - Gemini AI 연동
    - 키워드 기반 빠른 필터링

    Phase 7.5 Optimization:
    - Smart Filtering: 중요 뉴스만 AI 분석
    - Gemini API 호출 최소화
    """

    # 호재 키워드 (점수 순)
    POSITIVE_KEYWORDS: Dict[float, List[str]] = {
        2.0: ['대규모수주', '계약체결', '신약승인', 'FDA승인', '흑자전환'],
        1.5: ['매출급증', '실적호조', '수주잔고', '신규시장진출'],
        1.0: ['배당확대', '자사주매입', '신규투자', '사업확장'],
        0.5: ['호실적', '성장', '증가', '개선', '신제품'],
    }

    # 악재 키워드 (점수 순)
    NEGATIVE_KEYWORDS: Dict[float, List[str]] = {
        -2.0: ['횡령', '배임', '분식회계', '상장폐지', '거래정지'],
        -1.5: ['대규모적자', '영업중단', '파산', '회생절차'],
        -1.0: ['실적악화', '적자전환', '하향조정', '공매도급증'],
        -0.5: ['감소', '하락', '부진', '우려', '리스크'],
    }

    # [Phase 7.5] Smart Filtering - AI 분석 대상 키워드
    HIGH_PRIORITY_KEYWORDS: List[str] = [
        '특징주', '공시', '단독', '속보', '긴급',
        '급등', '급락', '상한가', '하한가',
        '계약', '수주', '인수', '합병', 'M&A',
        '실적발표', '어닝서프라이즈', '어닝쇼크',
    ]

    # [Phase 7.5] Smart Filtering - 주요 언론사 (AI 분석 대상)
    MAJOR_SOURCES: List[str] = [
        '연합뉴스', '연합인포맥스', '이데일리', '머니투데이',
        '한국경제', '매일경제', '서울경제', '파이낸셜뉴스',
        '블룸버그', 'Reuters', '조선비즈', '한경비즈니스',
    ]

    # Naver 뉴스 API
    NAVER_NEWS_API = "https://m.stock.naver.com/api/stock/{ticker}/news?page=1&pageSize=20"

    # 캐시 TTL (15분)
    CACHE_TTL = timedelta(minutes=15)

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._cache: Dict[str, Tuple[NewsSentimentResult, datetime]] = {}
        self._gemini_client: Optional[GeminiClient] = None

    def _get_gemini_client(self) -> GeminiClient:
        """Gemini 클라이언트 지연 초기화"""
        if self._gemini_client is None:
            self._gemini_client = GeminiClient()
        return self._gemini_client

    def _is_high_priority_news(self, item: NewsItem) -> bool:
        """
        [Phase 7.5] Smart Filtering - AI 분석 대상 뉴스인지 판단

        AI 분석 대상:
        1. 제목에 중요 키워드 포함 (특징주, 공시, 단독, 속보 등)
        2. 주요 언론사 기사 (연합, 이데일리 등)

        Returns:
            True: AI 분석 대상
            False: 키워드 점수만 사용
        """
        # 1. 중요 키워드 체크
        for keyword in self.HIGH_PRIORITY_KEYWORDS:
            if keyword in item.title:
                return True

        # 2. 주요 언론사 체크
        for source in self.MAJOR_SOURCES:
            if source in item.source:
                return True

        return False

    def _filter_for_ai_analysis(self, news_items: List[NewsItem]) -> List[NewsItem]:
        """
        [Phase 7.5] AI 분석 대상 뉴스만 필터링

        Returns:
            AI 분석 대상 뉴스 리스트 (최대 5개로 제한)
        """
        high_priority = [
            item for item in news_items
            if self._is_high_priority_news(item)
        ]

        self.logger.debug(
            f"Smart Filter: {len(high_priority)}/{len(news_items)} news selected for AI"
        )

        # 최대 5개로 제한 (API 비용 절감)
        return high_priority[:5]

    async def analyze(
        self,
        ticker: str,
        days: int = 3,
        use_ai: bool = True
    ) -> NewsSentimentResult:
        """
        종목의 뉴스 감성 분석

        Args:
            ticker: 종목코드
            days: 분석 기간 (일)
            use_ai: Gemini AI 사용 여부

        Returns:
            NewsSentimentResult: 감성 분석 결과
        """
        # 캐시 확인
        cache_key = f"{ticker}_{days}"
        if cache_key in self._cache:
            cached, cached_at = self._cache[cache_key]
            if datetime.now() - cached_at < self.CACHE_TTL:
                self.logger.debug(f"Cache hit for {ticker}")
                return cached

        self.logger.info(f"Analyzing news sentiment for {ticker}")

        # 1. 뉴스 수집
        news_items = await self._fetch_news(ticker, days)

        if not news_items:
            return self._create_empty_result(ticker)

        # 2. 키워드 기반 빠른 분석 (모든 뉴스)
        keyword_scores = self._analyze_keywords(news_items)

        # 3. [Phase 7.5] Smart Filtering + AI 분석 (선택적)
        ai_summary = None
        ai_score = 0.0
        ai_analyzed_count = 0

        if use_ai:
            # Smart Filtering: 중요 뉴스만 AI 분석
            high_priority_news = self._filter_for_ai_analysis(news_items)
            ai_analyzed_count = len(high_priority_news)

            if high_priority_news:
                self.logger.info(
                    f"[Smart Filter] {ai_analyzed_count}/{len(news_items)} news -> AI analysis"
                )
                ai_result = await self._analyze_with_ai(ticker, high_priority_news)
                ai_summary = ai_result.get('summary')
                ai_score = ai_result.get('score', 0.0)
            else:
                self.logger.info(
                    f"[Smart Filter] No high-priority news, skipping AI (saved API call)"
                )

        # 4. 최종 점수 계산
        # 키워드 70% + AI 30%
        if use_ai and ai_score != 0.0:
            final_score = keyword_scores['average'] * 0.7 + ai_score * 0.3
        else:
            final_score = keyword_scores['average']

        # 점수 범위 제한
        final_score = max(-2.0, min(2.0, final_score))

        # 감성 분류
        sentiment = self._score_to_sentiment(final_score)

        # 주요 헤드라인 추출
        key_headlines = self._extract_key_headlines(news_items)

        result = NewsSentimentResult(
            ticker=ticker,
            score=round(final_score, 2),
            sentiment=sentiment,
            news_count=len(news_items),
            positive_count=keyword_scores['positive_count'],
            negative_count=keyword_scores['negative_count'],
            key_headlines=key_headlines,
            ai_summary=ai_summary,
            analyzed_at=datetime.now().isoformat(),
            details={
                'keyword_score': keyword_scores['average'],
                'ai_score': ai_score,
                'days_analyzed': days,
                'ai_analyzed_count': ai_analyzed_count,  # [Phase 7.5] Smart Filtering 결과
                'total_news_count': len(news_items),
            }
        )

        # 캐시 저장
        self._cache[cache_key] = (result, datetime.now())

        return result

    async def _fetch_news(self, ticker: str, days: int) -> List[NewsItem]:
        """뉴스 수집"""
        news_items = []

        try:
            url = self.NAVER_NEWS_API.format(ticker=ticker)

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        self.logger.warning(f"Naver news API returned {response.status}")
                        return []

                    data = await response.json()

                    for item in data.get('news', []):
                        try:
                            published = datetime.fromisoformat(
                                item.get('datetime', '').replace('Z', '+00:00')
                            )
                        except (ValueError, TypeError):
                            published = datetime.now()

                        # 기간 필터
                        if datetime.now() - published > timedelta(days=days):
                            continue

                        news_items.append(NewsItem(
                            title=item.get('title', ''),
                            content=item.get('body', '')[:500],  # 500자 제한
                            source=item.get('officeNameDisplay', ''),
                            published_at=published,
                            url=item.get('originalLink', ''),
                        ))

        except Exception as e:
            self.logger.error(f"Failed to fetch news: {e}")

        # 중복 제거
        news_items = self._deduplicate_news(news_items)

        return news_items[:20]  # 최대 20개

    def _deduplicate_news(self, news_items: List[NewsItem]) -> List[NewsItem]:
        """중복 뉴스 제거 (제목 유사도 기반)"""
        seen_hashes = set()
        unique_items = []

        for item in news_items:
            # 제목에서 특수문자 제거 후 해시
            clean_title = re.sub(r'[^\w\s]', '', item.title)
            title_hash = hashlib.md5(clean_title.encode()).hexdigest()[:8]

            if title_hash not in seen_hashes:
                seen_hashes.add(title_hash)
                unique_items.append(item)

        return unique_items

    def _analyze_keywords(self, news_items: List[NewsItem]) -> Dict[str, Any]:
        """키워드 기반 감성 분석"""
        total_score = 0.0
        positive_count = 0
        negative_count = 0

        for item in news_items:
            text = f"{item.title} {item.content}"
            item_score = 0.0
            found_keywords = []

            # 호재 키워드 검색
            for score, keywords in self.POSITIVE_KEYWORDS.items():
                for kw in keywords:
                    if kw in text:
                        item_score += score
                        found_keywords.append(kw)
                        positive_count += 1

            # 악재 키워드 검색
            for score, keywords in self.NEGATIVE_KEYWORDS.items():
                for kw in keywords:
                    if kw in text:
                        item_score += score  # 음수
                        found_keywords.append(kw)
                        negative_count += 1

            item.sentiment_score = item_score
            item.keywords = found_keywords
            total_score += item_score

        avg_score = total_score / len(news_items) if news_items else 0.0

        return {
            'average': round(avg_score, 2),
            'total': round(total_score, 2),
            'positive_count': positive_count,
            'negative_count': negative_count,
        }

    async def _analyze_with_ai(
        self,
        ticker: str,
        news_items: List[NewsItem]
    ) -> Dict[str, Any]:
        """Gemini AI를 통한 심층 분석"""
        try:
            gemini = self._get_gemini_client()

            if not gemini.model:
                return {'summary': None, 'score': 0.0}

            # 뉴스 요약 구성
            news_text = "\n".join([
                f"- [{item.source}] {item.title}"
                for item in news_items[:10]
            ])

            prompt = f"""
다음은 종목 {ticker}에 관한 최근 뉴스 헤드라인입니다:

{news_text}

위 뉴스들을 분석하여 다음 형식으로 답변해주세요:

1. 종합 감성 점수: (숫자만, -2.0 ~ +2.0 범위)
   - +2.0: 매우 긍정적 (대규모 계약, 흑자전환 등)
   - +1.0: 긍정적 (실적 개선, 신규 투자 등)
   - 0.0: 중립
   - -1.0: 부정적 (실적 부진, 하향 조정 등)
   - -2.0: 매우 부정적 (횡령, 상장폐지 우려 등)

2. 한줄 요약: (50자 이내)

답변 형식:
점수: [숫자]
요약: [내용]
"""

            response = await gemini.generate_content(prompt)

            if not response:
                return {'summary': None, 'score': 0.0}

            # 응답 파싱
            score = 0.0
            summary = None

            for line in response.split('\n'):
                line = line.strip()
                if line.startswith('점수:'):
                    try:
                        score_text = line.replace('점수:', '').strip()
                        # 숫자 추출
                        match = re.search(r'[-+]?\d*\.?\d+', score_text)
                        if match:
                            score = float(match.group())
                            score = max(-2.0, min(2.0, score))
                    except ValueError:
                        pass
                elif line.startswith('요약:'):
                    summary = line.replace('요약:', '').strip()

            return {'summary': summary, 'score': score}

        except Exception as e:
            self.logger.error(f"AI analysis failed: {e}")
            return {'summary': None, 'score': 0.0}

    def _score_to_sentiment(self, score: float) -> NewsSentiment:
        """점수를 감성으로 변환"""
        if score >= 1.5:
            return NewsSentiment.VERY_POSITIVE
        elif score >= 0.5:
            return NewsSentiment.POSITIVE
        elif score <= -1.5:
            return NewsSentiment.VERY_NEGATIVE
        elif score <= -0.5:
            return NewsSentiment.NEGATIVE
        else:
            return NewsSentiment.NEUTRAL

    def _extract_key_headlines(self, news_items: List[NewsItem]) -> List[Dict[str, Any]]:
        """주요 헤드라인 추출 (점수 기준 정렬)"""
        # 점수 절대값 기준 정렬
        sorted_items = sorted(
            news_items,
            key=lambda x: abs(x.sentiment_score),
            reverse=True
        )

        return [
            {
                'title': item.title,
                'source': item.source,
                'score': item.sentiment_score,
                'keywords': item.keywords,
                'published_at': item.published_at.isoformat(),
            }
            for item in sorted_items[:5]
        ]

    def _create_empty_result(self, ticker: str) -> NewsSentimentResult:
        """빈 결과 생성"""
        return NewsSentimentResult(
            ticker=ticker,
            score=0.0,
            sentiment=NewsSentiment.NEUTRAL,
            news_count=0,
            positive_count=0,
            negative_count=0,
            key_headlines=[],
            ai_summary=None,
            analyzed_at=datetime.now().isoformat(),
        )

    def clear_cache(self):
        """캐시 초기화"""
        self._cache.clear()
        self.logger.info("News sentiment cache cleared")


# Singleton instance
_analyzer_instance: Optional[NewsSentimentAnalyzer] = None


def get_news_sentiment_analyzer() -> NewsSentimentAnalyzer:
    """Get singleton NewsSentimentAnalyzer instance"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = NewsSentimentAnalyzer()
    return _analyzer_instance


# Convenience function
async def analyze_news_sentiment(
    ticker: str,
    days: int = 3,
    use_ai: bool = True
) -> NewsSentimentResult:
    """뉴스 감성 분석 편의 함수"""
    analyzer = get_news_sentiment_analyzer()
    return await analyzer.analyze(ticker, days, use_ai)
