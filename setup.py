from setuptools import setup, find_packages

setup(
    name="song-research",
    version="0.1",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "google-cloud-aiplatform>=1.38.1",
        "python-dotenv>=1.0.0",
        "pydantic>=2.6.1",
    ],
) 