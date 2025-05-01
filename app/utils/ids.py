"""ID generation utilities."""
import uuid
from uuid import UUID


def generate_article_id() -> UUID:
    """Generate a unique article ID.

    Returns:
        UUID: Generated article ID
    """
    return uuid.uuid4()


def generate_memo_id() -> UUID:
    """Generate a unique memo ID.

    Returns:
        UUID: Generated memo ID
    """
    return uuid.uuid4()


def generate_citation_id() -> UUID:
    """Generate a unique citation ID.

    Returns:
        UUID: Generated citation ID
    """
    return uuid.uuid4()


def generate_visual_id() -> UUID:
    """Generate a unique visual ID.

    Returns:
        UUID: Generated visual ID
    """
    return uuid.uuid4() 