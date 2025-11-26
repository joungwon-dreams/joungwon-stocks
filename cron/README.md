# Cron 작업 설정 가이드

## 📋 개요

`1min.py` 스크립트는 1분마다 보유 종목의 실시간 가격, 거래량, 호가 데이터를 수집하여 `min_ticks` 테이블에 저장합니다.

## 🎯 수집 데이터

- **가격 정보**: 현재가, 등락률
- **거래량**: 누적 거래량
- **호가 정보**: 매수호가1, 매도호가1, 매수잔량1, 매도잔량1
- **저장 테이블**: `min_ticks`

## ⚙️ Crontab 설정

### 1. crontab 편집

```bash
crontab -e
```

### 2. Cron 작업 추가

#### 옵션 1: 장 중 1분마다 실행 (09:00-15:30)
```bash
# 1분마다 실시간 주식 데이터 수집 (장 시간: 09:00-15:30)
* 9-15 * * 1-5 cd /Users/wonny/Dev/joungwon.stocks && /Users/wonny/Dev/joungwon.stocks/venv/bin/python cron/1min.py >> /Users/wonny/Dev/joungwon.stocks/logs/1min.log 2>&1
```

#### 옵션 2: 분 단위로 세밀하게 제어
```bash
# 09:00-15:29는 매 분 실행
* 9-14 * * 1-5 cd /Users/wonny/Dev/joungwon.stocks && /Users/wonny/Dev/joungwon.stocks/venv/bin/python cron/1min.py >> /Users/wonny/Dev/joungwon.stocks/logs/1min.log 2>&1

# 15:00-15:30만 실행
0-30 15 * * 1-5 cd /Users/wonny/Dev/joungwon.stocks && /Users/wonny/Dev/joungwon.stocks/venv/bin/python cron/1min.py >> /Users/wonny/Dev/joungwon.stocks/logs/1min.log 2>&1
```

### 3. Crontab 형식 설명

```
* * * * * command
│ │ │ │ │
│ │ │ │ └─ 요일 (0-7, 0과 7은 일요일)
│ │ │ └─── 월 (1-12)
│ │ └───── 일 (1-31)
│ └─────── 시 (0-23)
└───────── 분 (0-59)
```

**예제**:
- `* 9-15 * * 1-5`: 월~금, 09:00-15:59, 매 분
- `*/5 * * * *`: 5분마다
- `0 9 * * 1-5`: 월~금, 09:00에 1회

### 4. 로그 디렉토리 생성

```bash
mkdir -p /Users/wonny/Dev/joungwon.stocks/logs
```

### 5. Crontab 설정 확인

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
python cron/1min.py
```

### 로그 확인

```bash
# 실시간 로그 모니터링
tail -f /Users/wonny/Dev/joungwon.stocks/logs/1min.log

# 최근 100줄 확인
tail -100 /Users/wonny/Dev/joungwon.stocks/logs/1min.log

# 오늘 날짜 로그만 필터링
grep "$(date +%Y-%m-%d)" /Users/wonny/Dev/joungwon.stocks/logs/1min.log
```

### 데이터베이스 확인

```bash
# PostgreSQL에 접속
psql -U wonny -d stock_investment_db

# 최근 수집 데이터 확인
SELECT
    stock_code,
    timestamp,
    price,
    volume,
    change_rate
FROM min_ticks
ORDER BY timestamp DESC
LIMIT 20;

# 특정 종목 데이터 확인
SELECT * FROM min_ticks
WHERE stock_code = '015760'
ORDER BY timestamp DESC
LIMIT 10;

# 오늘 수집된 데이터 건수
SELECT COUNT(*) FROM min_ticks
WHERE DATE(timestamp) = CURRENT_DATE;
```

## 🚨 주의사항

### 1. API 호출 제한
- Korea Investment Securities API는 **초당 20건** 제한이 있습니다
- 스크립트는 종목당 0.1초 대기하여 안전하게 처리합니다

### 2. 장 시간 확인
- 스크립트는 자동으로 장 시간(09:00-15:30)을 확인합니다
- 장 마감 시간에는 "장 마감 시간입니다" 메시지 출력 후 종료

### 3. API 키 설정
- `.env` 파일에 KIS API 키가 설정되어 있어야 합니다:
  ```bash
  KIS_APP_KEY=your_app_key
  KIS_APP_SECRET=your_app_secret
  ```

### 4. 로그 파일 관리
- 로그 파일이 계속 쌓이므로 주기적으로 정리 필요:
  ```bash
  # 7일 이상 된 로그 삭제
  find /Users/wonny/Dev/joungwon.stocks/logs -name "*.log" -mtime +7 -delete
  ```

## 📊 예상 데이터량

- 거래일 기준 6.5시간 (390분)
- 보유 종목 10개 가정
- 일일 수집 건수: 390 x 10 = **3,900건**
- 월간 수집 건수 (20거래일): 78,000건

## 🔧 트러블슈팅

### Cron이 실행되지 않는 경우

1. **경로 확인**
   ```bash
   which python  # Python 경로 확인
   pwd          # 현재 디렉토리 확인
   ```

2. **권한 확인**
   ```bash
   ls -la /Users/wonny/Dev/joungwon.stocks/cron/1min.py
   # -rwxr-xr-x 여야 함 (실행 권한)
   ```

3. **macOS Full Disk Access 권한**
   - 시스템 환경설정 > 보안 및 개인 정보 보호 > 전체 디스크 접근 권한
   - `/usr/sbin/cron` 추가

### API 에러 발생 시

```bash
# API 키 확인
grep KIS /Users/wonny/Dev/joungwon.stocks/.env

# 네트워크 연결 확인
ping -c 3 openapi.koreainvestment.com
```

### 데이터베이스 연결 에러

```bash
# PostgreSQL 실행 확인
pg_isready

# 연결 테스트
psql -U wonny -d stock_investment_db -c "SELECT 1"
```

## 📅 Cron 작업 중지/재개

### 중지
```bash
# crontab 편집
crontab -e

# 해당 라인 앞에 # 추가하여 주석 처리
# * 9-15 * * 1-5 cd /Users/wonny/Dev/joungwon.stocks && ...
```

### 삭제
```bash
# 모든 cron 작업 삭제 (주의!)
crontab -r

# 특정 작업만 삭제
crontab -e  # 편집기에서 해당 라인 삭제
```

## 🎯 다음 단계

1. **데이터 분석**: 수집된 `min_ticks` 데이터로 실시간 차트 생성
2. **알림 설정**: 급등/급락 시 알림 발송
3. **자동 매매**: 실시간 데이터 기반 자동 매매 로직 구현

---

**마지막 업데이트**: 2025-11-25
**작성자**: Claude Code Assistant
