from setuptools import setup, find_packages

setup(
    name="axe",
    version="0.1.0",
    description="A CLI tool for managing and troubleshooting prometheus alertmanager configurations",
    author="Thomas Nyambati",
    author_email="thomasnyambati@gmail.com",
    packages=["axe"],
    install_requires=[
        "click>=8.0.0",
        "pyyaml>=6.0.2",
        "rich>=13.5.0",
    ],
    entry_points={
        "console_scripts": [
            "axe=axe.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)
