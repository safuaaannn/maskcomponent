"""
Main mask generation module
Extracted from tryon_inference_lora.py
"""
import os
import time
import logging
import numpy as np
import cv2
from pathlib import Path
from typing import Tuple, Optional, Dict
from PIL import Image

from .config import IMG_H, IMG_W, MASK_DIR, CATEGORY_MAPPING
from .utils import get_mask_location, center_crop
from .models import get_models, MaskGenerationModels

logger = logging.getLogger(__name__)


def map_category_to_mask_type(category: str) -> str:
    """
    Map category to mask type
    
    Args:
        category: Category name (e.g., "Shirts", "Pants")
        
    Returns:
        Mask type string (e.g., "upper_body", "lower_body")
    """
    return CATEGORY_MAPPING.get(category, "upper_body")


def get_gender_specific_radii(mask_type: str, gender: str) -> Dict[str, int]:
    """
    Get radius values based on gender and mask type
    
    Args:
        mask_type: Type of mask (e.g., "upper_body", "lower_body")
        gender: Gender string ("M" for male, "F" for female)
        
    Returns:
        Dictionary mapping category to radius value
    """
    if gender == "M":  # Male
        radii = {
            "upper_body": {"upper_body": 2, "lower_body": 0},  # Shirts: no lower body
            "upper_body_tshirts": {"upper_body": 2, "lower_body": 2},  # T-shirts: with lower body
            "upper_body_coat": {"upper_body": 2, "lower_body": 2},  # Coat: with lower body
            "lower_body": {"lower_body": 2},
            "ethnic_combined": {"upper_body": 1, "lower_body": 10},  # Male: upper 1, lower 10
            "baggy_lower": {"lower_body": 7},
            "dress": {"dress": 2}
        }
    else:  # Female (default)
        radii = {
            "upper_body": {"upper_body": 3, "lower_body": 2},  # Shirts: with lower body
            "upper_body_tshirts": {"upper_body": 3, "lower_body": 2},  # T-shirts: with lower body
            "upper_body_coat": {"upper_body": 3, "lower_body": 2},  # Coat: with lower body
            "lower_body": {"lower_body": 2},
            "ethnic_combined": {"upper_body": 5, "lower_body": 13},  # Female: upper 5, lower 13
            "baggy_lower": {"lower_body": 7},
            "dress": {"dress": 2}
        }
    return radii.get(mask_type, {})


def update_category_info(category, gender):
    """Update category info based on selected category and gender"""
    info_map = {
        "Shirts": f"Shirts: Male (upper only, radius 2), Female (upper radius 3 + lower radius 2)",
        "Tshirts": f"Tshirts: Male (upper radius 2 + lower radius 2), Female (upper radius 3 + lower radius 2)",
        "Coat": f"Coat: Male (upper radius 2 + lower radius 2), Female (upper radius 3 + lower radius 2)",
        "Pants": f"Pants: Both genders (lower body only, radius 2)",
        "Ethnic": f"Ethnic: Male (upper radius 1 + lower radius 10), Female (upper radius 5 + lower radius 13)",
        "Baggy": f"Baggy: Both genders (lower body only, radius 7)",
        "Full Body": f"Full Body: Both genders (dress only, radius 2)"
    }
    return info_map.get(category, "Unknown category")


def generate_automatic_mask(
    image_path: str,
    mask_type: str = "upper_body",
    radius: int = 1,
    neck_mask_radius: float = 0.4,
    gender: str = "F",
    save_output: bool = True,
    models: Optional[MaskGenerationModels] = None
) -> Tuple[Optional[Image.Image], str]:
    """
    Generate automatic mask using the integrated masking system
    
    Args:
        image_path: Path to input image
        mask_type: Type of mask to generate ("upper_body", "lower_body", "dress", "ethnic_combined", "baggy_lower")
        radius: Dilation radius for mask refinement (fallback if gender-specific not available)
        neck_mask_radius: Neck mask radius (0.0=no neck mask, 1.0=full neck mask, 0.4=bottom 40% masked)
        gender: Gender for mask generation ("M" or "F")
        save_output: Whether to save mask to disk
        models: MaskGenerationModels instance (will be created if None)
    
    Returns:
        Tuple of (mask, message)
    """
    if image_path is None:
        return None, "No image provided"
    
    # Get models
    if models is None:
        models = get_models()
    
    openpose_model = models.get_openpose()
    parsing_model = models.get_parsing()
    
    try:
        start_time = time.time()
        logger.debug(f"Loading image from {image_path}")
        
        # Load and preprocess image
        image = Image.open(image_path)
        image = center_crop(image)
        image = image.resize((IMG_W, IMG_H))
        
        load_time = time.time() - start_time
        logger.debug(f"Image loaded and preprocessed in {load_time:.2f}s")
        
        # Generate keypoints
        start_time = time.time()
        logger.debug("Generating pose keypoints...")
        keypoints = openpose_model(image)
        keypoint_time = time.time() - start_time
        logger.debug(f"Keypoints generated in {keypoint_time:.2f}s")
        
        # Generate parsing
        start_time = time.time()
        logger.debug("Generating human parsing...")
        model_parse, _ = parsing_model(image)
        parse_time = time.time() - start_time
        logger.debug(f"Parsing generated in {parse_time:.2f}s")
        
        # Generate mask based on mask_type
        start_time = time.time()
        logger.info(f"Generating {mask_type} mask for gender {gender}")
        
        # Get gender-specific radii
        gender_radii = get_gender_specific_radii(mask_type, gender)
        
        if mask_type in ["upper_body", "upper_body_tshirts", "upper_body_coat"]:
            # Generate masks for upper_body and optionally lower_body based on category and gender
            combined_mask = None
            
            # Determine which categories to process based on mask_type and gender
            # IMPORTANT: For Male (M) with upper_body, ONLY process upper_body (no lower_body)
            if mask_type == "upper_body" and gender == "M":
                # Male Shirts: only upper_body, NO lower_body mask should be created
                upper_lower_categories = ['upper_body']
                logger.debug("Male upper_body: Processing ONLY upper_body (no lower_body)")
            else:
                # All other cases: upper_body + lower_body
                upper_lower_categories = ['upper_body', 'lower_body']
            
            for category_utils in upper_lower_categories:
                logger.debug(f"Processing {category_utils} category...")
                # Use gender-specific radius
                category_radius = gender_radii.get(category_utils, radius)
                
                # Skip if radius is 0 (no mask for this category)
                # This is an additional safeguard: even if category is in list, skip if radius=0
                if category_radius == 0 or category_radius is None:
                    logger.debug(f"Skipping {category_utils} (radius=0 or None)")
                    continue
                
                mask, _ = get_mask_location(
                    'hd', 
                    category_utils, 
                    model_parse, 
                    keypoints, 
                    radius=category_radius,
                    neck_mask_radius=neck_mask_radius
                )
                mask = mask.resize((IMG_W, IMG_H), Image.NEAREST)
                
                # Convert to numpy array for combination
                mask_array = np.array(mask)
                
                # Apply morphological operations to fill holes and smooth edges
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                mask_array = cv2.morphologyEx(mask_array, cv2.MORPH_CLOSE, kernel, iterations=2)
                mask_array = cv2.morphologyEx(mask_array, cv2.MORPH_OPEN, kernel, iterations=1)
                
                # Initialize combined mask if first iteration
                if combined_mask is None:
                    combined_mask = mask_array
                else:
                    # Combine masks using logical OR (union)
                    combined_mask = np.logical_or(combined_mask, mask_array).astype(np.uint8) * 255
                
                logger.debug(f"{category_utils} mask processed successfully")
            
            # Apply final hole filling to combined mask
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel, iterations=3)
            
            # Convert back to PIL Image
            full_body_mask = Image.fromarray(combined_mask, mode='L')
            
        elif mask_type == "lower_body":
            # Generate only lower body mask with gender-specific radius
            lower_body_radius = gender_radii.get('lower_body', radius)
            mask, _ = get_mask_location(
                'hd', 
                'lower_body', 
                model_parse, 
                keypoints, 
                radius=lower_body_radius,
                neck_mask_radius=neck_mask_radius
            )
            mask = mask.resize((IMG_W, IMG_H), Image.NEAREST)
            
            # Apply morphological operations to fill holes and smooth edges
            mask_array = np.array(mask)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            mask_array = cv2.morphologyEx(mask_array, cv2.MORPH_CLOSE, kernel, iterations=2)
            mask_array = cv2.morphologyEx(mask_array, cv2.MORPH_OPEN, kernel, iterations=1)
            full_body_mask = Image.fromarray(mask_array, mode='L')
            
        elif mask_type == "dress":
            # Generate only dress mask with gender-specific radius
            dress_radius = gender_radii.get('dress', radius)
            mask, _ = get_mask_location(
                'hd', 
                'dresses', 
                model_parse, 
                keypoints, 
                radius=dress_radius,
                neck_mask_radius=neck_mask_radius
            )
            mask = mask.resize((IMG_W, IMG_H), Image.NEAREST)
            
            # Apply morphological operations to fill holes and smooth edges
            mask_array = np.array(mask)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            mask_array = cv2.morphologyEx(mask_array, cv2.MORPH_CLOSE, kernel, iterations=2)
            mask_array = cv2.morphologyEx(mask_array, cv2.MORPH_OPEN, kernel, iterations=1)
            full_body_mask = Image.fromarray(mask_array, mode='L')
            
        elif mask_type == "ethnic_combined":
            # Generate ethnic mask: upper_body + lower_body combined with gender-specific radii
            # Note: mask_shoes=True enables masking of shoes for ethnic clothing
            logger.debug("Generating ethnic combined mask...")
            combined_mask = None
            ethnic_categories = ['upper_body', 'lower_body']
            
            for category_utils in ethnic_categories:
                category_radius = gender_radii.get(category_utils, radius)
                logger.debug(f"Processing {category_utils} with radius {category_radius}...")
                # Enable shoe masking for ethnic_combined (especially important for lower_body)
                mask_shoes_enabled = (category_utils == 'lower_body')
                mask, _ = get_mask_location(
                    'hd', 
                    category_utils, 
                    model_parse, 
                    keypoints, 
                    radius=category_radius,
                    neck_mask_radius=neck_mask_radius,
                    mask_shoes=mask_shoes_enabled
                )
                mask = mask.resize((IMG_W, IMG_H), Image.NEAREST)
                
                # Convert to numpy array for combination
                mask_array = np.array(mask)
                
                # Apply morphological operations to fill holes and smooth edges
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                mask_array = cv2.morphologyEx(mask_array, cv2.MORPH_CLOSE, kernel, iterations=2)
                mask_array = cv2.morphologyEx(mask_array, cv2.MORPH_OPEN, kernel, iterations=1)
                
                # Initialize combined mask if first iteration
                if combined_mask is None:
                    combined_mask = mask_array
                else:
                    # Combine masks using logical OR (union)
                    combined_mask = np.logical_or(combined_mask, mask_array).astype(np.uint8) * 255
                
                logger.debug(f"{category_utils} mask processed successfully")
            
            # Apply final hole filling to combined mask
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel, iterations=3)
            
            # Convert back to PIL Image
            full_body_mask = Image.fromarray(combined_mask, mode='L')
            
        elif mask_type == "baggy_lower":
            # Generate baggy lower body mask with gender-specific radius
            # Note: mask_shoes=True enables masking of shoes/toes for baggy clothing
            baggy_radius = gender_radii.get('lower_body', radius)
            mask, _ = get_mask_location(
                'hd', 
                'lower_body', 
                model_parse, 
                keypoints, 
                radius=baggy_radius,
                neck_mask_radius=neck_mask_radius,
                mask_shoes=True  # Include shoes/toes in baggy mask
            )
            mask = mask.resize((IMG_W, IMG_H), Image.NEAREST)
            
            # Apply morphological operations to fill holes and smooth edges
            mask_array = np.array(mask)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            mask_array = cv2.morphologyEx(mask_array, cv2.MORPH_CLOSE, kernel, iterations=2)
            mask_array = cv2.morphologyEx(mask_array, cv2.MORPH_OPEN, kernel, iterations=1)
            full_body_mask = Image.fromarray(mask_array, mode='L')
            
        else:
            raise ValueError(f"Invalid mask_type: {mask_type}")
        
        mask_time = time.time() - start_time
        logger.info(f"{mask_type} mask generated successfully in {mask_time:.2f}s")
        
        # Save mask if requested
        if save_output:
            os.makedirs(MASK_DIR, exist_ok=True)
            original_name = Path(image_path).stem
            mask_path = os.path.join(MASK_DIR, f"{original_name}_{mask_type}_mask.png")
            full_body_mask.save(mask_path)
            logger.debug(f"Mask saved to: {mask_path}")
        
        total_time = time.time() - start_time
        return full_body_mask, f"Success! {mask_type} mask generated in {total_time:.2f}s"
        
    except Exception as e:
        logger.error(f"Error generating {mask_type} mask: {e}", exc_info=True)
        return None, f"Error generating mask: {str(e)}"

