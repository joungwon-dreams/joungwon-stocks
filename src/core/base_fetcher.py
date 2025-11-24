"""
Base Fetcher Abstract Class
All tier fetchers inherit from this base class
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import time
import logging

from src.config.database import db


class BaseFetcher(ABC):
    """
    Abstract base class for all site fetchers.
    Provides common functionality for logging, health checks, and data collection.
    """

    def __init__(self, site_id: int, config: Dict[str, Any]):
        """
        Initialize fetcher

        Args:
            site_id: Reference site ID from database
            config: Site configuration (from reference_sites table)
        """
        self.site_id = site_id
        self.config = config
        self.site_name = config.get('site_name_ko', f'Site-{site_id}')
        self.logger = logging.getLogger(f"Fetcher.{self.site_name}")

    @abstractmethod
    async def fetch(self, ticker: str) -> Dict[str, Any]:
        """
        Fetch data for a specific ticker.
        Must be implemented by subclasses.

        Args:
            ticker: Stock ticker code (e.g., "005930")

        Returns:
            Dictionary containing fetched data
        """
        pass

    @abstractmethod
    async def validate_structure(self) -> bool:
        """
        Check if the site structure matches expectations.
        Used for detecting site changes.

        Returns:
            True if structure is valid, False otherwise
        """
        pass

    async def log_execution(self, log_data: Dict[str, Any]):
        """
        Log execution details to fetch_execution_logs table.

        Args:
            log_data: Dictionary containing execution metadata
        """
        query = """
            INSERT INTO fetch_execution_logs (
                site_id, ticker, execution_status, started_at, completed_at,
                execution_time_ms, records_fetched, error_type, error_message, retry_count
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10
            )
        """
        try:
            await db.execute(
                query,
                self.site_id,
                log_data.get('ticker'),
                log_data.get('status', 'unknown'),
                log_data.get('started_at'),
                log_data.get('completed_at'),
                log_data.get('duration_ms'),
                log_data.get('records_count', 0),
                log_data.get('error_type'),
                log_data.get('error_message'),
                log_data.get('retry_count', 0)
            )
        except Exception as e:
            self.logger.error(f"Failed to log execution: {e}")

    async def update_health_status(
        self,
        success: bool,
        response_time_ms: Optional[int] = None
    ):
        """
        Update site health status in site_health_status table.

        Args:
            success: Whether the fetch was successful
            response_time_ms: Response time in milliseconds
        """
        if success:
            query = """
                INSERT INTO site_health_status (
                    site_id, status, last_success_at, consecutive_failures,
                    avg_response_time_ms, last_checked_at
                )
                VALUES ($1, 'active', NOW(), 0, $2, NOW())
                ON CONFLICT (site_id) DO UPDATE SET
                    status = 'active',
                    last_success_at = NOW(),
                    consecutive_failures = 0,
                    avg_response_time_ms = COALESCE($2, site_health_status.avg_response_time_ms),
                    last_checked_at = NOW()
            """
            await db.execute(query, self.site_id, response_time_ms)
        else:
            query = """
                INSERT INTO site_health_status (
                    site_id, status, last_failure_at, consecutive_failures, last_checked_at
                )
                VALUES ($1, 'degraded', NOW(), 1, NOW())
                ON CONFLICT (site_id) DO UPDATE SET
                    last_failure_at = NOW(),
                    consecutive_failures = site_health_status.consecutive_failures + 1,
                    last_checked_at = NOW(),
                    status = CASE
                        WHEN site_health_status.consecutive_failures + 1 >= 3 THEN 'failed'
                        WHEN site_health_status.consecutive_failures + 1 >= 1 THEN 'degraded'
                        ELSE 'active'
                    END
            """
            await db.execute(query, self.site_id)

    async def execute(self, ticker: str) -> Dict[str, Any]:
        """
        Wrapper around fetch() to handle logging and health updates.
        This is the main entry point for data collection.

        Args:
            ticker: Stock ticker code

        Returns:
            Dictionary containing fetched data
        """
        start_time = datetime.now()
        start_ts = time.time()
        status = "success"
        error_type = None
        error_msg = None
        records = 0
        data = {}

        try:
            self.logger.info(f"Fetching {ticker} from {self.site_name}...")
            data = await self.fetch(ticker)

            if not data:
                status = "skipped"  # Fixed: 'no_data' -> 'skipped' (allowed value)
                error_msg = "No data returned"
                self.logger.warning(f"No data returned for {ticker}")
            else:
                records = data.get('records_count', 1)
                self.logger.info(f"Successfully fetched {ticker} from {self.site_name}")

        except TimeoutError as e:
            status = "timeout"  # Already valid
            error_type = "timeout"
            error_msg = str(e)
            self.logger.error(f"Timeout fetching {ticker}: {e}")

        except ConnectionError as e:
            status = "failed"  # Fixed: 'connection_error' -> 'failed' (allowed value)
            error_type = "connection"
            error_msg = str(e)
            self.logger.error(f"Connection error fetching {ticker}: {e}")

        except ValueError as e:
            status = "failed"  # Fixed: 'validation_error' -> 'failed' (allowed value)
            error_type = "validation"
            error_msg = str(e)
            self.logger.error(f"Validation error for {ticker}: {e}")

        except Exception as e:
            status = "failed"  # Already valid
            error_type = "unknown"
            error_msg = str(e)
            self.logger.error(f"Unexpected error fetching {ticker}: {e}")

        end_time = datetime.now()
        duration_ms = int((time.time() - start_ts) * 1000)

        # Log execution
        await self.log_execution({
            "ticker": ticker,
            "status": status,
            "started_at": start_time,
            "completed_at": end_time,
            "duration_ms": duration_ms,
            "records_count": records,
            "error_type": error_type,
            "error_message": error_msg,
            "retry_count": 0
        })

        # Update health status
        await self.update_health_status(
            success=(status == "success"),
            response_time_ms=duration_ms if status == "success" else None
        )

        return data

    async def save_collected_data(
        self,
        ticker: str,
        domain_id: int,
        data_type: str,
        data_content: Dict[str, Any],
        data_date: Optional[str] = None
    ):
        """
        Save raw collected data to collected_data table.

        Args:
            ticker: Stock ticker code
            domain_id: Analysis domain ID (from analysis_domains table)
            data_type: Type of data (ohlcv/supply/news/report/disclosure)
            data_content: Raw JSON data to store
            data_date: Data date (YYYY-MM-DD), defaults to today
        """
        from datetime import date, datetime
        import json

        # Convert data_date to date object for PostgreSQL
        if data_date is None:
            date_obj = date.today()
        else:
            date_obj = datetime.strptime(data_date, "%Y-%m-%d").date()

        query = """
            INSERT INTO collected_data (
                ticker, site_id, domain_id, data_type, data_content, data_date
            ) VALUES (
                $1, $2, $3, $4, $5, $6
            )
            ON CONFLICT (ticker, site_id, domain_id, data_type, data_date) DO UPDATE SET
                data_content = EXCLUDED.data_content,
                collected_at = CURRENT_TIMESTAMP
        """

        try:
            await db.execute(
                query,
                ticker,
                self.site_id,
                domain_id,
                data_type,
                json.dumps(data_content),  # Convert dict to JSON string
                date_obj  # Use date object, not string
            )
            self.logger.info(f"Saved {data_type} data to collected_data (ticker={ticker}, domain={domain_id})")
        except Exception as e:
            self.logger.error(f"Failed to save collected_data: {e}")

    async def health_check(self) -> bool:
        """
        Perform basic health check.
        Can be overridden by subclasses for more specific checks.

        Returns:
            True if healthy, False otherwise
        """
        try:
            return await self.validate_structure()
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
