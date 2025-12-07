"""
Bruno Core - Foundation package for the Bruno AI Assistant ecosystem.

This package provides the core interfaces, base implementations, and utilities
that other Bruno packages build upon.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

# Read version from __version__.py
version = {}
with open("bruno_core/__version__.py") as fp:
    exec(fp.read(), version)

setup(
    name="bruno-core",
    version=version["__version__"],
    author="Meggy AI",
    author_email="contact@meggy.ai",
    description="Foundation package for the Bruno AI Assistant ecosystem",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/meggy-ai/bruno-core",
    project_urls={
        "Bug Tracker": "https://github.com/meggy-ai/bruno-core/issues",
        "Documentation": "https://bruno-core.readthedocs.io",
        "Source Code": "https://github.com/meggy-ai/bruno-core",
    },
    packages=find_packages(exclude=["tests", "tests.*", "examples", "docs"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Typing :: Typed",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pydantic>=2.0.0,<3.0.0",
        "typing-extensions>=4.0.0",
        "python-dotenv>=1.0.0",
        "structlog>=24.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
            "ruff>=0.1.0",
            "pre-commit>=3.0.0",
        ],
        "docs": [
            "mkdocs>=1.5.0",
            "mkdocs-material>=9.0.0",
            "mkdocstrings[python]>=0.24.0",
        ],
    },
    entry_points={
        "bruno.abilities": [
            # Extension packages can register abilities here
        ],
        "bruno.llm_providers": [
            # Extension packages can register LLM providers here
        ],
        "bruno.memory_backends": [
            # Extension packages can register memory backends here
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords=[
        "bruno",
        "ai-assistant",
        "llm",
        "chatbot",
        "framework",
        "plugin-system",
        "async",
    ],
)
