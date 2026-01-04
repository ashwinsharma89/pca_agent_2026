"""
LinkedIn Ads API Connector.

Supports LinkedIn Marketing API with OAuth 2.0 authentication.
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


LINKEDIN_CAMPAIGNS = [
    {
        "id": "li_camp_001",
        "name": "Sponsored Content - B2B Lead Gen",
        "status": "ACTIVE",
        "budget": 30000.00,
        "spend": 26450.75,
        "impressions": 1200000,
        "clicks": 24000,
        "conversions": 1800.0,
        "objective": "LEAD_GENERATION",
        "start_date": "2024-10-01",
        "end_date": "2024-12-31",
    },
    {
        "id": "li_camp_002",
        "name": "Message Ads - Sales Outreach",
        "status": "ACTIVE",
        "budget": 15000.00,
        "spend": 12875.50,
        "impressions": 450000,
        "clicks": 13500,
        "conversions": 950.0,
        "objective": "WEBSITE_CONVERSIONS",
        "start_date": "2024-09-15",
        "end_date": None,
    },
    {
        "id": "li_camp_003",
        "name": "Video Ads - Thought Leadership",
        "status": "ACTIVE",
        "budget": 20000.00,
        "spend": 17234.25,
        "impressions": 2500000,
        "clicks": 50000,
        "conversions": 2200.0,
        "objective": "VIDEO_VIEWS",
        "start_date": "2024-11-01",
        "end_date": None,
    },
    {
        "id": "li_camp_004",
        "name": "Carousel Ads - Product Showcase",
        "status": "ACTIVE",
        "budget": 18000.00,
        "spend": 15650.00,
        "impressions": 1800000,
        "clicks": 36000,
        "conversions": 1450.0,
        "objective": "BRAND_AWARENESS",
        "start_date": "2024-10-15",
        "end_date": None,
    },
    {
        "id": "li_camp_005",
        "name": "Text Ads - Job Postings",
        "status": "PAUSED",
        "budget": 5000.00,
        "spend": 4850.00,
        "impressions": 800000,
        "clicks": 8000,
        "conversions": 320.0,
        "objective": "JOB_APPLICANTS",
        "start_date": "2024-08-01",
        "end_date": "2024-10-31",
    },
]

LINKEDIN_ACCOUNT = {
    "id": "li_acc_567890",
    "name": "Demo LinkedIn Ads Account",
    "currency": "USD",
    "timezone": "America/New_York",
    "status": "ACTIVE",
}


class LinkedInAdsConnector(BaseAdConnector):
    """
    LinkedIn Marketing API connector.
    
    Credentials needed:
    - LINKEDIN_CLIENT_ID: OAuth Client ID
    - LINKEDIN_CLIENT_SECRET: OAuth Client Secret
    - LINKEDIN_ACCESS_TOKEN: Access Token
    - LINKEDIN_AD_ACCOUNT_ID: Ad Account ID
    """
    
    PLATFORM_NAME = "linkedin_ads"
    API_VERSION = "v2"
    
    def __init__(self, use_mock: bool = None, **credentials):
        creds = {
            "client_id": credentials.get("client_id") or os.getenv("LINKEDIN_CLIENT_ID"),
            "client_secret": credentials.get("client_secret") or os.getenv("LINKEDIN_CLIENT_SECRET"),
            "access_token": credentials.get("access_token") or os.getenv("LINKEDIN_ACCESS_TOKEN"),
            "ad_account_id": credentials.get("ad_account_id") or os.getenv("LINKEDIN_AD_ACCOUNT_ID"),
        }
        super().__init__(use_mock=use_mock, **creds)
    
    def _validate_credentials(self) -> bool:
        required = ["access_token", "ad_account_id"]
        return all(self.credentials.get(k) for k in required)
    
    def _connect_real(self) -> ConnectionResult:
        try:
            import requests
            headers = {"Authorization": f"Bearer {self.credentials['access_token']}"}
            response = requests.get(
                "https://api.linkedin.com/v2/me",
                headers=headers,
                timeout=30
            )
            if response.status_code == 200:
                return ConnectionResult(
                    success=True, status=ConnectorStatus.CONNECTED,
                    message="Connected to LinkedIn Ads", platform=self.PLATFORM_NAME,
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
                platform=self.PLATFORM_NAME, account_id=LINKEDIN_ACCOUNT["id"],
                budget=c["budget"], spend=c["spend"], impressions=c["impressions"],
                clicks=c["clicks"], conversions=c["conversions"],
                start_date=datetime.strptime(c["start_date"], "%Y-%m-%d") if c.get("start_date") else None,
                end_date=datetime.strptime(c["end_date"], "%Y-%m-%d") if c.get("end_date") else None,
                objective=c["objective"],
            )
            for c in LINKEDIN_CAMPAIGNS
        ]
    
    def _get_mock_performance(self, start_date, end_date) -> PerformanceMetrics:
        total = {k: sum(c[k] for c in LINKEDIN_CAMPAIGNS) for k in ["spend", "impressions", "clicks", "conversions"]}
        return PerformanceMetrics(
            platform=self.PLATFORM_NAME, account_id=LINKEDIN_ACCOUNT["id"],
            date_range={"start": start_date.isoformat(), "end": end_date.isoformat()},
            spend=total["spend"], impressions=total["impressions"],
            clicks=total["clicks"], conversions=total["conversions"],
            revenue=total["conversions"] * 85.0,
        )
    
    def get_accounts(self) -> List[Dict[str, Any]]:
        return [LINKEDIN_ACCOUNT] if self.use_mock else []

    def get_ad_sets(self, campaign_id: str = None) -> List[Dict[str, Any]]:
        """Get ad sets (mock only) - treating as child of Campaign for hierarchy view."""
        if not self.use_mock:
            return []
            
        ad_sets = []
        campaigns = [c for c in LINKEDIN_CAMPAIGNS if not campaign_id or c["id"] == campaign_id]
        
        for camp in campaigns:
            # Create 2 ad sets per campaign
            for i in range(1, 3):
                ad_sets.append({
                    "id": f"{camp['id']}_aset_{i:03d}",
                    "name": f"{camp['name']} - Target Audience {i}",
                    "campaign_id": camp["id"],
                    "status": camp["status"],
                    "optimization_goal": camp["objective"],
                    "spend": camp["spend"] * 0.5,
                })
        return ad_sets

    def get_ads(self, campaign_id: str = None, ad_set_id: str = None) -> List[Dict[str, Any]]:
        """Get ads (mock only)."""
        if not self.use_mock:
            return []
            
        ads = []
        ad_sets = self.get_ad_sets(campaign_id)
        if ad_set_id:
            ad_sets = [aset for aset in ad_sets if aset["id"] == ad_set_id]
            
        for aset in ad_sets:
            # Create 3 ads per ad set
            for i in range(1, 4):
                spend = aset["spend"] / 3
                impressions = int(spend * 1000 / 35.0)  # CPM ~ $35 (LinkedIn is expensive)
                clicks = int(impressions * 0.008)       # CTR ~ 0.8%
                conversions = int(clicks * 0.08)        # CVR ~ 8%
                
                ads.append({
                    "id": f"{aset['id']}_ad_{i:03d}",
                    "name": f"{aset['name']} - Content {i}",
                    "ad_set_id": aset["id"],
                    "campaign_id": aset["campaign_id"],
                    "status": aset["status"],
                    "format": "SINGLE_IMAGE_AD",
                    "spend": spend,
                    "impressions": impressions,
                    "clicks": clicks,
                    "conversions": conversions,
                    "ctr": 0.008,
                    "cpc": spend / clicks if clicks > 0 else 0,
                    "cpa": spend / conversions if conversions > 0 else 0,
                })
        return ads
