"""
Unified Ad Connector Manager.

Provides a single interface to manage all ad platform connectors,
test connections, and retrieve aggregated data.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
import os


import pybreaker
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests

from src.connectors.base_connector import (
    BaseAdConnector,
    Campaign,
    ConnectionResult,
    ConnectorStatus,
    PerformanceMetrics,
)
from src.connectors.google_ads_connector import GoogleAdsConnector
from src.connectors.meta_ads_connector import MetaAdsConnector
from src.connectors.campaign_manager_connector import CampaignManagerConnector
from src.connectors.dv360_connector import DV360Connector
from src.connectors.snapchat_ads_connector import SnapchatAdsConnector
from src.connectors.tiktok_ads_connector import TikTokAdsConnector
from src.connectors.twitter_ads_connector import TwitterAdsConnector
from src.connectors.linkedin_ads_connector import LinkedInAdsConnector
from src.connectors.tradedesk_connector import TradeDeskConnector
from src.connectors.amazon_dsp_connector import AmazonDSPConnector
from src.connectors.pinterest_ads_connector import PinterestAdsConnector
from src.connectors.apple_search_ads_connector import AppleSearchAdsConnector


class AdConnectorManager:
    """
    Unified manager for all ad platform connectors.
    
    Provides:
    - Single interface to test all connections
    - Aggregated campaign data across platforms
    - Unified performance metrics
    - Mock mode support for all connectors
    """
    
    SUPPORTED_PLATFORMS = {
        # Phase 1: Core Platforms
        "google_ads": GoogleAdsConnector,
        "meta_ads": MetaAdsConnector,
        "campaign_manager": CampaignManagerConnector,
        "dv360": DV360Connector,
        # Phase 2: Additional Platforms
        "snapchat_ads": SnapchatAdsConnector,
        "tiktok_ads": TikTokAdsConnector,
        "twitter_ads": TwitterAdsConnector,
        "linkedin_ads": LinkedInAdsConnector,
        "tradedesk": TradeDeskConnector,
        "amazon_dsp": AmazonDSPConnector,
        "pinterest_ads": PinterestAdsConnector,
        "apple_search_ads": AppleSearchAdsConnector,
    }
    
    def __init__(self, use_mock: bool = None, platforms: Optional[List[str]] = None):
        """
        Initialize the connector manager.
        
        Args:
            use_mock: If True, all connectors use mock mode.
            platforms: List of platforms to initialize. If None, initializes all.
        """
        if use_mock is None:
            use_mock = os.getenv("AD_CONNECTORS_MOCK_MODE", "true").lower() == "true"
        
        self.use_mock = use_mock
        self._connectors: Dict[str, BaseAdConnector] = {}
        
        # Phase 1 Step 2: Circuit Breakers (One per platform)
        # Default: 5 failures trips it, 60s reset timeout
        self.circuit_breakers: Dict[str, pybreaker.CircuitBreaker] = {}
        
        # Initialize requested platforms
        platforms = platforms or list(self.SUPPORTED_PLATFORMS.keys())
        for platform in platforms:
            if platform in self.SUPPORTED_PLATFORMS:
                self._connectors[platform] = self.SUPPORTED_PLATFORMS[platform](use_mock=use_mock)
            else:
                logger.warning(f"Unknown platform: {platform}")
        
        logger.info(
            "Ad Connector Manager initialized",
            platforms=list(self._connectors.keys()),
            mock_mode=use_mock,
        )
    
    
    def _get_breaker(self, platform: str) -> pybreaker.CircuitBreaker:
        """Get or create a circuit breaker for the platform."""
        if platform not in self.circuit_breakers:
            # Create a new breaker for this platform
            # fail_max=5: 5 consecutive failures opens the circuit
            # reset_timeout=60: Wait 60s before trying again (Half-Open)
            self.circuit_breakers[platform] = pybreaker.CircuitBreaker(
                fail_max=5, 
                reset_timeout=60,
                name=f"{platform}_breaker"
            )
        return self.circuit_breakers[platform]

    def _call_with_retry(self, platform: str, func, *args, **kwargs):
        """
        Call a connector function with retry and circuit breaker protection.
        
        Retries up to 3 times with exponential backoff (1s, 2s, 4s) for transient errors.
        Circuit breaker opens after 5 consecutive failures.
        
        Args:
            platform: Platform name for logging and breaker lookup.
            func: The function to call.
            *args, **kwargs: Arguments to pass to the function.
            
        Returns:
            Result from the function call.
            
        Raises:
            pybreaker.CircuitBreakerError: If the circuit is open.
            Exception: If all retries are exhausted.
        """
        breaker = self._get_breaker(platform)
        
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((
                requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
                ConnectionResetError,
            )),
            before_sleep=lambda retry_state: logger.warning(
                f"Retry {retry_state.attempt_number}/3 for {platform} after {retry_state.outcome.exception()}"
            )
        )
        def _inner():
            return breaker.call(func, *args, **kwargs)
        
        return _inner()

    def get_connector(self, platform: str) -> Optional[BaseAdConnector]:
        """Get a specific connector by platform name."""
        return self._connectors.get(platform)
    
    def test_connection(self, platform: str) -> ConnectionResult:
        """Test connection for a specific platform."""
        connector = self._connectors.get(platform)
        if not connector:
            return ConnectionResult(
                success=False,
                status=ConnectorStatus.ERROR,
                message=f"Unknown platform: {platform}",
                platform=platform,
                error_details=f"Supported platforms: {list(self.SUPPORTED_PLATFORMS.keys())}",
            )
        
        try:
            return self._call_with_retry(platform, connector.test_connection)
        except pybreaker.CircuitBreakerError:
            logger.error(f"Circuit Breaker OPEN for {platform}. Skipping connection test.")
            return ConnectionResult(
                success=False,
                status=ConnectorStatus.ERROR,
                message=f"Circuit Breaker OPEN for {platform}",
                platform=platform,
                error_details="Too many recent failures. Circuit is open to prevent cascading failure."
            )
        except Exception as e:
            # Let the breaker count this as a failure, but we also return a failed result
            logger.error(f"Connection test failed for {platform}: {e}")
            return ConnectionResult(
                success=False,
                status=ConnectorStatus.ERROR,
                message=str(e),
                platform=platform
            )
    
    def test_all_connections(self) -> Dict[str, ConnectionResult]:
        """Test connections for all configured platforms."""
        results = {}
        for platform, connector in self._connectors.items():
            logger.info(f"Testing connection for {platform}...")
            results[platform] = connector.test_connection()
        return results
    
    def get_connection_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status summary for all connectors."""
        status = {}
        for platform, connector in self._connectors.items():
            result = connector.test_connection()
            status[platform] = {
                "connected": result.success,
                "status": result.status.value,
                "message": result.message,
                "is_mock": result.is_mock,
                "account_id": result.account_id,
                "account_name": result.account_name,
            }
        return status
    
    def get_campaigns(
        self,
        platforms: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, List[Campaign]]:
        """
        Get campaigns from specified platforms.
        
        Args:
            platforms: List of platforms to query. If None, queries all.
            start_date: Optional start date filter.
            end_date: Optional end date filter.
            
        Returns:
            Dictionary mapping platform name to list of campaigns.
        """
        platforms = platforms or list(self._connectors.keys())
        campaigns = {}
        
        for platform in platforms:
            connector = self._connectors.get(platform)
            if connector:
                try:
                    campaigns[platform] = self._call_with_retry(platform, connector.get_campaigns, start_date, end_date)
                except pybreaker.CircuitBreakerError:
                    logger.warning(f"Circuit Breaker OPEN for {platform}. Skipping campaigns fetch.")
                    campaigns[platform] = []
                except Exception as e:
                    logger.error(f"Failed to get campaigns from {platform}: {e}")
                    campaigns[platform] = []
        
        return campaigns
    
    def get_all_campaigns(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Campaign]:
        """
        Get all campaigns from all platforms as a flat list.
        
        Args:
            start_date: Optional start date filter.
            end_date: Optional end date filter.
            
        Returns:
            List of all campaigns across platforms.
        """
        all_campaigns = []
        campaigns_by_platform = self.get_campaigns(None, start_date, end_date)
        
        for platform, campaigns in campaigns_by_platform.items():
            all_campaigns.extend(campaigns)
        
        return all_campaigns
    
    def get_performance(
        self,
        platforms: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, PerformanceMetrics]:
        """
        Get performance metrics from specified platforms.
        
        Args:
            platforms: List of platforms to query. If None, queries all.
            start_date: Start date for metrics.
            end_date: End date for metrics.
            
        Returns:
            Dictionary mapping platform name to performance metrics.
        """
        platforms = platforms or list(self._connectors.keys())
        performance = {}
        
        for platform in platforms:
            connector = self._connectors.get(platform)
            if connector:
                try:
                    performance[platform] = self._call_with_retry(platform, connector.get_performance, start_date, end_date)
                except pybreaker.CircuitBreakerError:
                    logger.warning(f"Circuit Breaker OPEN for {platform}. Skipping performance fetch.")
                except Exception as e:
                    logger.error(f"Failed to get performance from {platform}: {e}")
        
        return performance
    
    def get_aggregated_performance(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get aggregated performance metrics across all platforms.
        
        Returns:
            Dictionary with totals and per-platform breakdown.
        """
        performance = self.get_performance(None, start_date, end_date)
        
        # Calculate totals
        total_spend = 0.0
        total_impressions = 0
        total_clicks = 0
        total_conversions = 0.0
        total_revenue = 0.0
        
        platform_breakdown = {}
        
        for platform, metrics in performance.items():
            total_spend += metrics.spend
            total_impressions += metrics.impressions
            total_clicks += metrics.clicks
            total_conversions += metrics.conversions
            total_revenue += metrics.revenue
            
            platform_breakdown[platform] = metrics.to_dict()
        
        return {
            "totals": {
                "spend": round(total_spend, 2),
                "impressions": total_impressions,
                "clicks": total_clicks,
                "conversions": round(total_conversions, 2),
                "revenue": round(total_revenue, 2),
                "ctr": round((total_clicks / total_impressions * 100) if total_impressions > 0 else 0, 2),
                "cpc": round(total_spend / total_clicks if total_clicks > 0 else 0, 2),
                "roas": round(total_revenue / total_spend if total_spend > 0 else 0, 2),
            },
            "by_platform": platform_breakdown,
            "date_range": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            },
            "is_mock": self.use_mock,
        }
    
    def disconnect_all(self):
        """Disconnect from all platforms."""
        for platform, connector in self._connectors.items():
            connector.disconnect()
        logger.info("Disconnected from all platforms")


# Convenience function for quick testing
def test_all_ad_connectors(use_mock: bool = True) -> Dict[str, Dict[str, Any]]:
    """
    Quick test of all ad platform connectors.
    
    Args:
        use_mock: Use mock mode for testing.
        
    Returns:
        Status dictionary for all platforms.
    """
    manager = AdConnectorManager(use_mock=use_mock)
    return manager.get_connection_status()
