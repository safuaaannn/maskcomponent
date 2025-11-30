"""
Setup script for mask_generation package
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="mask_generation",
    version="1.0.0",
    description="Standalone module for generating masks for virtual try-on applications",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Mask Generation Team",
    packages=find_packages(exclude=["preprocess", "checkpoints", "generated_masks", "__pycache__"]),
    python_requires=">=3.8",
    install_requires=[
        "torch>=2.0.0",
        "torchvision>=0.15.0",
        "numpy>=1.24.0,<2.0.0",
        "scipy>=1.10.0",
        "scikit-image>=0.20.0",
        "opencv-python>=4.8.0,<4.12.0",
        "pillow>=10.0.0",
        "onnxruntime>=1.15.0",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)





