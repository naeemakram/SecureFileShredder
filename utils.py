#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Utility Functions
----------------
Helper functions for the file shredder application.
"""

import os
import sys
from typing import Any

def resource_path(relative_path: str) -> str:
    """
    Get the absolute path to a resource, works for development and for PyInstaller.
    
    Args:
        relative_path: The relative path to the resource
        
    Returns:
        The absolute path to the resource
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)
    except Exception:
        return relative_path

def get_human_readable_size(size_in_bytes: int) -> str:
    """
    Convert a file size in bytes to a human-readable string.
    
    Args:
        size_in_bytes: File size in bytes
        
    Returns:
        Human-readable size string (e.g., "2.5 MB")
    """
    if size_in_bytes < 1024:
        return f"{size_in_bytes} bytes"
    elif size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.1f} KB"
    elif size_in_bytes < 1024 * 1024 * 1024:
        return f"{size_in_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_in_bytes / (1024 * 1024 * 1024):.2f} GB"
