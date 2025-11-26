"""
Tier 3 Web Scraping Fetchers
Korean investment analysis websites (28 sites)
"""
from .base_scraper import BaseScraper
from .fnguide_scraper import FnGuideScraper
from .wisefn_scraper import WISEfnScraper
from .comm38_scraper import Comm38Scraper
from .mirae_asset_scraper import MiraeAssetScraper
from .samsung_securities_scraper import SamsungSecuritiesScraper
from .kiwoom_scraper import KiwoomScraper
from .kb_securities_scraper import KBSecuritiesScraper
from .shinhan_scraper import ShinhanScraper
from .meritz_scraper import MeritzScraper
from .hana_scraper import HanaScraper
from .daishin_scraper import DaishinScraper
from .korea_investment_scraper import KoreaInvestmentScraper
from .nh_investment_scraper import NHInvestmentScraper
from .quantiwise_scraper import QuantiWiseScraper
from .wise_report_scraper import WiseReportScraper
from .ebest_scraper import EBestScraper
from .eugene_scraper import EugeneScraper
from .korea_economy_scraper import KoreaEconomyScraper
from .maeil_business_scraper import MaeilBusinessScraper
from .seoul_economy_scraper import SeoulEconomyScraper
from .financial_news_scraper import FinancialNewsScraper
from .money_today_scraper import MoneyTodayScraper
from .edaily_scraper import EdailyScraper
from .yonhap_infomax_scraper import YonhapInfomaxScraper
from .newspim_scraper import NewspimScraper
from .daum_stock_news_scraper import DaumStockNewsScraper
from .naver_stock_news_scraper import NaverStockNewsScraper
from .stock_plus_scraper import StockPlusScraper

__all__ = [
    'BaseScraper',
    'FnGuideScraper',
    'WISEfnScraper',
    'Comm38Scraper',
    'MiraeAssetScraper',
    'SamsungSecuritiesScraper',
    'KiwoomScraper',
    'KBSecuritiesScraper',
    'ShinhanScraper',
    'MeritzScraper',
    'HanaScraper',
    'DaishinScraper',
    'KoreaInvestmentScraper',
    'NHInvestmentScraper',
    'QuantiWiseScraper',
    'WiseReportScraper',
    'EBestScraper',
    'EugeneScraper',
    'KoreaEconomyScraper',
    'MaeilBusinessScraper',
    'SeoulEconomyScraper',
    'FinancialNewsScraper',
    'MoneyTodayScraper',
    'EdailyScraper',
    'YonhapInfomaxScraper',
    'NewspimScraper',
    'DaumStockNewsScraper',
    'NaverStockNewsScraper',
    'StockPlusScraper',
]
