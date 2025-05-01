"""FoglioAI API main module."""
import logging
from time import sleep
from uuid import UUID

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import article, editor, pdf, visuals
from app.settings import STATIC_DIR, TEMPLATES_DIR
from app.storage.article_run import get_recent_article_runs, get_article_run

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Create the FastAPI app
app = FastAPI(
    title="FoglioAI",
    description="Vintage newspaper-style article generator using AI agents",
    version="0.1.0",
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Set up templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Include API routers
app.include_router(article.router)
app.include_router(editor.router)
app.include_router(pdf.router)
app.include_router(visuals.router)


# Error handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions.

    Args:
        request (Request): The request object
        exc (StarletteHTTPException): The exception

    Returns:
        TemplateResponse: The rendered template
    """
    if exc.status_code == 404:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request},
            status_code=404,
        )
    return templates.TemplateResponse(
        "errors/500.html",
        {"request": request},
        status_code=exc.status_code,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation exceptions.

    Args:
        request (Request): The request object
        exc (RequestValidationError): The exception

    Returns:
        TemplateResponse: The rendered template
    """
    return templates.TemplateResponse(
        "errors/500.html",
        {"request": request},
        status_code=422,
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions.

    Args:
        request (Request): The request object
        exc (Exception): The exception

    Returns:
        TemplateResponse: The rendered template
    """
    logging.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return templates.TemplateResponse(
        "errors/500.html",
        {"request": request},
        status_code=500,
    )


@app.get("/")
async def root(request: Request):
    """Root endpoint.

    Args:
        request (Request): The request object

    Returns:
        TemplateResponse: The rendered template
    """
    # Get recent articles
    recent_articles = get_recent_article_runs(limit=6)
    
    # Format articles for display
    formatted_articles = []
    for run in recent_articles:
        excerpt = run.content[:200] + "..." if run.content and len(run.content) > 200 else "No content available"
        formatted_articles.append({
            "id": run.id,
            "title": run.title or "Untitled Article",
            "excerpt": excerpt,
            "created_at": run.created_at,
        })
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "FoglioAI - Vintage Newspaper Article Generator",
            "recent_articles": formatted_articles,
        },
    )


@app.get("/articles/{article_id}")
async def article_detail(request: Request, article_id: UUID):
    """Article detail endpoint.

    Args:
        request (Request): The request object
        article_id (UUID): The article ID

    Returns:
        TemplateResponse: The rendered template
    """
    article_run = get_article_run(article_id)
    if not article_run:
        raise HTTPException(status_code=404, detail="Article not found")
    
    return templates.TemplateResponse(
        "article.html",
        {
            "request": request,
            "article": {
                "id": article_run.id,
                "title": article_run.title or "Untitled Article",
                "subtitle": article_run.subtitle,
                "content": article_run.content,
                "created_at": article_run.created_at,
                "sources": article_run.citations if hasattr(article_run, "citations") else []
            }
        },
    )


@app.get("/articles")
async def articles_list(request: Request):
    """Articles list endpoint.

    Args:
        request (Request): The request object

    Returns:
        TemplateResponse: The rendered template or redirect
    """
    # For now, redirect to home since we don't have a separate article list page
    return RedirectResponse(url="/")


@app.get("/about")
async def about(request: Request):
    """About page endpoint.

    Args:
        request (Request): The request object

    Returns:
        TemplateResponse: The rendered template
    """
    return templates.TemplateResponse(
        "about.html",
        {
            "request": request,
            "title": "About FoglioAI - Vintage Newspaper Article Generator",
        },
    )


@app.get("/health")
async def health():
    """Health check endpoint.

    Returns:
        dict: Health status
    """
    return {"status": "ok"} 