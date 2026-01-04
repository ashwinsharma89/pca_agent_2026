"""
Database connection management with connection pooling.
"""

import os
import logging
from typing import Optional
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from src.database.models import Base

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration."""
    
    def __init__(self):
        self.host = os.getenv('DB_HOST', 'localhost')
        self.port = int(os.getenv('DB_PORT', '5432'))
        self.database = os.getenv('DB_NAME', 'pca_agent')
        self.user = os.getenv('DB_USER', 'postgres')
        self.password = os.getenv('DB_PASSWORD', '')
        
        # SSL Configuration (optional for secure PostgreSQL connections)
        self.ssl_mode = os.getenv('DB_SSL_MODE', '')  # e.g., 'require' for SSL
        
        # Connection pool settings
        self.pool_size = int(os.getenv('DB_POOL_SIZE', '5'))
        self.max_overflow = int(os.getenv('DB_MAX_OVERFLOW', '10'))
        self.pool_timeout = int(os.getenv('DB_POOL_TIMEOUT', '30'))
        self.pool_recycle = int(os.getenv('DB_POOL_RECYCLE', '3600'))
        
        # Connection pool settings
    
    def get_database_url(self) -> str:
        """Get database URL (PostgreSQL only)."""
        # Prioritize explicit URL
        env_url = os.getenv('DATABASE_URL')
        if env_url:
            return env_url
        
        # Build PostgreSQL URL from components
        base_url = f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        
        # Add SSL mode if specified
        if self.ssl_mode:
            base_url += f"?sslmode={self.ssl_mode}"
        
        return base_url



class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self.engine = None
        self.SessionLocal = None
        self._initialized = False
    
    def initialize(self):
        """Initialize database connection and create tables."""
        if self._initialized:
            logger.warning("Database already initialized")
            return
        
        try:
            database_url = self.config.get_database_url()
            logger.info(f"Connecting to database: {database_url.split('@')[-1] if '@' in database_url else database_url}")
            
            # Create engine with connection pooling
            self.engine = create_engine(
                database_url,
                poolclass=QueuePool,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle,
                echo=False
            )
            
            # Add connection event listeners
            @event.listens_for(self.engine, "connect")
            def receive_connect(dbapi_conn, connection_record):
                logger.debug("Database connection established")
            
            @event.listens_for(self.engine, "checkout")
            def receive_checkout(dbapi_conn, connection_record, connection_proxy):
                logger.debug("Connection checked out from pool")
            
            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            # Create tables
            Base.metadata.create_all(bind=self.engine)
            
            self._initialized = True
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Session:
        """
        Get a database session with automatic cleanup.
        
        Usage:
            with db_manager.get_session() as session:
                # Use session
                pass
        """
        if not self._initialized:
            self.initialize()
        
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Session error: {e}")
            raise
        finally:
            session.close()
    
    def get_session_direct(self) -> Session:
        """
        Get a database session (manual management required).
        Caller is responsible for closing the session.
        """
        if not self._initialized:
            self.initialize()
        
        return self.SessionLocal()
    
    def close(self):
        """Close database connections."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed")
            self._initialized = False
    
    def health_check(self) -> bool:
        """
        Check database connectivity with circuit breaker protection.
        Prevents cascading failures during database outages.
        """
        try:
            from src.utils.circuit_breaker import database_circuit
            from sqlalchemy import text
            
            # Use circuit breaker to prevent hammering a failed database
            with database_circuit:
                with self.get_session() as session:
                    session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get or create global database manager instance.
    
    Returns None-like manager if DB is unavailable (allows app to start).
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        try:
            _db_manager.initialize()
        except Exception as e:
            logger.warning(f"⚠️ PostgreSQL unavailable: {e}")
            logger.warning("App will continue - DuckDB/Parquet features work without SQL database")
            # Don't raise - let app continue without SQL DB
            # Features using SQL will fail gracefully
    return _db_manager


def get_db_session() -> Session:
    """Get a database session (for dependency injection)."""
    db_manager = get_db_manager()
    return db_manager.get_session_direct()


def get_db():
    """
    FastAPI dependency for database session.
    
    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            # Use db session
            pass
    """
    db_manager = get_db_manager()
    db = db_manager.get_session_direct()
    try:
        yield db
        db.commit()  # Commit changes before closing
    except Exception as e:
        db.rollback()  # Rollback on error
        raise
    finally:
        db.close()
