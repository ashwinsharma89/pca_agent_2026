"""
Ingestion Adapters (Layer 1)

Provides distinct adapters for different data sources:
- CSV/Excel files (with encoding detection)
- API responses (async, paginated)
- Database connections (server-side cursor)

Design Pattern: Adapter Pattern
Output: Yields pandas DataFrames in uniform chunks
"""

import pandas as pd
import polars as pl
from pathlib import Path
from typing import Iterator, Dict, Any, Optional, List, AsyncIterator
from loguru import logger
from abc import ABC, abstractmethod
import io


class BaseAdapter(ABC):
    """Base class for all ingestion adapters."""
    
    def __init__(self, chunk_size: int = 10000):
        self.chunk_size = chunk_size
    
    @abstractmethod
    def read_chunks(self) -> Iterator[pd.DataFrame]:
        """Yield DataFrames in chunks."""
        pass
    
    @property
    @abstractmethod
    def source_type(self) -> str:
        """Return the source type identifier."""
        pass


class CSVAdapter(BaseAdapter):
    """
    Adapter for CSV files with encoding detection.
    
    Features:
    - Auto-detects encoding (utf-8, latin-1, etc.)
    - Uses Polars for fast parsing with error recovery
    - Chunks large files for memory efficiency
    """
    
    def __init__(
        self,
        file_path: str | Path,
        chunk_size: int = 10000,
        encoding: Optional[str] = None
    ):
        super().__init__(chunk_size)
        self.file_path = Path(file_path)
        self.encoding = encoding
    
    @property
    def source_type(self) -> str:
        return "csv"
    
    def _detect_encoding(self) -> str:
        """Detect file encoding using chardet (first 10KB sample)."""
        if self.encoding:
            return self.encoding
        
        try:
            import chardet
            with open(self.file_path, 'rb') as f:
                sample = f.read(10240)  # 10KB sample
                result = chardet.detect(sample)
                detected = result.get('encoding', 'utf-8')
                confidence = result.get('confidence', 0)
                logger.info(f"Detected encoding: {detected} (confidence: {confidence:.1%})")
                return detected if confidence > 0.7 else 'utf-8'
        except ImportError:
            logger.warning("chardet not installed, defaulting to utf-8")
            return 'utf-8'
    
    def read_chunks(self) -> Iterator[pd.DataFrame]:
        """Read CSV in chunks using Polars for speed."""
        encoding = self._detect_encoding()
        
        try:
            # Use Polars lazy API for streaming
            lf = pl.scan_csv(
                self.file_path,
                encoding=encoding if encoding != 'utf-8-sig' else 'utf-8',
                ignore_errors=True,  # Recoverable parsing
                infer_schema_length=1000
            )
            
            # Get total rows for chunking
            total_rows = lf.select(pl.count()).collect().item()
            
            for offset in range(0, total_rows, self.chunk_size):
                chunk = lf.slice(offset, self.chunk_size).collect()
                yield chunk.to_pandas()
                
        except Exception as e:
            logger.warning(f"Polars failed, falling back to pandas: {e}")
            # Fallback to pandas chunked reading
            for chunk in pd.read_csv(
                self.file_path,
                encoding=encoding,
                chunksize=self.chunk_size,
                on_bad_lines='warn'
            ):
                yield chunk


class ExcelAdapter(BaseAdapter):
    """
    Adapter for Excel files (xlsx, xls).
    
    Features:
    - Sheet selection
    - Uses openpyxl for xlsx, xlrd for xls
    - Chunks large sheets
    """
    
    def __init__(
        self,
        file_path: str | Path,
        sheet_name: Optional[str] = None,
        chunk_size: int = 10000
    ):
        super().__init__(chunk_size)
        self.file_path = Path(file_path)
        self.sheet_name = sheet_name
    
    @property
    def source_type(self) -> str:
        return "excel"
    
    def get_sheet_names(self) -> List[str]:
        """Get list of available sheets."""
        return pd.ExcelFile(self.file_path).sheet_names
    
    def read_chunks(self) -> Iterator[pd.DataFrame]:
        """Read Excel sheet in chunks."""
        # Excel doesn't support native chunking, so we read all and chunk
        df = pd.read_excel(
            self.file_path,
            sheet_name=self.sheet_name or 0
        )
        
        total_rows = len(df)
        for start in range(0, total_rows, self.chunk_size):
            yield df.iloc[start:start + self.chunk_size]


class APIAdapter(BaseAdapter):
    """
    Adapter for API responses (async, paginated).
    
    Features:
    - Async generator for paginated APIs
    - JSON flattening with pd.json_normalize
    - Batch processing (1000 items)
    """
    
    def __init__(
        self,
        api_responses: List[Dict[str, Any]] | Iterator[Dict[str, Any]],
        data_key: Optional[str] = None,
        chunk_size: int = 1000
    ):
        super().__init__(chunk_size)
        self.api_responses = api_responses
        self.data_key = data_key  # Key to extract data array from response
    
    @property
    def source_type(self) -> str:
        return "api"
    
    def read_chunks(self) -> Iterator[pd.DataFrame]:
        """Flatten and yield API responses as DataFrames."""
        batch = []
        
        for response in self.api_responses:
            # Extract data from response
            data = response.get(self.data_key, response) if self.data_key else response
            
            if isinstance(data, list):
                batch.extend(data)
            else:
                batch.append(data)
            
            # Yield when batch is full
            while len(batch) >= self.chunk_size:
                chunk_data = batch[:self.chunk_size]
                batch = batch[self.chunk_size:]
                yield pd.json_normalize(chunk_data)
        
        # Yield remaining
        if batch:
            yield pd.json_normalize(batch)


class DatabaseAdapter(BaseAdapter):
    """
    Adapter for database connections with server-side cursors.
    
    Features:
    - Server-side cursor for memory efficiency
    - Type mapping (TIMESTAMPTZ -> datetime64[ns])
    - Connection pooling support
    """
    
    def __init__(
        self,
        connection,
        query: str,
        chunk_size: int = 2000
    ):
        super().__init__(chunk_size)
        self.connection = connection
        self.query = query
    
    @property
    def source_type(self) -> str:
        return "database"
    
    def read_chunks(self) -> Iterator[pd.DataFrame]:
        """Read query results using server-side cursor."""
        try:
            cursor = self.connection.cursor(name='ingestion_cursor')
            cursor.itersize = self.chunk_size
            
            cursor.execute(self.query)
            columns = [desc[0] for desc in cursor.description]
            
            while True:
                rows = cursor.fetchmany(self.chunk_size)
                if not rows:
                    break
                
                df = pd.DataFrame(rows, columns=columns)
                yield self._map_types(df)
            
            cursor.close()
            
        except Exception as e:
            logger.error(f"Database read failed: {e}")
            raise
    
    def _map_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Map database types to pandas types."""
        for col in df.columns:
            # Convert timestamp columns
            if df[col].dtype == 'object':
                try:
                    df[col] = pd.to_datetime(df[col], errors='ignore')
                except Exception:
                    pass
        return df


class BytesAdapter(BaseAdapter):
    """
    Adapter for in-memory bytes (from file uploads).
    
    Features:
    - Handles both CSV and Excel from bytes
    - Auto-detects format from filename or content
    """
    
    def __init__(
        self,
        data: bytes,
        filename: str,
        sheet_name: Optional[str] = None,
        chunk_size: int = 10000
    ):
        super().__init__(chunk_size)
        self.data = data
        self.filename = filename
        self.sheet_name = sheet_name
    
    @property
    def source_type(self) -> str:
        ext = Path(self.filename).suffix.lower()
        return "excel" if ext in ['.xlsx', '.xls'] else "csv"
    
    def read_chunks(self) -> Iterator[pd.DataFrame]:
        """Read bytes data in chunks."""
        ext = Path(self.filename).suffix.lower()
        
        if ext in ['.xlsx', '.xls']:
            # Excel from bytes
            df = pd.read_excel(
                io.BytesIO(self.data),
                sheet_name=self.sheet_name or 0
            )
            for start in range(0, len(df), self.chunk_size):
                yield df.iloc[start:start + self.chunk_size]
        else:
            # CSV from bytes
            df = pd.read_csv(io.BytesIO(self.data))
            for start in range(0, len(df), self.chunk_size):
                yield df.iloc[start:start + self.chunk_size]


def get_adapter(
    source: str | Path | bytes,
    source_type: Optional[str] = None,
    **kwargs
) -> BaseAdapter:
    """
    Factory function to get the appropriate adapter.
    
    Args:
        source: File path, bytes, or connection
        source_type: Optional type hint ('csv', 'excel', 'api', 'database')
        **kwargs: Additional arguments for the adapter
    
    Returns:
        Appropriate adapter instance
    """
    if isinstance(source, bytes):
        return BytesAdapter(source, kwargs.pop('filename', 'data.csv'), **kwargs)
    
    if isinstance(source, (str, Path)):
        path = Path(source)
        ext = path.suffix.lower()
        
        if ext == '.csv':
            return CSVAdapter(path, **kwargs)
        elif ext in ['.xlsx', '.xls']:
            return ExcelAdapter(path, **kwargs)
    
    raise ValueError(f"Could not determine adapter for source: {source}")
