# Package setup file
from setuptools import setup, find_packages

setup(
    name="song-research",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "google-generativeai>=0.3.2",
        "python-dotenv>=1.0.0",
        "pydantic>=2.6.1",
        "fastapi>=0.109.2",
        "uvicorn>=0.27.1", 
        "python-multipart>=0.0.9",
        "Pillow>=10.0.0",
    ],
) 