---
created: 2025-11-24 13:32:08
updated: 2025-11-24 13:32:08
tags: [troubleshooting, error, database, asyncpg]
author: wonny
status: active
severity: medium
---

# Database Integration Troubleshooting

## 오류 목록

### 1. PostgreSQL DATE 타입 형식 오류
**발생 시점**: 2025-11-24 13:30:12
**심각도**: medium
**관련 파일**: `src/core/base_fetcher.py:240`

#### 증상
- collected_data 테이블에 데이터 저장 시 오류 발생
- 에러 메시지: `invalid input for query argument $6: '2025-11-24' ('str' object has no attribute 'toordinal')`
- 데이터는 fetch되지만 저장되지 않음

#### 원인 분석
asyncpg는 PostgreSQL DATE 타입에 대해 엄격한 타입 체크를 수행:
- PostgreSQL의 DATE 컬럼에 문자열 '2025-11-24'를 전달
- asyncpg는 `datetime.date` 객체를 기대하지만 str을 받음
- Python의 `str` 객체에는 `toordinal()` 메서드가 없어 변환 실패

```python
# 문제가 있는 코드
await db.execute(
    query,
    ticker,
    self.site_id,
    domain_id,
    data_type,
    json.dumps(data_content),
    data_date  # ❌ 문자열 '2025-11-24'
)
```

#### 해결 방법
```python
# 해결 후 코드
from datetime import date, datetime

# 문자열을 date 객체로 변환
if data_date is None:
    date_obj = date.today()
else:
    date_obj = datetime.strptime(data_date, "%Y-%m-%d").date()

await db.execute(
    query,
    ticker,
    self.site_id,
    domain_id,
    data_type,
    json.dumps(data_content),
    date_obj  # ✅ datetime.date 객체
)
```

#### 예방 방법
- asyncpg 사용 시 PostgreSQL 데이터 타입과 Python 타입 매핑 확인
- DATE → `datetime.date`
- TIMESTAMP → `datetime.datetime`
- TEXT → `str`
- JSON/JSONB → `str` (json.dumps 사용)
- Pydantic 모델로 타입 검증 추가 고려

#### 관련 이슈
- BaseFetcher.save_collected_data() 메서드 수정
- 모든 fetcher에서 data_date를 문자열로 전달하지만 내부에서 자동 변환

---

### 2. Database Pool 미초기화 경고
**발생 시점**: 2025-11-24 13:29:58
**심각도**: low
**관련 파일**: `scripts/test_fetchers.py:41-61`

#### 증상
- `'NoneType' object has no attribute 'acquire'` 에러 메시지
- test_tier1_fetchers(), test_tier2_fetchers()에서 발생
- 데이터베이스 없이 fetcher 테스트 시 발생

#### 원인 분석
- fetcher가 `fetch()` 메서드 내부에서 `save_collected_data()` 호출
- `db.pool`이 초기화되지 않은 상태 (None)
- `await db.execute()`에서 `self.pool.acquire()` 호출 시 AttributeError

#### 해결 방법
의도된 동작이므로 수정 불필요:
- 데이터베이스 없이 테스트할 때는 에러 로그만 출력
- 데이터 수집은 정상 작동
- `test_with_database()`에서는 `await db.connect()` 호출 후 정상 작동

선택적 개선 방안:
```python
async def save_collected_data(...):
    # Pool이 없으면 조용히 건너뛰기
    if db.pool is None:
        self.logger.debug("Database pool not initialized, skipping save")
        return

    # ... 기존 코드
```

#### 예방 방법
- 테스트 코드에서 데이터베이스 연결 여부 명확히 구분
- production 환경에서는 항상 db.connect() 먼저 호출
- 환경 변수로 데이터베이스 연결 필수 여부 설정

---

## 교훈 및 개선사항

### 배운 점
1. **asyncpg 타입 엄격성**: 문자열 자동 변환 없음, 명시적 타입 변환 필요
2. **우아한 저하(Graceful Degradation)**: DB 없이도 fetcher가 작동하도록 설계
3. **테스트 분리**: 단위 테스트(DB 없음)와 통합 테스트(DB 있음) 명확히 구분

### 개선 아이디어
1. Pydantic 모델로 collected_data 스키마 정의
2. Type hints 강화 (`data_date: Optional[Union[str, date]]`)
3. 데이터베이스 의존성 주입 패턴 고려
4. retry 로직 추가 (일시적 DB 연결 문제 대응)
