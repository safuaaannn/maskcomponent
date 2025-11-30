"""
Configuration constants for mask generation module
"""
from pathlib import Path

# Image dimensions
IMG_H = 1024
IMG_W = 768

# Default mask directory
MASK_DIR = "generated_masks"

# Category definitions
CATEGORY_DICT_UTILS = ['upper_body', 'lower_body', 'dresses']

# Category to mask type mapping
CATEGORY_MAPPING = {
    "Shirts": "upper_body",
    "Tshirts": "upper_body_tshirts",
    "Coat": "upper_body_coat",
    "Pants": "lower_body", 
    "Ethnic": "ethnic_combined",
    "Baggy": "baggy_lower",
    "Full Body": "dress"
}

# Get project root
PROJECT_ROOT = Path(__file__).absolute().parents[0].absolute()

# Paths to checkpoints
CHECKPOINTS_DIR = PROJECT_ROOT / "checkpoints"
HUMANPARSING_DIR = CHECKPOINTS_DIR / "humanparsing"
OPENPOSE_DIR = CHECKPOINTS_DIR / "openpose"

# Paths to preprocess modules
PREPROCESS_DIR = PROJECT_ROOT / "preprocess"
DETECTRON2_DIR = PREPROCESS_DIR / "detectron2"
DENSEPOSE_DIR = DETECTRON2_DIR / "projects" / "DensePose"
HUMANPARSING_MODULE_DIR = PREPROCESS_DIR / "humanparsing"
OPENPOSE_MODULE_DIR = PREPROCESS_DIR / "openpose"


