#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
File Shredder Application
-------------------------
A secure file deletion application that implements pattern-based file shredding.
"""

import sys
from gui import FileShredderApp
import tkinter as tk

def main():
    """Main application entry point."""
    root = tk.Tk()
    app = FileShredderApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
