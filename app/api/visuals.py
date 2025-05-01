"""API endpoints for visual asset generation and management."""
import logging
import os
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, File, UploadFile, Form
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from app.api.dependencies import get_rate_limiter, get_article_run
from app.models.article_run import ArticleRunStatus
from app.services.visuals import ChartGenerator, ImageGenerator, VisualizationExecutor, VisualCache
from app.services.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/visuals", tags=["visuals"])

# Create services
chart_generator = ChartGenerator()
image_generator = ImageGenerator()
visualization_executor = VisualizationExecutor()
visual_cache = VisualCache()


class ChartRequest(BaseModel):
    """Chart generation request model."""

    chart_type: str = Field(..., description="Type of chart (bar, line, pie, etc.)")
    data: Dict[str, Any] = Field(..., description="Data for the chart")
    title: str = Field(..., description="Chart title")
    subtitle: Optional[str] = Field(None, description="Chart subtitle")
    width: int = Field(800, description="Chart width in pixels")
    height: int = Field(600, description="Chart height in pixels")
    cache: bool = Field(True, description="Whether to cache the result")
    article_id: Optional[uuid.UUID] = Field(None, description="ID of the associated article")


class ImageRequest(BaseModel):
    """Image generation request model."""

    prompt: str = Field(..., description="Description of the image to generate")
    style: str = Field("vintage", description="Style of the image")
    size: str = Field("1024x1024", description="Size of the image")
    quality: str = Field("standard", description="Image quality")
    cache: bool = Field(True, description="Whether to cache the result")
    article_id: Optional[uuid.UUID] = Field(None, description="ID of the associated article")


class CodeExecutionRequest(BaseModel):
    """Code execution request model."""

    code: str = Field(..., description="Python code to execute")
    timeout: int = Field(10, description="Execution timeout in seconds")
    max_memory_mb: int = Field(100, description="Maximum memory usage in MB")
    cache: bool = Field(True, description="Whether to cache the result")
    article_id: Optional[uuid.UUID] = Field(None, description="ID of the associated article")


@router.post("/chart", response_model=Dict[str, Any])
async def generate_chart(
    request: ChartRequest,
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> Dict[str, Any]:
    """Generate a chart.

    Args:
        request (ChartRequest): Chart generation request

    Returns:
        Dict[str, Any]: Chart generation result with path to the chart image
    """
    # Apply rate limiting
    await rate_limiter.check_rate_limit("chart")

    # Check if the result is in the cache
    if request.cache:
        cache_key = f"chart_{request.chart_type}_{hash(str(request.data))}_{request.title}"
        cached_path = visual_cache.get(cache_key)
        if cached_path:
            logger.info("Returning cached chart: %s", cached_path)
            return {
                "success": True,
                "path": cached_path,
                "cached": True,
            }

    try:
        # Generate the chart
        chart_path, figure = chart_generator.create_chart(
            chart_type=request.chart_type,
            data=request.data,
            title=request.title,
            subtitle=request.subtitle,
            width=request.width / 100,  # Convert to inches (assuming 100 DPI)
            height=request.height / 100,
        )

        # Close the figure to free memory
        chart_generator.close_figure(figure)

        # Add the result to the cache if requested
        if request.cache:
            cache_key = f"chart_{request.chart_type}_{hash(str(request.data))}_{request.title}"
            visual_cache.put(cache_key, chart_path)

        return {
            "success": True,
            "path": chart_path,
            "cached": False,
        }

    except Exception as e:
        logger.error("Chart generation failed: %s", e)
        raise HTTPException(
            status_code=500, 
            detail=f"Chart generation failed: {str(e)}"
        )


@router.post("/image", response_model=Dict[str, Any])
async def generate_image(
    request: ImageRequest,
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> Dict[str, Any]:
    """Generate an image using AI.

    Args:
        request (ImageRequest): Image generation request

    Returns:
        Dict[str, Any]: Image generation result with path to the image
    """
    # Apply rate limiting
    await rate_limiter.check_rate_limit("image")

    # Check if the result is in the cache
    if request.cache:
        cache_key = f"image_{request.prompt}_{request.style}_{request.size}"
        cached_path = visual_cache.get(cache_key)
        if cached_path:
            logger.info("Returning cached image: %s", cached_path)
            return {
                "success": True,
                "path": cached_path,
                "cached": True,
            }

    try:
        # Generate the image
        image_path = await image_generator.generate_image(
            prompt=request.prompt,
            style=request.style,
            size=request.size,
            quality=request.quality,
        )

        # Add the result to the cache if requested
        if request.cache:
            cache_key = f"image_{request.prompt}_{request.style}_{request.size}"
            visual_cache.put(cache_key, image_path)

        return {
            "success": True,
            "path": image_path,
            "cached": False,
        }

    except Exception as e:
        logger.error("Image generation failed: %s", e)
        raise HTTPException(
            status_code=500, 
            detail=f"Image generation failed: {str(e)}"
        )


@router.post("/execute", response_model=Dict[str, Any])
async def execute_code(
    request: CodeExecutionRequest,
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> Dict[str, Any]:
    """Execute Python code for visualization.

    Args:
        request (CodeExecutionRequest): Code execution request

    Returns:
        Dict[str, Any]: Code execution result with paths to generated figures
    """
    # Apply rate limiting
    await rate_limiter.check_rate_limit("execute")

    # Check if the result is in the cache
    if request.cache:
        cache_key = f"execute_{hash(request.code)}_{request.timeout}_{request.max_memory_mb}"
        cached_path = visual_cache.get(cache_key)
        if cached_path and os.path.isfile(cached_path):
            # For code execution, we cache the result object as JSON
            try:
                import json
                with open(cached_path, "r") as f:
                    result = json.load(f)
                
                logger.info("Returning cached execution result: %s", cached_path)
                result["cached"] = True
                return result
            except (json.JSONDecodeError, IOError) as e:
                logger.error("Failed to read cached execution result: %s", e)
                # Continue with execution if cache read fails

    try:
        # Execute the code
        result = visualization_executor.execute_code(
            code=request.code,
            timeout=request.timeout,
            max_memory_mb=request.max_memory_mb,
        )

        # Add cached flag
        result["cached"] = False

        # Add the result to the cache if requested
        if request.cache:
            try:
                # Save the result object as JSON
                import json
                import tempfile
                
                with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
                    json.dump(result, f)
                    temp_path = f.name
                
                cache_key = f"execute_{hash(request.code)}_{request.timeout}_{request.max_memory_mb}"
                visual_cache.put(cache_key, temp_path)
                
                # Clean up the temporary file
                os.unlink(temp_path)
            except Exception as e:
                logger.error("Failed to cache execution result: %s", e)

        return result

    except Exception as e:
        logger.error("Code execution failed: %s", e)
        raise HTTPException(
            status_code=500, 
            detail=f"Code execution failed: {str(e)}"
        )


@router.get("/asset/{path:path}", response_class=FileResponse)
async def get_visual_asset(
    path: str,
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> FileResponse:
    """Get a visual asset by path.

    Args:
        path (str): Path to the asset

    Returns:
        FileResponse: The visual asset
    """
    # Apply rate limiting
    await rate_limiter.check_rate_limit("get_asset")

    # Check if the file exists
    if not os.path.isfile(path):
        raise HTTPException(
            status_code=404, 
            detail=f"Asset not found: {path}"
        )

    # Return the file
    return FileResponse(path)


@router.post("/upload", response_model=Dict[str, Any])
async def upload_visual_asset(
    file: UploadFile = File(...),
    article_id: Optional[str] = Form(None),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> Dict[str, Any]:
    """Upload a visual asset.

    Args:
        file (UploadFile): The file to upload
        article_id (Optional[str], optional): ID of the associated article. Defaults to None.

    Returns:
        Dict[str, Any]: Upload result with path to the saved asset
    """
    # Apply rate limiting
    await rate_limiter.check_rate_limit("upload")

    try:
        # Generate a unique ID for the asset
        asset_id = str(uuid.uuid4())
        
        # Get the file extension
        _, ext = os.path.splitext(file.filename)
        if not ext:
            ext = ".png"  # Default extension
        
        # Create the save path
        save_dir = os.path.join("data", "visuals", "uploads")
        os.makedirs(save_dir, exist_ok=True)
        
        save_path = os.path.join(save_dir, f"{asset_id}{ext}")
        
        # Save the file
        with open(save_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        return {
            "success": True,
            "path": save_path,
            "original_filename": file.filename,
            "article_id": article_id,
        }
        
    except Exception as e:
        logger.error("File upload failed: %s", e)
        raise HTTPException(
            status_code=500, 
            detail=f"File upload failed: {str(e)}"
        )


@router.delete("/cache", response_model=Dict[str, Any])
async def clear_cache(
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> Dict[str, Any]:
    """Clear the visual asset cache.

    Returns:
        Dict[str, Any]: Operation result
    """
    # Apply rate limiting
    await rate_limiter.check_rate_limit("clear_cache")

    try:
        # Clear the cache
        visual_cache.clear()
        
        return {
            "success": True,
            "message": "Cache cleared successfully",
        }
        
    except Exception as e:
        logger.error("Cache clearing failed: %s", e)
        raise HTTPException(
            status_code=500, 
            detail=f"Cache clearing failed: {str(e)}"
        )


@router.get("/cache/stats", response_model=Dict[str, Any])
async def get_cache_stats(
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> Dict[str, Any]:
    """Get cache statistics.

    Returns:
        Dict[str, Any]: Cache statistics
    """
    # Apply rate limiting
    await rate_limiter.check_rate_limit("cache_stats")

    try:
        # Get cache stats
        stats = visual_cache.get_stats()
        
        return {
            "success": True,
            "stats": stats,
        }
        
    except Exception as e:
        logger.error("Failed to get cache stats: %s", e)
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get cache stats: {str(e)}"
        ) 