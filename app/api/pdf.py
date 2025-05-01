"""PDF export API endpoints."""
import logging
import os
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.api.dependencies import get_rate_limiter, get_article_run
from app.models.article_run import ArticleRunStatus
from app.services.newspaper_renderer import NewspaperRenderer
from app.services.pdf_generator import PDFGenerator
from app.services.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pdf", tags=["pdf"])

# Create services
pdf_generator = PDFGenerator()
newspaper_renderer = NewspaperRenderer()


class PDFExportRequest(BaseModel):
    """PDF export request model."""
    
    paper_format: str = Field(
        "tabloid", 
        description="Paper size format (tabloid, broadsheet, berliner, letter, a4, a3)"
    )
    newspaper_name: Optional[str] = Field(
        None, 
        description="Custom newspaper name for the PDF"
    )


async def cleanup_temp_pdf(file_path: str) -> None:
    """Clean up temporary PDF file after it has been served.
    
    Args:
        file_path (str): Path to the PDF file to delete
    """
    try:
        # Only delete if it's in the temporary directory
        if os.path.dirname(file_path) == pdf_generator.cache_dir:
            os.unlink(file_path)
            logger.debug(f"Deleted temporary PDF file: {file_path}")
    except Exception as e:
        logger.error(f"Failed to delete temporary PDF file {file_path}: {e}")


@router.post("/export/{article_id}")
async def export_article_to_pdf(
    article_id: UUID,
    request: PDFExportRequest,
    background_tasks: BackgroundTasks,
    fastapi_request: Request,
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> FileResponse:
    """Export an article to PDF.
    
    Args:
        article_id (UUID): ID of the article to export
        request (PDFExportRequest): PDF export options
        background_tasks (BackgroundTasks): FastAPI background tasks
        fastapi_request (Request): FastAPI request object
        rate_limiter (RateLimiter, optional): Rate limiter. Defaults to Depends(get_rate_limiter).
        
    Returns:
        FileResponse: PDF file response
        
    Raises:
        HTTPException: If article is not found or not ready
    """
    await rate_limiter(fastapi_request)
    
    try:
        # Get the article
        article_run = await get_article_run(article_id)
        
        if not article_run:
            raise HTTPException(status_code=404, detail="Article not found")
            
        if article_run.status != ArticleRunStatus.COMPLETED:
            raise HTTPException(
                status_code=400, 
                detail=f"Article is not ready for export (status: {article_run.status})"
            )
        
        # Render article to HTML
        html = newspaper_renderer.render_article(article_run.article)
        
        # Use the article title if available, otherwise the ID
        title = article_run.article.title or f"Article_{article_id}"
        
        # Generate a clean filename
        safe_title = "".join([c if c.isalnum() or c == "_" else "_" for c in title])
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"{safe_title}_{date_str}.pdf"
        
        # Generate PDF from HTML
        newspaper_name = request.newspaper_name or "FoglioAI Gazette"
        pdf_path, from_cache = await pdf_generator.generate_pdf(
            html=html,
            paper_size=request.paper_format,
            print_background=True,
            display_header_footer=True,
            header_template=f"""
            <div style="width: 100%; font-family: 'Old Standard TT', serif; font-size: 8pt; text-align: center; color: #888;">
                {newspaper_name}
            </div>
            """,
            footer_template="""
            <div style="width: 100%; font-family: 'Old Standard TT', serif; font-size: 8pt; 
                 display: flex; justify-content: space-between; padding: 0 1cm;">
                <span></span>
                <span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>
            </div>
            """
        )
        
        # Add cleanup task for temporary files (if not from cache)
        if not from_cache:
            background_tasks.add_task(cleanup_temp_pdf, pdf_path)
        
        # Return the PDF file
        return FileResponse(
            path=pdf_path,
            filename=filename,
            media_type="application/pdf",
            background=background_tasks
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export article {article_id} to PDF: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate PDF")


@router.post("/export/newspaper/{article_id}")
async def export_newspaper_to_pdf(
    article_id: UUID,
    request: PDFExportRequest,
    background_tasks: BackgroundTasks,
    fastapi_request: Request,
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> FileResponse:
    """Export an article with newspaper styling to PDF.
    
    Args:
        article_id (UUID): ID of the article to export
        request (PDFExportRequest): PDF export options
        background_tasks (BackgroundTasks): FastAPI background tasks
        fastapi_request (Request): FastAPI request object
        rate_limiter (RateLimiter, optional): Rate limiter. Defaults to Depends(get_rate_limiter).
        
    Returns:
        FileResponse: PDF file response
        
    Raises:
        HTTPException: If article is not found or not ready
    """
    await rate_limiter(fastapi_request)
    
    try:
        # Get the article
        article_run = await get_article_run(article_id)
        
        if not article_run:
            raise HTTPException(status_code=404, detail="Article not found")
            
        if article_run.status != ArticleRunStatus.COMPLETED:
            raise HTTPException(
                status_code=400, 
                detail=f"Article is not ready for export (status: {article_run.status})"
            )
        
        # Use the vintage newspaper renderer
        html = newspaper_renderer.render_article(
            article_run.article,
            use_external_css=True  # Use the external CSS for proper styling
        )
        
        # Use the article title if available, otherwise the ID
        title = article_run.article.title or f"Article_{article_id}"
        
        # Generate a clean filename
        safe_title = "".join([c if c.isalnum() or c == "_" else "_" for c in title])
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"{safe_title}_newspaper_{date_str}.pdf"
        
        # Use the convenience method for newspaper PDFs
        newspaper_name = request.newspaper_name or "FoglioAI Gazette"
        pdf_path = await pdf_generator.generate_newspaper_pdf(
            html=html,
            newspaper_name=newspaper_name,
            paper_format=request.paper_format
        )
        
        # Add cleanup task for temporary files
        background_tasks.add_task(cleanup_temp_pdf, pdf_path)
        
        # Return the PDF file
        return FileResponse(
            path=pdf_path,
            filename=filename,
            media_type="application/pdf",
            background=background_tasks
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export newspaper {article_id} to PDF: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate newspaper PDF") 