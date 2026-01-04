"""
TikTok Ads API Connector.

Supports TikTok Marketing API with OAuth authentication.
Includes mock mode for testing without real accounts.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
import os

from loguru import logger

from src.connectors.base_connector import (
    BaseAdConnector,
    Campaign,
    ConnectionResult,
    ConnectorStatus,
    PerformanceMetrics,
)


TIKTOK_CAMPAIGNS = [
    {
        "id": "tt_camp_001",
        "name": "In-Feed Ads - Gen Z Reach",
        "status": "CAMPAIGN_STATUS_ENABLE",
        "budget": 35000.00,
        "spend": 29875.50,
        "impressions": 15000000,
        "clicks": 750000,
        "conversions": 25000.0,
        "objective": "REACH",
        "start_date": "2024-10-01",
        "end_date": "2024-12-31",
    },
    {
        "id": "tt_camp_002",
        "name": "Spark Ads - UGC Amplification",
        "status": "CAMPAIGN_STATUS_ENABLE",
        "budget": 20000.00,
        "spend": 17234.75,
        "impressions": 8500000,
        "clicks": 510000,
        "conversions": 18500.0,
        "objective": "VIDEO_VIEWS",
        "start_date": "2024-09-15",
        "end_date": None,
    },
    {
        "id": "tt_camp_003",
        "name": "TopView - Brand Takeover",
        "status": "CAMPAIGN_STATUS_ENABLE",
        "budget": 75000.00,
        "spend": 68500.00,
        "impressions": 25000000,
        "clicks": 1250000,
        "conversions": 45000.0,
        "objective": "AWARENESS",
        "start_date": "2024-11-01",
        "end_date": "2024-11-30",
    },
    {
        "id": "tt_camp_004",
        "name": "Shopping Ads - Product Catalog",
        "status": "CAMPAIGN_STATUS_ENABLE",
        "budget": 15000.00,
        "spend": 12450.25,
        "impressions": 5200000,
        "clicks": 312000,
        "conversions": 8900.0,
        "objective": "CATALOG_SALES",
        "start_date": "2024-10-15",
        "end_date": None,
    },
    {
        "id": "tt_camp_005",
        "name": "App Install - Gaming",
        "status": "CAMPAIGN_STATUS_DISABLE",
        "budget": 25000.00,
        "spend": 24500.00,
        "impressions": 12000000,
        "clicks": 840000,
        "conversions": 125000.0,
        "objective": "APP_INSTALL",
        "start_date": "2024-07-01",
        "end_date": "2024-09-30",
    },
]

TIKTOK_ACCOUNT = {
    "id": "tt_adv_789012",
    "name": "Demo TikTok Ads Account",
    "currency": "USD",
    "timezone": "America/New_York",
    "status": "STATUS_ENABLE",
}


class TikTokAdsConnector(BaseAdConnector):
    """
    TikTok Marketing API connector.
    
    Credentials needed:
    - TIKTOK_APP_ID: App ID from TikTok for Business
    - TIKTOK_APP_SECRET: App Secret
    - TIKTOK_ACCESS_TOKEN: Access Token
    - TIKTOK_ADVERTISER_ID: Advertiser ID
    """
    
    PLATFORM_NAME = "tiktok_ads"
    API_VERSION = "v1.3"
    
    def __init__(self, use_mock: bool = None, **credentials):
        creds = {
            "app_id": credentials.get("app_id") or os.getenv("TIKTOK_APP_ID"),
            "app_secret": credentials.get("app_secret") or os.getenv("TIKTOK_APP_SECRET"),
            "access_token": credentials.get("access_token") or os.getenv("TIKTOK_ACCESS_TOKEN"),
            "advertiser_id": credentials.get("advertiser_id") or os.getenv("TIKTOK_ADVERTISER_ID"),
        }
        super().__init__(use_mock=use_mock, **creds)
    
    def _validate_credentials(self) -> bool:
        required = ["access_token", "advertiser_id"]
        return all(self.credentials.get(k) for k in required)
    
    def _connect_real(self) -> ConnectionResult:
        try:
            import requests
            headers = {"Access-Token": self.credentials["access_token"]}
            response = requests.get(
                f"https://business-api.tiktok.com/open_api/{self.API_VERSION}/advertiser/info/",
                headers=headers,
                params={"advertiser_ids": [self.credentials["advertiser_id"]]},
                timeout=30
            )
            if response.status_code == 200:
                return ConnectionResult(
                    success=True, status=ConnectorStatus.CONNECTED,
                    message="Connected to TikTok Ads", platform=self.PLATFORM_NAME,
                )
            return ConnectionResult(
                success=False, status=ConnectorStatus.ERROR,
                message="Failed to connect", platform=self.PLATFORM_NAME,
                error_details=response.text,
            )
        except Exception as e:
            return ConnectionResult(
                success=False, status=ConnectorStatus.ERROR,
                message="Connection failed", platform=self.PLATFORM_NAME,
                error_details=str(e),
            )
    
    def _get_campaigns_real(self, start_date=None, end_date=None) -> List[Campaign]:
        return []
    
    def _get_performance_real(self, start_date, end_date, campaign_ids=None) -> PerformanceMetrics:
        return PerformanceMetrics(
            platform=self.PLATFORM_NAME, account_id="", date_range={},
            spend=0, impressions=0, clicks=0, conversions=0, revenue=0
        )
    
    def _get_mock_campaigns(self) -> List[Campaign]:
        return [
            Campaign(
                id=c["id"], name=c["name"], status=c["status"],
                platform=self.PLATFORM_NAME, account_id=TIKTOK_ACCOUNT["id"],
                budget=c["budget"], spend=c["spend"], impressions=c["impressions"],
                clicks=c["clicks"], conversions=c["conversions"],
                start_date=datetime.strptime(c["start_date"], "%Y-%m-%d") if c.get("start_date") else None,
                end_date=datetime.strptime(c["end_date"], "%Y-%m-%d") if c.get("end_date") else None,
                objective=c["objective"],
            )
            for c in TIKTOK_CAMPAIGNS
        ]
    
    def _get_mock_performance(self, start_date, end_date) -> PerformanceMetrics:
        total = {k: sum(c[k] for c in TIKTOK_CAMPAIGNS) for k in ["spend", "impressions", "clicks", "conversions"]}
        return PerformanceMetrics(
            platform=self.PLATFORM_NAME, account_id=TIKTOK_ACCOUNT["id"],
            date_range={"start": start_date.isoformat(), "end": end_date.isoformat()},
            spend=total["spend"], impressions=total["impressions"],
            clicks=total["clicks"], conversions=total["conversions"],
            revenue=total["conversions"] * 8.5,
        )
    
    def get_accounts(self) -> List[Dict[str, Any]]:
        return [TIKTOK_ACCOUNT] if self.use_mock else []

    def get_ad_groups(self, campaign_id: str = None) -> List[Dict[str, Any]]:
        """Get ad groups (mock only)."""
        if not self.use_mock:
            return []
            
        ad_groups = []
        campaigns = [c for c in TIKTOK_CAMPAIGNS if not campaign_id or c["id"] == campaign_id]
        
        for camp in campaigns:
            # Create 2 ad groups per campaign
            for i in range(1, 3):
                ad_groups.append({
                    "id": f"{camp['id']}_ag_{i:03d}",
                    "name": f"{camp['name']} - Ad Group {i}",
                    "campaign_id": camp["id"],
                    "status": camp["status"],
                    "type": "STANDARD",
                    "spend": camp["spend"] * 0.5,
                })
        return ad_groups

    def get_ads(self, campaign_id: str = None, ad_group_id: str = None) -> List[Dict[str, Any]]:
        """Get ads (mock only)."""
        if not self.use_mock:
            return []
            
        ads = []
        ad_groups = self.get_ad_groups(campaign_id)
        if ad_group_id:
            ad_groups = [ag for ag in ad_groups if ag["id"] == ad_group_id]
            
        for ag in ad_groups:
            # Create 3 ads per ad group
            for i in range(1, 4):
                spend = ag["spend"] / 3
                impressions = int(spend * 1000 / 5.0)  # CPM ~ $5
                clicks = int(impressions * 0.015)      # CTR ~ 1.5%
                conversions = int(clicks * 0.05)       # CVR ~ 5%
                
                ads.append({
                    "id": f"{ag['id']}_ad_{i:03d}",
                    "name": f"{ag['name']} - Video Ad {i}",
                    "ad_group_id": ag["id"],
                    "campaign_id": ag["campaign_id"],
                    "status": ag["status"],
                    "type": "VIDEO",
                    "spend": spend,
                    "impressions": impressions,
                    "clicks": clicks,
                    "conversions": conversions,
                    "ctr": 0.015,
                    "cpc": spend / clicks if clicks > 0 else 0,
                    "cpa": spend / conversions if conversions > 0 else 0,
                })
        return ads
