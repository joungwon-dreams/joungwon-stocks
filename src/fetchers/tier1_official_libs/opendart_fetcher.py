"""
OpenDART Fetcher - Tier 1 (Official Library)
Uses opendartreader library to fetch data from OpenDART API
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
import OpenDartReader

from src.core.base_fetcher import BaseFetcher
from src.config.settings import settings


class OpenDartFetcher(BaseFetcher):
    """
    Fetcher for OpenDART API using OpenDartReader library.

    Data provided:
    - Company information
    - Financial statements
    - Disclosure documents
    """

    def __init__(self, site_id: int, config: Dict[str, Any]):
        super().__init__(site_id, config)

        # Initialize OpenDartReader with API key
        self.dart = OpenDartReader(settings.DART_API_KEY)

    async def fetch(self, ticker: str) -> Dict[str, Any]:
        """
        Fetch disclosure data from OpenDART API.

        Args:
            ticker: 6-digit stock code (e.g., "005930")

        Returns:
            Dictionary containing disclosure data
        """
        try:
            self.logger.info(f"Fetching OpenDART data for {ticker}")

            # Get company code from stock code
            corp_code = await asyncio.to_thread(
                self.dart.find_corp_code,
                ticker
            )

            if not corp_code:
                self.logger.warning(f"No corp_code found for ticker {ticker}")
                return {}

            # Get company information
            company_info = await asyncio.to_thread(
                self.dart.company,
                corp_code
            )

            # Get recent disclosures (last 14 days)
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=14)).strftime("%Y%m%d")

            disclosures = await asyncio.to_thread(
                self.dart.list,
                corp=corp_code,
                start=start_date,
                end=end_date
            )

            # Parse disclosures
            disclosure_list = []
            if disclosures is not None and not disclosures.empty:
                for _, row in disclosures.head(10).iterrows():
                    disclosure_list.append({
                        "title": row['report_nm'],
                        "date": row['rcept_dt'],
                        "type": row['corp_cls']
                    })

            # Build result
            data = {
                "ticker": ticker,
                "corp_code": corp_code,
                "corp_name": company_info.get('corp_name') if isinstance(company_info, dict) else None,
                "ceo_name": company_info.get('ceo_nm') if isinstance(company_info, dict) else None,
                "disclosures": disclosure_list,
                "disclosure_count": len(disclosure_list),
                "source": "OpenDART",
                "records_count": len(disclosure_list)
            }

            # Save to collected_data table
            await self.save_collected_data(
                ticker=ticker,
                domain_id=12,  # disclosure domain
                data_type="disclosure",
                data_content=data
            )

            return data

        except Exception as e:
            self.logger.error(f"Failed to fetch data from OpenDART for {ticker}: {e}")
            raise

    async def validate_structure(self) -> bool:
        """
        Validate OpenDART API is working.

        Returns:
            True if validation succeeds
        """
        try:
            # Test API connectivity
            corp_code = await asyncio.to_thread(
                self.dart.stock_to_corpcode,
                "005930"
            )

            if not corp_code:
                return False

            return True

        except Exception as e:
            self.logger.error(f"OpenDART structure validation failed: {e}")
            return False
