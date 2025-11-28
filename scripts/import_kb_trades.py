"""
KB증권 거래내역 엑셀 파일 파싱 및 DB 저장
"""
import asyncio
import sys
import pandas as pd
from datetime import datetime
from decimal import Decimal
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from src.config.database import db


class KBTradeParser:
    """KB증권 엑셀 파서"""

    def __init__(self, excel_path: str):
        self.excel_path = excel_path
        self.trades = []
        self.deposits = []
        self.withdrawals = []

    def parse(self):
        """엑셀 파일 파싱"""
        print(f"📂 파일 읽는 중: {self.excel_path}")

        # 헤더 없이 읽기
        df_raw = pd.read_excel(self.excel_path, sheet_name=0, header=None)

        print(f"📊 총 {len(df_raw)} 행 로드")
        print()

        # 데이터 파싱
        i = 2  # 헤더 2행 건너뛰기
        while i < len(df_raw):
            row = df_raw.iloc[i]

            # 거래일자가 있는 행만 처리
            if pd.notna(row[0]):
                trade_date = self._parse_date(row[0])
                trade_type = str(row[1]) if pd.notna(row[1]) else None

                if trade_type:
                    if '주식장내매수' in trade_type or '주식장내매도' in trade_type:
                        # 주식 거래
                        trade = self._parse_stock_trade(df_raw, i, trade_date, trade_type)
                        if trade:
                            self.trades.append(trade)

                    elif '입금' in trade_type:
                        # 입금
                        deposit = self._parse_deposit(row, trade_date, trade_type)
                        if deposit:
                            self.deposits.append(deposit)

            i += 1

        print(f"✅ 파싱 완료:")
        print(f"   - 주식 거래: {len(self.trades)}건")
        print(f"   - 입금: {len(self.deposits)}건")
        print()

        return self.trades, self.deposits

    def _parse_date(self, date_val):
        """날짜 파싱"""
        if isinstance(date_val, str):
            # '2025/11/03' 형식
            return datetime.strptime(date_val, '%Y/%m/%d').date()
        elif isinstance(date_val, pd.Timestamp):
            return date_val.date()
        else:
            return date_val

    def _parse_stock_trade(self, df_raw, idx, trade_date, trade_type):
        """주식 거래 파싱"""
        try:
            row_main = df_raw.iloc[idx]
            row_detail = df_raw.iloc[idx + 1]  # 다음 행에 종목명, 단가

            # 종목명
            stock_name = str(row_detail[1]).strip() if pd.notna(row_detail[1]) else None
            if not stock_name or stock_name == 'nan':
                return None

            # 종목코드는 나중에 매핑 (한국전력 → 015760)
            stock_code = self._map_stock_code(stock_name)

            # 데이터 추출
            quantity = int(row_main[2]) if pd.notna(row_main[2]) else 0
            unit_price = int(row_detail[2]) if pd.notna(row_detail[2]) else 0
            trade_amount = int(row_main[3]) if pd.notna(row_main[3]) else 0
            settlement_amount = int(row_main[4]) if pd.notna(row_main[4]) else 0

            # 수수료 = 거래금액 - 정산금액 (매수는 +, 매도는 -)
            if '매수' in trade_type:
                fee = settlement_amount - trade_amount
            else:  # 매도
                fee = trade_amount - settlement_amount

            return {
                'trade_date': trade_date,
                'trade_type': '매수' if '매수' in trade_type else '매도',
                'stock_code': stock_code,
                'stock_name': stock_name,
                'quantity': quantity,
                'unit_price': unit_price,
                'trade_amount': trade_amount,
                'settlement_amount': settlement_amount,
                'fee': fee,
                'tax': 0,  # 세금은 별도 계산 필요
            }

        except Exception as e:
            print(f"⚠️  파싱 오류 (행 {idx}): {e}")
            return None

    def _parse_deposit(self, row, trade_date, trade_type):
        """입금 파싱"""
        try:
            amount = int(row[3]) if pd.notna(row[3]) else 0

            return {
                'date': trade_date,
                'type': trade_type,
                'amount': amount,
            }
        except Exception as e:
            print(f"⚠️  입금 파싱 오류: {e}")
            return None

    def _map_stock_code(self, stock_name: str) -> str:
        """종목명 → 종목코드 매핑"""
        # 주요 종목 매핑
        mapping = {
            '한국전력': '015760',
            '삼성전자': '005930',
            'SK하이닉스': '000660',
            'NAVER': '035420',
            '카카오': '035720',
            'LG에너지솔루션': '373220',
            '현대차': '005380',
            '기아': '000270',
            'POSCO홀딩스': '005490',
            '삼성바이오로직스': '207940',
            # KB Securities 거래내역에서 발견된 추가 종목들
            'SK이노베이션': '096770',
            '삼성중공업': '010140',
            '우리금융지주': '316140',
            '한화솔루션': '009830',
            'SNT다이내믹스': '003570',
            'S-Oil': '010950',
            '한국카본': '017960',
            '파라다이스': '034230',
            'OCI홀딩스': '010060',
            '두산에너빌리티': '034020',
            '한화': '000880',
            '동국홀딩스': '001230',
            'HDC현대산업개발': '294870',
        }

        return mapping.get(stock_name, 'UNKNOWN')


async def save_to_database(trades, deposits):
    """DB에 저장"""

    print("💾 데이터베이스 저장 중...")
    print()

    await db.connect()

    try:
        # 1. 거래내역 저장
        print("1️⃣  거래내역 저장 (trade_history)")

        saved_count = 0
        skipped_count = 0

        for trade in trades:
            # 종목코드가 UNKNOWN이면 건너뛰기
            if trade['stock_code'] == 'UNKNOWN':
                print(f"   ⚠️  건너뜀: {trade['stock_name']} (종목코드 없음)")
                skipped_count += 1
                continue

            # 중복 체크 (같은 날짜, 종목, 수량, 금액)
            check_query = """
                SELECT id FROM trade_history
                WHERE trade_date = $1
                  AND stock_code = $2
                  AND quantity = $3
                  AND price = $4
                  AND trade_type = $5
                LIMIT 1
            """

            existing = await db.fetchrow(
                check_query,
                trade['trade_date'],
                trade['stock_code'],
                trade['quantity'],
                trade['unit_price'],
                trade['trade_type']
            )

            if existing:
                skipped_count += 1
                continue

            # 삽입 (total_amount는 자동 계산됨)
            insert_query = """
                INSERT INTO trade_history (
                    stock_code, trade_type, quantity, price,
                    trade_date, fee, tax,
                    gemini_reasoning, created_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, NOW()
                )
            """

            await db.execute(
                insert_query,
                trade['stock_code'],
                trade['trade_type'],
                trade['quantity'],
                trade['unit_price'],
                trade['trade_date'],
                trade['fee'],
                trade['tax'],
                f"KB증권 엑셀 자동 임포트 - {trade['stock_name']}"
            )

            saved_count += 1

        print(f"   ✅ 저장: {saved_count}건")
        print(f"   ⏭️  건너뜀: {skipped_count}건 (중복 또는 종목코드 없음)")
        print()

        # 2. 보유종목 계산 및 업데이트
        print("2️⃣  보유종목 계산 및 업데이트 (stock_assets)")

        # 종목별 집계
        stock_summary_query = """
            SELECT
                stock_code,
                SUM(CASE WHEN trade_type = '매수' THEN quantity ELSE 0 END) as total_buy_qty,
                SUM(CASE WHEN trade_type = '매도' THEN quantity ELSE 0 END) as total_sell_qty,
                SUM(CASE WHEN trade_type = '매수' THEN quantity * price ELSE 0 END) as total_buy_amount,
                SUM(CASE WHEN trade_type = '매도' THEN quantity * price ELSE 0 END) as total_sell_amount
            FROM trade_history
            WHERE stock_code != 'UNKNOWN'
            GROUP BY stock_code
            HAVING SUM(CASE WHEN trade_type = '매수' THEN quantity ELSE -quantity END) > 0
        """

        holdings = await db.fetch(stock_summary_query)

        for holding in holdings:
            stock_code = holding['stock_code']
            buy_qty = holding['total_buy_qty'] or 0
            sell_qty = holding['total_sell_qty'] or 0
            current_qty = buy_qty - sell_qty

            if current_qty <= 0:
                continue

            # 평균 매수가 계산
            buy_amount = holding['total_buy_amount'] or 0
            avg_price = int(buy_amount / buy_qty) if buy_qty > 0 else 0

            # 종목명 조회
            stock_name_query = "SELECT stock_name FROM stocks WHERE stock_code = $1"
            stock_info = await db.fetchrow(stock_name_query, stock_code)
            stock_name = stock_info['stock_name'] if stock_info else stock_code

            # stock_assets 업데이트 (UPSERT)
            upsert_query = """
                INSERT INTO stock_assets (
                    stock_code, stock_name, quantity, avg_buy_price
                )
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (stock_code)
                DO UPDATE SET
                    stock_name = $2,
                    quantity = $3,
                    avg_buy_price = $4,
                    updated_at = NOW()
            """

            await db.execute(upsert_query, stock_code, stock_name, current_qty, avg_price)

            print(f"   ✅ {stock_code}: {current_qty}주 (평균단가 {avg_price:,}원)")

        print()

        # 3. 예수금 계산 (입금 합계)
        print("3️⃣  예수금 계산")

        total_deposits = sum(d['amount'] for d in deposits)
        print(f"   총 입금: {total_deposits:,}원")

        # trade_history에서 매수/매도 금액 집계
        cash_query = """
            SELECT
                SUM(CASE WHEN trade_type = '매도' THEN total_amount ELSE 0 END) as total_sell,
                SUM(CASE WHEN trade_type = '매수' THEN total_amount ELSE 0 END) as total_buy
            FROM trade_history
        """

        cash_result = await db.fetchrow(cash_query)
        total_sell = cash_result['total_sell'] or 0
        total_buy = cash_result['total_buy'] or 0

        # 예수금 = 입금 + 매도 - 매수
        available_cash = total_deposits + total_sell - total_buy

        print(f"   매도 입금: +{total_sell:,}원")
        print(f"   매수 출금: -{total_buy:,}원")
        print(f"   💰 예수금: {available_cash:,}원")
        print()

        # 4. 최종 요약
        print("=" * 70)
        print("📊 최종 요약")
        print("=" * 70)

        holdings_count_query = """
            SELECT COUNT(*) as cnt
            FROM stock_assets
            WHERE quantity > 0
        """
        holdings_count = await db.fetchrow(holdings_count_query)

        print(f"보유 종목 수: {holdings_count['cnt']}개")
        print(f"예수금: {available_cash:,}원")
        print(f"거래 내역: {saved_count}건 저장")
        print()

    finally:
        await db.disconnect()


async def main():
    """메인 실행"""

    print("=" * 70)
    print("📥 KB증권 거래내역 임포트")
    print("=" * 70)
    print()

    # 파일 경로
    excel_path = 'download/1101-1124.xlsx'

    # 1. 파싱
    parser = KBTradeParser(excel_path)
    trades, deposits = parser.parse()

    # 2. DB 저장
    await save_to_database(trades, deposits)

    print("✅ 완료!")


if __name__ == '__main__':
    asyncio.run(main())
