"""
Optimized mask generation for maximum GPU utilization and speed
"""
import os
import time
import logging
import numpy as np
import cv2
from pathlib import Path
from typing import Tuple, Optional
from PIL import Image
import torch
import threading
from concurrent.futures import ThreadPoolExecutor

from .config import IMG_H, IMG_W, MASK_DIR, CATEGORY_MAPPING
from .utils import get_mask_location, center_crop
from .models import get_models, MaskGenerationModels
from .mask_generator import get_gender_specific_radii

logger = logging.getLogger(__name__)


def optimize_gpu_settings():
    """Enable GPU optimizations for maximum performance"""
    if torch.cuda.is_available():
        # Enable cuDNN benchmarking for faster convolutions
        torch.backends.cudnn.benchmark = True
        torch.backends.cudnn.deterministic = False
        # Enable TensorFloat-32 for faster computation on Ampere+ GPUs
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        logger.debug("GPU optimizations enabled (cuDNN benchmark, TF32)")


def generate_automatic_mask_fast(
    image_path: str,
    mask_type: str = "upper_body",
    radius: int = 1,
    neck_mask_radius: float = 0.4,
    gender: str = "F",
    save_output: bool = True,
    models: Optional[MaskGenerationModels] = None
) -> Tuple[Optional[Image.Image], str]:
    """
    Optimized mask generation with maximum GPU utilization
    
    Features:
    - Parallel execution of pose and parsing models
    - GPU optimizations (cuDNN benchmark, TF32)
    - Optimized memory usage
    - Faster inference mode
    """
    if image_path is None:
        return None, "No image provided"
    
    # Enable GPU optimizations
    optimize_gpu_settings()
    
    # Get models
    if models is None:
        models = get_models()
    
    openpose_model = models.get_openpose()
    parsing_model = models.get_parsing()
    
    try:
        total_start = time.time()
        
        # Load and preprocess image (fast, CPU operation)
        stt = time.time()
        image = Image.open(image_path)
        image = center_crop(image)
        image = image.resize((IMG_W, IMG_H))
        load_time = time.time() - stt
        
        # Run pose and parsing in parallel for maximum GPU utilization
        stt = time.time()
        
        # Use ThreadPoolExecutor to run both models in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit both tasks
            pose_future = executor.submit(openpose_model, image)
            parse_future = executor.submit(parsing_model, image)
            
            # Wait for both to complete
            keypoints = pose_future.result()
            model_parse, _ = parse_future.result()
        
        inference_time = time.time() - stt
        
        # Generate mask based on mask_type
        stt = time.time()
        
        # Get gender-specific radii
        gender_radii = get_gender_specific_radii(mask_type, gender)
        
        if mask_type in ["upper_body", "upper_body_tshirts", "upper_body_coat"]:
            combined_mask = None
            # IMPORTANT: For Male (M) with upper_body, ONLY process upper_body (no lower_body)
            if mask_type == "upper_body" and gender == "M":
                # Male Shirts: only upper_body, NO lower_body mask should be created
                upper_lower_categories = ['upper_body']
            else:
                # All other cases: upper_body + lower_body
                upper_lower_categories = ['upper_body', 'lower_body']
            
            for category_utils in upper_lower_categories:
                category_radius = gender_radii.get(category_utils, radius)
                # Skip if radius is 0 or None (no mask for this category)
                # This is an additional safeguard: even if category is in list, skip if radius=0
                if category_radius == 0 or category_radius is None:
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
                mask_array = np.array(mask)
                
                # Optimized morphological operations
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                mask_array = cv2.morphologyEx(mask_array, cv2.MORPH_CLOSE, kernel, iterations=2)
                mask_array = cv2.morphologyEx(mask_array, cv2.MORPH_OPEN, kernel, iterations=1)
                
                if combined_mask is None:
                    combined_mask = mask_array
                else:
                    combined_mask = np.logical_or(combined_mask, mask_array).astype(np.uint8) * 255
            
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel, iterations=3)
            full_body_mask = Image.fromarray(combined_mask, mode='L')
            
        elif mask_type == "lower_body":
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
            mask_array = np.array(mask)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            mask_array = cv2.morphologyEx(mask_array, cv2.MORPH_CLOSE, kernel, iterations=2)
            mask_array = cv2.morphologyEx(mask_array, cv2.MORPH_OPEN, kernel, iterations=1)
            full_body_mask = Image.fromarray(mask_array, mode='L')
            
        elif mask_type == "dress":
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
            mask_array = np.array(mask)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            mask_array = cv2.morphologyEx(mask_array, cv2.MORPH_CLOSE, kernel, iterations=2)
            mask_array = cv2.morphologyEx(mask_array, cv2.MORPH_OPEN, kernel, iterations=1)
            full_body_mask = Image.fromarray(mask_array, mode='L')
            
        elif mask_type == "ethnic_combined":
            combined_mask = None
            ethnic_categories = ['upper_body', 'lower_body']
            
            for category_utils in ethnic_categories:
                category_radius = gender_radii.get(category_utils, radius)
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
                mask_array = np.array(mask)
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                mask_array = cv2.morphologyEx(mask_array, cv2.MORPH_CLOSE, kernel, iterations=2)
                mask_array = cv2.morphologyEx(mask_array, cv2.MORPH_OPEN, kernel, iterations=1)
                
                if combined_mask is None:
                    combined_mask = mask_array
                else:
                    combined_mask = np.logical_or(combined_mask, mask_array).astype(np.uint8) * 255
            
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel, iterations=3)
            full_body_mask = Image.fromarray(combined_mask, mode='L')
            
        elif mask_type == "baggy_lower":
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
            mask_array = np.array(mask)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            mask_array = cv2.morphologyEx(mask_array, cv2.MORPH_CLOSE, kernel, iterations=2)
            mask_array = cv2.morphologyEx(mask_array, cv2.MORPH_OPEN, kernel, iterations=1)
            full_body_mask = Image.fromarray(mask_array, mode='L')
        else:
            raise ValueError(f"Invalid mask_type: {mask_type}")
        
        mask_time = time.time() - stt
        total_time = time.time() - total_start
        
        # Save mask if requested
        if save_output:
            os.makedirs(MASK_DIR, exist_ok=True)
            original_name = Path(image_path).stem
            mask_path = os.path.join(MASK_DIR, f"{original_name}_{mask_type}_mask.png")
            full_body_mask.save(mask_path)
        
        return full_body_mask, f"Success! {mask_type} mask generated in {total_time:.2f}s (load: {load_time:.2f}s, inference: {inference_time:.2f}s, mask: {mask_time:.2f}s)"
        
    except Exception as e:
        logger.error(f"Error generating {mask_type} mask: {e}", exc_info=True)
        return None, f"Error generating mask: {str(e)}"




