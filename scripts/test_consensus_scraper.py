"""
Test Naver Finance consensus scraper
"""
import asyncio
import sys
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from scripts.naver.consensus_scraper import NaverConsensusScraper
from src.config.database import db

async def main():
    stock_code = "015760"  # 한국전력
    stock_name = "한국전력"

    print("=" * 80)
    print(f"{stock_name} 투자의견 컨센서스 스크래핑 테스트")
    print("=" * 80)

    # Connect to database
    await db.connect()

    # Step 1: Scrape and save consensus
    print(f"\n📊 Step 1: Naver Finance 컨센서스 스크래핑 및 저장...")
    scraper = NaverConsensusScraper()
    consensus = await scraper.fetch_and_save(stock_code)

    if consensus:
        print(f"\n✅ 컨센서스 데이터:")
        print(f"   투자의견 점수: {consensus['consensus_score']}/5.0")
        print(f"   매수: {consensus['buy_count']}명")
        print(f"   보유: {consensus['hold_count']}명")
        print(f"   매도: {consensus['sell_count']}명")
        print(f"   목표주가: {consensus['target_price']:,}원" if consensus['target_price'] else "   목표주가: -")
        print(f"   EPS: {consensus['eps']:,}원" if consensus['eps'] else "   EPS: -")
        print(f"   PER: {consensus['per']}배" if consensus['per'] else "   PER: -")
        print(f"   추정기관수: {consensus['analyst_count']}개" if consensus['analyst_count'] else "   추정기관수: -")
    else:
        print(f"   ⚠️  컨센서스 데이터 없음")

    # Step 2: Read from database
    print(f"\n📖 Step 2: 데이터베이스에서 읽기...")
    db_consensus = await NaverConsensusScraper.get_from_db(stock_code)

    if db_consensus:
        print(f"✅ DB에서 읽은 컨센서스 데이터:")
        print(f"   투자의견 점수: {db_consensus['consensus_score']}/5.0")
        print(f"   매수: {db_consensus['buy_count']}명")
        print(f"   보유: {db_consensus['hold_count']}명")
        print(f"   매도: {db_consensus['sell_count']}명")
        print(f"   데이터 기준일: {db_consensus['data_date']}")
    else:
        print(f"⚠️  DB에 데이터 없음")

    # Disconnect
    await db.disconnect()

    print(f"\n✅ 테스트 완료!")

if __name__ == '__main__':
    asyncio.run(main())
