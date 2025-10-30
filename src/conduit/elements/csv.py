"""CSV reading element for Conduit.

Reads CSV files and yields each row as a dictionary.
"""

import csv
import io
from dataclasses import dataclass
from typing import Iterator, Optional, Union, Any, Dict
from pathlib import Path

from ..pipelineElement import PipelineElement


@dataclass
class CsvReaderInput:
    """Input for CSVReader element.
    
    All fields are optional except input - if not provided, will use defaults from constructor.
    This allows global configuration via constructor with per-datum overrides.
    """
    # Can be a filename path, a file-like object (BytesIO/file), or a dict
    # containing 'file_obj' or 'local_path' keys (from download elements)
    input: Any
    delimiter: Optional[str] = None
    quotechar: Optional[str] = None
    encoding: Optional[str] = None
    skip_empty_rows: Optional[bool] = None
    fieldnames: Optional[list] = None


class CsvReader(PipelineElement):
    """Read CSV files and yield each row as a dictionary.
    
    Accepts filenames, file-like objects, or dicts from download elements.
    Uses Python's built-in csv.DictReader for robust CSV parsing.
    """
    
    def __init__(self,
                 delimiter: str = ',',
                 quotechar: str = '"',
                 encoding: str = 'utf-8',
                 skip_empty_rows: bool = True,
                 fieldnames: Optional[list] = None):
        """Initialize CSV reader.
        
        Args:
            delimiter: Field delimiter character (default: ',')
            quotechar: Quote character for fields (default: '"')
            encoding: Text encoding for file reading (default: 'utf-8')
            skip_empty_rows: Skip rows with all empty values (default: True)
            fieldnames: Custom field names (if None, uses first row as header)
        """
        super().__init__()  # Automatically captures all constructor parameters
    
    def _get_text_stream(self, input_item: Any, encoding: str):
        """Convert various input types to a text stream for csv.DictReader.
        
        Handles:
        - String paths to files
        - File-like objects (BytesIO from downloads)
        - Dicts with 'file_obj', 'local_path', or 'remote_path' keys
        
        Args:
            input_item: The input to convert
            encoding: Text encoding to use
        """
        # If it's a dict (from download elements), extract the file reference
        if isinstance(input_item, dict):
            # Try file_obj first (memory mode downloads)
            if 'file_obj' in input_item:
                file_obj = input_item['file_obj']
                # If it's a BytesIO, wrap it in TextIOWrapper
                if hasattr(file_obj, 'read') and hasattr(file_obj, 'mode'):
                    # Already a file object
                    return io.TextIOWrapper(file_obj, encoding=encoding)
                elif isinstance(file_obj, (io.BytesIO, io.BufferedReader)):
                    # Seek to start if possible
                    if hasattr(file_obj, 'seek'):
                        file_obj.seek(0)
                    return io.TextIOWrapper(file_obj, encoding=encoding)
                else:
                    # Try to treat as text stream
                    return file_obj
            
            # Try local_path (temp/local mode downloads)
            if 'local_path' in input_item:
                return open(input_item['local_path'], 'r', encoding=encoding)
            
            # Try remote_path or path (for compatibility)
            if 'remote_path' in input_item:
                return open(input_item['remote_path'], 'r', encoding=encoding)
            if 'path' in input_item:
                return open(input_item['path'], 'r', encoding=encoding)
        
        # If it's a string, treat as filename
        if isinstance(input_item, str):
            return open(input_item, 'r', encoding=encoding)
        
        # If it's already a file-like object
        if hasattr(input_item, 'read'):
            # If it's binary, wrap in TextIOWrapper
            if isinstance(input_item, (io.BytesIO, io.BufferedReader)):
                if hasattr(input_item, 'seek'):
                    input_item.seek(0)
                return io.TextIOWrapper(input_item, encoding=encoding)
            # Otherwise assume it's already text
            return input_item
        
        raise ValueError(f"Unsupported input type for CsvReader: {type(input_item)}")
    
    def process(self, input: Iterator[CsvReaderInput]) -> Iterator[Dict[str, Any]]:
        """Process CSV inputs and yield each row as a dictionary.
        
        Args:
            input: Iterator of CsvReaderInput items
            
        Yields:
            dict: Each CSV row as a dictionary with column names as keys
        """
        for csv_input in input:
            # Apply constructor defaults to None fields
            csv_input = self.apply_defaults(csv_input)
            
            text_stream = None
            should_close = False
            
            try:
                # Get a text stream from the input using per-datum encoding
                text_stream = self._get_text_stream(csv_input.input, csv_input.encoding)
                
                # Mark for closing if we opened a file
                if isinstance(csv_input.input, str) or (isinstance(csv_input.input, dict) and 
                    any(k in csv_input.input for k in ['local_path', 'remote_path', 'path'])):
                    should_close = True
                
                # Create CSV DictReader with per-datum parameters
                reader = csv.DictReader(
                    text_stream,
                    delimiter=csv_input.delimiter,
                    quotechar=csv_input.quotechar,
                    fieldnames=csv_input.fieldnames
                )
                
                # Yield each row
                for row in reader:
                    # Skip empty rows if requested
                    if csv_input.skip_empty_rows and all(not v for v in row.values()):
                        continue
                    yield dict(row)
            
            except Exception as e:
                self.logger.error(f"Error reading CSV from {csv_input.input}: {e}")
                # Optionally yield an error record
                yield {'error': True, 'message': str(e), 'input': str(csv_input.input)}
            
            finally:
                # Clean up file handles
                if should_close and text_stream:
                    try:
                        text_stream.close()
                    except Exception:
                        pass
