"""
API v1 Router.
"""

from fastapi import APIRouter
from loguru import logger

# Create v1 router
router_v1 = APIRouter(prefix="/api/v1", tags=["v1"])

# Import and include sub-routers
from .auth import router as auth_router
from .campaigns import router as campaigns_router
from .user_management import router as user_management_router
from .api_keys import router as api_keys_router
from .webhooks import router as webhooks_router
from .intelligence import router as intelligence_router
from .dashboards import router as dashboards_router
from .connectors import router as connectors_router
from .health_check import router as health_check_router

router_v1.include_router(auth_router)
router_v1.include_router(campaigns_router)
router_v1.include_router(user_management_router)
router_v1.include_router(api_keys_router)
router_v1.include_router(webhooks_router)
router_v1.include_router(intelligence_router)
router_v1.include_router(dashboards_router)
router_v1.include_router(connectors_router)
router_v1.include_router(health_check_router)

from .databases import router as databases_router
router_v1.include_router(databases_router)

from .upload import router as upload_router
router_v1.include_router(upload_router)

from .orchestrator import router as orchestrator_router
router_v1.include_router(orchestrator_router)


__all__ = ['router_v1']

