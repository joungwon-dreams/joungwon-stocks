---
created: 2025-11-28 08:41:50
updated: 2025-11-28 08:41:50
tags: [feature, pdf, structure-lock, critical]
author: wonny
status: active
---

# PDF 문서 구조 잠금 (Structure Lock)

## 개요

realtime_dashboard.pdf 및 종목명.pdf의 문서 구조가 예기치 않게 변경되는 것을 방지하기 위한 시스템입니다.

## 배경

- **문제**: PDF 구조가 개발 과정에서 자주 변경되어 일관성 저하
- **요청일**: 2025-11-28
- **해결방안**: 구조 명세서 작성 + 코드 주석 + CLAUDE.md 규칙 추가

## 구현 내용

### 1. PDF 구조 명세서
- **위치**: `docs/PDF_STRUCTURE_SPECIFICATION.md`
- **내용**:
  - realtime_dashboard.pdf 전체 구조
  - 종목명.pdf 전체 구조 (7페이지, 16개 섹션)
  - 차트 스펙 (크기, 색상, 스타일)
  - 변경 금지 체크리스트

### 2. 코드 주석 추가
- `scripts/gemini/generate_pdf_report.py` 상단에 STRUCTURE LOCKED 경고
- `scripts/generate_realtime_dashboard_terminal_style.py` 상단에 STRUCTURE LOCKED 경고

### 3. CLAUDE.md 규칙 추가
- "PDF 문서 구조 변경 금지 (CRITICAL)" 섹션 추가
- 변경 시 필요 절차 명시

## 변경 금지 항목

| 항목 | 설명 |
|------|------|
| 섹션 순서 | 페이지별 섹션 배치 순서 |
| 섹션 제목 | 이모지 포함 제목 텍스트 |
| 테이블 컬럼 | 순서, 너비, 헤더 텍스트 |
| 색상 코드 | COLOR_RED, COLOR_BLUE 등 |
| 폰트 크기 | 제목, 본문, 라벨 크기 |
| 페이지 브레이크 | PageBreak 위치 |
| 차트 크기 | figsize, width x height |

## 변경 절차

구조 변경이 필요한 경우:

1. `docs/PDF_STRUCTURE_SPECIFICATION.md` 확인
2. 사용자에게 변경 사유 설명 및 승인 요청
3. 명세서 버전 업데이트 (예: 1.0.0 → 1.1.0)
4. 변경 이력 기록
5. 테스트 후 배포

## 관련 파일

- `docs/PDF_STRUCTURE_SPECIFICATION.md` - 전체 구조 명세서
- `scripts/gemini/generate_pdf_report.py` - 종목명.pdf 생성
- `scripts/generate_realtime_dashboard_terminal_style.py` - 대시보드 생성
- `cron/1min.py` - 대시보드 호출
- `cron/10min.py` - 종목 리포트 호출

## 주의사항

- 데이터 값 변경은 허용됨 (구조만 잠금)
- 버그 수정은 허용됨 (기능 변경 아님)
- 새 섹션 추가는 사용자 승인 필요
