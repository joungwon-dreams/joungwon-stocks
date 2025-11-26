import asyncio
import sys
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')
from src.config.database import db

async def check_all_data():
    await db.connect()

    print('=' * 80)
    print('📊 추가 수집 필요 데이터 분석 (한국전력 015760)')
    print('=' * 80)
    print()

    # === 1. Peer 재무데이터 ===
    print('🔍 1. Peer 종목 재무데이터')
    print('-' * 80)
    peers = await db.fetch('SELECT peer_code, peer_name FROM stock_peers WHERE stock_code = $1', '015760')
    print(f'Peer 종목: {len(peers)}개')
    for p in peers:
        print(f'  - {p["peer_code"]}: {p["peer_name"]}')
    print()

    missing_peer_data = []
    for p in peers:
        # Fundamentals 체크
        fund = await db.fetchrow('SELECT per, pbr, roe FROM stock_fundamentals WHERE stock_code = $1', p['peer_code'])
        # Financials 체크
        fin = await db.fetchrow('''
            SELECT fiscal_year, revenue, total_assets
            FROM stock_financials
            WHERE stock_code = $1 AND period_type = 'yearly'
            ORDER BY fiscal_year DESC LIMIT 1
        ''', p['peer_code'])

        if not fund and not fin:
            missing_peer_data.append({
                'code': p['peer_code'],
                'name': p['peer_name'],
                'need_fundamentals': True,
                'need_financials': True
            })
        elif not fund:
            missing_peer_data.append({
                'code': p['peer_code'],
                'name': p['peer_name'],
                'need_fundamentals': True,
                'need_financials': False
            })
        elif not fin:
            missing_peer_data.append({
                'code': p['peer_code'],
                'name': p['peer_name'],
                'need_fundamentals': False,
                'need_financials': True
            })

    if missing_peer_data:
        print('❌ 수집 필요:')
        for item in missing_peer_data:
            needs = []
            if item['need_fundamentals']:
                needs.append('Fundamentals(PER/PBR/ROE)')
            if item['need_financials']:
                needs.append('Financials(매출/자산)')
            print(f'   - {item["code"]} ({item["name"]}): {", ".join(needs)}')
    else:
        print('✅ 모든 Peer 재무데이터 수집 완료')
    print()

    # === 2. 컨센서스 상세 ===
    print('🔍 2. 컨센서스 상세 데이터')
    print('-' * 80)
    cons = await db.fetchrow('''
        SELECT target_price, opinion, eps_consensus, per_consensus, target_high, target_low
        FROM stock_consensus WHERE stock_code = $1
    ''', '015760')

    missing_consensus = []
    if cons:
        if not cons['eps_consensus']:
            missing_consensus.append('EPS 컨센서스')
        if not cons['per_consensus']:
            missing_consensus.append('PER 컨센서스')
        if not cons['target_high']:
            missing_consensus.append('목표가 상단')
        if not cons['target_low']:
            missing_consensus.append('목표가 하단')

    if missing_consensus:
        print('❌ 수집 필요:')
        for item in missing_consensus:
            print(f'   - {item}')
        print()
        print('📝 수집 방법: NaverConsensusFetcher.fetch_consensus_detail() 수정 필요')
        print('   - API 응답 확인 후 올바른 필드명 매핑')
    else:
        print('✅ 컨센서스 상세 데이터 수집 완료')
    print()

    # === 3. 증권사 목표가 ===
    print('🔍 3. 증권사 목표가 데이터')
    print('-' * 80)
    reports_with_target = await db.fetchval('''
        SELECT COUNT(*) FROM analyst_target_prices
        WHERE stock_code = $1 AND target_price > 0
    ''', '015760')
    reports_total = await db.fetchval('''
        SELECT COUNT(*) FROM analyst_target_prices WHERE stock_code = $1
    ''', '015760')

    print(f'총 리포트: {reports_total}건')
    print(f'목표가 있는 리포트: {reports_with_target}건')

    if reports_with_target == 0:
        print()
        print('❌ 수집 필요: 모든 리포트의 target_price가 0원')
        print()
        print('📝 수집 방법 옵션:')
        print('   1. DaumReportsFetcher 재시도 (권장)')
        print('      - User-Agent 로테이션')
        print('      - 타임아웃/재시도 로직')
        print('   2. 대체 소스 추가')
        print('      - 38커뮤니케이션즈 API')
        print('      - 네이버 증권 HTML 파싱')
    else:
        print(f'✅ {reports_with_target}개 리포트에 목표가 데이터 있음')
    print()

    # === 4. 52주 최고/최저 ===
    print('🔍 4. 52주 최고/최저 (OHLCV)')
    print('-' * 80)
    fund = await db.fetchrow('SELECT week52_high, week52_low FROM stock_fundamentals WHERE stock_code = $1', '015760')
    if fund and fund['week52_high'] and fund['week52_low']:
        print(f'✅ 52주 최고: {fund["week52_high"]:,}원')
        print(f'✅ 52주 최저: {fund["week52_low"]:,}원')
    else:
        ohlcv_count = await db.fetchval('SELECT COUNT(*) FROM daily_ohlcv WHERE stock_code = $1', '015760')
        if ohlcv_count >= 252:
            print(f'✅ OHLCV 데이터 {ohlcv_count}일 - 계산 가능')
        else:
            print(f'❌ OHLCV 데이터 부족: {ohlcv_count}일 (필요: 252일)')
    print()

    # === 요약 ===
    print('=' * 80)
    print('📋 수집 필요 데이터 요약')
    print('=' * 80)
    print()

    print('1️⃣  Peer 종목 재무데이터 (필수) ⭐⭐⭐')
    if missing_peer_data:
        print(f'   ❌ {len(missing_peer_data)}개 종목 데이터 없음')
        print('   📌 수집 대상:')
        for item in missing_peer_data:
            print(f'      - {item["code"]}: {item["name"]}')
    else:
        print('   ✅ 완료')
    print()

    print('2️⃣  컨센서스 상세 (EPS/PER/목표가 상하단) ⭐⭐⭐')
    if missing_consensus:
        print(f'   ❌ {len(missing_consensus)}개 필드 없음')
        print('   📌 수집 대상:', ', '.join(missing_consensus))
    else:
        print('   ✅ 완료')
    print()

    print('3️⃣  증권사 목표가 ⭐⭐')
    if reports_with_target == 0:
        print('   ❌ 모든 리포트 목표가 0원')
        print('   📌 DaumReportsFetcher 수정 또는 대체 소스 필요')
    else:
        print('   ✅ 완료')
    print()

    await db.disconnect()

asyncio.run(check_all_data())
