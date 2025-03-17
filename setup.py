"""
Setup script for Brainy.
"""
from setuptools import setup, find_packages

# Read requirements from requirements.txt
with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="brainy",
    version="0.1.0",
    description="AI Bot Manager",
    author="Nazary21",
    author_email="",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "brainy=brainy.main:run",
        ],
    },
) 