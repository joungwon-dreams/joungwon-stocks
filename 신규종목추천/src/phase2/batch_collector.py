"""
Phase 2A: 배치 데이터 수집
50개 종목의 뉴스/리포트/컨센서스를 병렬 수집

목표: ~5분 내 실행
방법: 소스별 병렬, 소스 내 Rate Limit 준수
"""
import asyncio
import aiohttp
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import re
from bs4 import BeautifulSoup

import sys
sys.path.insert(0, '.')
from 신규종목추천.config.settings import settings
from 신규종목추천.src.utils.database import db

logger = logging.getLogger(__name__)


@dataclass
class CollectedData:
    """수집 데이터 컨테이너"""
    stock_code: str
    news: List[Dict] = None
    reports: List[Dict] = None
    consensus: Dict = None
    policy_keywords: List[str] = None
    collected_at: datetime = None

    def __post_init__(self):
        self.news = self.news or []
        self.reports = self.reports or []
        self.consensus = self.consensus or {}
        self.policy_keywords = self.policy_keywords or []
        self.collected_at = self.collected_at or datetime.now()


class RateLimiter:
    """단순 Rate Limiter"""

    def __init__(self, calls_per_minute: int):
        self.calls_per_minute = calls_per_minute
        self.interval = 60.0 / calls_per_minute
        self.last_call = 0

    async def acquire(self):
        """Rate limit 대기"""
        now = asyncio.get_event_loop().time()
        wait_time = self.last_call + self.interval - now
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        self.last_call = asyncio.get_event_loop().time()


class BatchCollector:
    """
    배치 데이터 수집기

    전략:
    1. 캐시 먼저 확인 (6시간 TTL)
    2. 소스별 독립 큐 운영 (병렬)
    3. 소스 내 Rate Limit 준수 (순차)
    """

    def __init__(self, config=None):
        self.config = config or settings.phase2a

        # Rate Limiters
        self.rate_limiters = {
            name: RateLimiter(rate)
            for name, rate in self.config.rate_limits.items()
        }

        # HTTP 세션
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        )
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    async def collect_all(
        self,
        candidates: List[Dict[str, Any]]
    ) -> Dict[str, CollectedData]:
        """
        50개 종목의 뉴스/리포트/컨센서스 수집

        Args:
            candidates: Phase 1B 결과

        Returns:
            종목코드 -> CollectedData 딕셔너리
        """
        if not candidates:
            return {}

        start_time = datetime.now()
        codes = [c['stock_code'] for c in candidates]

        logger.info(f"Phase 2A 시작: {len(codes)}개 종목 데이터 수집")

        # 1. 캐시 확인
        cached = await self._check_cache(codes)
        cached_codes = set(cached.keys())
        uncached_codes = [c for c in codes if c not in cached_codes]

        logger.info(f"캐시 히트: {len(cached_codes)}개, 신규 수집: {len(uncached_codes)}개")

        results = dict(cached)

        if uncached_codes:
            # 2. 소스별 병렬 수집
            collected = await self._collect_from_sources(uncached_codes)
            results.update(collected)

            # 3. 캐시 저장
            await self._save_cache(collected)

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Phase 2A 완료: {len(results)}개 종목 ({elapsed:.1f}초)")

        return results

    async def _check_cache(self, codes: List[str]) -> Dict[str, CollectedData]:
        """캐시된 데이터 확인"""
        query = """
            SELECT
                stock_code,
                data_type,
                title,
                content,
                sentiment,
                target_price,
                rating,
                firm_name,
                data_date,
                raw_data
            FROM smart_collected_data
            WHERE stock_code = ANY($1)
              AND expires_at > NOW()
            ORDER BY stock_code, collected_at DESC
        """

        rows = await db.fetch(query, codes)

        # 종목별로 그룹화
        result = {}
        for row in rows:
            code = row['stock_code']
            if code not in result:
                result[code] = CollectedData(stock_code=code)

            data = result[code]
            data_type = row['data_type']

            if data_type == 'news':
                data.news.append({
                    'title': row['title'],
                    'sentiment': row.get('sentiment', 0),
                    'date': str(row.get('data_date', '')),
                })
            elif data_type == 'report':
                data.reports.append({
                    'firm': row.get('firm_name', ''),
                    'target_price': row.get('target_price'),
                    'rating': row.get('rating', ''),
                    'date': str(row.get('data_date', '')),
                })
            elif data_type == 'consensus':
                raw = row.get('raw_data', {})
                if raw:
                    data.consensus = raw

        return result

    async def _collect_from_sources(
        self,
        codes: List[str]
    ) -> Dict[str, CollectedData]:
        """소스별 병렬 수집"""
        # 소스별 태스크 생성
        tasks = [
            self._collect_naver_news(codes),
            self._collect_daum_news(codes),
            self._collect_consensus(codes),
        ]

        # 병렬 실행
        source_results = await asyncio.gather(*tasks, return_exceptions=True)

        # 결과 병합
        result = {code: CollectedData(stock_code=code) for code in codes}

        for source_data in source_results:
            if isinstance(source_data, Exception):
                logger.error(f"소스 수집 실패: {source_data}")
                continue

            for code, data in source_data.items():
                if code in result:
                    # news 병합
                    if hasattr(data, 'news') and data.news:
                        result[code].news.extend(data.news)
                    elif isinstance(data, dict) and 'news' in data:
                        result[code].news.extend(data['news'])

                    # reports 병합
                    if hasattr(data, 'reports') and data.reports:
                        result[code].reports.extend(data.reports)
                    elif isinstance(data, dict) and 'reports' in data:
                        result[code].reports.extend(data['reports'])

                    # consensus 병합
                    if hasattr(data, 'consensus') and data.consensus:
                        result[code].consensus.update(data.consensus)
                    elif isinstance(data, dict) and 'consensus' in data:
                        result[code].consensus.update(data['consensus'])

        # 정책 키워드 추출
        for code, data in result.items():
            data.policy_keywords = self._extract_policy_keywords(data.news)

        return result

    async def _collect_naver_news(self, codes: List[str]) -> Dict[str, Dict]:
        """네이버 뉴스 수집"""
        result = {}
        limiter = self.rate_limiters.get('naver_api', RateLimiter(30))

        for code in codes:
            try:
                await limiter.acquire()
                news = await self._fetch_naver_news(code)
                result[code] = {'news': news}
            except Exception as e:
                logger.debug(f"네이버 뉴스 수집 실패 {code}: {e}")
                result[code] = {'news': []}

        return result

    async def _fetch_naver_news(self, code: str) -> List[Dict]:
        """네이버 금융 뉴스 HTML 스크래핑"""
        url = f"https://finance.naver.com/item/news_news.naver?code={code}&page=1&sm=title_entity_id.basic&clusterId="

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Referer': 'https://finance.naver.com/'
            }
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    return []

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                result = []
                # 뉴스 테이블 파싱
                news_table = soup.select('table.type5 tbody tr')

                for row in news_table[:self.config.news_limit]:
                    title_td = row.select_one('td.title a')
                    date_td = row.select_one('td.date')

                    if title_td:
                        title = title_td.get_text(strip=True)
                        date = date_td.get_text(strip=True) if date_td else ''

                        if title and len(title) > 5:
                            result.append({
                                'title': title,
                                'date': date,
                                'sentiment': self._analyze_sentiment(title),
                            })

                return result

        except Exception as e:
            logger.debug(f"네이버 뉴스 스크래핑 오류 {code}: {e}")
            return []

    async def _collect_daum_news(self, codes: List[str]) -> Dict[str, Dict]:
        """다음 뉴스 수집"""
        result = {}
        limiter = self.rate_limiters.get('daum_api', RateLimiter(30))

        for code in codes:
            try:
                await limiter.acquire()
                news = await self._fetch_daum_news(code)
                result[code] = {'news': news}
            except Exception as e:
                logger.debug(f"다음 뉴스 수집 실패 {code}: {e}")
                result[code] = {'news': []}

        return result

    async def _fetch_daum_news(self, code: str) -> List[Dict]:
        """다음 개별 종목 뉴스 API 호출"""
        url = f"https://finance.daum.net/api/news/stock/{code}?page=1&perPage={self.config.news_limit}"

        try:
            headers = {
                'Referer': 'https://finance.daum.net/',
                'User-Agent': 'Mozilla/5.0'
            }
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    return []

                data = await response.json()
                news_list = data.get('data', [])

                result = []
                for item in news_list[:self.config.news_limit]:
                    result.append({
                        'title': item.get('title', ''),
                        'date': item.get('createdAt', ''),
                        'sentiment': self._analyze_sentiment(item.get('title', '')),
                    })

                return result

        except Exception as e:
            logger.debug(f"다음 뉴스 API 오류 {code}: {e}")
            return []

    async def _collect_consensus(self, codes: List[str]) -> Dict[str, Dict]:
        """컨센서스 데이터 수집 (DB 기반)"""
        # stock_opinions 테이블에서 조회
        query = """
            SELECT
                stock_code,
                AVG(target_price) as avg_target_price,
                COUNT(CASE WHEN opinion ILIKE '%매수%' OR opinion ILIKE '%buy%' THEN 1 END) as buy_count,
                COUNT(CASE WHEN opinion ILIKE '%중립%' OR opinion ILIKE '%hold%' THEN 1 END) as hold_count,
                COUNT(CASE WHEN opinion ILIKE '%매도%' OR opinion ILIKE '%sell%' THEN 1 END) as sell_count,
                COUNT(*) as total_count
            FROM stock_opinions
            WHERE stock_code = ANY($1)
              AND created_at >= NOW() - INTERVAL '30 days'
            GROUP BY stock_code
        """

        try:
            rows = await db.fetch(query, codes)
            result = {}

            for row in rows:
                code = row['stock_code']
                result[code] = {
                    'consensus': {
                        'avg_target_price': int(row['avg_target_price'] or 0),
                        'buy': row['buy_count'] or 0,
                        'hold': row['hold_count'] or 0,
                        'sell': row['sell_count'] or 0,
                        'total': row['total_count'] or 0,
                    }
                }

            # 없는 종목은 빈 컨센서스
            for code in codes:
                if code not in result:
                    result[code] = {'consensus': {}}

            return result

        except Exception as e:
            logger.warning(f"컨센서스 조회 실패: {e}")
            return {code: {'consensus': {}} for code in codes}

    def _analyze_sentiment(self, text: str) -> float:
        """
        간단한 감성 분석 (-1.0 ~ 1.0)

        긍정 키워드: +0.2
        부정 키워드: -0.2
        """
        if not text:
            return 0.0

        positive_keywords = [
            '상승', '급등', '신고가', '호실적', '턴어라운드', '매수', '추천',
            '목표가 상향', '실적 개선', '수주', '계약', '성장', '기대',
            '흑자전환', '영업이익', '증가', '호조'
        ]

        negative_keywords = [
            '하락', '급락', '신저가', '적자', '손실', '매도', '주의',
            '목표가 하향', '실적 부진', '감소', '악화', '우려', '위험',
            '적자전환', '감익', '부진'
        ]

        score = 0.0
        text_lower = text.lower()

        for keyword in positive_keywords:
            if keyword in text:
                score += 0.2

        for keyword in negative_keywords:
            if keyword in text:
                score -= 0.2

        return max(-1.0, min(1.0, score))

    def _extract_policy_keywords(self, news: List[Dict]) -> List[str]:
        """정책 관련 키워드 추출"""
        policy_patterns = [
            '밸류업', 'value-up', 'value up',
            '배당', '자사주', '주주환원',
            '신재생', '원전', '에너지',
            '반도체', '2차전지', '배터리',
            '방산', 'K-방산', '국방',
            '바이오', '헬스케어', '제약',
            'AI', '인공지능', '데이터센터',
            '전기차', 'EV', '자율주행',
        ]

        found_keywords = set()

        for item in news:
            title = item.get('title', '')
            for pattern in policy_patterns:
                if pattern.lower() in title.lower():
                    found_keywords.add(pattern)

        return list(found_keywords)

    async def _save_cache(self, data: Dict[str, CollectedData]) -> None:
        """수집 데이터를 캐시 테이블에 저장"""
        expires_at = datetime.now() + timedelta(hours=self.config.cache_ttl_hours)

        for code, collected in data.items():
            # 뉴스 저장
            for news in collected.news:
                await self._insert_cache(
                    code, 'news', news.get('title', ''),
                    sentiment=news.get('sentiment', 0),
                    data_date=news.get('date'),
                    expires_at=expires_at
                )

            # 컨센서스 저장
            if collected.consensus:
                await self._insert_cache(
                    code, 'consensus', '',
                    raw_data=collected.consensus,
                    expires_at=expires_at
                )

    async def _insert_cache(
        self,
        code: str,
        data_type: str,
        title: str,
        **kwargs
    ) -> None:
        """캐시 테이블에 단일 레코드 삽입"""
        query = """
            INSERT INTO smart_collected_data
                (stock_code, data_type, source, title, sentiment, data_date, raw_data, expires_at)
            VALUES ($1, $2, 'batch_collector', $3, $4, $5, $6, $7)
        """

        try:
            await db.execute(
                query,
                code,
                data_type,
                title,
                kwargs.get('sentiment'),
                kwargs.get('data_date'),
                json.dumps(kwargs.get('raw_data', {})) if kwargs.get('raw_data') else None,
                kwargs.get('expires_at'),
            )
        except Exception as e:
            logger.debug(f"캐시 저장 실패 {code}: {e}")


async def main():
    """테스트 실행"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    from 신규종목추천.src.phase1 import Phase1AFilter, Phase1BFilter

    await db.connect()

    try:
        # Phase 1 실행
        filter_1a = Phase1AFilter()
        candidates_1a = await filter_1a.filter()

        filter_1b = Phase1BFilter()
        candidates_1b = await filter_1b.filter(candidates_1a)

        print(f"\n=== Phase 1 완료: {len(candidates_1b)}개 종목 ===\n")

        # Phase 2A 실행
        async with BatchCollector() as collector:
            collected = await collector.collect_all(candidates_1b[:10])  # 테스트용 10개

        print(f"\n=== Phase 2A 결과: {len(collected)}개 종목 수집 ===")
        for code, data in list(collected.items())[:5]:
            print(f"\n{code}:")
            print(f"  뉴스: {len(data.news)}개")
            if data.news:
                print(f"    - {data.news[0].get('title', '')[:50]}...")
            print(f"  정책 키워드: {data.policy_keywords}")
            print(f"  컨센서스: {data.consensus}")

    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
