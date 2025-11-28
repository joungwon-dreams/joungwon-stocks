# Phase 3.9: Advanced Data Pipeline - Implementation Document

> **Version:** 1.0
> **Author:** Claude (Implementer)
> **Date:** 2025-11-28
> **Status:** Completed (Core Features)

---

## Overview

Phase 3.9는 AEGIS가 더 나은 의사결정을 할 수 있도록 **데이터 품질을 높이는** 단계입니다.
"Input이 좋아야 Output이 좋다"는 원칙에 따라, AI 분석(Phase 4) 전에 데이터 수집 레이어를 고도화했습니다.

---

## Implemented Components

### 1. EnhancedNewsFetcher (뉴스 고도화)

**위치:** `src/fetchers/tier4_browser_automation/naver_stock_news_fetcher.py`

**기존 fetcher에 통합** (신규 파일 생성 X)

#### 1.1 중복 뉴스 제거 (De-duplication)

```python
# Phase 3.9: 중복 판단 임계값
SIMILARITY_THRESHOLD = 0.7

def _deduplicate_news(self, news_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    SequenceMatcher를 사용한 제목 유사도 기반 중복 제거.

    - 유사도 >= 0.7 이면 중복으로 판단
    - 먼저 수집된 뉴스를 유지
    """
```

#### 1.2 우선순위 점수 (Priority Scoring)

```python
# Phase 3.9: 우선순위 키워드 (1-5점)
PRIORITY_KEYWORDS = {
    5: ['단독', '속보', '긴급', '특종'],           # 최우선
    4: ['공시', '계약', '수주', '인수', '합병', 'M&A'],  # 핵심 이벤트
    3: ['실적', '매출', '영업이익', '순이익', '흑자전환', '적자전환'],  # 재무
    2: ['목표가', '투자의견', '상향', '하향', '매수', '매도'],  # 증권사
    1: ['특징주', '테마', '급등', '급락', '신고가', '신저가'],  # 시장 관심
}

@staticmethod
def calculate_priority(title: str) -> int:
    """키워드 기반 우선순위 계산 (0-5)"""
```

#### 1.3 반환 데이터 구조

```python
{
    'ticker': '005930',
    'source': 'naver_stock_news',
    'crawled_at': '2025-11-28T...',
    'news_list': [...],       # 우선순위 순 정렬된 뉴스
    'news_count': 15,         # 중복 제거 후 개수
    'raw_count': 20,          # 원본 개수
    'duplicates_removed': 5   # 제거된 중복 수
}
```

---

### 2. MarketScanner (시장 컨텍스트)

**위치:** `src/fetchers/tier1_official_libs/market_scanner.py`

**신규 생성** (개별 종목이 아닌 시장 전체 스캔이므로 별도 모듈)

#### 2.1 Sector Heatmap (업종별 등락률)

```python
async def get_sector_heatmap(self, market: str = "KOSPI") -> Dict[str, Any]:
    """
    pykrx를 사용하여 업종별 등락률 수집.

    Returns:
        {
            "market": "KOSPI",
            "date": "20251128",
            "sectors": [
                {"name": "의료·정밀기기", "change_rate": +1.73, ...},
                {"name": "건설", "change_rate": +1.42, ...},
                ...
            ],
            "top_3": [...],    # 상위 3개 업종
            "bottom_3": [...]  # 하위 3개 업종
        }
    """
```

#### 2.2 Market Breadth (ADR)

```python
async def get_market_breadth(self, market: str = "KOSPI") -> Dict[str, Any]:
    """
    ADR (Advance-Decline Ratio) 계산.

    - ADR > 1.5: strong_bullish
    - ADR > 1.0: bullish
    - ADR > 0.67: neutral
    - ADR > 0.5: bearish
    - ADR <= 0.5: strong_bearish

    Returns:
        {
            "advancing": 595,
            "declining": 282,
            "unchanged": 81,
            "adr": 2.11,
            "adr_interpretation": "strong_bullish",
            "breadth_pct": 67.8
        }
    """
```

#### 2.3 Full Market Context

```python
async def get_full_market_context(market: str = "KOSPI") -> Dict[str, Any]:
    """
    AEGIS를 위한 종합 시장 컨텍스트.

    - 5분 캐시 적용
    - 업종 히트맵 + 시장 breadth 통합

    Returns:
        {
            "summary": {
                "leading_sectors": ["의료·정밀기기", "건설", "전기·가스"],
                "lagging_sectors": ["유통", "제조", "전기전자"],
                "market_sentiment": "strong_bullish",
                "adr": 2.11,
                "breadth_pct": 67.8
            }
        }
    """
```

#### 2.4 사용법

```python
from src.fetchers.tier1_official_libs.market_scanner import (
    get_market_context,
    get_leading_sectors
)

# 전체 컨텍스트
context = await get_market_context("KOSPI")
print(context["summary"]["market_sentiment"])  # "strong_bullish"

# 상위 3개 업종만
top_sectors = await get_leading_sectors(3, "KOSPI")
```

---

### 3. DataCleaner (데이터 품질 보증)

**상태:** 필요시 구현 예정

설계 명세에 따르면:
- 이상치 탐지/수정 (min_ticks 가격 스파이크 등)
- 결측값 forward-fill

현재는 기존 데이터 품질이 양호하여 구현을 보류합니다.
AEGIS 운영 중 품질 이슈 발생 시 즉시 추가 구현 예정.

---

## Test Results

```
============================================================
Phase 3.9 MarketScanner Test
============================================================

1. Testing Sector Heatmap (KOSPI)...
   Found 24 sectors
   Top 5 Sectors:
   - 의료·정밀기기: +1.73%
   - 건설: +1.42%
   - 전기·가스: +0.89%
   - 오락·문화: +0.89%
   - 섬유·의류: +0.60%

2. Testing Market Breadth (ADR)...
   Advancing: 595
   Declining: 282
   ADR: 2.11
   Sentiment: strong_bullish
   Breadth %: 67.8%

3. Testing Full Market Context...
   Leading Sectors: 의료·정밀기기, 건설, 전기·가스
   Lagging Sectors: 유통, 제조, 전기전자
   Market Sentiment: strong_bullish

============================================================
MarketScanner Test Complete!
```

---

## Files Modified/Created

| File | Action | Description |
|------|--------|-------------|
| `src/fetchers/tier4_browser_automation/naver_stock_news_fetcher.py` | Modified | 중복 제거 + 우선순위 추가 |
| `src/fetchers/tier1_official_libs/market_scanner.py` | Created | 시장 스캐너 신규 |
| `scripts/test_market_scanner.py` | Created | 테스트 스크립트 |
| `docs/PHASE_3.9_IMPLEMENTATION.md` | Created | 이 문서 |

---

## Integration with AEGIS

Phase 3.9 컴포넌트들은 Phase 4 (Multi-modal Fusion)에서 다음과 같이 활용됩니다:

```python
# 예시: InformationFusionEngine에서 활용
from src.fetchers.tier1_official_libs.market_scanner import get_market_context

async def get_fusion_score(ticker: str):
    # 1. 시장 컨텍스트 확인
    market_context = await get_market_context("KOSPI")

    # 2. 업종 동향 반영
    if ticker_sector in market_context["summary"]["leading_sectors"]:
        score_boost = 0.1  # 주도 업종이면 가점

    # 3. 시장 심리 반영
    if market_context["summary"]["market_sentiment"] == "strong_bullish":
        risk_adjustment = 0.8  # 리스크 완화
```

---

## Next Steps

1. ✅ Phase 3.9 Core 완료
2. ⏳ Phase 4: Multi-modal Fusion 준비
   - `InformationFusionEngine`
   - `NewsSentimentAnalyzer` (Gemini 연동)
   - `DynamicWeightOptimizer`

---

*Last Updated: 2025-11-28*
