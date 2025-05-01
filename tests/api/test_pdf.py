"""Tests for PDF API endpoints."""
import os
import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient
from fastapi.responses import FileResponse

from app.main import app
from app.api.pdf import PDFGenerator, export_article_to_pdf, export_newspaper_to_pdf
from app.models.article import Article, ArticleStatus


@pytest.fixture
def test_client():
    """Return a TestClient instance."""
    return TestClient(app)


@pytest.fixture
def mock_article():
    """Return a mock article."""
    return Article(
        id=uuid.uuid4(),
        title="Test Article",
        subtitle="Test Subtitle",
        author="Test Author",
        content="Test content for the article",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        status=ArticleStatus.COMPLETED,
        error=None,
    )


@pytest.fixture
def mock_pdf_path():
    """Return a mock PDF path."""
    pdf_path = "/tmp/test_article.pdf"
    # Create an empty file
    with open(pdf_path, "wb") as f:
        f.write(b"PDF content")
    
    yield pdf_path
    
    # Cleanup
    if os.path.exists(pdf_path):
        os.remove(pdf_path)


@pytest.mark.asyncio
async def test_export_article_to_pdf(mock_article, mock_pdf_path):
    """Test the export_article_to_pdf endpoint."""
    article_id = mock_article.id
    
    # Mock the get_article_run function
    with patch("app.api.pdf.get_article_run") as mock_get_article:
        # Mock the rate limiter
        with patch("app.api.pdf.get_rate_limiter") as mock_rate_limiter:
            # Mock the PDFGenerator.generate_pdf method
            with patch.object(PDFGenerator, "generate_pdf") as mock_generate_pdf:
                # Set up the mocks
                mock_get_article.return_value = MagicMock(
                    article=mock_article,
                    status=ArticleStatus.COMPLETED
                )
                mock_rate_limiter.return_value = AsyncMock()
                mock_generate_pdf.return_value = (mock_pdf_path, False)
                
                # Make the request
                request = MagicMock()
                request.paper_format = "tabloid"
                request.newspaper_name = "Test Gazette"
                
                background_tasks = BackgroundTasks()
                fastapi_request = MagicMock()
                
                response = await export_article_to_pdf(
                    article_id=article_id,
                    request=request,
                    background_tasks=background_tasks,
                    fastapi_request=fastapi_request,
                    rate_limiter=AsyncMock()
                )
                
                # Check the response
                assert isinstance(response, FileResponse)
                assert response.path == mock_pdf_path
                assert response.media_type == "application/pdf"
                assert "Test_Article_" in response.filename
                
                # Verify the mocks were called correctly
                mock_get_article.assert_called_once_with(article_id)
                mock_rate_limiter.return_value.assert_called_once_with(fastapi_request)
                mock_generate_pdf.assert_called_once()


@pytest.mark.asyncio
async def test_export_newspaper_to_pdf(mock_article, mock_pdf_path):
    """Test the export_newspaper_to_pdf endpoint."""
    article_id = mock_article.id
    
    # Mock the get_article_run function
    with patch("app.api.pdf.get_article_run") as mock_get_article:
        # Mock the rate limiter
        with patch("app.api.pdf.get_rate_limiter") as mock_rate_limiter:
            # Mock the PDFGenerator.generate_newspaper_pdf method
            with patch.object(PDFGenerator, "generate_newspaper_pdf") as mock_generate_pdf:
                # Set up the mocks
                mock_get_article.return_value = MagicMock(
                    article=mock_article,
                    status=ArticleStatus.COMPLETED
                )
                mock_rate_limiter.return_value = AsyncMock()
                mock_generate_pdf.return_value = mock_pdf_path
                
                # Make the request
                request = MagicMock()
                request.paper_format = "tabloid"
                request.newspaper_name = "Test Gazette"
                
                background_tasks = BackgroundTasks()
                fastapi_request = MagicMock()
                
                response = await export_newspaper_to_pdf(
                    article_id=article_id,
                    request=request,
                    background_tasks=background_tasks,
                    fastapi_request=fastapi_request,
                    rate_limiter=AsyncMock()
                )
                
                # Check the response
                assert isinstance(response, FileResponse)
                assert response.path == mock_pdf_path
                assert response.media_type == "application/pdf"
                assert "Test_Article_newspaper_" in response.filename
                
                # Verify the mocks were called correctly
                mock_get_article.assert_called_once_with(article_id)
                mock_rate_limiter.return_value.assert_called_once_with(fastapi_request)
                mock_generate_pdf.assert_called_once()


@pytest.mark.asyncio
async def test_export_article_not_found():
    """Test the export_article_to_pdf endpoint with article not found."""
    article_id = uuid.uuid4()
    
    # Mock the get_article_run function
    with patch("app.api.pdf.get_article_run") as mock_get_article:
        # Mock the rate limiter
        with patch("app.api.pdf.get_rate_limiter") as mock_rate_limiter:
            # Set up the mocks
            mock_get_article.return_value = None
            mock_rate_limiter.return_value = AsyncMock()
            
            # Make the request
            request = MagicMock()
            background_tasks = BackgroundTasks()
            fastapi_request = MagicMock()
            
            with pytest.raises(Exception) as excinfo:
                await export_article_to_pdf(
                    article_id=article_id,
                    request=request,
                    background_tasks=background_tasks,
                    fastapi_request=fastapi_request,
                    rate_limiter=AsyncMock()
                )
            
            assert "Article not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_export_article_not_ready(mock_article):
    """Test the export_article_to_pdf endpoint with article not ready."""
    article_id = mock_article.id
    
    # Mock the get_article_run function
    with patch("app.api.pdf.get_article_run") as mock_get_article:
        # Mock the rate limiter
        with patch("app.api.pdf.get_rate_limiter") as mock_rate_limiter:
            # Set up the mocks
            mock_get_article.return_value = MagicMock(
                article=mock_article,
                status=ArticleStatus.PENDING
            )
            mock_rate_limiter.return_value = AsyncMock()
            
            # Make the request
            request = MagicMock()
            background_tasks = BackgroundTasks()
            fastapi_request = MagicMock()
            
            with pytest.raises(Exception) as excinfo:
                await export_article_to_pdf(
                    article_id=article_id,
                    request=request,
                    background_tasks=background_tasks,
                    fastapi_request=fastapi_request,
                    rate_limiter=AsyncMock()
                )
            
            assert "Article is not ready for export" in str(excinfo.value) 