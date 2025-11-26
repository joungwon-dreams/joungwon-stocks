---
created: 2025-11-24 17:36:43
updated: 2025-11-24 17:54:00
tags: [feature, pdf, report, trading]
author: wonny
status: active
---

# 거래내역 PDF 리포트 생성

## 개요
KB증권에서 임포트한 거래내역과 현재 보유종목 정보를 PDF 리포트로 생성하는 기능

## 구현 내용

### 생성된 파일
- `scripts/generate_trading_report_pdf.py`: PDF 생성 스크립트

### 주요 기능
1. **대시보드 페이지**: 포트폴리오 요약 정보
   - 총자산, 예수금, 보유종목 평가액, 보유종목 수
   - 보유종목 상세 테이블 (종목코드, 종목명, 수량, 평균매수가, 총매수금액)

2. **거래내역 페이지**: 모든 거래 내역
   - 거래일자, 종목코드, 종목명, 구분(매수/매도), 수량, 단가, 거래금액, 수수료
   - 매수는 빨간색, 매도는 파란색으로 구분

### 기술 스택
- **ReportLab**: PDF 생성 라이브러리
- **asyncpg**: PostgreSQL 비동기 쿼리
- **한글 폰트**: AppleSDGothicNeo (macOS 기본 폰트)

## 사용 방법

### 실행
```bash
venv/bin/python scripts/generate_trading_report_pdf.py
```

### 출력 위치
```
/Users/wonny/Dev/joungwon.stocks.report/trading_report.pdf
```

### 실행 결과
```
=== 거래내역 손익 리포트 PDF 생성 ===

📊 데이터 조회 중...
✅ 보유종목: 6개
✅ 거래내역: 200건

📝 PDF 생성 중: /Users/wonny/Dev/joungwon.stocks.report/trading_report.pdf

✅ PDF 생성 완료

=== 요약 ===
총자산: 70,326,218원
예수금: 13,435,890원
보유종목 평가액: 56,890,328원
보유종목 수: 6개
```

## API 문서

### 데이터 조회 함수

#### `get_portfolio_summary()`
포트폴리오 요약 데이터 조회

**반환값**:
```python
{
    'holdings': List[Dict],  # 보유종목 목록
    'holdings_count': int,   # 보유종목 수
    'total_investment': int, # 총 투자금액
    'available_cash': int,   # 예수금
    'total_assets': int,     # 총자산
    'total_deposits': int    # 총 입금액
}
```

#### `get_trade_history(limit: int = 100)`
거래내역 조회

**파라미터**:
- `limit`: 조회할 거래 수 (기본값: 100)

**반환값**: List[Dict] - 거래내역 리스트

### PDF 생성 함수

#### `create_dashboard_page(pdf_elements: List, summary: Dict)`
대시보드 페이지 생성

**파라미터**:
- `pdf_elements`: ReportLab PDF 요소 리스트
- `summary`: `get_portfolio_summary()`의 반환값

#### `create_trade_history_pages(pdf_elements: List, trades: List[Dict])`
거래내역 페이지 생성

**파라미터**:
- `pdf_elements`: ReportLab PDF 요소 리스트
- `trades`: `get_trade_history()`의 반환값

#### `generate_pdf()`
메인 실행 함수 (비동기)

## 데이터 소스

### stock_assets 테이블
```sql
SELECT stock_code, stock_name, quantity, avg_buy_price,
       total_cost, total_value, profit_loss, profit_loss_rate
FROM stock_assets
WHERE quantity > 0
ORDER BY total_cost DESC
```

### trade_history 테이블
```sql
SELECT trade_date, th.stock_code, s.stock_name, trade_type,
       quantity, price, total_amount, fee, tax
FROM trade_history th
LEFT JOIN stocks s ON th.stock_code = s.stock_code
WHERE gemini_reasoning LIKE 'KB증권 엑셀 자동 임포트%'
ORDER BY trade_date DESC, id DESC
LIMIT 200
```

## 스타일링

### 색상 구성
- **헤더**: `#34495e` (다크 그레이)
- **테이블 배경**: `#ecf0f1`, `#d5dbdb` (번갈아 가며)
- **매수 텍스트**: `#e74c3c` (빨간색)
- **매도 텍스트**: `#3498db` (파란색)

### 레이아웃
- **페이지 크기**: A4
- **여백**: 상단/하단 2cm, 좌우 1.5cm
- **폰트**: NanumGothic (일반), NanumGothicBold (굵게)

## 주의사항

### 한글 폰트
- **NanumGothic TTF 폰트** 사용 (프로젝트 내부 `fonts/` 폴더)
- 폰트 파일이 없는 경우 Helvetica로 대체 (한글 깨짐 가능)
- 폰트 로딩 성공 시 메시지: `✅ 한글 폰트 로드 성공`
- 폰트 위치:
  - `fonts/NanumGothic.ttf` (Regular, 2.0MB)
  - `fonts/NanumGothicBold.ttf` (Bold, 2.0MB)

### 거래내역 제한
- 기본 200건 조회 (성능 고려)
- 필요시 `get_trade_history(limit=1000)` 등으로 조정 가능

### KB증권 데이터만 포함
- `gemini_reasoning LIKE 'KB증권 엑셀 자동 임포트%'` 필터 사용
- 다른 소스의 거래내역은 제외됨

## 확장 가능성

### 추가 기능 아이디어
- [ ] 월별/연도별 손익 차트 추가
- [ ] 종목별 수익률 분석 페이지
- [ ] 매매 타이밍 분석
- [ ] PDF 파일명에 날짜 자동 추가
- [ ] 이메일 자동 발송 기능

## 관련 문서
- Troubleshooting: [[troubleshooting/pdf-generation-errors]]
- 변경 이력: [[changelog/2025-11-24-changes]]
- KB증권 임포트: [[features/kb-trade-import]]
