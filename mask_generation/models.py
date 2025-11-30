"""
Model initialization for mask generation
Handles OpenPose, Parsing, and DensePose model loading
"""
import os
import sys
import logging
from pathlib import Path
from typing import Optional
import torch
import onnxruntime as ort

logger = logging.getLogger(__name__)

# Get project root (parent of mask_generation package directory)
PROJECT_ROOT = Path(__file__).absolute().parents[1].absolute()
PREPROCESS_DIR = PROJECT_ROOT / "preprocess"
DETECTRON2_DIR = PREPROCESS_DIR / "detectron2"

# Add preprocess directories to path (needed for relative imports in preprocess modules)
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PREPROCESS_DIR))
sys.path.insert(0, str(DETECTRON2_DIR))

# Import preprocess modules
# Note: These modules use relative imports, so we need to be in the right directory context
from preprocess.openpose.run_openpose import OpenPose
from preprocess.humanparsing.run_parsing import Parsing

# DensePose import is optional - handle gracefully if detectron2 build failed
try:
    from preprocess.detectron2.projects.DensePose.apply_net_gradio import DensePose4Gradio
    DENSEPOSE_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:
    DENSEPOSE_AVAILABLE = False
    DensePose4Gradio = None
    import warnings
    warnings.warn(f"DensePose not available (optional): {e}. Mask generation will work without it.")

from .config import (
    HUMANPARSING_DIR,
    OPENPOSE_DIR,
    DENSEPOSE_DIR,
)


class MaskGenerationModels:
    """Container for all mask generation models"""
    
    def __init__(self, gpu_id=0):
        """
        Initialize all models
        
        Args:
            gpu_id: GPU device ID (default: 0)
        """
        self.gpu_id = gpu_id
        self.openpose_model = None
        self.parsing_model = None
        self.densepose_model = None
        self._initialized = False
    
    def initialize(self):
        """Initialize all models"""
        if self._initialized:
            logger.info("Models already initialized")
            return
        
        logger.info("Initializing mask generation models...")
        
        # Initialize OpenPose
        logger.info("Loading OpenPose model...")
        try:
        self.openpose_model = OpenPose(self.gpu_id)
        if torch.cuda.is_available():
            self.openpose_model.preprocessor.body_estimation.model.to('cuda')
            # Enable GPU optimizations
            torch.backends.cudnn.benchmark = True
            torch.backends.cudnn.deterministic = False
            # Enable TF32 for faster computation on Ampere+ GPUs
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
            # Set model to eval mode for inference
            self.openpose_model.preprocessor.body_estimation.model.eval()
            logger.info("OpenPose model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load OpenPose model: {e}", exc_info=True)
            raise
        
        # Initialize Parsing
        logger.info("Loading Parsing model...")
        try:
        self.parsing_model = Parsing(self.gpu_id)
            logger.info("Parsing model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Parsing model: {e}", exc_info=True)
            raise
        
        # Initialize DensePose (optional, only if needed)
        if DENSEPOSE_AVAILABLE and DensePose4Gradio is not None:
            logger.info("Loading DensePose model (optional)...")
            densepose_cfg = str(DENSEPOSE_DIR / "configs" / "densepose_rcnn_R_50_FPN_s1x.yaml")
            densepose_model_url = 'https://dl.fbaipublicfiles.com/densepose/densepose_rcnn_R_50_FPN_s1x/165712039/model_final_162be9.pkl'
            
            try:
                self.densepose_model = DensePose4Gradio(
                    cfg=densepose_cfg,
                    model=densepose_model_url,
                )
                logger.info("DensePose model loaded successfully")
            except Exception as e:
                logger.warning(f"DensePose loading failed (optional): {e}")
                self.densepose_model = None
        else:
            logger.info("DensePose not available (optional - mask generation works without it)")
            self.densepose_model = None
        
        self._initialized = True
        logger.info("All mask generation models initialized successfully")
    
    def get_openpose(self):
        """
        Get OpenPose model
        
        Returns:
            OpenPose model instance
            
        Raises:
            RuntimeError: If models are not initialized
        """
        if not self._initialized:
            self.initialize()
        if self.openpose_model is None:
            raise RuntimeError("OpenPose model not initialized")
        return self.openpose_model
    
    def get_parsing(self):
        """
        Get Parsing model
        
        Returns:
            Parsing model instance
            
        Raises:
            RuntimeError: If models are not initialized
        """
        if not self._initialized:
            self.initialize()
        if self.parsing_model is None:
            raise RuntimeError("Parsing model not initialized")
        return self.parsing_model
    
    def get_densepose(self) -> Optional[object]:
        """
        Get DensePose model (may be None if not available)
        
        Returns:
            DensePose model instance or None if not available
        """
        if not self._initialized:
            self.initialize()
        return self.densepose_model


# Global model instance
_models = None


def get_models(gpu_id: int = 0) -> MaskGenerationModels:
    """
    Get or create global model instance (singleton pattern)
    
    Args:
        gpu_id: GPU device ID (default: 0)
        
    Returns:
        MaskGenerationModels instance
    """
    global _models
    if _models is None:
        _models = MaskGenerationModels(gpu_id)
        _models.initialize()
    return _models

