"""
Helper functions to construct mask URLs from database filenames
"""
from typing import Optional, Dict
from .config import ServiceConfig


def get_mask_url(
    base_url: str,
    user_id: str,
    request_id: str,
    filename: str
) -> str:
    """
    Construct full mask URL from components
    
    Args:
        base_url: Base URL from config (e.g., "http://127.0.0.1:9000/masks")
        user_id: User identifier
        request_id: Request ID
        filename: Mask filename (e.g., "upper_body_mask.png")
    
    Returns:
        Full URL: {base_url}/{user_id}/{request_id}/{filename}
    
    Example:
        base_url = "http://127.0.0.1:9000/masks"
        user_id = "1"
        request_id = "test-1-M"
        filename = "upper_body_mask.png"
        Returns: "http://127.0.0.1:9000/masks/1/test-1-M/upper_body_mask.png"
    """
    return f"{base_url}/{user_id}/{request_id}/{filename}"


def get_all_mask_urls(
    base_url: str,
    user_id: str,
    request_id: str,
    mask_filenames: Dict[str, str]
) -> Dict[str, str]:
    """
    Construct all mask URLs for a user
    
    Args:
        base_url: Base URL from config
        user_id: User identifier
        request_id: Request ID
        mask_filenames: Dictionary of mask_type -> filename
    
    Returns:
        Dictionary of mask_type -> full URL
    
    Example:
        mask_filenames = {
            "upper_body": "upper_body_mask.png",
            "lower_body": "lower_body_mask.png"
        }
        Returns: {
            "upper_body": "http://127.0.0.1:9000/masks/1/test-1-M/upper_body_mask.png",
            "lower_body": "http://127.0.0.1:9000/masks/1/test-1-M/lower_body_mask.png"
        }
    """
    urls = {}
    for mask_type, filename in mask_filenames.items():
        if filename:
            urls[mask_type] = get_mask_url(base_url, user_id, request_id, filename)
    return urls


def get_mask_urls_from_db_row(
    base_url: str,
    row: Dict
) -> Dict[str, str]:
    """
    Construct mask URLs from database row
    
    Args:
        base_url: Base URL from config
        row: Database row with user_id, request_id, and mask filenames
    
    Returns:
        Dictionary of mask_type -> full URL
    """
    user_id = row.get('user_id')
    request_id = row.get('request_id')
    
    if not user_id or not request_id:
        return {}
    
    mask_filenames = {
        "upper_body": row.get('upper_body_mask'),
        "lower_body": row.get('lower_body_mask'),
        "ethnic_combined": row.get('ethnic_combined_mask')
    }
    
    return get_all_mask_urls(base_url, user_id, request_id, mask_filenames)

