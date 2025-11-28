"""
Windows Excel 보유종목 데이터를 stock_assets 테이블에 저장

Excel 파일은 한번 임포트 후 삭제되므로 모든 데이터를 DB에 저장해야 함.
"""
import asyncio
import sys
import pandas as pd
from datetime import datetime

sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')
from src.config.database import db

# Windows Excel 파일 경로
EXCEL_FILE = '/Users/wonny/Dev/joungwon.stocks.report/windows/da03450000.xls'

# 종목코드 매핑
STOCK_CODE_MAP = {
    '한국전력': '015760',
    '우리금융지주': '316140',
    '카카오': '035720',
    'HDC현대산업개발': '294870',
    '파라다이스': '034230',
    '한국카본': '017960',
    'HD현대에너지솔루션': '329180',
    '롯데쇼핑': '023530',
    '금양그린파워': '322310',
}


def parse_windows_excel(file_path):
    """Windows Excel 파일 파싱"""
    df = pd.read_excel(file_path, sheet_name=0, header=None)

    holdings = []

    # 행 11부터 보유종목 데이터 (2행씩)
    i = 11
    while i < len(df):
        try:
            stock_name = df.iloc[i, 0]

            if pd.isna(stock_name) or stock_name == '':
                break

            stock_name = str(stock_name).strip()

            # 종목코드 매핑
            stock_code = STOCK_CODE_MAP.get(stock_name)

            if not stock_code:
                print(f"⚠️  종목코드 매핑 없음: {stock_name}")
                i += 2
                continue

            holding = {
                'stock_code': stock_code,
                'stock_name': stock_name,
                'quantity': int(df.iloc[i, 8]),          # 보유수량
                'avg_buy_price': int(df.iloc[i, 12]),    # 평균매수가
                'current_price': int(df.iloc[i, 16]),    # 현재가
                'total_cost': int(df.iloc[i, 19]),       # 매수금액
                'total_value': int(df.iloc[i+1, 0]),     # 평가금액
                'profit_loss': int(df.iloc[i, 3]),       # 평가손익
            }

            holdings.append(holding)
            i += 2

        except Exception as e:
            print(f"⚠️  행 {i} 파싱 에러: {e}")
            i += 2

    return holdings


async def import_holdings_to_db(holdings):
    """보유종목 데이터를 stock_assets 테이블에 저장"""

    await db.connect()

    try:
        print("=" * 80)
        print("Windows Excel 보유종목 데이터베이스 임포트")
        print("=" * 80)
        print()

        imported_count = 0
        updated_count = 0

        for holding in holdings:
            stock_code = holding['stock_code']

            # 이미 존재하는지 확인
            check_query = 'SELECT stock_code FROM stock_assets WHERE stock_code = $1'
            existing = await db.fetchrow(check_query, stock_code)

            if existing:
                # UPDATE
                update_query = '''
                    UPDATE stock_assets
                    SET
                        stock_name = $2,
                        quantity = $3,
                        avg_buy_price = $4,
                        current_price = $5,
                        updated_at = NOW()
                    WHERE stock_code = $1
                '''
                await db.execute(
                    update_query,
                    stock_code,
                    holding['stock_name'],
                    holding['quantity'],
                    holding['avg_buy_price'],
                    holding['current_price']
                )
                updated_count += 1
                status = "업데이트"
            else:
                # INSERT
                insert_query = '''
                    INSERT INTO stock_assets (
                        stock_code, stock_name, quantity,
                        avg_buy_price, current_price,
                        is_active, created_at, updated_at
                    )
                    VALUES ($1, $2, $3, $4, $5, TRUE, NOW(), NOW())
                '''
                await db.execute(
                    insert_query,
                    stock_code,
                    holding['stock_name'],
                    holding['quantity'],
                    holding['avg_buy_price'],
                    holding['current_price']
                )
                imported_count += 1
                status = "추가"

            print(f"✅ {status}: {holding['stock_name']} ({stock_code})")
            print(f"   보유수량: {holding['quantity']:,}주")
            print(f"   평균매수가: {holding['avg_buy_price']:,}원")
            print(f"   현재가: {holding['current_price']:,}원")
            print(f"   손익: {holding['profit_loss']:,}원")
            print()

        print("=" * 80)
        print(f"✅ 임포트 완료: 신규 {imported_count}개, 업데이트 {updated_count}개")
        print("=" * 80)

    finally:
        await db.disconnect()


async def main():
    """메인 실행 함수"""
    print(f"📂 Excel 파일: {EXCEL_FILE}")
    print()

    # Excel 파일 파싱
    holdings = parse_windows_excel(EXCEL_FILE)

    print(f"📊 파싱 완료: {len(holdings)}개 종목")
    print()

    # 데이터베이스에 저장
    await import_holdings_to_db(holdings)


if __name__ == '__main__':
    asyncio.run(main())
