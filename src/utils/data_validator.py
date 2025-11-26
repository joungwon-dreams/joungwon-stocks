"""
Data Validation and Missing Data Tracker
PDF 생성 시 누락된 데이터를 감지하고 재시도 큐에 추가
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import json
from pathlib import Path


@dataclass
class MissingDataInfo:
    """누락된 데이터 정보"""
    stock_code: str
    stock_name: str
    data_type: str  # 'financial', 'consensus', 'peers', 'metrics'
    field_name: str  # 'PER', 'ROE', 'revenue', etc.
    fetcher_name: str  # 'DaumFinancialsFetcher', 'NaverConsensusFetcher'
    detected_at: str
    retry_count: int = 0
    last_retry_at: Optional[str] = None
    status: str = 'pending'  # 'pending', 'retrying', 'failed', 'resolved'


class DataValidator:
    """데이터 검증 및 누락 추적"""

    def __init__(self, log_dir: str = "/Users/wonny/Dev/joungwon.stocks/logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.missing_data_log = self.log_dir / "missing_data.jsonl"

    def validate_realtime_data(self, stock_code: str, stock_name: str, data: Dict) -> List[MissingDataInfo]:
        """실시간 데이터 검증"""
        missing = []
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Daum 데이터 검증
        daum = data.get('daum', {})

        # 1. Quote 데이터 검증
        quotes = daum.get('quotes', {})
        if not quotes or not isinstance(quotes, dict):
            missing.append(MissingDataInfo(
                stock_code=stock_code,
                stock_name=stock_name,
                data_type='quote',
                field_name='quotes',
                fetcher_name='DaumPriceFetcher',
                detected_at=now
            ))

        # 2. Financial Ratios 검증
        financials = daum.get('financials', {})
        required_metrics = ['PER', 'PBR', 'ROE', 'market_cap', 'dividend_yield']

        for metric in required_metrics:
            value = financials.get(metric)
            if value is None or value == 0 or value == '0' or value == '':
                missing.append(MissingDataInfo(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    data_type='financial_metrics',
                    field_name=metric,
                    fetcher_name='DaumFinancialsFetcher',
                    detected_at=now
                ))

        # 3. Peer 비교 검증
        peers = daum.get('peers', [])
        if not peers or len(peers) == 0:
            missing.append(MissingDataInfo(
                stock_code=stock_code,
                stock_name=stock_name,
                data_type='peers',
                field_name='peer_companies',
                fetcher_name='DaumFinancialsFetcher',
                detected_at=now
            ))

        # 4. Naver 컨센서스 검증
        naver = data.get('naver', {})
        consensus = naver.get('consensus', {})

        if not consensus or not isinstance(consensus, dict):
            missing.append(MissingDataInfo(
                stock_code=stock_code,
                stock_name=stock_name,
                data_type='consensus',
                field_name='consensus_data',
                fetcher_name='NaverConsensusFetcher',
                detected_at=now
            ))
        else:
            # 목표가, 투자의견 개수 확인
            target_price = consensus.get('target_price')
            opinions = consensus.get('opinions', [])

            if not target_price or target_price == 0:
                missing.append(MissingDataInfo(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    data_type='consensus',
                    field_name='target_price',
                    fetcher_name='NaverConsensusFetcher',
                    detected_at=now
                ))

            if not opinions or len(opinions) == 0:
                missing.append(MissingDataInfo(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    data_type='consensus',
                    field_name='analyst_opinions',
                    fetcher_name='NaverConsensusFetcher',
                    detected_at=now
                ))

        return missing

    def validate_historical_data(self, stock_code: str, stock_name: str,
                                history_data: List[Dict]) -> List[MissingDataInfo]:
        """과거 데이터 검증"""
        missing = []
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if not history_data or len(history_data) == 0:
            missing.append(MissingDataInfo(
                stock_code=stock_code,
                stock_name=stock_name,
                data_type='historical',
                field_name='ohlcv_data',
                fetcher_name='DaumPriceFetcher',
                detected_at=now
            ))
        elif len(history_data) < 120:  # 최소 6개월 데이터 필요
            missing.append(MissingDataInfo(
                stock_code=stock_code,
                stock_name=stock_name,
                data_type='historical',
                field_name='insufficient_history',
                fetcher_name='DaumPriceFetcher',
                detected_at=now
            ))

        return missing

    def validate_investor_data(self, stock_code: str, stock_name: str,
                              investor_data: List[Dict]) -> List[MissingDataInfo]:
        """수급 데이터 검증"""
        missing = []
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if not investor_data or len(investor_data) == 0:
            missing.append(MissingDataInfo(
                stock_code=stock_code,
                stock_name=stock_name,
                data_type='investor',
                field_name='investor_trends',
                fetcher_name='DaumSupplyFetcher',
                detected_at=now
            ))
        elif len(investor_data) < 30:  # 최소 30일 데이터 필요
            missing.append(MissingDataInfo(
                stock_code=stock_code,
                stock_name=stock_name,
                data_type='investor',
                field_name='insufficient_investor_data',
                fetcher_name='DaumSupplyFetcher',
                detected_at=now
            ))

        return missing

    def validate_news_data(self, stock_code: str, stock_name: str,
                          news_data: List[Dict]) -> List[MissingDataInfo]:
        """뉴스 데이터 검증"""
        missing = []
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if not news_data or len(news_data) == 0:
            missing.append(MissingDataInfo(
                stock_code=stock_code,
                stock_name=stock_name,
                data_type='news',
                field_name='news_articles',
                fetcher_name='NaverNewsFetcher',
                detected_at=now
            ))

        return missing

    def log_missing_data(self, missing_list: List[MissingDataInfo]):
        """누락 데이터 로그 저장 (JSONL 형식)"""
        if not missing_list:
            return

        with open(self.missing_data_log, 'a', encoding='utf-8') as f:
            for item in missing_list:
                f.write(json.dumps(asdict(item), ensure_ascii=False) + '\n')

    def get_pending_retries(self, max_retry: int = 3) -> List[MissingDataInfo]:
        """재시도 대기 중인 항목 조회"""
        if not self.missing_data_log.exists():
            return []

        pending = []
        with open(self.missing_data_log, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line.strip())
                item = MissingDataInfo(**data)

                # 재시도 횟수 제한 내에서 pending 상태인 항목만
                if item.status == 'pending' and item.retry_count < max_retry:
                    pending.append(item)

        return pending

    def update_retry_status(self, stock_code: str, data_type: str,
                           field_name: str, new_status: str):
        """재시도 상태 업데이트"""
        if not self.missing_data_log.exists():
            return

        updated_lines = []
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        with open(self.missing_data_log, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line.strip())

                # 매칭되는 항목 업데이트
                if (data['stock_code'] == stock_code and
                    data['data_type'] == data_type and
                    data['field_name'] == field_name):
                    data['status'] = new_status
                    data['retry_count'] += 1
                    data['last_retry_at'] = now

                updated_lines.append(json.dumps(data, ensure_ascii=False) + '\n')

        # 파일 덮어쓰기
        with open(self.missing_data_log, 'w', encoding='utf-8') as f:
            f.writelines(updated_lines)

    def get_missing_summary(self) -> Dict[str, Any]:
        """누락 데이터 요약 통계"""
        if not self.missing_data_log.exists():
            return {
                'total': 0,
                'by_type': {},
                'by_fetcher': {},
                'by_status': {}
            }

        by_type = {}
        by_fetcher = {}
        by_status = {}
        total = 0

        with open(self.missing_data_log, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line.strip())
                total += 1

                # 타입별 집계
                dtype = data['data_type']
                by_type[dtype] = by_type.get(dtype, 0) + 1

                # Fetcher별 집계
                fetcher = data['fetcher_name']
                by_fetcher[fetcher] = by_fetcher.get(fetcher, 0) + 1

                # 상태별 집계
                status = data['status']
                by_status[status] = by_status.get(status, 0) + 1

        return {
            'total': total,
            'by_type': by_type,
            'by_fetcher': by_fetcher,
            'by_status': by_status
        }


def validate_and_log_missing_data(stock_code: str, stock_name: str,
                                  realtime_data: Dict,
                                  history_data: List[Dict],
                                  investor_data: List[Dict],
                                  news_data: List[Dict]) -> List[MissingDataInfo]:
    """
    모든 데이터 검증 및 누락 로그 저장

    Returns:
        List[MissingDataInfo]: 누락된 데이터 목록
    """
    validator = DataValidator()

    all_missing = []

    # 각 데이터 소스별 검증
    all_missing.extend(validator.validate_realtime_data(stock_code, stock_name, realtime_data))
    all_missing.extend(validator.validate_historical_data(stock_code, stock_name, history_data))
    all_missing.extend(validator.validate_investor_data(stock_code, stock_name, investor_data))
    all_missing.extend(validator.validate_news_data(stock_code, stock_name, news_data))

    # 로그 저장
    if all_missing:
        validator.log_missing_data(all_missing)
        print(f"⚠️  {stock_name}({stock_code}): {len(all_missing)}개 데이터 누락 감지")

        # 타입별 요약
        by_type = {}
        for item in all_missing:
            by_type[item.data_type] = by_type.get(item.data_type, 0) + 1

        for dtype, count in by_type.items():
            print(f"   - {dtype}: {count}개")

    return all_missing
