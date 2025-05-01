"""Visual model module."""
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import Field, field_validator

from app.models.base import BaseModelWithId


class VisualType(str, Enum):
    """Type of visual asset."""

    CHART = "chart"
    IMAGE = "image"


class Visual(BaseModelWithId):
    """Visual model for managing generated images and charts."""

    type: VisualType
    source: Dict[str, Any] = Field(
        ..., description="Source data for charts or prompt for images"
    )
    content: str = Field(
        ..., description="Base64 encoded image data or URL to the generated content"
    )
    caption: str = Field(..., description="Descriptive caption for the visual")
    alt_text: str = Field(..., description="Accessibility text for the visual")
    width: Optional[int] = Field(None, description="Width in pixels")
    height: Optional[int] = Field(None, description="Height in pixels")
    format: str = Field("png", description="File format of the visual")

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate content is either a valid URL or base64 data.

        Args:
            v (str): Content value to validate

        Returns:
            str: Validated content value

        Raises:
            ValueError: If content is neither a valid URL nor base64 data
        """
        # TODO: Add validation for URL and base64 data
        return v

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "type": "image",
                "source": {
                    "prompt": "A vintage black and white photograph of a bustling city street in the 1920s"
                },
                "content": "data:image/png;base64,...</base64-data>",
                "caption": "New York City's Broadway, circa 1925",
                "alt_text": "Black and white photograph showing cars and pedestrians on Broadway",
                "width": 800,
                "height": 600,
                "format": "png",
            }
        } 