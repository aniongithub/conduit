import os
import sys
import io
import tempfile
import traceback
from pathlib import Path
from typing import Dict, Any, Union, List
import uvicorn
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from contextlib import redirect_stdout, redirect_stderr

from .pipeline import Pipeline
from .common import logger, set_log_level


class PipelineRequest(BaseModel):
    """Request model for pipeline execution"""
    pipeline: Union[List[Dict[str, Any]], Dict[str, Any], str]  # Can be list (JSON array), dict (JSON object), or string (YAML)
    args: Dict[str, str] = {}
    working_directory: str = None
    stop_on_error: bool = True


class PipelineResponse(BaseModel):
    """Response model for pipeline execution"""
    success: bool
    results: Any = None
    error: str = None
    logs: str = ""
    stdout: List[str] = []
    stderr: List[str] = []
    stats: Dict[str, Any] = {}


# Global working directory for server
_server_working_directory = None

app = FastAPI(
    title="Conduit Pipeline Server",
    description="Execute Conduit data pipelines via REST API",
    version="1.0.0"
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Conduit Pipeline Server", "status": "running"}


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/run", response_model=PipelineResponse)
async def run_pipeline(request: PipelineRequest):
    """
    Execute a pipeline configuration
    
    Accepts either:
    - JSON pipeline configuration (dict)
    - YAML pipeline configuration (string)
    """
    try:
        # Set working directory
        original_cwd = os.getcwd()
        working_dir = request.working_directory or _server_working_directory or original_cwd
        os.chdir(working_dir)
        
        # Set environment args
        for key, value in request.args.items():
            os.environ[key] = value
        
        # Capture stdout, stderr, and logs
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        log_capture = io.StringIO()
        
        # Handle pipeline configuration
        if isinstance(request.pipeline, list):
            # Direct JSON pipeline array (most common)
            pipeline = Pipeline(request.pipeline, stop_on_error=request.stop_on_error)
        elif isinstance(request.pipeline, dict):
            # JSON pipeline as single object - wrap in list
            pipeline = Pipeline([request.pipeline], stop_on_error=request.stop_on_error)
        elif isinstance(request.pipeline, str):
            # YAML string - write to temp file and load
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                f.write(request.pipeline)
                temp_path = f.name
            
            try:
                pipeline = Pipeline.from_config(temp_path, expand_env=True, stop_on_error=request.stop_on_error)
            finally:
                os.unlink(temp_path)
        else:
            raise HTTPException(status_code=400, detail="Pipeline must be either list (JSON array), dict (JSON object), or string (YAML)")
        
        # Execute pipeline with output capture and collect all results
        results = []
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            # Use process() to get the generator, not run() which only returns the last result
            pipeline_generator = pipeline.process([None])
            # Collect all results from the streaming pipeline
            for result in pipeline_generator:
                results.append(result)
        
        # Finalize stats and extract them
        pipeline.finalize_stats()
        stats = {}
        if hasattr(pipeline, 'stats') and pipeline.stats:
            stats = {
                "duration": pipeline.stats.duration,
                "total_items_processed": pipeline.stats.total_items_processed,
                "total_elements": len(pipeline.stats.element_metrics),
                "throughput": pipeline.stats.total_items_processed / pipeline.stats.duration if pipeline.stats.duration > 0 else 0,
                "element_metrics": [
                    {
                        "element_id": m.element_id,
                        "duration": m.duration,
                        "items_processed": m.items_processed,
                        "throughput": m.items_processed / m.duration if m.duration > 0 else 0
                    }
                    for m in pipeline.stats.element_metrics
                ]
            }
        
        return PipelineResponse(
            success=True,
            results=results,  # Return all collected results
            logs="",  # TODO: Capture actual log messages
            stdout=stdout_capture.getvalue().strip().split('\n') if stdout_capture.getvalue().strip() else [],
            stderr=stderr_capture.getvalue().strip().split('\n') if stderr_capture.getvalue().strip() else [],
            stats=stats
        )
        
    except Exception as e:
        logger().error(f"Pipeline execution failed: {str(e)}", exc_info=e)
        return PipelineResponse(
            success=False,
            error=str(e),
            logs=traceback.format_exc(),
            stdout=[],
            stderr=[],
            stats={}
        )
    finally:
        # Restore working directory
        os.chdir(original_cwd)


@app.get("/schema")
async def get_schema():
    """
    Get the current pipeline schema for available elements
    """
    try:
        from .schema_generator import generate_schema
        schema = generate_schema()
        return schema
    except Exception as e:
        logger().error(f"Schema generation failed: {str(e)}", exc_info=e)
        raise HTTPException(status_code=500, detail=f"Schema generation failed: {str(e)}")


def start_server(host: str = "127.0.0.1", port: int = 8000, working_directory: str = None):
    """
    Start the Conduit FastAPI server
    
    Args:
        host: Host to bind to
        port: Port to bind to  
        working_directory: Default working directory for pipeline execution
    """
    global _server_working_directory
    _server_working_directory = working_directory
    
    logger().info(f"Starting Conduit server on {host}:{port}")
    if working_directory:
        logger().info(f"Default working directory: {working_directory}")
    
    # Configure uvicorn logging to match conduit logging
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": "INFO",
                "handlers": ["default"],
            },
        }
    )