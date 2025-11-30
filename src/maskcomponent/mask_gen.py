"""
Mask generation wrapper around existing mask_generation module
"""
import sys
import asyncio
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
from PIL import Image
from .logger import setup_logger

logger = setup_logger(__name__)

# Add parent directory to path to import mask_generation
PROJECT_ROOT = Path(__file__).absolute().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from mask_generation.mask_generator_fast import generate_automatic_mask_fast
    from mask_generation.models import MaskGenerationModels
except ImportError:
    # Fallback to regular generator
    try:
        from mask_generation.mask_generator import generate_automatic_mask
        generate_automatic_mask_fast = generate_automatic_mask
    except ImportError as e:
        logger.error(f"Failed to import mask_generation module: {e}")
        raise


def map_gender(gender: str) -> str:
    """
    Map gender string to mask_generation format
    
    Args:
        gender: "male", "female", "other", "M", or "F"
    
    Returns:
        "M" or "F"
    """
    gender_lower = gender.lower()
    if gender_lower in ("male", "m"):
        return "M"
    elif gender_lower in ("female", "f"):
        return "F"
    else:
        # Default to "F" for "other" or unknown
        return "F"


async def generate_masks(
    image: Image.Image,
    mask_types: List[str],
    gender: str,
    models: MaskGenerationModels,
    neck_mask_radius: float = 0.4
) -> Dict[str, Image.Image]:
    """
    Generate multiple masks for an image
    
    Args:
        image: PIL Image to process
        mask_types: List of mask types to generate (e.g., ["upper_body", "lower_body"])
        gender: Gender string ("male", "female", "M", "F")
        models: MaskGenerationModels instance (initialized at startup)
        neck_mask_radius: Neck mask radius (0.0-1.0)
    
    Returns:
        Dictionary mapping mask_type -> PIL Image
    """
    # Map gender to mask_generation format
    gender_mapped = map_gender(gender)
    
    # Save image to temporary file (mask_generation expects file path)
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
        tmp_path = tmp_file.name
        image.save(tmp_path, format="JPEG")
    
    try:
        results = {}
        
        # Generate each mask type
        for mask_type in mask_types:
            try:
                logger.info(f"Generating {mask_type} mask for gender {gender_mapped}")
                
                # Run mask generation in executor (it's synchronous)
                loop = asyncio.get_event_loop()
                mask, message = await loop.run_in_executor(
                    None,
                    generate_automatic_mask_fast,
                    tmp_path,
                    mask_type,
                    1,  # radius (will use gender-specific)
                    neck_mask_radius,
                    gender_mapped,
                    False,  # save_output=False (we handle saving)
                    models
                )
                
                if mask is not None:
                    results[mask_type] = mask
                    logger.info(f"Successfully generated {mask_type} mask: {message}")
                else:
                    logger.warning(f"Failed to generate {mask_type} mask: {message}")
            
            except Exception as e:
                logger.error(f"Error generating {mask_type} mask: {e}", exc_info=True)
                # Continue with other mask types
        
        return results
    
    finally:
        # Clean up temporary file
        try:
            Path(tmp_path).unlink()
        except Exception as e:
            logger.warning(f"Failed to delete temporary file {tmp_path}: {e}")



