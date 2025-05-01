"""Tests for visual model."""
import uuid
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models.visual import Visual, VisualType


def test_visual_creation() -> None:
    """Test creating a visual."""
    visual = Visual(
        type=VisualType.IMAGE,
        source_data={"prompt": "Test prompt"},
        generated_content="base64_encoded_data",
        caption="Test caption",
        alt_text="Test alt text",
    )
    assert visual.id is not None
    assert visual.created_at is not None
    assert visual.type == VisualType.IMAGE
    assert visual.source_data == {"prompt": "Test prompt"}
    assert visual.generated_content == "base64_encoded_data"
    assert visual.caption == "Test caption"
    assert visual.alt_text == "Test alt text"
    assert visual.width is None
    assert visual.height is None
    assert visual.mime_type == "image/png"
    assert visual.metadata == {}


def test_visual_with_all_fields() -> None:
    """Test creating a visual with all fields."""
    visual = Visual(
        id=uuid.uuid4(),
        type=VisualType.CHART,
        source_data={"data": [1, 2, 3], "labels": ["A", "B", "C"]},
        generated_content="base64_encoded_data",
        caption="Test chart",
        alt_text="A bar chart showing values for A, B, and C",
        created_at=datetime.utcnow(),
        width=800,
        height=600,
        mime_type="image/jpeg",
        metadata={"chart_type": "bar", "theme": "dark"},
    )

    assert visual.id is not None
    assert visual.created_at is not None
    assert visual.type == VisualType.CHART
    assert visual.source_data == {"data": [1, 2, 3], "labels": ["A", "B", "C"]}
    assert visual.generated_content == "base64_encoded_data"
    assert visual.caption == "Test chart"
    assert visual.alt_text == "A bar chart showing values for A, B, and C"
    assert visual.width == 800
    assert visual.height == 600
    assert visual.mime_type == "image/jpeg"
    assert visual.metadata == {"chart_type": "bar", "theme": "dark"}


def test_visual_validation_error() -> None:
    """Test visual validation error."""
    with pytest.raises(ValidationError):
        Visual()  # Missing required fields

    with pytest.raises(ValidationError):
        Visual(
            type=VisualType.IMAGE,
            source_data={"prompt": "Test prompt"},
            generated_content="base64_encoded_data",
            caption="Test caption",
            # Missing alt_text
        )

    with pytest.raises(ValidationError):
        Visual(
            type="invalid_type",  # Invalid type
            source_data={"prompt": "Test prompt"},
            generated_content="base64_encoded_data",
            caption="Test caption",
            alt_text="Test alt text",
        )


def test_visual_type_enum() -> None:
    """Test visual type enum."""
    assert VisualType.CHART == "chart"
    assert VisualType.IMAGE == "image"
    assert list(VisualType) == [VisualType.CHART, VisualType.IMAGE]


def test_visual_json_serialization() -> None:
    """Test visual JSON serialization."""
    visual = Visual(
        type=VisualType.CHART,
        source_data={"data": [1, 2, 3], "labels": ["A", "B", "C"]},
        generated_content="base64_encoded_data",
        caption="Test chart",
        alt_text="A bar chart showing values for A, B, and C",
        width=800,
        height=600,
        mime_type="image/jpeg",
        metadata={"chart_type": "bar", "theme": "dark"},
    )

    json_data = visual.model_dump_json()
    assert isinstance(json_data, str)

    loaded_visual = Visual.model_validate_json(json_data)
    assert loaded_visual.type == visual.type
    assert loaded_visual.source_data == visual.source_data
    assert loaded_visual.generated_content == visual.generated_content
    assert loaded_visual.caption == visual.caption
    assert loaded_visual.alt_text == visual.alt_text
    assert loaded_visual.width == visual.width
    assert loaded_visual.height == visual.height
    assert loaded_visual.mime_type == visual.mime_type
    assert loaded_visual.metadata == visual.metadata


def test_visual_metadata_update() -> None:
    """Test updating visual metadata."""
    visual = Visual(
        type=VisualType.IMAGE,
        source_data={"prompt": "Test prompt"},
        generated_content="base64_encoded_data",
        caption="Test caption",
        alt_text="Test alt text",
    )

    visual.metadata["processing_time"] = 1.5
    visual.metadata["model_version"] = "v2"

    assert visual.metadata == {
        "processing_time": 1.5,
        "model_version": "v2",
    } 