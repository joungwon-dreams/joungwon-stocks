---
created: 2025-11-24 17:36:43
updated: 2025-11-24 17:54:00
tags: [troubleshooting, error, pdf, sql, font]
author: wonny
status: active
severity: high
---

# PDF Report Generation Troubleshooting

## 오류 목록

### 1. SQL Ambiguous Column Error (stock_code)
**발생 시점**: 2025-11-24 17:36:43
**심각도**: medium
**관련 파일**: `scripts/generate_trading_report_pdf.py:88`

#### 증상
- PDF 생성 스크립트 실행 시 즉시 에러 발생
- 에러 메시지:
  ```
  asyncpg.exceptions.AmbiguousColumnError: column reference "stock_code" is ambiguous
  ```
- 거래내역 조회 쿼리에서 발생

#### 원인 분석
- `get_trade_history()` 함수의 SQL 쿼리에서 `trade_history`와 `stocks` 테이블을 JOIN할 때 발생
- 두 테이블 모두 `stock_code` 컬럼을 가지고 있어 SELECT 절에서 `stock_code`만 사용하면 어느 테이블의 컬럼인지 알 수 없음
- asyncpg는 명시적인 테이블 별칭을 요구함

#### 해결 방법
```python
# 해결 전 코드 (line 88)
SELECT
    trade_date,
    stock_code,  # ❌ 모호한 컬럼 참조
    s.stock_name,
    ...

# 해결 후 코드
SELECT
    trade_date,
    th.stock_code,  # ✅ 테이블 별칭으로 명확히 지정
    s.stock_name,
    ...
```

**적용 위치**: `scripts/generate_trading_report_pdf.py:89`

#### 예방 방법
- JOIN을 사용하는 모든 쿼리에서 컬럼명 앞에 테이블 별칭 명시
- 특히 양쪽 테이블에 동일한 컬럼명이 있는 경우 필수
- 체크리스트:
  - [ ] SELECT 절의 모든 컬럼에 테이블 별칭 확인
  - [ ] JOIN 조건에서 양쪽 테이블 별칭 명시
  - [ ] ORDER BY, WHERE 절에서도 별칭 사용

#### 관련 이슈
- 참고: asyncpg는 PostgreSQL의 strict 모드를 사용하여 모호한 참조를 허용하지 않음

---

## 교훈 및 개선사항
- asyncpg를 사용할 때는 JOIN 쿼리에서 항상 테이블 별칭을 명시해야 함
- SQL 쿼리 작성 시 명시적인 테이블 참조를 습관화
- 유사한 패턴이 있는 다른 스크립트도 검토 필요 (import_kb_trades.py 등)

### 2. Korean Font Rendering Error (한글 깨짐)
**발생 시점**: 2025-11-24 17:54:00
**심각도**: high
**관련 파일**: `scripts/generate_trading_report_pdf.py:21-43`

#### 증상
- PDF 파일에서 한글이 검은 네모 박스로 표시됨
- 모든 한글 텍스트가 깨져서 읽을 수 없음
- 숫자와 영문은 정상 표시

#### 원인 분석
- AppleSDGothicNeo.ttc 파일은 존재하지만 ReportLab에서 TTC (TrueType Collection) 형식 처리 실패
- `subfontIndex` 파라미터가 올바르지 않거나 ReportLab 버전과 호환 문제
- TTC 파일은 여러 폰트를 하나의 파일에 담은 형식으로, TTF에 비해 호환성이 낮음

#### 해결 방법
**Step 1: NanumGothic TTF 폰트 다운로드**
```bash
mkdir -p fonts
cd fonts
curl -L -o NanumGothic.ttf "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
curl -L -o NanumGothicBold.ttf "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf"
```

**Step 2: 스크립트 수정**
```python
# Before (lines 21-30)
try:
    pdfmetrics.registerFont(TTFont('NanumGothic', 
        '/System/Library/Fonts/AppleSDGothicNeo.ttc', subfontIndex=0))
    pdfmetrics.registerFont(TTFont('NanumGothicBold', 
        '/System/Library/Fonts/AppleSDGothicNeo.ttc', subfontIndex=3))
    FONT_NAME = 'NanumGothic'
    FONT_NAME_BOLD = 'NanumGothicBold'
except:
    FONT_NAME = 'Helvetica'
    FONT_NAME_BOLD = 'Helvetica-Bold'

# After (lines 21-43)
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
font_dir = os.path.join(project_root, 'fonts')

try:
    font_regular = os.path.join(font_dir, 'NanumGothic.ttf')
    font_bold = os.path.join(font_dir, 'NanumGothicBold.ttf')
    
    if os.path.exists(font_regular) and os.path.exists(font_bold):
        pdfmetrics.registerFont(TTFont('NanumGothic', font_regular))
        pdfmetrics.registerFont(TTFont('NanumGothicBold', font_bold))
        FONT_NAME = 'NanumGothic'
        FONT_NAME_BOLD = 'NanumGothicBold'
        print(f"✅ 한글 폰트 로드 성공: {font_regular}")
    else:
        raise FileNotFoundError("Font files not found")
except Exception as e:
    print(f"⚠️  폰트 로드 실패: {e}")
    print("   Helvetica 폰트로 대체 (한글 깨질 수 있음)")
    FONT_NAME = 'Helvetica'
    FONT_NAME_BOLD = 'Helvetica-Bold'
```

**Step 3: 검증**
```bash
venv/bin/python scripts/generate_trading_report_pdf.py
# 출력: ✅ 한글 폰트 로드 성공: /Users/wonny/Dev/joungwon.stocks/fonts/NanumGothic.ttf
```

#### 예방 방법
- TTF 파일 사용 권장 (TTC보다 호환성 높음)
- 폰트 로딩 실패 시 명확한 에러 메시지 출력
- 프로젝트 내부에 폰트 파일 포함 (외부 시스템 폰트 의존 최소화)
- 체크리스트:
  - [ ] 폰트 파일 존재 여부 확인
  - [ ] TTF 형식 사용 (TTC 아님)
  - [ ] 폰트 로딩 성공 메시지 확인
  - [ ] PDF 열어서 한글 정상 표시 확인

#### 관련 이슈
- TTC (TrueType Collection) vs TTF (TrueType Font):
  - TTC: 여러 폰트를 하나의 파일에 저장 (용량 절약)
  - TTF: 단일 폰트만 포함 (호환성 높음)
- ReportLab은 TTF를 더 안정적으로 지원

#### 테스트 결과
```
✅ 한글 폰트 로드 성공
✅ 보유종목: 6개
✅ 거래내역: 200건
✅ PDF 생성 완료
✅ 한글 정상 표시 확인
```
