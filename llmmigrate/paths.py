""" paths.py
Exposes common paths useful for manipulating datasets and generating figures.
"""
from pathlib import Path

# Absolute path to the top level of the repository
root = Path(__file__).resolve().parents[1].absolute()

# Absolute path to the project folder
src = root

# Data directory
data = src / 'data'