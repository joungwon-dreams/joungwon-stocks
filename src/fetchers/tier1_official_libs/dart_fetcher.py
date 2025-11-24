"""
DART Fetcher - Tier 1 (Official Library)
Uses dart-fss library to fetch disclosure data from DART
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
import xml.etree.ElementTree as ET
import xml.parsers.expat
import dart_fss as dart

from src.core.base_fetcher import BaseFetcher
from src.config.settings import settings


class DartFetcher(BaseFetcher):
    """
    Fetcher for DART (전자공시시스템) using dart-fss library.

    Data provided:
    - Company disclosures
    - Financial statements
    - Business reports
    """

    def __init__(self, site_id: int, config: Dict[str, Any]):
        super().__init__(site_id, config)

        # Set DART API key
        dart.set_api_key(settings.DART_API_KEY)

    async def fetch(self, ticker: str) -> Dict[str, Any]:
        """
        Fetch disclosure data from DART.

        Args:
            ticker: 6-digit stock code (e.g., "005930")

        Returns:
            Dictionary containing disclosure data
        """
        try:
            self.logger.info(f"Fetching DART data for {ticker}")

            # Get company information with XML error handling
            try:
                corp_list = await asyncio.to_thread(dart.get_corp_list)
                corp = corp_list.find_by_stock_code(ticker)
            except (xml.parsers.expat.ExpatError, ET.ParseError) as xml_err:
                self.logger.error(f"XML parsing error for {ticker}: {xml_err}")
                # Return empty data but don't raise - allows other fetchers to continue
                return {}

            if not corp:
                self.logger.warning(f"No company found for ticker {ticker}")
                return {}

            # Get recent disclosures (last 30 days)
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

            # Get disclosure list from DART
            try:
                from dart_fss.api.filings import search_filings
                import pandas as pd

                disclosure_data = await asyncio.to_thread(
                    search_filings,
                    corp_code=corp.corp_code,
                    bgn_de=start_date,
                    end_de=end_date
                )

                disclosure_list = []
                # Check if result is DataFrame
                if disclosure_data is not None:
                    if isinstance(disclosure_data, pd.DataFrame) and not disclosure_data.empty:
                        for _, row in disclosure_data.head(10).iterrows():
                            disclosure_list.append({
                                "title": row.get('report_nm', ''),
                                "date": row.get('rcept_dt', ''),
                                "type": row.get('corp_cls', '')
                            })
                    elif isinstance(disclosure_data, dict):
                        # Handle dict response (error case)
                        self.logger.warning(f"DART API returned dict: {disclosure_data}")
            except (xml.parsers.expat.ExpatError, ET.ParseError) as xml_err:
                # Gracefully handle malformed XML from DART API
                self.logger.warning(f"XML parsing error for disclosures ({ticker}): {xml_err}")
                self.logger.info(f"Continuing with empty disclosure list for {ticker}")
                disclosure_list = []
            except Exception as e:
                self.logger.warning(f"Could not fetch disclosures: {e}")
                disclosure_list = []

            # Basic financial data
            financial_data = {
                "corp_name": corp.corp_name,
                "stock_code": corp.stock_code
            }

            # Build result
            data = {
                "ticker": ticker,
                "corp_name": corp.corp_name,
                "corp_code": corp.corp_code,
                "stock_code": corp.stock_code,
                "disclosures": disclosure_list[:10],  # Latest 10
                "disclosure_count": len(disclosure_list),
                "financial_data": financial_data,
                "source": "DART",
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
            self.logger.error(f"Failed to fetch data from DART for {ticker}: {e}")
            raise

    async def validate_structure(self) -> bool:
        """
        Validate that DART API is working properly.
        Test with Samsung Electronics (005930).

        Returns:
            True if validation succeeds
        """
        try:
            # Test API key and connectivity
            corp_list = await asyncio.to_thread(dart.get_corp_list)
            corp = corp_list.find_by_stock_code("005930")

            if corp is None:
                return False

            # If we get here, API is working
            return True

        except Exception as e:
            self.logger.error(f"DART structure validation failed: {e}")
            return False
