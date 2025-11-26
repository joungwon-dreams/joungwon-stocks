"""
Data Retry Manager
누락된 데이터 재수집 로직
"""
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

from src.utils.data_validator import DataValidator, MissingDataInfo


class DataRetryManager:
    """데이터 재시도 매니저"""

    def __init__(self):
        self.validator = DataValidator()

    async def retry_missing_data(self, stock_code: str, stock_name: str,
                                 missing_items: List[MissingDataInfo]) -> Dict:
        """
        누락된 데이터 재수집

        Returns:
            Dict: {
                'realtime_data': {...},
                'history_data': [...],
                'investor_data': [...],
                'news_data': [...]
            }
        """
        print(f"\n🔄 {stock_name}({stock_code}) 누락 데이터 재수집 시작...")

        # Fetcher별 재시도 그룹핑
        retry_groups = self._group_by_fetcher(missing_items)

        # 재수집된 데이터 저장
        retried_data = {
            'realtime_data': {'daum': {}, 'naver': {}},
            'history_data': [],
            'investor_data': [],
            'news_data': []
        }

        # Fetcher별 재수집 실행
        for fetcher_name, items in retry_groups.items():
            print(f"   🔧 {fetcher_name} 재시도 ({len(items)}개 항목)")

            if fetcher_name == 'DaumPriceFetcher':
                data = await self._retry_daum_price(stock_code, items)
                retried_data['realtime_data']['daum'].update(data.get('quotes', {}))
                if data.get('history'):
                    retried_data['history_data'] = data['history']

            elif fetcher_name == 'DaumFinancialsFetcher':
                data = await self._retry_daum_financials(stock_code, items)
                retried_data['realtime_data']['daum']['financials'] = data.get('ratios', {})
                retried_data['realtime_data']['daum']['peers'] = data.get('peers', [])

            elif fetcher_name == 'DaumSupplyFetcher':
                data = await self._retry_daum_supply(stock_code, items)
                if data:
                    retried_data['investor_data'] = data

            elif fetcher_name == 'NaverConsensusFetcher':
                data = await self._retry_naver_consensus(stock_code, items)
                retried_data['realtime_data']['naver']['consensus'] = data

            elif fetcher_name == 'NaverNewsFetcher':
                data = await self._retry_naver_news(stock_code, items)
                if data:
                    retried_data['news_data'] = data

            # 재시도 상태 업데이트
            for item in items:
                self.validator.update_retry_status(
                    stock_code, item.data_type, item.field_name, 'retrying'
                )

        print(f"✅ {stock_name}({stock_code}) 재수집 완료")
        return retried_data

    def _group_by_fetcher(self, missing_items: List[MissingDataInfo]) -> Dict[str, List[MissingDataInfo]]:
        """Fetcher별 그룹핑"""
        groups = {}
        for item in missing_items:
            fetcher = item.fetcher_name
            if fetcher not in groups:
                groups[fetcher] = []
            groups[fetcher].append(item)
        return groups

    async def _retry_daum_price(self, stock_code: str, items: List[MissingDataInfo]) -> Dict:
        """Daum 가격 데이터 재수집"""
        try:
            from scripts.gemini.daum.price import DaumPriceFetcher

            fetcher = DaumPriceFetcher()

            result = {}

            # Quote 데이터 필요 시
            if any(item.field_name == 'quotes' for item in items):
                quotes = await fetcher.fetch_quote(stock_code)
                if quotes:
                    result['quotes'] = quotes
                    print(f"      ✓ Quote 데이터 수집 성공")

            # Historical 데이터 필요 시
            if any(item.data_type == 'historical' for item in items):
                history = await fetcher.fetch_history(stock_code, 365)
                if history:
                    result['history'] = history
                    print(f"      ✓ 과거 데이터 수집 성공 ({len(history)}일)")

            return result

        except Exception as e:
            print(f"      ✗ DaumPriceFetcher 오류: {e}")
            return {}

    async def _retry_daum_financials(self, stock_code: str, items: List[MissingDataInfo]) -> Dict:
        """Daum 재무 데이터 재수집"""
        try:
            from scripts.gemini.daum.financials import DaumFinancialsFetcher

            fetcher = DaumFinancialsFetcher()
            data = await fetcher.fetch_ratios(stock_code)

            if data:
                print(f"      ✓ 재무 지표 수집 성공")
                if data.get('peers'):
                    print(f"      ✓ 동종업계 {len(data['peers'])}개 기업 수집 성공")

            return data

        except Exception as e:
            print(f"      ✗ DaumFinancialsFetcher 오류: {e}")
            return {}

    async def _retry_daum_supply(self, stock_code: str, items: List[MissingDataInfo]) -> List[Dict]:
        """Daum 수급 데이터 재수집"""
        try:
            from scripts.gemini.daum.supply import DaumSupplyFetcher

            fetcher = DaumSupplyFetcher()
            data = await fetcher.fetch_history(stock_code, 365)

            if data:
                print(f"      ✓ 수급 데이터 수집 성공 ({len(data)}일)")

            return data

        except Exception as e:
            print(f"      ✗ DaumSupplyFetcher 오류: {e}")
            return []

    async def _retry_naver_consensus(self, stock_code: str, items: List[MissingDataInfo]) -> Dict:
        """Naver 컨센서스 재수집"""
        try:
            from scripts.gemini.naver.consensus import NaverConsensusFetcher

            fetcher = NaverConsensusFetcher()
            data = await fetcher.fetch_consensus(stock_code)

            if data:
                target_price = data.get('target_price', 0)
                opinions = data.get('opinions', [])
                print(f"      ✓ 컨센서스 수집 성공 (목표가: {target_price:,}원, {len(opinions)}개 의견)")

            return data

        except Exception as e:
            print(f"      ✗ NaverConsensusFetcher 오류: {e}")
            return {}

    async def _retry_naver_news(self, stock_code: str, items: List[MissingDataInfo]) -> List[Dict]:
        """Naver 뉴스 재수집"""
        try:
            from scripts.gemini.naver.news import NaverNewsFetcher

            fetcher = NaverNewsFetcher()
            data = await fetcher.fetch_news(stock_code)

            if data:
                print(f"      ✓ 뉴스 수집 성공 ({len(data)}개)")

            return data

        except Exception as e:
            print(f"      ✗ NaverNewsFetcher 오류: {e}")
            return []

    async def process_pending_retries(self, max_retry: int = 3):
        """대기 중인 재시도 작업 일괄 처리"""
        pending = self.validator.get_pending_retries(max_retry)

        if not pending:
            print("📭 재시도 대기 중인 항목 없음")
            return

        print(f"\n📋 재시도 대기 항목: {len(pending)}개")

        # 종목별 그룹핑
        by_stock = {}
        for item in pending:
            key = (item.stock_code, item.stock_name)
            if key not in by_stock:
                by_stock[key] = []
            by_stock[key].append(item)

        # 종목별 재시도 실행
        for (stock_code, stock_name), items in by_stock.items():
            print(f"\n🔄 {stock_name}({stock_code}): {len(items)}개 항목 재시도")

            retried_data = await self.retry_missing_data(stock_code, stock_name, items)

            # 재검증
            all_missing = []

            if retried_data['realtime_data']:
                missing = self.validator.validate_realtime_data(
                    stock_code, stock_name, retried_data['realtime_data']
                )
                all_missing.extend(missing)

            if retried_data['history_data']:
                missing = self.validator.validate_historical_data(
                    stock_code, stock_name, retried_data['history_data']
                )
                all_missing.extend(missing)

            if retried_data['investor_data']:
                missing = self.validator.validate_investor_data(
                    stock_code, stock_name, retried_data['investor_data']
                )
                all_missing.extend(missing)

            if retried_data['news_data']:
                missing = self.validator.validate_news_data(
                    stock_code, stock_name, retried_data['news_data']
                )
                all_missing.extend(missing)

            # 상태 업데이트
            for item in items:
                if any(m.field_name == item.field_name for m in all_missing):
                    # 여전히 누락됨
                    status = 'failed' if item.retry_count >= max_retry - 1 else 'pending'
                else:
                    # 해결됨
                    status = 'resolved'

                self.validator.update_retry_status(
                    stock_code, item.data_type, item.field_name, status
                )

            print(f"✅ {stock_name}({stock_code}) 재시도 완료")


async def main():
    """재시도 매니저 실행 (독립 스크립트)"""
    manager = DataRetryManager()
    await manager.process_pending_retries(max_retry=3)

    # 통계 출력
    summary = manager.validator.get_missing_summary()
    print(f"\n📊 누락 데이터 통계:")
    print(f"   전체: {summary['total']}개")
    print(f"\n   타입별:")
    for dtype, count in summary['by_type'].items():
        print(f"      - {dtype}: {count}개")
    print(f"\n   상태별:")
    for status, count in summary['by_status'].items():
        print(f"      - {status}: {count}개")


if __name__ == '__main__':
    asyncio.run(main())
