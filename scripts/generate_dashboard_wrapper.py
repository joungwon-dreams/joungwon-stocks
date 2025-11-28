#!/usr/bin/env python3
"""
Dashboard PDF 생성 래퍼 스크립트
5분마다 실행되어 대시보드를 업데이트
"""
import subprocess
import sys
from pathlib import Path
from datetime import datetime

def main():
    """Dashboard PDF 생성 실행"""
    print(f"\n{'='*60}")
    print(f"📊 Dashboard PDF 생성 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    try:
        # generate_dashboard.py 실행
        result = subprocess.run(
            [
                '/Users/wonny/Dev/joungwon.stocks/venv/bin/python',
                '/Users/wonny/Dev/joungwon.stocks/scripts/gemini/generate_dashboard.py'
            ],
            capture_output=True,
            text=True,
            timeout=60  # 1분 타임아웃
        )

        if result.returncode == 0:
            print("✅ Dashboard PDF 생성 성공")
            print(result.stdout)
        else:
            print("❌ Dashboard PDF 생성 실패")
            print(result.stderr)
            sys.exit(1)

    except subprocess.TimeoutExpired:
        print("⏱️  Dashboard PDF 생성 시간 초과 (1분)")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Dashboard PDF 생성 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
