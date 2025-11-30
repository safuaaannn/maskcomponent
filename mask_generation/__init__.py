"""
Mask Generation Module
Standalone module for generating masks for virtual try-on applications
"""

from .mask_generator import (
    generate_automatic_mask,
    map_category_to_mask_type,
    get_gender_specific_radii,
    update_category_info
)

from .models import (
    MaskGenerationModels,
    get_models
)

from .utils import (
    get_mask_location,
    center_crop,
    hole_fill,
    refine_mask,
    extend_arm_mask,
    LABEL_MAP
)

from .config import (
    IMG_H,
    IMG_W,
    MASK_DIR,
    CATEGORY_MAPPING,
    CATEGORY_DICT_UTILS
)

__version__ = "1.0.0"
__all__ = [
    "generate_automatic_mask",
    "map_category_to_mask_type",
    "get_gender_specific_radii",
    "update_category_info",
    "MaskGenerationModels",
    "get_models",
    "get_mask_location",
    "center_crop",
    "hole_fill",
    "refine_mask",
    "extend_arm_mask",
    "LABEL_MAP",
    "IMG_H",
    "IMG_W",
    "MASK_DIR",
    "CATEGORY_MAPPING",
    "CATEGORY_DICT_UTILS",
]


