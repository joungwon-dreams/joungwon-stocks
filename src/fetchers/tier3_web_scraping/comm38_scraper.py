"""
38 Communication Scraper
Tier 3 - Web Scraping
Priority #3 (Quality: 0.90, Rating: 4/5)

38comm provides:
- Market analysis
- Trading signals
- Technical indicators
- Investment opinions
"""
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
from datetime import datetime

from .base_scraper import BaseScraper


class Comm38Scraper(BaseScraper):
    """
    38comm web scraper for market analysis and trading signals.

    Data Types:
    - Market Analysis
    - Trading Signals (Buy/Sell)
    - Technical Indicators
    - Investment Opinions
    """

    # 38comm URL patterns
    # Note: These are template URLs - actual URLs need verification
    COMPANY_URL_TEMPLATE = "http://www.38.co.kr/html/fund/index.htm?kind=A&code={ticker}"
    SIGNAL_URL_TEMPLATE = "http://www.38.co.kr/html/fund/signal.htm?code={ticker}"

    # CSS Selectors for data extraction
    SELECTORS = {
        'company_name': 'div.company-name h2',
        'current_price': 'span.current-price',
        'signal': 'div.trading-signal',
        'signal_strength': 'span.signal-strength',
        'technical_score': 'div.technical-score',
        'volume_analysis': 'div.volume-analysis',
        'support_level': 'td.support-level',
        'resistance_level': 'td.resistance-level',
        'trend_direction': 'span.trend',
        'recommendation': 'div.recommendation',
        'target_price_short': 'span.target-short',
        'target_price_mid': 'span.target-mid',
    }

    async def build_url(self, ticker: str) -> str:
        """
        Build 38comm URL for ticker.

        Args:
            ticker: Stock ticker code (e.g., "005930")

        Returns:
            Complete URL for the ticker
        """
        return self.COMPANY_URL_TEMPLATE.format(ticker=ticker)

    async def parse_company_info(self, soup: BeautifulSoup, ticker: str) -> Dict[str, Any]:
        """
        Parse company basic information.

        Args:
            soup: BeautifulSoup object
            ticker: Stock ticker code

        Returns:
            Dictionary with company info
        """
        info = {
            'ticker': ticker,
            'source': '38comm',
            'company_name': None,
            'current_price': None,
            'crawled_at': datetime.now().isoformat(),
        }

        try:
            # Company name
            name_elem = soup.select_one(self.SELECTORS['company_name'])
            if name_elem:
                info['company_name'] = name_elem.get_text(strip=True)

            # Current price
            price_elem = soup.select_one(self.SELECTORS['current_price'])
            if price_elem:
                price_text = price_elem.get_text(strip=True).replace(',', '').replace('won', '')
                info['current_price'] = int(price_text) if price_text.isdigit() else None

        except Exception as e:
            self.logger.warning(f"Error parsing company info: {e}")

        return info

    async def parse_trading_signals(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Parse trading signals.

        Args:
            soup: BeautifulSoup object

        Returns:
            Dictionary with trading signals
        """
        signals = {
            'signal': None,  # 'buy', 'sell', 'hold'
            'signal_strength': None,  # 1-5
            'signal_date': None,
            'confidence': None,
        }

        try:
            # Trading signal
            signal_elem = soup.select_one(self.SELECTORS['signal'])
            if signal_elem:
                signal_text = signal_elem.get_text(strip=True).lower()
                if 'buy' in signal_text:
                    signals['signal'] = 'buy'
                elif 'sell' in signal_text:
                    signals['signal'] = 'sell'
                else:
                    signals['signal'] = 'hold'

            # Signal strength
            strength_elem = soup.select_one(self.SELECTORS['signal_strength'])
            if strength_elem:
                strength_text = strength_elem.get_text(strip=True)
                import re
                match = re.search(r'(\d)', strength_text)
                if match:
                    signals['signal_strength'] = int(match.group(1))

        except Exception as e:
            self.logger.warning(f"Error parsing trading signals: {e}")

        return signals

    async def parse_technical_analysis(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Parse technical analysis indicators.

        Args:
            soup: BeautifulSoup object

        Returns:
            Dictionary with technical indicators
        """
        technical = {
            'technical_score': None,  # Overall technical score
            'trend_direction': None,  # 'up', 'down', 'sideways'
            'support_levels': [],
            'resistance_levels': [],
            'volume_trend': None,  # 'increasing', 'decreasing', 'stable'
        }

        try:
            # Technical score
            score_elem = soup.select_one(self.SELECTORS['technical_score'])
            if score_elem:
                score_text = score_elem.get_text(strip=True)
                import re
                match = re.search(r'(\d+)', score_text)
                if match:
                    technical['technical_score'] = int(match.group(1))

            # Trend direction
            trend_elem = soup.select_one(self.SELECTORS['trend_direction'])
            if trend_elem:
                trend_text = trend_elem.get_text(strip=True).lower()
                if 'up' in trend_text:
                    technical['trend_direction'] = 'up'
                elif 'down' in trend_text:
                    technical['trend_direction'] = 'down'
                else:
                    technical['trend_direction'] = 'sideways'

            # Support level
            support_elem = soup.select_one(self.SELECTORS['support_level'])
            if support_elem:
                support_text = support_elem.get_text(strip=True).replace(',', '')
                if support_text.isdigit():
                    technical['support_levels'].append(int(support_text))

            # Resistance level
            resistance_elem = soup.select_one(self.SELECTORS['resistance_level'])
            if resistance_elem:
                resistance_text = resistance_elem.get_text(strip=True).replace(',', '')
                if resistance_text.isdigit():
                    technical['resistance_levels'].append(int(resistance_text))

            # Volume analysis
            volume_elem = soup.select_one(self.SELECTORS['volume_analysis'])
            if volume_elem:
                volume_text = volume_elem.get_text(strip=True).lower()
                if 'increas' in volume_text:
                    technical['volume_trend'] = 'increasing'
                elif 'decreas' in volume_text:
                    technical['volume_trend'] = 'decreasing'
                else:
                    technical['volume_trend'] = 'stable'

        except Exception as e:
            self.logger.warning(f"Error parsing technical analysis: {e}")

        return technical

    async def parse_recommendations(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Parse investment recommendations and target prices.

        Args:
            soup: BeautifulSoup object

        Returns:
            Dictionary with recommendations
        """
        recommendations = {
            'recommendation': None,  # Text recommendation
            'target_price_short': None,  # Short-term target
            'target_price_mid': None,  # Mid-term target
        }

        try:
            # Recommendation text
            rec_elem = soup.select_one(self.SELECTORS['recommendation'])
            if rec_elem:
                recommendations['recommendation'] = rec_elem.get_text(strip=True)

            # Short-term target
            short_elem = soup.select_one(self.SELECTORS['target_price_short'])
            if short_elem:
                short_text = short_elem.get_text(strip=True).replace(',', '').replace('won', '')
                recommendations['target_price_short'] = int(short_text) if short_text.isdigit() else None

            # Mid-term target
            mid_elem = soup.select_one(self.SELECTORS['target_price_mid'])
            if mid_elem:
                mid_text = mid_elem.get_text(strip=True).replace(',', '').replace('won', '')
                recommendations['target_price_mid'] = int(mid_text) if mid_text.isdigit() else None

        except Exception as e:
            self.logger.warning(f"Error parsing recommendations: {e}")

        return recommendations

    async def parse_data(self, soup: BeautifulSoup, ticker: str) -> Dict[str, Any]:
        """
        Main parsing method - extracts all data from HTML.

        Args:
            soup: BeautifulSoup object
            ticker: Stock ticker code

        Returns:
            Dictionary containing all parsed data
        """
        self.logger.info(f"Parsing 38comm data for {ticker}")

        # Parse different sections
        company_info = await self.parse_company_info(soup, ticker)
        trading_signals = await self.parse_trading_signals(soup)
        technical_analysis = await self.parse_technical_analysis(soup)
        recommendations = await self.parse_recommendations(soup)

        # Combine all data
        data = {
            **company_info,
            'signals': trading_signals,
            'technical': technical_analysis,
            'recommendations': recommendations,
            'data_quality': self._assess_data_quality(
                company_info,
                trading_signals,
                technical_analysis,
                recommendations
            ),
        }

        # Log what was parsed
        self.logger.info(
            f"38comm data parsed for {ticker}: "
            f"company={bool(company_info['company_name'])}, "
            f"signal={trading_signals['signal']}, "
            f"technical={bool(technical_analysis['technical_score'])}, "
            f"recommendation={bool(recommendations['recommendation'])}"
        )

        return data

    def _assess_data_quality(
        self,
        company_info: Dict,
        trading_signals: Dict,
        technical_analysis: Dict,
        recommendations: Dict
    ) -> int:
        """
        Assess data quality based on completeness.

        Args:
            company_info: Company information dict
            trading_signals: Trading signals dict
            technical_analysis: Technical analysis dict
            recommendations: Recommendations dict

        Returns:
            Quality score (1-5)
        """
        # Count non-null fields
        company_fields = sum(1 for v in company_info.values() if v is not None)
        signal_fields = sum(1 for v in trading_signals.values() if v is not None)
        technical_fields = sum(1 for v in technical_analysis.values() if v is not None and (not isinstance(v, list) or len(v) > 0))
        rec_fields = sum(1 for v in recommendations.values() if v is not None)

        total_fields = company_fields + signal_fields + technical_fields + rec_fields
        max_fields = len(company_info) + len(trading_signals) + len(technical_analysis) + len(recommendations)

        completeness = total_fields / max_fields if max_fields > 0 else 0

        # Convert to 1-5 scale
        if completeness >= 0.9:
            return 5
        elif completeness >= 0.7:
            return 4
        elif completeness >= 0.5:
            return 3
        elif completeness >= 0.3:
            return 2
        else:
            return 1

    async def validate_structure(self) -> bool:
        """
        Validate 38comm site structure.

        Returns:
            True if structure is valid, False otherwise
        """
        try:
            # Test with a well-known ticker (Samsung Electronics)
            test_ticker = "005930"
            url = await self.build_url(test_ticker)

            html = await self.fetch_html(url)
            if not html:
                return False

            soup = await self.parse_html(html)

            # Check for key elements
            required_elements = [
                self.SELECTORS['company_name'],
                self.SELECTORS['current_price'],
            ]

            for selector in required_elements:
                element = soup.select_one(selector)
                if not element:
                    self.logger.warning(f"Required element not found: {selector}")
                    return False

            self.logger.info("38comm structure validation passed")
            return True

        except Exception as e:
            self.logger.error(f"Structure validation failed: {e}")
            return False


# Factory function for easy instantiation
async def create_comm38_scraper(site_id: int, config: Dict[str, Any]) -> Comm38Scraper:
    """
    Create and initialize 38comm scraper.

    Args:
        site_id: Reference site ID from database
        config: Site configuration

    Returns:
        Initialized Comm38Scraper instance
    """
    scraper = Comm38Scraper(site_id, config)
    return scraper
