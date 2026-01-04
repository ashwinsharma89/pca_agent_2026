"""
Database connector for loading campaign data from various database sources.
Supports PostgreSQL, MySQL, SQLite, SQL Server, and more.
"""

import pandas as pd
from typing import Optional, Dict, Any, List
from loguru import logger
import sqlalchemy
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus


class DatabaseConnector:
    """Connect to various databases and load campaign data."""
    
    SUPPORTED_DATABASES = {
        # Traditional Databases
        'postgresql': 'PostgreSQL',
        'mysql': 'MySQL',
        'sqlite': 'SQLite',
        'mssql': 'SQL Server',
        'oracle': 'Oracle',
        'supabase': 'Supabase',
        
        # Modern Data Warehouses
        'duckdb': 'DuckDB',
        'snowflake': 'Snowflake',
        'bigquery': 'Google BigQuery',
        'redshift': 'AWS Redshift',
        'databricks': 'Databricks',
        
        # Cloud Storage
        's3': 'AWS S3',
        'azure_blob': 'Azure Blob Storage',
        'gcs': 'Google Cloud Storage'
    }
    
    def __init__(self):
        """Initialize database connector."""
        self.engine = None
        self.connection_string = None
    
    def build_connection_string(
        self,
        db_type: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: str = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        file_path: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Build database connection string.
        
        Args:
            db_type: Database type (postgresql, mysql, sqlite, mssql, oracle)
            host: Database host
            port: Database port
            database: Database name
            username: Database username
            password: Database password
            file_path: File path for SQLite
            **kwargs: Additional connection parameters
            
        Returns:
            Connection string
        """
        db_type = db_type.lower()
        
        if db_type not in self.SUPPORTED_DATABASES and db_type != 'postgresql': # Handle aliased
             # Re-check if it was original key
             if db_type == 'postgresql' and 'supabase' in self.SUPPORTED_DATABASES:
                 pass
             else:
                raise ValueError(f"Unsupported database type: {db_type}. Supported: {list(self.SUPPORTED_DATABASES.keys())}")
        
        # SQLite
        if db_type == 'sqlite':
            if not file_path:
                raise ValueError("file_path is required for SQLite")
            return f"sqlite:///{file_path}"
        
        # Other databases require credentials
        if not all([host, database, username, password]):
            raise ValueError(f"{db_type} requires host, database, username, and password")
        
        # Encode password for special characters
        encoded_password = quote_plus(password)
        
        # PostgreSQL
        if db_type == 'postgresql':
            port = port or 5432
            return f"postgresql://{username}:{encoded_password}@{host}:{port}/{database}"
        
        # MySQL
        elif db_type == 'mysql':
            port = port or 3306
            driver = kwargs.get('driver', 'pymysql')
            return f"mysql+{driver}://{username}:{encoded_password}@{host}:{port}/{database}"
        
        # SQL Server
        elif db_type == 'mssql':
            port = port or 1433
            driver = kwargs.get('driver', 'ODBC Driver 17 for SQL Server')
            return f"mssql+pyodbc://{username}:{encoded_password}@{host}:{port}/{database}?driver={quote_plus(driver)}"
        
        # Oracle
        elif db_type == 'oracle':
            port = port or 1521
            return f"oracle+cx_oracle://{username}:{encoded_password}@{host}:{port}/{database}"
        
        # DuckDB (file-based or in-memory)
        elif db_type == 'duckdb':
            file_path = kwargs.get('file_path', ':memory:')
            return f"duckdb:///{file_path}"
        
        # Snowflake
        elif db_type == 'snowflake':
            account = kwargs.get('account')
            warehouse = kwargs.get('warehouse')
            schema = kwargs.get('schema', 'public')
            role = kwargs.get('role')
            
            if not account:
                raise ValueError("Snowflake requires 'account' parameter")
            
            conn_str = f"snowflake://{username}:{encoded_password}@{account}/{database}/{schema}"
            
            params = []
            if warehouse:
                params.append(f"warehouse={warehouse}")
            if role:
                params.append(f"role={role}")
            
            if params:
                conn_str += "?" + "&".join(params)
            
            return conn_str
        
        # Google BigQuery
        elif db_type == 'bigquery':
            project_id = kwargs.get('project_id') or database
            credentials_path = kwargs.get('credentials_path')
            
            if credentials_path:
                return f"bigquery://{project_id}?credentials_path={credentials_path}"
            else:
                # Use default credentials
                return f"bigquery://{project_id}"
        
        # AWS Redshift
        elif db_type == 'redshift':
            port = port or 5439
            return f"redshift+psycopg2://{username}:{encoded_password}@{host}:{port}/{database}"
        
        # Databricks
        elif db_type == 'databricks':
            http_path = kwargs.get('http_path')
            token = kwargs.get('token') or password
            
            if not http_path:
                raise ValueError("Databricks requires 'http_path' parameter")
            
            return f"databricks://token:{token}@{host}?http_path={http_path}&catalog={database}"
            
        # Supabase (PostgreSQL with forced SSL)
        elif db_type == 'supabase':
            port = port or 5432
            # Supabase requires SSL - Use explicit driver to match debug script success
            return f"postgresql+psycopg2://{username}:{encoded_password}@{host}:{port}/{database}?sslmode=require"
        
        return None
    
    def connect(
        self,
        connection_string: Optional[str] = None,
        db_type: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        Connect to database.
        
        Args:
            connection_string: Pre-built connection string
            db_type: Database type (if building connection string)
            **kwargs: Connection parameters for build_connection_string
            
        Returns:
            True if connection successful
        """
        try:
            if connection_string:
                self.connection_string = connection_string
                # Auto-fix Supabase SSL & Encoding
                if 'supabase.co' in self.connection_string:
                    try:
                        from sqlalchemy.engine.url import make_url
                        u = make_url(self.connection_string)
                        
                        # Apply SSL
                        query = u.query.copy()
                        query['sslmode'] = 'require'
                        u = u._replace(query=query)
                        
                        # Ensure driver is specified if missing
                        if u.drivername == 'postgresql':
                             u = u._replace(drivername='postgresql+psycopg2')
                        
                        # Force re-render which handles encoding
                        self.connection_string = u.render_as_string(hide_password=False)
                        
                        logger.info(f"Fixed Supabase connection string: {u.render_as_string(hide_password=True)}")
                    except Exception as e:
                        logger.warning(f"Failed to auto-fix Supabase string: {e}")

            elif db_type:
                self.connection_string = self.build_connection_string(db_type, **kwargs)
            else:
                raise ValueError("Either connection_string or db_type must be provided")
            
            logger.info(f"Connecting to database...")
            
            # Simple create_engine, relying on the robust string we built
            self.engine = create_engine(self.connection_string)
            
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            logger.success("✅ Database connection successful!")
            return True
            
        except Exception as e:
            # Redact password for safe logging
            safe_conn_str = "REDACTED"
            if self.connection_string:
                try:
                    from sqlalchemy.engine.url import make_url
                    safe_conn_str = make_url(self.connection_string).render_as_string(hide_password=True)
                except:
                    pass
            
            logger.error(f"❌ Database connection failed: {e}")
            self.engine = None
            # Re-raise with safe string for UI
            raise Exception(f"Connection failed to {safe_conn_str}. Error: {str(e)}")
    
    def get_tables(self) -> List[str]:
        """
        Get list of tables in the database.
        
        Returns:
            List of table names
        """
        if not self.engine:
            raise ValueError("Not connected to database. Call connect() first.")
        
        try:
            inspector = sqlalchemy.inspect(self.engine)
            tables = inspector.get_table_names()
            logger.info(f"Found {len(tables)} tables in database")
            return tables
        except Exception as e:
            logger.error(f"Failed to get tables: {e}")
            raise
    
    def get_table_schema(self, table_name: str) -> pd.DataFrame:
        """
        Get schema information for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            DataFrame with column information
        """
        if not self.engine:
            raise ValueError("Not connected to database. Call connect() first.")
        
        try:
            inspector = sqlalchemy.inspect(self.engine)
            columns = inspector.get_columns(table_name)
            
            schema_df = pd.DataFrame([
                {
                    'column_name': col['name'],
                    'data_type': str(col['type']),
                    'nullable': col['nullable']
                }
                for col in columns
            ])
            
            return schema_df
        except Exception as e:
            logger.error(f"Failed to get schema for {table_name}: {e}")
            raise
    
    def execute_query(self, query: str, params: Optional[Dict] = None) -> pd.DataFrame:
        """
        Execute SQL query and return results as DataFrame.
        
        Args:
            query: SQL query to execute
            params: Query parameters (for parameterized queries)
            
        Returns:
            DataFrame with query results
        """
        if not self.engine:
            raise ValueError("Not connected to database. Call connect() first.")
        
        try:
            logger.info(f"Executing query: {query[:100]}...")
            
            with self.engine.connect() as conn:
                if params:
                    result = pd.read_sql(text(query), conn, params=params)
                else:
                    result = pd.read_sql(text(query), conn)
            
            logger.success(f"✅ Query executed successfully. Rows: {len(result)}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Query execution failed: {e}")
            raise
    
    def load_table(self, table_name: str, limit: Optional[int] = None) -> pd.DataFrame:
        """
        Load entire table or limited rows.
        
        Args:
            table_name: Name of the table
            limit: Maximum number of rows to load
            
        Returns:
            DataFrame with table data
        """
        query = f'SELECT * FROM "{table_name}"'  # nosec B608
        if limit:
            query += f" LIMIT {limit}"
        
        return self.execute_query(query)
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test database connection and return info.
        
        Returns:
            Dictionary with connection info
        """
        if not self.engine:
            return {'connected': False, 'error': 'Not connected'}
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            
            tables = self.get_tables()
            
            return {
                'connected': True,
                'database_type': self.engine.dialect.name,
                'table_count': len(tables),
                'tables': tables[:10]  # First 10 tables
            }
        except Exception as e:
            return {
                'connected': False,
                'error': str(e)
            }
    
    def load_from_s3(
        self,
        s3_path: str,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = 'us-east-1',
        **read_kwargs
    ) -> pd.DataFrame:
        """
        Load data from AWS S3.
        
        Args:
            s3_path: S3 path (s3://bucket/path/to/file.csv)
            aws_access_key_id: AWS access key
            aws_secret_access_key: AWS secret key
            region_name: AWS region
            **read_kwargs: Additional arguments for pd.read_csv/read_parquet
            
        Returns:
            DataFrame with data from S3
        """
        try:
            import boto3
            from io import BytesIO
            
            # Parse S3 path
            if not s3_path.startswith('s3://'):
                raise ValueError("S3 path must start with 's3://'")
            
            path_parts = s3_path[5:].split('/', 1)
            bucket = path_parts[0]
            key = path_parts[1] if len(path_parts) > 1 else ''
            
            # Create S3 client
            if aws_access_key_id and aws_secret_access_key:
                s3_client = boto3.client(
                    's3',
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    region_name=region_name
                )
            else:
                # Use default credentials
                s3_client = boto3.client('s3', region_name=region_name)
            
            # Download file
            logger.info(f"Loading data from S3: {s3_path}")
            obj = s3_client.get_object(Bucket=bucket, Key=key)
            data = obj['Body'].read()
            
            # Determine file type and read
            if key.endswith('.csv'):
                df = pd.read_csv(BytesIO(data), **read_kwargs)
            elif key.endswith('.parquet'):
                df = pd.read_parquet(BytesIO(data), **read_kwargs)
            elif key.endswith('.json'):
                df = pd.read_json(BytesIO(data), **read_kwargs)
            else:
                raise ValueError(f"Unsupported file type: {key}")
            
            logger.success(f"✅ Loaded {len(df)} rows from S3")
            return df
            
        except Exception as e:
            logger.error(f"❌ Failed to load from S3: {e}")
            raise
    
    def load_from_azure_blob(
        self,
        container_name: str,
        blob_name: str,
        connection_string: Optional[str] = None,
        account_name: Optional[str] = None,
        account_key: Optional[str] = None,
        **read_kwargs
    ) -> pd.DataFrame:
        """
        Load data from Azure Blob Storage.
        
        Args:
            container_name: Azure container name
            blob_name: Blob name (path to file)
            connection_string: Azure connection string
            account_name: Azure account name
            account_key: Azure account key
            **read_kwargs: Additional arguments for pd.read_csv/read_parquet
            
        Returns:
            DataFrame with data from Azure
        """
        try:
            from azure.storage.blob import BlobServiceClient
            from io import BytesIO
            
            # Create blob service client
            if connection_string:
                blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            elif account_name and account_key:
                blob_service_client = BlobServiceClient(
                    account_url=f"https://{account_name}.blob.core.windows.net",
                    credential=account_key
                )
            else:
                raise ValueError("Either connection_string or (account_name + account_key) required")
            
            # Download blob
            logger.info(f"Loading data from Azure: {container_name}/{blob_name}")
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            data = blob_client.download_blob().readall()
            
            # Determine file type and read
            if blob_name.endswith('.csv'):
                df = pd.read_csv(BytesIO(data), **read_kwargs)
            elif blob_name.endswith('.parquet'):
                df = pd.read_parquet(BytesIO(data), **read_kwargs)
            elif blob_name.endswith('.json'):
                df = pd.read_json(BytesIO(data), **read_kwargs)
            else:
                raise ValueError(f"Unsupported file type: {blob_name}")
            
            logger.success(f"✅ Loaded {len(df)} rows from Azure")
            return df
            
        except Exception as e:
            logger.error(f"❌ Failed to load from Azure: {e}")
            raise
    
    def load_from_gcs(
        self,
        bucket_name: str,
        blob_name: str,
        credentials_path: Optional[str] = None,
        **read_kwargs
    ) -> pd.DataFrame:
        """
        Load data from Google Cloud Storage.
        
        Args:
            bucket_name: GCS bucket name
            blob_name: Blob name (path to file)
            credentials_path: Path to service account JSON
            **read_kwargs: Additional arguments for pd.read_csv/read_parquet
            
        Returns:
            DataFrame with data from GCS
        """
        try:
            from google.cloud import storage
            from io import BytesIO
            
            # Create storage client
            if credentials_path:
                storage_client = storage.Client.from_service_account_json(credentials_path)
            else:
                # Use default credentials
                storage_client = storage.Client()
            
            # Download blob
            logger.info(f"Loading data from GCS: gs://{bucket_name}/{blob_name}")
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            data = blob.download_as_bytes()
            
            # Determine file type and read
            if blob_name.endswith('.csv'):
                df = pd.read_csv(BytesIO(data), **read_kwargs)
            elif blob_name.endswith('.parquet'):
                df = pd.read_parquet(BytesIO(data), **read_kwargs)
            elif blob_name.endswith('.json'):
                df = pd.read_json(BytesIO(data), **read_kwargs)
            else:
                raise ValueError(f"Unsupported file type: {blob_name}")
            
            logger.success(f"✅ Loaded {len(df)} rows from GCS")
            return df
            
        except Exception as e:
            logger.error(f"❌ Failed to load from GCS: {e}")
            raise
    
    def close(self):
        """Close database connection."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed")
            self.engine = None


# Convenience functions
def connect_to_database(
    db_type: str,
    host: Optional[str] = None,
    port: Optional[int] = None,
    database: str = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    file_path: Optional[str] = None,
    **kwargs
) -> DatabaseConnector:
    """
    Quick connect to database.
    
    Returns:
        Connected DatabaseConnector instance
    """
    connector = DatabaseConnector()
    connector.connect(
        db_type=db_type,
        host=host,
        port=port,
        database=database,
        username=username,
        password=password,
        file_path=file_path,
        **kwargs
    )
    return connector


def load_from_database(
    query: str,
    db_type: str,
    host: Optional[str] = None,
    port: Optional[int] = None,
    database: str = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    file_path: Optional[str] = None,
    **kwargs
) -> pd.DataFrame:
    """
    Quick load data from database with query.
    
    Returns:
        DataFrame with query results
    """
    connector = connect_to_database(
        db_type=db_type,
        host=host,
        port=port,
        database=database,
        username=username,
        password=password,
        file_path=file_path,
        **kwargs
    )
    
    try:
        df = connector.execute_query(query)
        return df
    finally:
        connector.close()
