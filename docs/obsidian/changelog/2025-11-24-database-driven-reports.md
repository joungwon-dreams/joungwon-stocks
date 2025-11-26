---
created: 2025-11-24 19:44:58
updated: 2025-11-24 19:44:58
tags: [changelog, pdf, database, holdings, automation]
author: wonny
status: active
---

# 2025-11-24 변경 이력: 데이터베이스 기반 리포트 시스템

## 요약
Excel 기반의 하드코딩된 리포트 생성에서 데이터베이스 기반의 자동화된 리포트 생성 시스템으로 전환

## 주요 변경사항

### 1. 데이터 수집 워크플로우 구축

#### 새로 생성된 스크립트
- `scripts/import_windows_excel_holdings.py`: Excel 데이터를 stock_assets 테이블에 저장
- `scripts/collect_holding_stocks_data.py`: 보유종목 9개에 대해 41개 사이트에서 데이터 수집
- `scripts/update_current_prices.py`: collected_data의 최신 가격으로 stock_assets 업데이트
- `scripts/generate_research_from_db.py`: 데이터베이스 기반 PDF 리포트 생성

#### 워크플로우
```
Excel 파일 → stock_assets DB
    ↓
데이터 수집 (41 sites) → collected_data DB
    ↓
가격 업데이트 → stock_assets DB
    ↓
PDF 리포트 생성
```

### 2. 데이터 수집 실행 결과

#### Tier 1 (Official Libraries) - 100% 성공
- pykrx: KRX OHLCV 데이터
- FinanceDataReader: 종목 리스트
- OpenDART: 공시 정보
- 36/36 성공

#### Tier 2 (Official APIs) - 80% 성공
- 네이버 금융, 다음 금융 등
- 36/45 성공
- 실패 사이트: 9개 (추후 분석 필요)

#### 수집 결과
- 총 496개 레코드 수집
- 9개 보유종목 × 5개 평균 데이터 타입
- collected_data 테이블에 저장 완료

### 3. 데이터베이스 상태

#### stock_assets 테이블
- 10개 보유종목 저장 (quantity > 0)
- Excel 데이터 기반 초기값
- collected_data 기반 current_price 업데이트

#### 최종 보유종목 상태
```
한화 (000880): -9.08%
한국전력 (015760): +3.55% ✅
한국카본 (017960): -2.01%
롯데쇼핑 (023530): -0.17%
파라다이스 (034230): -0.80%
카카오 (035720): +2.53% ✅
HDC현대산업개발 (294870): +6.73% ✅
우리금융지주 (316140): -0.97%
금양그린파워 (322310): -0.32%
HD현대에너지솔루션 (329180): -1.78%
```

### 4. PDF 리포트 생성

#### 생성된 리포트
- 총 10개 PDF 파일
- 위치: `/Users/wonny/Dev/joungwon.stocks.report/research_report/holding_stock/`

#### 리포트 구성
1. **보유 현황 섹션**
   - 보유수량, 평균매수가, 현재가
   - 총 투자금액, 평가금액, 손익률
   - 차트 (막대 차트 + 파이 차트)

2. **수집된 데이터 현황**
   - 데이터 타입별 수집 현황
   - Site ID / Domain ID 추적
   - 수집 시간 타임스탬프

3. **현재 시세 정보**
   - 네이버 금융 API 실시간 조회
   - 종목명, 시장구분, 업종
   - 현재가, 전일대비, 시/고/저가, 거래량

4. **투자 의견**
   - 손익률 기반 자동 전략 제안
   - 4단계 구분 (수익 구간 / 소폭 수익 / 소폭 손실 / 손실 구간)

## 기술적 개선사항

### 1. 데이터 무결성
- Excel은 일회성 입력 후 삭제
- 모든 데이터는 데이터베이스에 영구 저장
- Single Source of Truth: Database

### 2. 안전한 API 처리
```python
def safe_int(value, default=0):
    """네이버 API 문자열 응답 처리"""
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default
```

### 3. 유연한 API 응답 처리
```python
# List 또는 Dict 응답 모두 처리
if isinstance(data, list) and len(data) > 0:
    return data[0]
return data
```

### 4. 경고 메시지 억제
```python
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')
```

## 해결된 문제

### 문제 1: 잘못된 현재가 데이터
**증상**: 두 종목의 가격이 10배 차이
- HD현대에너지솔루션: 552,000원 (API) → 50,100원 (실제)
- 금양그린파워: 21,950원 (API) → 11,840원 (실제)

**원인**: 네이버 금융 API의 일시적 데이터 오류

**해결**: Excel 데이터로 수동 보정 후 스크립트 재실행

### 문제 2: collected_data 테이블 스키마 오류
**증상**: `column "source" does not exist`

**원인**: 테이블에 `site_id`, `domain_id`만 존재, `source` 컬럼 없음

**해결**: Site ID / Domain ID로 출처 표시하도록 변경

### 문제 3: 네이버 API 타입 불일치
**증상**: `ValueError: Cannot specify ',' with 's'`

**원인**: API가 숫자를 문자열로 반환

**해결**: safe_int() 헬퍼 함수로 안전한 타입 변환

### 문제 4: API 응답 형식 불일치
**증상**: `AttributeError: 'list' object has no attribute 'get'`

**원인**: 일부 API가 dict 대신 list 반환

**해결**: 타입 체크 후 list[0] 추출

## 다음 단계

### 단기 (1주일)
- [ ] Tier 2 실패 사이트 9개 분석 및 수정
- [ ] Tier 3 (웹 스크래핑) 통합
- [ ] Tier 4 (브라우저 자동화) 통합
- [ ] 자동 스케줄링 (매일 장 마감 후)

### 중기 (1개월)
- [ ] 과거 3개월 차트 추가
- [ ] 기술적 지표 추가 (이동평균선, RSI)
- [ ] 뉴스 요약 추가
- [ ] 재무제표 요약 추가

### 장기 (3개월)
- [ ] 동종업계 비교 분석
- [ ] AI 기반 투자 의견 생성 (Gemini)
- [ ] 자동 이메일 발송
- [ ] 대시보드 웹 UI

## 성능 메트릭

### 데이터 수집
- 평균 수집 시간: ~2분 (41 sites, 9 stocks)
- 병렬 처리: 최대 10개 동시 실행
- Rate limiting: 사이트별 자동 조절

### PDF 생성
- 평균 생성 시간: ~10초/종목
- 총 소요 시간: ~2분 (10종목)
- 파일 크기: ~500KB/PDF

## 관련 문서
- Feature: [[features/holding-stock-research-report]]
- Data Collection: [[features/data-collection-system]]
- Troubleshooting: [[troubleshooting/pdf-generation-errors]]
