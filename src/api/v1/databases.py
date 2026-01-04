from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
from src.data.database_connector import DatabaseConnector
from loguru import logger

router = APIRouter(prefix="/databases", tags=["databases"])

class ConnectionRequest(BaseModel):
    category: str
    type: str
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    # Additional fields for specific connectors
    account: Optional[str] = None
    warehouse: Optional[str] = None
    project_id: Optional[str] = None
    bucket: Optional[str] = None
    region: Optional[str] = None
    api_key: Optional[str] = None
    environment: Optional[str] = None
    
    # Extended fields
    http_path: Optional[str] = None
    token: Optional[str] = None
    catalog: Optional[str] = None
    container: Optional[str] = None
    connection_string: Optional[str] = None
    credentials_json: Optional[str] = None
    dataset: Optional[str] = None
    keyspace: Optional[str] = None
    file_path_or_memory: Optional[str] = None
    index_name: Optional[str] = None
    url: Optional[str] = None
    domain: Optional[str] = None
    
    # Platform / OAuth fields
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    developer_token: Optional[str] = None
    refresh_token: Optional[str] = None
    access_token: Optional[str] = None
    customer_id: Optional[str] = None
    ad_account_id: Optional[str] = None
    advertiser_id: Optional[str] = None
    channel_id: Optional[str] = None
    profile_id: Optional[str] = None
    partner_id: Optional[str] = None
    account_id: Optional[str] = None
    app_id: Optional[str] = None
    app_secret: Optional[str] = None
    api_secret: Optional[str] = None

class ConnectionResponse(BaseModel):
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None

@router.post("/test-connection", response_model=ConnectionResponse)
def test_connection(request: ConnectionRequest):
    """
    Test connection to a database or data source.
    """
    try:
        logger.info(f"Testing connection to {request.category}/{request.type}")
        
        # Determine if we have a real driver for this
        if request.type in DatabaseConnector.SUPPORTED_DATABASES:
            # Attempt real connection for supported types
            connector = DatabaseConnector()
            
            # Map request fields to connector args
            kwargs = {}
            if request.type == 'snowflake':
                kwargs['account'] = request.account
                kwargs['warehouse'] = request.warehouse
                kwargs['role'] = 'ACCOUNTADMIN' # Default or from request if added
            elif request.type == 'bigquery':
                kwargs['project_id'] = request.project_id
            
            try:
                # We reuse the build_connection_string logic but for now just validation
                # In a real scenario, we would call connector.connect()
                # For this task, we will mock the "Success" if fields are present, 
                # unless it's one we want to actually try (like the SQL ones if local).
                
                # For the purpose of this UI task, we will return a success mock 
                # if the basic required fields for that type are present.
                
                # Check if we should really test (e.g. Supabase/Postgres)
                # REAL CONNECTION TEST
                # Map standard request fields
                req_kwargs = _map_request_to_kwargs(request)
                kwargs.update(req_kwargs)
                
                logger.info(f"Attempting real connection to {request.type}...")
                connector.connect(db_type=request.type, **kwargs)
                
                # If connect() didn't raise, we are good
                return ConnectionResponse(
                    success=True, 
                    message=f"Successfully connected to {request.type}",
                    details={"status": "Connected"}
                )

            except Exception as e:
                logger.error(f"Connection error: {e}")
                return ConnectionResponse(success=False, message=str(e))
            finally:
                if 'connector' in locals():
                    connector.close()
        
        # For types NOT in DatabaseConnector yet (like Vector DBs), return Mock Success
        # if relevant fields are provided.
        if _validate_required_fields(request):
            return ConnectionResponse(
                success=True, 
                message=f"Successfully connected to {request.type} (Mock)",
                details={"status": "Online", "collections": ["demo_collection"]}
            )
        else:
             return ConnectionResponse(success=False, message="Missing required credentials")

    except Exception as e:
        logger.error(f"Test connection endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class SaveConnectionResponse(BaseModel):
    success: bool
    message: str
    connection_id: str

@router.post("/save-connection", response_model=SaveConnectionResponse)
def save_connection(request: ConnectionRequest):
    """
    Save a database connection.
    In a real app, this would securely store credentials.
    For this demo, we mock the persistence and return a success.
    """
    try:
        logger.info(f"Saving connection for {request.category}/{request.type}")
        
        # Validation
        if not _validate_required_fields(request):
             return SaveConnectionResponse(
                success=False, 
                message="Missing required fields",
                connection_id=""
            )

        # Mock ID generation
        import uuid
        conn_id = str(uuid.uuid4())
        
        # In a real scenario: save to DB/Vault
        # db.save_connection(conn_id, request.dict())
        
        return SaveConnectionResponse(
            success=True,
            message=f"Successfully saved {request.type} connection.",
            connection_id=conn_id
        )

    except Exception as e:
        logger.error(f"Save connection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tables")
def list_tables(request: ConnectionRequest):
    """List tables for a given connection."""
    try:
        # Mock for platforms not in connector
        if request.type not in DatabaseConnector.SUPPORTED_DATABASES:
             return {"success": True, "tables": ["mock_table_1", "mock_table_2"]}

        connector = DatabaseConnector()
        # Map fields (reuse logic or make helper)
        kwargs = _map_request_to_kwargs(request)
        
        try:
            connector.connect(db_type=request.type, **kwargs)
            tables = connector.get_tables()
            return {"success": True, "tables": tables}
        finally:
            connector.close()

    except Exception as e:
        logger.error(f"List tables error: {e}")
        return {"success": False, "message": str(e), "tables": []}

@router.post("/preview")
def preview_table(request: ConnectionRequest, table_name: str):
    """Preview data from a specific table."""
    try:
        # Mock for unsupported
        if request.type not in DatabaseConnector.SUPPORTED_DATABASES:
             return {
                 "success": True, 
                 "schema": [{"column": "col1", "dtype": "string"}, {"column": "col2", "dtype": "int"}],
                 "preview": [{"col1": "test", "col2": 1}, {"col1": "demo", "col2": 2}]
             }

        connector = DatabaseConnector()
        kwargs = _map_request_to_kwargs(request)
        
        try:
            connector.connect(db_type=request.type, **kwargs)
            df = connector.load_table(table_name, limit=5)
            
            # Simple schema
            schema = [{"column": col, "dtype": str(dtype)} for col, dtype in df.dtypes.items()]
            preview = df.replace({float('nan'): None}).to_dict(orient='records')
            
            return {"success": True, "schema": schema, "preview": preview}
        finally:
            connector.close()

    except Exception as e:
        return {"success": False, "message": str(e)}

@router.post("/import")
def import_table(
    request: ConnectionRequest, 
    table_name: str,
):
    """Import data from table into Analytics Engine."""
    """Import data from table into Analytics Engine."""
    try:
        from src.api.dependencies import get_campaign_service
        service = get_campaign_service()
        
        # Mock import for unsupported types
        if request.type not in DatabaseConnector.SUPPORTED_DATABASES:
             import pandas as pd
             import numpy as np
             from datetime import datetime, timedelta
             import random
             
             # Generate 50 rows of mock data
             data = []
             base_date = datetime.now() - timedelta(days=30)
             platforms = ['Google Ads', 'Meta Ads', 'LinkedIn Ads', 'TikTok Ads']
             if request.type in ['google_ads', 'meta_ads', 'linkedin_ads', 'tiktok_ads']:
                 platforms = [request.type.replace('_', ' ').title()]
                 
             for i in range(50):
                 date_val = base_date + timedelta(days=i % 30)
                 spend = round(random.uniform(100, 5000), 2)
                 imps = int(spend * random.uniform(50, 200))
                 clicks = int(imps * random.uniform(0.01, 0.05))
                 convs = int(clicks * random.uniform(0.05, 0.2))
                 
                 data.append({
                     "Campaign": f"Mock Campaign {i+1}",
                     "Platform": random.choice(platforms),
                     "Channel": "Social" if request.type in ['meta_ads', 'tiktok_ads'] else "Search",
                     "Status": "Active",
                     "Date": date_val.strftime("%Y-%m-%d"),
                     "Spend": spend,
                     "Impressions": imps,
                     "Clicks": clicks,
                     "Conversions": convs,
                     "ROAS": round(random.uniform(1.5, 8.0), 2)
                 })
                 
             df = pd.DataFrame(data)
             result = service.import_from_dataframe(df)
             result['message'] = f"Successfully imported {len(df)} mock records."
             return result

        connector = DatabaseConnector()
        kwargs = _map_request_to_kwargs(request)
        
        try:
            connector.connect(db_type=request.type, **kwargs)
            # Load full table (maybe add limit?)
            df = connector.load_table(table_name, limit=5000) 
            
            result = service.import_from_dataframe(df)
            return result
        finally:
            connector.close()

    except Exception as e:
        logger.error(f"Import error: {e}")
        return {"success": False, "message": str(e)}

def _map_request_to_kwargs(req: ConnectionRequest) -> Dict[str, Any]:
    """Helper to map Request model to Connector kwargs."""
    kwargs = {
        'host': req.host,
        'port': req.port,
        'database': req.database,
        'username': req.username,
        'password': req.password,
        'account': req.account,
        'warehouse': req.warehouse,
        'project_id': req.project_id,
        'token': req.token,
        'http_path': req.http_path,
        'bucket': req.bucket,
        'connection_string': req.connection_string,
        'credentials_json': req.credentials_json
    }
    # Clean None values and strip strings
    cleaned = {}
    for k, v in kwargs.items():
        if v is not None:
             if isinstance(v, str):
                 cleaned[k] = v.strip()
             else:
                 cleaned[k] = v
    return cleaned

def _validate_required_fields(req: ConnectionRequest) -> bool:
    """Helper to check if minimum fields are present for the type"""
    if req.category == 'warehouse':
        if req.type == 'snowflake':
            return bool(req.account and req.username and req.password)
        if req.type == 'databricks':
            return bool(req.host and req.token and req.http_path)
            
    if req.type in ['postgresql', 'mysql', 'mssql', 'clickhouse', 'redshift', 'azure_synapse', 'supabase']:
        return bool(req.host and req.username and req.password)
        
    if req.type == 'duckdb':
        return True 

    if req.category == 'vector':
        return bool(req.host or req.api_key or req.url)
        
    if req.category == 'storage':
        if req.type == 's3':
             return bool(req.bucket)
        if req.type == 'gcs':
             return bool(req.bucket)
        if req.type == 'azure_blob':
             return bool(req.connection_string or (req.account and req.api_key))
        if req.type == 'sftp':
             return bool(req.host and req.username and req.password)
             
    if req.category == 'services':
        if req.type == 'mailgun':
            return bool(req.api_key and req.domain)

    if req.category == 'platform':
        # General check: most platforms need an ID and a Token/Secret
        if req.type == 'google_ads':
            return bool(req.client_id and req.client_secret and req.developer_token and req.refresh_token)
        if req.type == 'meta_ads':
            return bool(req.access_token and req.ad_account_id)
        if req.type == 'linkedin_ads':
            return bool((req.access_token or (req.client_id and req.client_secret)))
        if req.type == 'tiktok_ads':
            return bool(req.access_token and req.advertiser_id)
        if req.type == 'snapchat_ads':
            return bool(req.client_id and req.client_secret)
        if req.type == 'twitter_ads':
            return bool(req.api_key and req.api_secret)
        # Fallback for others - check if at least one auth field is present
        return bool(req.access_token or req.api_key or req.client_id)
        
    return True
