"""
FnGuide Playwright Fetcher
Tier 4 - Browser Automation

Fetches:
- 재무제표 (Financial Statements)
- 애널리스트 컨센서스 (Analyst Consensus)
- 투자의견 (Investment Opinion)
- 목표주가 (Target Price)
"""
from typing import Dict, Any, Optional, List
import re
from datetime import datetime

from .base_playwright_fetcher import BasePlaywrightFetcher


class FnGuidePlaywrightFetcher(BasePlaywrightFetcher):
    """
    FnGuide fetcher using Playwright for dynamic content.

    Target URL: https://comp.fnguide.com/SVO2/ASP/SVD_Main.asp?pGB=1&gicode=A{ticker}
    """

    BASE_URL = "https://comp.fnguide.com/SVO2/ASP/SVD_Main.asp"

    def __init__(self, site_id: int, config: Dict[str, Any]):
        super().__init__(site_id, config)
        self.config['data_type'] = 'fnguide_analysis'

    def build_url(self, ticker: str) -> str:
        """Build FnGuide URL for ticker"""
        return f"{self.BASE_URL}?pGB=1&gicode=A{ticker}"

    async def fetch_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch FnGuide data for ticker.

        Args:
            ticker: Stock ticker code

        Returns:
            Parsed data dictionary or None
        """
        url = self.build_url(ticker)

        # Navigate to page
        success = await self.navigate_to(url, wait_until='networkidle')
        if not success:
            return None

        # Wait for main content to load
        await self.wait_for_selector('#div_summary', timeout=10000)

        # Parse data
        data = await self.parse_data(ticker)

        return data

    async def parse_data(self, ticker: str) -> Dict[str, Any]:
        """
        Parse FnGuide data from current page.

        Args:
            ticker: Stock ticker code

        Returns:
            Parsed data dictionary
        """
        data = {
            'ticker': ticker,
            'source': 'fnguide',
            'crawled_at': datetime.now().isoformat(),
            'company_info': await self.parse_company_info(),
            'financial_summary': await self.parse_financial_summary(),
            'analyst_consensus': await self.parse_analyst_consensus(),
            'valuation_metrics': await self.parse_valuation_metrics()
        }

        self.logger.info(
            f"FnGuide data parsed for {ticker}: "
            f"company={bool(data['company_info'])}, "
            f"financials={bool(data['financial_summary'])}, "
            f"consensus={bool(data['analyst_consensus'])}"
        )

        return data

    async def parse_company_info(self) -> Dict[str, Any]:
        """Parse company basic information"""
        info = {}

        try:
            # Company name
            name_elem = await self.page.query_selector('#giName')
            if name_elem:
                info['company_name'] = (await name_elem.text_content()).strip()

            # Industry
            industry_elem = await self.page.query_selector('#bizSummary td')
            if industry_elem:
                info['industry'] = (await industry_elem.text_content()).strip()

            # CEO
            ceo_selector = 'dt:has-text("대표이사") + dd'
            ceo_text = await self.get_text_content(ceo_selector)
            if ceo_text:
                info['ceo'] = ceo_text.strip()

            # Market cap
            market_cap_selector = '#corp_group2 > dl:nth-child(1) > dd'
            market_cap_text = await self.get_text_content(market_cap_selector)
            if market_cap_text:
                info['market_cap'] = market_cap_text.strip()

        except Exception as e:
            self.logger.warning(f"Error parsing company info: {e}")

        return info

    async def parse_financial_summary(self) -> Dict[str, Any]:
        """Parse financial summary (최근 4개년)"""
        financials = {
            'years': [],
            'revenue': [],
            'operating_profit': [],
            'net_profit': [],
            'eps': [],
            'per': [],
            'pbr': [],
            'roe': []
        }

        try:
            # 주요 재무 정보 테이블
            table_selector = '#highlight_D_Y'

            # 연도
            year_cells = await self.page.query_selector_all(f'{table_selector} thead th')
            for cell in year_cells[1:]:  # Skip first header
                year_text = await cell.text_content()
                if year_text and year_text.strip():
                    financials['years'].append(year_text.strip())

            # 매출액
            revenue_row = await self.page.query_selector(f'{table_selector} tr:has-text("매출액")')
            if revenue_row:
                cells = await revenue_row.query_selector_all('td')
                for cell in cells:
                    text = await cell.text_content()
                    financials['revenue'].append(self.clean_number(text))

            # 영업이익
            op_profit_row = await self.page.query_selector(f'{table_selector} tr:has-text("영업이익")')
            if op_profit_row:
                cells = await op_profit_row.query_selector_all('td')
                for cell in cells:
                    text = await cell.text_content()
                    financials['operating_profit'].append(self.clean_number(text))

            # 당기순이익
            net_profit_row = await self.page.query_selector(f'{table_selector} tr:has-text("당기순이익")')
            if net_profit_row:
                cells = await net_profit_row.query_selector_all('td')
                for cell in cells:
                    text = await cell.text_content()
                    financials['net_profit'].append(self.clean_number(text))

            # EPS (주당순이익)
            eps_row = await self.page.query_selector(f'{table_selector} tr:has-text("EPS")')
            if eps_row:
                cells = await eps_row.query_selector_all('td')
                for cell in cells:
                    text = await cell.text_content()
                    financials['eps'].append(self.clean_number(text))

            # PER
            per_row = await self.page.query_selector(f'{table_selector} tr:has-text("PER")')
            if per_row:
                cells = await per_row.query_selector_all('td')
                for cell in cells:
                    text = await cell.text_content()
                    financials['per'].append(self.clean_number(text))

            # ROE
            roe_row = await self.page.query_selector(f'{table_selector} tr:has-text("ROE")')
            if roe_row:
                cells = await roe_row.query_selector_all('td')
                for cell in cells:
                    text = await cell.text_content()
                    financials['roe'].append(self.clean_number(text))

        except Exception as e:
            self.logger.warning(f"Error parsing financial summary: {e}")

        return financials

    async def parse_analyst_consensus(self) -> Dict[str, Any]:
        """Parse analyst consensus (증권사 투자의견)"""
        consensus = {
            'target_price': None,
            'opinion': None,
            'analyst_count': None,
            'opinions_breakdown': {
                'buy': 0,
                'hold': 0,
                'sell': 0
            }
        }

        try:
            # 목표주가
            target_price_selector = '#svdMainGrid1 > table > tbody > tr:nth-child(3) > td'
            target_price_text = await self.get_text_content(target_price_selector)
            if target_price_text:
                consensus['target_price'] = self.clean_number(target_price_text)

            # 투자의견 (매수/보유/매도 비율)
            opinion_selector = '#svdMainGrid1 > table > tbody > tr:nth-child(4) > td'
            opinion_text = await self.get_text_content(opinion_selector)
            if opinion_text:
                consensus['opinion'] = opinion_text.strip()

            # 애널리스트 수
            analyst_count_selector = '#svdMainGrid1 > table > tbody > tr:nth-child(1) > td'
            analyst_count_text = await self.get_text_content(analyst_count_selector)
            if analyst_count_text:
                match = re.search(r'(\d+)', analyst_count_text)
                if match:
                    consensus['analyst_count'] = int(match.group(1))

            # 의견 분포 (매수/보유/매도)
            # FnGuide 페이지 구조에 따라 다를 수 있음
            buy_count_selector = '#svdMainGrid1 > table > tbody > tr:has-text("매수") > td'
            buy_text = await self.get_text_content(buy_count_selector)
            if buy_text:
                match = re.search(r'(\d+)', buy_text)
                if match:
                    consensus['opinions_breakdown']['buy'] = int(match.group(1))

        except Exception as e:
            self.logger.warning(f"Error parsing analyst consensus: {e}")

        return consensus

    async def parse_valuation_metrics(self) -> Dict[str, Any]:
        """Parse valuation metrics (PER, PBR, etc.)"""
        metrics = {
            'per': None,
            'pbr': None,
            'pcr': None,
            'psr': None,
            'dividend_yield': None
        }

        try:
            # Valuation 테이블에서 추출
            # FnGuide의 경우 여러 지표가 표시됨

            # PER
            per_selector = '#corp_group2 > dl:has-text("PER") > dd'
            per_text = await self.get_text_content(per_selector)
            if per_text:
                metrics['per'] = self.clean_number(per_text)

            # PBR
            pbr_selector = '#corp_group2 > dl:has-text("PBR") > dd'
            pbr_text = await self.get_text_content(pbr_selector)
            if pbr_text:
                metrics['pbr'] = self.clean_number(pbr_text)

            # 배당수익률
            div_selector = '#corp_group2 > dl:has-text("배당") > dd'
            div_text = await self.get_text_content(div_selector)
            if div_text:
                metrics['dividend_yield'] = self.clean_number(div_text)

        except Exception as e:
            self.logger.warning(f"Error parsing valuation metrics: {e}")

        return metrics

    @staticmethod
    def clean_number(text: Optional[str]) -> Optional[float]:
        """
        Clean and convert text to number.

        Args:
            text: Text to clean

        Returns:
            Float number or None
        """
        if not text:
            return None

        try:
            # Remove commas, spaces, and non-numeric characters (except dot, minus)
            cleaned = re.sub(r'[^\d.\-]', '', text.strip())
            if cleaned and cleaned != '-':
                return float(cleaned)
        except ValueError:
            pass

        return None

    async def validate_structure(self) -> bool:
        """
        Validate FnGuide site structure (required by BaseFetcher).

        Returns:
            True (always valid for Playwright-based fetchers)
        """
        # Playwright fetchers don't need structure validation
        # as they handle dynamic content
        return True


# Factory function
async def create_fnguide_playwright_fetcher(site_id: int, config: Dict[str, Any]) -> FnGuidePlaywrightFetcher:
    """
    Create and initialize FnGuide Playwright fetcher.

    Args:
        site_id: Reference site ID from database
        config: Site configuration

    Returns:
        Initialized FnGuidePlaywrightFetcher instance
    """
    fetcher = FnGuidePlaywrightFetcher(site_id, config)
    return fetcher
