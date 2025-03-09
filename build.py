
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Build Script for Secure File Shredder
-------------------------------------
Creates a standalone executable using PyInstaller.
"""

import os
import subprocess
import platform

def build_executable():
    """Build the standalone executable using PyInstaller."""
    print("Building Secure File Shredder executable...")
    
    # Determine the icon format based on platform
    icon_path = os.path.join("icons", "shredder_icon.svg")
    icon_path_win = os.path.join("icons", "file-shredder.ico")
    if platform.system() == "Windows":
        icon_option = f"--icon={icon_path_win}"
    elif platform.system() == "Darwin":  # macOS
        icon_option = f"--icon={icon_path}"
    else:  # Linux
        icon_option = f"--icon={icon_path}"
    
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--name=SecureFileShredder",
        "--onefile",
        "--windowed",
        "main.py"
    ]
    
    # Run PyInstaller
    try:
        subprocess.run(cmd, check=True)
        print("\nBuild completed successfully!")
        print(f"Executable created at: {os.path.join('dist', 'SecureFileShredder')}")
    except subprocess.CalledProcessError as e:
        print(f"Error building executable: {e}")
        return False
    
    return True

if __name__ == "__main__":
    build_executable()
