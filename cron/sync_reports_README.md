# Reports Sync Cron 설정 가이드

## 📋 개요

`scripts/sync_reports.py` 스크립트는 `/Users/wonny/Dev/joungwon.stocks/reports` 폴더와 `/Users/wonny/Dev/joungwon.stocks/charts` 폴더에 새로운 파일이 생성되면 자동으로 `/Users/wonny/Dev/joungwon.stocks.report/research_report/holding_stock` 폴더로 복사합니다.

## 🎯 동작 방식

- **소스 디렉토리 1**: `/Users/wonny/Dev/joungwon.stocks/reports` → 타겟 루트로 복사
- **소스 디렉토리 2**: `/Users/wonny/Dev/joungwon.stocks/charts` → 타겟의 `charts/` 폴더로 복사 (재귀적)
- **타겟 디렉토리**: `/Users/wonny/Dev/joungwon.stocks.report/research_report/holding_stock`
- **로그 파일**: `/Users/wonny/Dev/joungwon.stocks/logs/sync_reports.log`

### 파일 복사 규칙

1. `reports/` 디렉토리의 모든 파일 스캔 및 복사
2. `charts/` 폴더의 모든 파일 재귀적으로 스캔 및 복사 (하위 폴더 구조 유지)
3. 타겟 디렉토리에 동일한 파일이 없거나 다른 경우에만 복사
4. 파일 크기와 수정 시간으로 중복 확인
5. 복사 결과를 로그 파일에 기록

## ⚙️ Crontab 설정

### 1. crontab 편집

```bash
crontab -e
```

### 2. Cron 작업 추가

#### 옵션 1: 5분마다 실행 (권장)
```bash
# Reports 자동 동기화 (5분마다)
*/5 * * * * cd /Users/wonny/Dev/joungwon.stocks && /Users/wonny/Dev/joungwon.stocks/venv/bin/python scripts/sync_reports.py >> /Users/wonny/Dev/joungwon.stocks/logs/sync_reports.log 2>&1
```

#### 옵션 2: 1분마다 실행 (빠른 동기화 필요 시)
```bash
# Reports 자동 동기화 (1분마다)
* * * * * cd /Users/wonny/Dev/joungwon.stocks && /Users/wonny/Dev/joungwon.stocks/venv/bin/python scripts/sync_reports.py >> /Users/wonny/Dev/joungwon.stocks/logs/sync_reports.log 2>&1
```

#### 옵션 3: 특정 시간에만 실행 (거래 시간)
```bash
# Reports 자동 동기화 (09:00-15:30, 5분마다)
*/5 9-15 * * 1-5 cd /Users/wonny/Dev/joungwon.stocks && /Users/wonny/Dev/joungwon.stocks/venv/bin/python scripts/sync_reports.py >> /Users/wonny/Dev/joungwon.stocks/logs/sync_reports.log 2>&1
```

### 3. Crontab 형식 설명

```
* * * * * command
│ │ │ │ │
│ │ │ │ └─ 요일 (0-7, 0과 7은 일요일, 1-5는 월~금)
│ │ │ └─── 월 (1-12)
│ │ └───── 일 (1-31)
│ └─────── 시 (0-23)
└───────── 분 (0-59)
```

**예제**:
- `*/5 * * * *`: 5분마다 (모든 날)
- `* * * * *`: 1분마다 (모든 날)
- `*/5 9-15 * * 1-5`: 월~금, 09:00-15:59, 5분마다
- `0 */1 * * *`: 매 시간 정각

### 4. Crontab 설정 확인

```bash
# 현재 crontab 목록 보기
crontab -l

# Cron 서비스 상태 확인 (macOS)
sudo launchctl list | grep cron
```

## 🧪 테스트

### 수동 실행 테스트

```bash
# 프로젝트 디렉토리로 이동
cd /Users/wonny/Dev/joungwon.stocks

# 가상환경 활성화
source venv/bin/activate

# 스크립트 실행
python scripts/sync_reports.py
```

**예상 출력**:
```
[2025-11-26 07:26:52] ================================================================================
[2025-11-26 07:26:52] 📁 Report Sync Started
[2025-11-26 07:26:52]
📂 Syncing reports/
[2025-11-26 07:26:52] 📊 Found 3 file(s) in reports/
[2025-11-26 07:26:52] ✅ Copied: 우리금융지주_1126_0723.pdf (303.8 KB)
[2025-11-26 07:26:52] ⏭️  Skipped: 우리금융지주_1126_0719.pdf
[2025-11-26 07:26:52]
📂 Syncing charts/
[2025-11-26 07:26:52] 📭 charts/ directory does not exist (or empty)
[2025-11-26 07:26:52]
--------------------------------------------------------------------------------
[2025-11-26 07:26:52] 📊 Sync Summary:
[2025-11-26 07:26:52]    ✅ Copied: 1 file(s)
[2025-11-26 07:26:52]    ⏭️  Skipped: 1 file(s)
[2025-11-26 07:26:52]    ❌ Errors: 0 file(s)
[2025-11-26 07:26:52] ================================================================================
```

### 로그 확인

```bash
# 실시간 로그 모니터링
tail -f /Users/wonny/Dev/joungwon.stocks/logs/sync_reports.log

# 최근 100줄 확인
tail -100 /Users/wonny/Dev/joungwon.stocks/logs/sync_reports.log

# 오늘 날짜 로그만 필터링
grep "$(date +%Y-%m-%d)" /Users/wonny/Dev/joungwon.stocks/logs/sync_reports.log
```

### 파일 복사 확인

```bash
# 소스 디렉토리 파일 목록
ls -lh /Users/wonny/Dev/joungwon.stocks/reports
ls -lhR /Users/wonny/Dev/joungwon.stocks/charts

# 타겟 디렉토리 파일 목록
ls -lh /Users/wonny/Dev/joungwon.stocks.report/research_report/holding_stock
ls -lhR /Users/wonny/Dev/joungwon.stocks.report/research_report/holding_stock/charts

# 파일 개수 비교
echo "소스 reports: $(ls /Users/wonny/Dev/joungwon.stocks/reports 2>/dev/null | wc -l)개"
echo "소스 charts: $(find /Users/wonny/Dev/joungwon.stocks/charts -type f 2>/dev/null | wc -l)개"
echo "타겟 전체: $(find /Users/wonny/Dev/joungwon.stocks.report/research_report/holding_stock -type f 2>/dev/null | wc -l)개"
```

## 🚨 주의사항

### 1. 파일 중복 방지

- 스크립트는 파일 크기와 수정 시간을 비교하여 중복 복사를 방지합니다
- 같은 이름의 파일이 이미 존재하고 내용이 같으면 건너뜁니다
- 파일이 업데이트된 경우에만 다시 복사합니다

### 2. 로그 파일 관리

- 로그 파일이 계속 쌓이므로 주기적으로 정리 필요:
  ```bash
  # 7일 이상 된 로그 삭제
  find /Users/wonny/Dev/joungwon.stocks/logs -name "sync_reports.log" -mtime +7 -delete

  # 또는 로그 파일 비우기
  > /Users/wonny/Dev/joungwon.stocks/logs/sync_reports.log
  ```

### 3. 디렉토리 권한

- 소스 및 타겟 디렉토리에 대한 읽기/쓰기 권한이 필요합니다
- 권한 확인:
  ```bash
  ls -ld /Users/wonny/Dev/joungwon.stocks/reports
  ls -ld /Users/wonny/Dev/joungwon.stocks.report/research_report/holding_stock
  ```

## 🔧 트러블슈팅

### Cron이 실행되지 않는 경우

1. **경로 확인**
   ```bash
   which python  # Python 경로 확인
   pwd          # 현재 디렉토리 확인
   ```

2. **권한 확인**
   ```bash
   ls -la /Users/wonny/Dev/joungwon.stocks/scripts/sync_reports.py
   # -rwxr-xr-x 여야 함 (실행 권한)
   ```

3. **macOS Full Disk Access 권한**
   - 시스템 환경설정 > 보안 및 개인 정보 보호 > 전체 디스크 접근 권한
   - `/usr/sbin/cron` 추가

### 파일이 복사되지 않는 경우

1. **디렉토리 존재 확인**
   ```bash
   ls -ld /Users/wonny/Dev/joungwon.stocks/reports
   ls -ld /Users/wonny/Dev/joungwon.stocks.report/research_report/holding_stock
   ```

2. **로그 확인**
   ```bash
   tail -50 /Users/wonny/Dev/joungwon.stocks/logs/sync_reports.log
   ```

3. **수동 실행으로 에러 확인**
   ```bash
   cd /Users/wonny/Dev/joungwon.stocks
   venv/bin/python scripts/sync_reports.py
   ```

## 📅 Cron 작업 중지/재개

### 중지
```bash
# crontab 편집
crontab -e

# 해당 라인 앞에 # 추가하여 주석 처리
# */5 * * * * cd /Users/wonny/Dev/joungwon.stocks && ...
```

### 삭제
```bash
# 모든 cron 작업 삭제 (주의!)
crontab -r

# 특정 작업만 삭제
crontab -e  # 편집기에서 해당 라인 삭제
```

## 📊 모니터링

### 동기화 상태 확인 스크립트

```bash
#!/bin/bash
# check_sync_status.sh

SOURCE_DIR="/Users/wonny/Dev/joungwon.stocks/reports"
TARGET_DIR="/Users/wonny/Dev/joungwon.stocks.report/research_report/holding_stock"

SOURCE_COUNT=$(ls "$SOURCE_DIR" 2>/dev/null | wc -l)
TARGET_COUNT=$(ls "$TARGET_DIR" 2>/dev/null | wc -l)

echo "=== Reports Sync Status ==="
echo "소스 파일: $SOURCE_COUNT개"
echo "타겟 파일: $TARGET_COUNT개"
echo ""
echo "최근 동기화 로그:"
tail -5 /Users/wonny/Dev/joungwon.stocks/logs/sync_reports.log
```

---

**마지막 업데이트**: 2025-11-26 07:21:25
**스크립트 위치**: `/Users/wonny/Dev/joungwon.stocks/scripts/sync_reports.py`
**로그 파일**: `/Users/wonny/Dev/joungwon.stocks/logs/sync_reports.log`
