"""
Ad Platform Connector API Endpoints.

Provides REST API for testing connections and fetching data
from Google Ads, Meta Ads, Campaign Manager 360, and DV360.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from loguru import logger

from src.connectors import AdConnectorManager


router = APIRouter(prefix="/connectors", tags=["Ad Platform Connectors"])


# =============================================================================
# Request/Response Models
# =============================================================================

class TestConnectionRequest(BaseModel):
    """Request to test a specific connector."""
    platform: str = Field(..., description="Platform to test: google_ads, meta_ads, campaign_manager, dv360")
    mock_mode: bool = Field(True, description="Use mock mode for testing without real credentials")


class ConnectionStatusResponse(BaseModel):
    """Response for connection status."""
    success: bool
    status: str
    message: str
    platform: str
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    is_mock: bool
    permissions: List[str] = []
    error_details: Optional[str] = None


class AllConnectionsResponse(BaseModel):
    """Response for all connections status."""
    platforms: dict
    summary: dict


class CampaignResponse(BaseModel):
    """Campaign data response."""
    id: str
    name: str
    status: str
    platform: str
    account_id: str
    budget: float
    spend: float
    impressions: int
    clicks: int
    conversions: float
    ctr: float
    cpc: float
    cpa: float
    objective: Optional[str] = None


class PerformanceResponse(BaseModel):
    """Aggregated performance response."""
    totals: dict
    by_platform: dict
    date_range: dict
    is_mock: bool


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/test", response_model=ConnectionStatusResponse)
async def test_connection(request: TestConnectionRequest):
    """
    Test connection to a specific ad platform.
    
    Use mock_mode=true for testing without real credentials.
    """
    logger.info(f"Testing connection for {request.platform}", mock_mode=request.mock_mode)
    
    try:
        manager = AdConnectorManager(
            use_mock=request.mock_mode,
            platforms=[request.platform]
        )
        
        result = manager.test_connection(request.platform)
        
        return ConnectionStatusResponse(
            success=result.success,
            status=result.status.value,
            message=result.message,
            platform=result.platform,
            account_id=result.account_id,
            account_name=result.account_name,
            is_mock=result.is_mock,
            permissions=result.permissions,
            error_details=result.error_details,
        )
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=AllConnectionsResponse)
async def get_all_connection_status(mock_mode: bool = Query(True, description="Use mock mode")):
    """
    Get connection status for all configured ad platforms.
    """
    try:
        manager = AdConnectorManager(use_mock=mock_mode)
        status = manager.get_connection_status()
        
        # Calculate summary
        total = len(status)
        connected = sum(1 for s in status.values() if s["connected"])
        
        return AllConnectionsResponse(
            platforms=status,
            summary={
                "total_platforms": total,
                "connected": connected,
                "disconnected": total - connected,
                "mock_mode": mock_mode,
            }
        )
    except Exception as e:
        logger.error(f"Failed to get connection status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{platform}/campaigns", response_model=List[CampaignResponse])
async def get_platform_campaigns(
    platform: str,
    mock_mode: bool = Query(True, description="Use mock mode"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
):
    """
    Get campaigns from a specific ad platform.
    """
    supported = list(AdConnectorManager.SUPPORTED_PLATFORMS.keys())
    if platform not in supported:
        raise HTTPException(
            status_code=400, 
            detail=f"Unknown platform: {platform}. Supported: {supported}"
        )
    
    try:
        manager = AdConnectorManager(use_mock=mock_mode, platforms=[platform])
        
        # Parse dates if provided
        start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
        
        campaigns_dict = manager.get_campaigns([platform], start_dt, end_dt)
        campaigns = campaigns_dict.get(platform, [])
        
        return [
            CampaignResponse(
                id=c.id,
                name=c.name,
                status=c.status,
                platform=c.platform,
                account_id=c.account_id,
                budget=c.budget,
                spend=c.spend,
                impressions=c.impressions,
                clicks=c.clicks,
                conversions=c.conversions,
                ctr=round(c.ctr, 2),
                cpc=round(c.cpc, 2),
                cpa=round(c.cpa, 2),
                objective=c.objective,
            )
            for c in campaigns
        ]
    except Exception as e:
        logger.error(f"Failed to get campaigns from {platform}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/campaigns/all")
async def get_all_campaigns(
    mock_mode: bool = Query(True, description="Use mock mode"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
):
    """
    Get campaigns from all ad platforms.
    """
    try:
        manager = AdConnectorManager(use_mock=mock_mode)
        
        start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
        
        all_campaigns = manager.get_all_campaigns(start_dt, end_dt)
        
        return {
            "total_campaigns": len(all_campaigns),
            "by_platform": {
                platform: len([c for c in all_campaigns if c.platform == platform])
                for platform in AdConnectorManager.SUPPORTED_PLATFORMS.keys()
            },
            "campaigns": [c.to_dict() for c in all_campaigns],
            "is_mock": mock_mode,
        }
    except Exception as e:
        logger.error(f"Failed to get all campaigns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance", response_model=PerformanceResponse)
async def get_aggregated_performance(
    mock_mode: bool = Query(True, description="Use mock mode"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    platforms: Optional[str] = Query(None, description="Comma-separated list of platforms"),
):
    """
    Get aggregated performance metrics across all platforms.
    """
    try:
        platform_list = platforms.split(",") if platforms else None
        
        manager = AdConnectorManager(use_mock=mock_mode, platforms=platform_list)
        
        start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
        
        performance = manager.get_aggregated_performance(start_dt, end_dt)
        
        return PerformanceResponse(**performance)
    except Exception as e:
        logger.error(f"Failed to get performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{platform}/accounts")
async def get_platform_accounts(
    platform: str,
    mock_mode: bool = Query(True, description="Use mock mode"),
):
    """
    Get accessible accounts for a specific platform.
    """
    supported = list(AdConnectorManager.SUPPORTED_PLATFORMS.keys())
    if platform not in supported:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown platform: {platform}. Supported: {supported}"
        )
    
    try:
        manager = AdConnectorManager(use_mock=mock_mode, platforms=[platform])
        connector = manager.get_connector(platform)
        
        if not connector:
            raise HTTPException(status_code=404, detail=f"Connector not found: {platform}")
        
        accounts = connector.get_accounts()
        
        return {
            "platform": platform,
            "accounts": accounts,
            "is_mock": mock_mode,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get accounts for {platform}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{platform}/ads")
async def get_platform_ads(
    platform: str,
    mock_mode: bool = Query(True, description="Use mock mode"),
    campaign_id: Optional[str] = Query(None, description="Filter by campaign ID"),
    ad_group_id: Optional[str] = Query(None, description="Filter by ad group/ad set ID (Google: ad_group_id, Meta: ad_set_id)"),
):
    """
    Get ads for a specific platform, optionally filtered by campaign or ad group/set.
    Supported: google_ads, meta_ads, snapchat_ads, amazon_dsp
    """
    ads_supported = ["google_ads", "meta_ads", "snapchat_ads", "amazon_dsp"]
    if platform not in ads_supported:
        raise HTTPException(
            status_code=400,
            detail=f"Ad-level data not yet available for: {platform}. Supported: {ads_supported}"
        )
    
    try:
        manager = AdConnectorManager(use_mock=mock_mode, platforms=[platform])
        connector = manager.get_connector(platform)
        
        if not connector or not hasattr(connector, 'get_ads'):
            raise HTTPException(status_code=501, detail=f"get_ads not implemented for {platform}")
        
        # Handle different parameter names for different platforms
        if platform == "meta_ads":
            ads = connector.get_ads(campaign_id=campaign_id, ad_set_id=ad_group_id)
        elif platform == "google_ads":
            ads = connector.get_ads(campaign_id=campaign_id, ad_group_id=ad_group_id)
        else:
            ads = connector.get_ads(campaign_id=campaign_id)
        
        return {
            "platform": platform,
            "campaign_id": campaign_id,
            "ad_group_id": ad_group_id,
            "total_ads": len(ads),
            "ads": ads,
            "is_mock": mock_mode,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get ads for {platform}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{platform}/ad_groups")
async def get_platform_ad_groups(
    platform: str,
    mock_mode: bool = Query(True, description="Use mock mode"),
    campaign_id: Optional[str] = Query(None, description="Filter by campaign ID"),
):
    """
    Get ad groups (Google Ads) or ad sets (Meta Ads).
    Supported: google_ads, meta_ads
    """
    supported = ["google_ads", "meta_ads"]
    if platform not in supported:
        raise HTTPException(
            status_code=400,
            detail=f"Ad group data not available for: {platform}. Supported: {supported}"
        )
    
    try:
        manager = AdConnectorManager(use_mock=mock_mode, platforms=[platform])
        connector = manager.get_connector(platform)
        
        if not connector:
            raise HTTPException(status_code=404, detail=f"Connector not found: {platform}")
        
        # Use appropriate method based on platform
        if platform == "google_ads":
            if not hasattr(connector, 'get_ad_groups'):
                raise HTTPException(status_code=501, detail="get_ad_groups not implemented")
            data = connector.get_ad_groups(campaign_id=campaign_id)
            level_name = "ad_groups"
        else:  # meta_ads
            if not hasattr(connector, 'get_ad_sets'):
                raise HTTPException(status_code=501, detail="get_ad_sets not implemented")
            data = connector.get_ad_sets(campaign_id=campaign_id)
            level_name = "ad_sets"
        
        return {
            "platform": platform,
            "campaign_id": campaign_id,
            "level": level_name,
            f"total_{level_name}": len(data),
            level_name: data,
            "is_mock": mock_mode,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get ad groups for {platform}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{platform}/hierarchy")
async def get_platform_hierarchy(
    platform: str,
    mock_mode: bool = Query(True, description="Use mock mode"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    lookback_days: Optional[int] = Query(None, description="Lookback window in days (overrides date range)"),
    campaign_id: Optional[str] = Query(None, description="Filter by campaign ID"),
    columns: Optional[str] = Query(None, description="Comma-separated columns to include"),
):
    """
    Get flattened hierarchy data: Campaign → Ad Group/Ad Set → Ad in single rows.
    Supports Google Ads (campaign→ad_group→ad) and Meta Ads (campaign→ad_set→ad).
    """
    supported = ["google_ads", "meta_ads", "tiktok_ads", "linkedin_ads"]
    if platform not in supported:
        raise HTTPException(
            status_code=400,
            detail=f"Hierarchy view available for: {supported}. Platform: {platform}"
        )
    
    try:
        manager = AdConnectorManager(use_mock=mock_mode, platforms=[platform])
        connector = manager.get_connector(platform)
        
        if not connector:
            raise HTTPException(status_code=404, detail=f"Connector not found: {platform}")
        
        # Calculate date range
        if lookback_days:
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=lookback_days)
        else:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
        
        # Fetch all levels
        campaigns = connector.get_campaigns(start_dt, end_dt)
        campaign_lookup = {c.id: c for c in campaigns}
        
        # Build flattened rows
        rows = []
        
        if platform == "google_ads" or platform == "tiktok_ads":
            # TikTok uses similar structure to Google (Ad Groups)
            ad_groups = connector.get_ad_groups(campaign_id=campaign_id)
            ads = connector.get_ads(campaign_id=campaign_id)
            ad_group_lookup = {ag["id"]: ag for ag in ad_groups}
            
            for ad in ads:
                ag = ad_group_lookup.get(ad.get("ad_group_id"), {})
                camp = campaign_lookup.get(ad.get("campaign_id"))
                
                row = {
                    "campaign_id": ad.get("campaign_id"), 
                    "campaign_name": camp.name if camp else "",
                    "campaign_status": camp.status if camp else "",
                    "campaign_objective": camp.objective if camp else "",
                    "campaign_budget": camp.budget if camp else 0,
                    "campaign_spend": camp.spend if camp else 0,
                    "ad_group_id": ad.get("ad_group_id"),
                    "ad_group_name": ag.get("name", ""),
                    "ad_group_status": ag.get("status", ""),
                    "ad_group_type": ag.get("type", ""),
                    "ad_group_spend": ag.get("spend", 0),
                    "ad_id": ad.get("id"),
                    "ad_name": ad.get("name"),
                    "ad_status": ad.get("status"),
                    "ad_type": ad.get("type"),
                    "ad_spend": ad.get("spend", 0),
                    "ad_impressions": ad.get("impressions", 0),
                    "ad_clicks": ad.get("clicks", 0),
                    "ad_conversions": ad.get("conversions", 0),
                    "ad_ctr": ad.get("ctr", 0),
                    "ad_cpc": ad.get("cpc", 0),
                    "ad_cpa": ad.get("cpa", 0),
                }
                rows.append(row)
        
        else:  # meta_ads or linkedin_ads
            # LinkedIn uses similar structure to Meta (Ad Sets)
            ad_sets = connector.get_ad_sets(campaign_id=campaign_id)
            ads = connector.get_ads(campaign_id=campaign_id)
            ad_set_lookup = {aset["id"]: aset for aset in ad_sets}
            
            for ad in ads:
                aset = ad_set_lookup.get(ad.get("ad_set_id"), {})
                camp = campaign_lookup.get(ad.get("campaign_id"))
                
                row = {
                    "campaign_id": ad.get("campaign_id"),
                    "campaign_name": camp.name if camp else "",
                    "campaign_status": camp.status if camp else "",
                    "campaign_objective": camp.objective if camp else "",
                    "campaign_budget": camp.budget if camp else 0,
                    "campaign_spend": camp.spend if camp else 0,
                    "ad_set_id": ad.get("ad_set_id"),
                    "ad_set_name": aset.get("name", ""),
                    "ad_set_status": aset.get("status", ""),
                    "ad_set_optimization": aset.get("optimization_goal", ""),
                    "ad_set_spend": aset.get("spend", 0),
                    "ad_id": ad.get("id"),
                    "ad_name": ad.get("name"),
                    "ad_status": ad.get("status"),
                    "ad_format": ad.get("format"),
                    "ad_spend": ad.get("spend", 0),
                    "ad_impressions": ad.get("impressions", 0),
                    "ad_clicks": ad.get("clicks", 0),
                    "ad_conversions": ad.get("conversions", 0),
                    "ad_ctr": ad.get("ctr", 0),
                    "ad_cpc": ad.get("cpc", 0),
                    "ad_cpa": ad.get("cpa", 0),
                }
                rows.append(row)
        
        # Filter columns if specified
        if columns:
            col_list = [c.strip() for c in columns.split(",")]
            rows = [{k: v for k, v in row.items() if k in col_list} for row in rows]
        
        return {
            "platform": platform,
            "total_rows": len(rows),
            "columns": list(rows[0].keys()) if rows else [],
            "data": rows,
            "filters": {
                "campaign_id": campaign_id,
                "start_date": start_dt.isoformat() if start_dt else None,
                "end_date": end_dt.isoformat() if end_dt else None,
                "lookback_days": lookback_days,
            },
            "is_mock": mock_mode,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get hierarchy for {platform}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

