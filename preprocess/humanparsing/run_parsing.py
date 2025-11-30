import os
import pdb
import sys
from pathlib import Path

import onnxruntime as ort

PROJECT_ROOT = Path(__file__).absolute().parents[0].absolute()
sys.path.insert(0, str(PROJECT_ROOT))
import torch
from parsing_api import onnx_inference


class Parsing:
    def __init__(self, gpu_id: int):
        self.gpu_id = gpu_id
        session_options = ort.SessionOptions()
        session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        session_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        
        # Try GPU first, fallback to CPU
        # Note: CUDAExecutionProvider may be listed but fail to load if cuDNN is missing
        # So we try it and let it fallback to CPU automatically
        available_providers = ort.get_available_providers()
        if 'CUDAExecutionProvider' in available_providers:
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            # Will print success message after initialization if GPU works
        else:
            providers = ['CPUExecutionProvider']
        
        # Try to initialize with GPU, will fallback to CPU if it fails
        try:
            self.session = ort.InferenceSession(os.path.join(Path(__file__).absolute().parents[2].absolute(), 'checkpoints/humanparsing/parsing_atr.onnx'),
                                                sess_options=session_options, providers=providers)
            # Check which provider was actually used
            actual_provider = self.session.get_providers()[0]
            if actual_provider == 'CUDAExecutionProvider':
                print(f"✓ Using GPU (CUDA) for Parsing model (device {gpu_id})")
            else:
                print(f"⚠ Using CPU for Parsing model (GPU unavailable - using {actual_provider})")
            
            # Initialize LIP session with same providers
            self.lip_session = ort.InferenceSession(os.path.join(Path(__file__).absolute().parents[2].absolute(), 'checkpoints/humanparsing/parsing_lip.onnx'),
                                                    sess_options=session_options, providers=providers)
        except Exception as e:
            # If GPU fails, try CPU only
            providers = ['CPUExecutionProvider']
            print(f"⚠ GPU initialization failed, using CPU: {str(e)[:100]}")
            self.session = ort.InferenceSession(os.path.join(Path(__file__).absolute().parents[2].absolute(), 'checkpoints/humanparsing/parsing_atr.onnx'),
                                                sess_options=session_options, providers=providers)
            self.lip_session = ort.InferenceSession(os.path.join(Path(__file__).absolute().parents[2].absolute(), 'checkpoints/humanparsing/parsing_lip.onnx'),
                                                    sess_options=session_options, providers=providers)

    def __call__(self, input_image):
        # torch.cuda.set_device(self.gpu_id)
        parsed_image, face_mask = onnx_inference(self.session, self.lip_session, input_image)
        return parsed_image, face_mask
