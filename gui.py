#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
File Shredder GUI
----------------
A user interface for the file shredding application.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import importlib.util
from typing import List, Dict, Any
import json
import logging

from file_shredder import FileShredder, ShreddingMethod
from utils import resource_path

# Configure logging
logging.basicConfig(level=logging.INFO)

# Check if PyPDF2 is available
pdf_support_available = importlib.util.find_spec("PyPDF2") is not None
if not pdf_support_available:
    logging.info("PyPDF2 is not available. PDF content search will be disabled.")
else:
    logging.info("PyPDF2 is available. PDF content search will be enabled.")

# Check for OCR libraries
ocr_support_available = importlib.util.find_spec("pytesseract") is not None
if ocr_support_available:
    try:
        import pytesseract
        ocr_lib_available = True
        from ocr_processor import OCRProcessor # Assuming this file exists and contains OCRProcessor class
    except ImportError as e:
        print(f"pytesseract installed but error importing: {e}")
        ocr_lib_available = False
else:
    print("pytesseract is not available. OCR functionality will be disabled.")
    ocr_lib_available = False



class FileShredderApp:
    """Main application window for File Shredder."""

    SETTINGS_FILE = "settings.json"

    def __init__(self, root: tk.Tk):
        """
        Initialize the application.

        Args:
            root: The tkinter root window
        """
        self.root = root
        self.root.title("Secure File Shredder")
        self.root.geometry("650x500")
        self.root.resizable(True, True)
        self.root.minsize(600, 450)

        # Initialize file shredder with default method
        self.shredder = FileShredder(method=ShreddingMethod.BASIC, passes=3)

        # Set application icon
        try:
            icon_path = resource_path(os.path.join("icons", "shredder_icon.svg"))
            self.root.iconbitmap(icon_path)
        except Exception:
            # Icon not critical, continue without it
            pass

        # Status variables
        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0.0)
        self.is_shredding = False
        self.matching_files = []
        self.excluded_count = 0

        # User preferences
        self.ocr_enabled = tk.BooleanVar(value=False)  # Default: OCR disabled

        # Create a main container frame that will expand
        self.container = ttk.Frame(self.root)
        self.container.pack(fill="both", expand=True)

        # Create canvas and scrollbar
        self.canvas = tk.Canvas(self.container)
        self.scrollbar = ttk.Scrollbar(self.container, orient="vertical", command=self.canvas.yview)
        
        # Create the scrollable frame inside the canvas
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        # Create a window inside the canvas to hold the scrollable frame
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # Configure canvas to expand with window
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        
        # Pack the canvas and scrollbar to fill the available space
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Configure the canvas scrolling
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Create main frame for controls that will expand within scrollable frame
        self.main_frame = ttk.Frame(self.scrollable_frame)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Move existing UI components to the scrollable frame
        self._create_ui()

        # Bind window close event to clean exit
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Create menu bar
        self._create_menu()

        # Load settings
        self._load_settings()

    def _on_canvas_configure(self, event):
        # Update the width of the canvas window when the canvas is resized
        self.canvas.itemconfig(self.canvas_frame, width=event.width)

    def _create_menu(self):
        """Create the application menu bar."""
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)

        # Options menu
        options_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Options", menu=options_menu)

        # OCR Toggle option
        options_menu.add_checkbutton(
            label="Enable OCR for image files",
            variable=self.ocr_enabled,
            command=self._toggle_ocr
        )

        # Set initial state based on OCR availability
        if not ocr_lib_available:
            options_menu.entryconfig("Enable OCR for image files", state=tk.DISABLED)
            self.ocr_enabled.set(False)

        # Sponsored By menu
        sponsored_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Sponsored By", menu=sponsored_menu)
        sponsored_menu.add_command(label="Advertise Here", command=self._show_sponsored_dialog)

        # About menu
        about_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Help", menu=about_menu)
        about_menu.add_command(label="Shredding Methods", command=self._show_method_info)
        about_menu.add_command(label="About", command=self._show_about)
        about_menu.add_command(label="Packages", command=self._show_packages)

        # Clear Settings menu
        settings_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Clear Saved Settings", command=self._clear_settings)

    def _toggle_ocr(self):
        """Handle OCR toggle and update UI accordingly."""
        ocr_status = "enabled" if self.ocr_enabled.get() else "disabled"
        self.status_var.set(f"OCR is now {ocr_status}")

        # Update context menu for OCR extraction
        if self.ocr_enabled.get() and ocr_lib_available:
            self.context_menu.entryconfig("🔍 Extract Text (OCR)", state=tk.NORMAL)
        else:
            self.context_menu.entryconfig("🔍 Extract Text (OCR)", state=tk.DISABLED)

    def _show_about(self):
        """Display the About dialog with version and author information."""
        # Create a custom dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("About Secure File Shredder")
        dialog.geometry("400x250")
        dialog.transient(self.root)  # Make dialog modal
        dialog.grab_set()  # Modal behavior
        dialog.resizable(False, False)

        # Create main frame
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # App name and version
        ttk.Label(frame, text="Secure File Shredder v1.1", 
                 font=("", 12, "bold")).pack(pady=(0, 10))

        # Author info
        ttk.Label(frame, text="Created by Naeem Akram Malik",
                 font=("", 10)).pack(pady=(0, 2))
        ttk.Label(frame, text="Sr. Test Engineer",
                 font=("", 10)).pack(pady=(0, 10))

        # Create hyperlinks
        linkedin_url = "https://www.linkedin.com/in/naeemakrammalik/"
        email = "naeem.akram.malik@gmail.com"

        # LinkedIn link
        linkedin_frame = ttk.Frame(frame)
        linkedin_frame.pack(fill=tk.X, pady=2)
        ttk.Label(linkedin_frame, text="LinkedIn: ").pack(side=tk.LEFT)
        linkedin_link = ttk.Label(linkedin_frame, text=linkedin_url,
                                foreground="blue", cursor="hand2")
        linkedin_link.pack(side=tk.LEFT)

        # Email link
        email_frame = ttk.Frame(frame)
        email_frame.pack(fill=tk.X, pady=2)
        ttk.Label(email_frame, text="Email: ").pack(side=tk.LEFT)
        email_link = ttk.Label(email_frame, text=email,
                             foreground="blue", cursor="hand2")
        email_link.pack(side=tk.LEFT)

        # Bind click events
        def open_linkedin(event):
            import webbrowser
            webbrowser.open(linkedin_url)

        def send_email(event):
            import webbrowser
            webbrowser.open(f"mailto:{email}")

        linkedin_link.bind("<Button-1>", open_linkedin)
        email_link.bind("<Button-1>", send_email)

        # Add hover effect
        def on_enter(event):
            event.widget.configure(font=("", 9, "underline"))

        def on_leave(event):
            event.widget.configure(font=("", 9))

        for link in (linkedin_link, email_link):
            link.bind("<Enter>", on_enter)
            link.bind("<Leave>", on_leave)

        # Close button
        ttk.Button(frame, text="Close", command=dialog.destroy).pack(pady=20)

        # Center the dialog relative to the main window
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

    def _show_sponsored_dialog(self):
        """Show a dialog with sponsorship information."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Sponsored By")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        # Main frame
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # Message
        message = ttk.Label(frame, text="Advertise Here", font=("", 16, "bold"), foreground="red")
        message.pack(pady=(0, 10))

        # Email
        contact_label = ttk.Label(frame, text="Contact:", font=("", 12))
        contact_label.pack()

        email_label = ttk.Label(frame, text="naeem.akram.malik@gmail.com", font=("", 12), foreground="blue", cursor="hand2")
        email_label.pack()

        # Make email clickable
        def send_email(event):
            import webbrowser
            webbrowser.open(f"mailto:naeem.akram.malik@gmail.com")

        email_label.bind("<Button-1>", send_email)

        # Close button
        close_btn = ttk.Button(frame, text="Close", command=dialog.destroy)
        close_btn.pack(pady=20)

        # Center the dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

    def _create_ui(self):
        """Create and layout the UI components."""
        # Main frame
        main_frame = ttk.Frame(self.main_frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Create folder selection frame
        folder_frame = ttk.LabelFrame(main_frame, text="Directory Selection", padding=10)
        folder_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(folder_frame, text="Folder:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.folder_path = tk.StringVar()
        folder_entry = ttk.Entry(folder_frame, textvariable=self.folder_path, width=50)
        folder_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        folder_entry.bind("<Return>", lambda e: self._find_files())

        browse_btn = ttk.Button(folder_frame, text="📂 Browse...", command=self._browse_folder)
        browse_btn.grid(row=0, column=2, sticky=tk.E, padx=5, pady=5)

            # Recursive option
        self.recursive_var = tk.BooleanVar(value=False)
        recursive_chk = ttk.Checkbutton(
            folder_frame, 
            text="Include subdirectories (recursive)",
            variable=self.recursive_var,
            command=self._find_files
        )
        recursive_chk.grid(row=2, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5)

        # Create pattern and options frame
        options_frame = ttk.LabelFrame(main_frame, text="Shredding Options", padding=10)
        options_frame.pack(fill=tk.X, padx=5, pady=5)

        # Add shredding method selection
        method_frame = ttk.Frame(options_frame)
        method_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=5)

        ttk.Label(method_frame, text="Shredding Method:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.method_var = tk.StringVar(value=ShreddingMethod.BASIC.value)
        method_combo = ttk.Combobox(method_frame, textvariable=self.method_var, state="readonly", width=30)
        method_combo["values"] = [
            f"Basic (Multi-pass Random) - {ShreddingMethod.BASIC.value}",
            f"DoD 5220.22-M (7-pass) - {ShreddingMethod.DOD_5220_22_M.value}"
        ]
        method_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        method_combo.bind("<<ComboboxSelected>>", self._on_method_change)

        # Add verification option and passes in a single frame
        controls_frame = ttk.Frame(method_frame)
        controls_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)

        # Add verification option
        self.verify_var = tk.BooleanVar(value=True)
        verify_chk = ttk.Checkbutton(
            controls_frame,
            text="Verify overwrite",
            variable=self.verify_var,
            command=self._update_shredder_config
        )
        verify_chk.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self._create_tooltip(verify_chk, 
            "When enabled, each overwrite pass will be verified\n"
            "to ensure data was written correctly.\n"
            "This doubles the operation time but increases security."
        )

        # Add passes spinbox (only for Basic method)
        ttk.Label(controls_frame, text="Passes:").grid(row=0, column=1, sticky=tk.W, padx=(15, 5), pady=5)
        self.passes_var = tk.IntVar(value=3)
        passes_spinbox = ttk.Spinbox(controls_frame, from_=1, to=100, width=5, textvariable=self.passes_var)
        passes_spinbox.grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        passes_spinbox.bind("<Return>", lambda e: self._update_shredder_config())
        self._create_tooltip(passes_spinbox, 
            "Number of overwrite passes for Basic method.\n"
            "More passes = more secure, but slower.\n"
            "DoD method always uses 7 passes."
        )

        # Store the passes controls for show/hide functionality
        self.passes_controls = [
            controls_frame.grid_slaves(row=0, column=1)[0],  # Label
            passes_spinbox
        ]

        ttk.Label(options_frame, text="File Pattern:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.pattern_var = tk.StringVar(value="*.*")
        pattern_entry = ttk.Entry(options_frame, textvariable=self.pattern_var, width=20)
        pattern_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        pattern_entry.bind("<Return>", lambda e: self._find_files())

        ttk.Label(options_frame, text="(e.g., *.txt, secret*, document?.pdf)").grid(
            row=1, column=2, sticky=tk.W, padx=5, pady=5)

        # Exclude pattern
        ttk.Label(options_frame, text="Exclude File Pattern:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.exclude_pattern_var = tk.StringVar(value="")
        exclude_pattern_entry = ttk.Entry(options_frame, textvariable=self.exclude_pattern_var, width=20)
        exclude_pattern_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        exclude_pattern_entry.bind("<Return>", lambda e: self._find_files())

        # Adjust the row for the recursive option
        ttk.Label(options_frame, text="(e.g., *.log, *.exe)").grid(
            row=2, column=2, sticky=tk.W, padx=5, pady=5)

        # Add metadata filtering section
        metadata_frame = ttk.LabelFrame(options_frame, text="Metadata Filters", padding=5)
        metadata_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=5)

        # Owner regex pattern
        ttk.Label(metadata_frame, text="Owner Name (regex):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.owner_pattern_var = tk.StringVar(value="")
        owner_entry = ttk.Entry(metadata_frame, textvariable=self.owner_pattern_var, width=20)
        owner_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        owner_entry.bind("<Return>", lambda e: self._find_files())

        # Content filtering frame
        content_frame = ttk.Frame(metadata_frame)
        content_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)

        ttk.Label(content_frame, text="Include if Content Contains:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.content_pattern_var = tk.StringVar(value="")
        content_pattern_entry = ttk.Entry(content_frame, textvariable=self.content_pattern_var, width=20)
        content_pattern_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        content_pattern_entry.bind("<Return>", lambda e: self._find_files())

        ttk.Label(content_frame, text="Min Occurrences:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.content_min_occurrences_var = tk.IntVar(value=1)
        content_min_spinbox = ttk.Spinbox(content_frame, from_=1, to=1000, width=5, textvariable=self.content_min_occurrences_var)
        content_min_spinbox.grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)

        # Exclude by content
        ttk.Label(content_frame, text="Exclude if Content Contains:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.exclude_content_pattern_var = tk.StringVar(value="")
        exclude_content_pattern_entry = ttk.Entry(content_frame, textvariable=self.exclude_content_pattern_var, width=20)
        exclude_content_pattern_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        exclude_content_pattern_entry.bind("<Return>", lambda e: self._find_files())

        ttk.Label(content_frame, text="Min Occurrences:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        self.exclude_content_min_occurrences_var = tk.IntVar(value=1)
        exclude_content_min_spinbox = ttk.Spinbox(content_frame, from_=1, to=1000, width=5, textvariable=self.exclude_content_min_occurrences_var)
        exclude_content_min_spinbox.grid(row=1, column=3, sticky=tk.W, padx=5, pady=5)

        ttk.Label(content_frame, text="(Searches .txt, .csv, .pdf files)").grid(row=2, column=0, columnspan=4, sticky=tk.W, padx=5, pady=2)

        # Date filters
        date_frame = ttk.Frame(metadata_frame)
        date_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)

        # Created after/before
        ttk.Label(date_frame, text="Created After:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.created_after_var = tk.StringVar(value="")
        created_after_entry = ttk.Entry(date_frame, textvariable=self.created_after_var, width=16)
        created_after_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        created_after_entry.bind("<Return>", lambda e: self._find_files())

        ttk.Label(date_frame, text="Created Before:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.created_before_var = tk.StringVar(value="")
        created_before_entry = ttk.Entry(date_frame, textvariable=self.created_before_var, width=16)
        created_before_entry.grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)
        created_before_entry.bind("<Return>", lambda e: self._find_files())

        # Modified after/before
        ttk.Label(date_frame, text="Modified After:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.modified_after_var = tk.StringVar(value="")
        modified_after_entry = ttk.Entry(date_frame, textvariable=self.modified_after_var, width=16)
        modified_after_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        modified_after_entry.bind("<Return>", lambda e: self._find_files())

        ttk.Label(date_frame, text="Modified Before:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        self.modified_before_var = tk.StringVar(value="")
        modified_before_entry = ttk.Entry(date_frame, textvariable=self.modified_before_var, width=16)
        modified_before_entry.grid(row=1, column=3, sticky=tk.W, padx=5, pady=5)
        modified_before_entry.bind("<Return>", lambda e: self._find_files())

        ttk.Label(date_frame, text="(Format: YYYY-MM-DD)").grid(row=2, column=0, columnspan=4, sticky=tk.W, padx=5, pady=2)

        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        self.find_btn = ttk.Button(
            button_frame, 
            text="🔍 Find Matching Files", 
            command=self._find_files
        )
        self.find_btn.pack(side=tk.LEFT, padx=5, pady=5)

        self.shred_btn = ttk.Button(
            button_frame, 
            text="🗑️ Shred Files", 
            command=self._confirm_shred,
            state=tk.DISABLED
        )
        self.shred_btn.pack(side=tk.LEFT, padx=5, pady=5)

        self.cancel_btn = ttk.Button(
            button_frame, 
            text="❌ Cancel", 
            command=self._cancel_operation,
            state=tk.DISABLED
        )
        self.cancel_btn.pack(side=tk.LEFT, padx=5, pady=5)

        self.clear_btn = ttk.Button(
            button_frame, 
            text="🧹 Clear", 
            command=self._clear_results
        )
        self.clear_btn.pack(side=tk.LEFT, padx=5, pady=5)

        self.excluded_btn = ttk.Button(
            button_frame, 
            text="👁️ View Excluded Files", 
            command=self._show_excluded_files,
            state=tk.DISABLED
        )
        self.excluded_btn.pack(side=tk.LEFT, padx=5, pady=5)

        # Results frame
        self.results_frame_text = tk.StringVar(value="Matching Files (0)")
        self.results_frame = ttk.LabelFrame(main_frame, text="Matching Files (0)", padding=10)
        self.results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create a treeview for files
        self.files_tree = ttk.Treeview(
            self.results_frame, 
            columns=("path", "size", "status", "matches"),
            show="headings",
            selectmode="browse"  # Allow selecting one item at a time
        )

        # Define columns
        self.files_tree.heading("path", text="File Path")
        self.files_tree.heading("size", text="Size")
        self.files_tree.heading("status", text="Status")
        self.files_tree.heading("matches", text="Content Matches")

        self.files_tree.column("path", width=250, stretch=True)
        self.files_tree.column("size", width=80, anchor=tk.E)
        self.files_tree.column("status", width=80)
        self.files_tree.column("matches", width=150)

        # Add scrollbars
        y_scroll = ttk.Scrollbar(self.results_frame, orient=tk.VERTICAL, command=self.files_tree.yview)
        self.files_tree.configure(yscrollcommand=y_scroll.set)

        x_scroll = ttk.Scrollbar(self.results_frame, orient=tk.HORIZONTAL, command=self.files_tree.xview)
        self.files_tree.configure(xscrollcommand=x_scroll.set)

        # Set up right-click context menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="📂 Open File Location", command=self._open_file_location)
        self.context_menu.add_command(label="📄 Open File", command=self._open_file)
        self.context_menu.add_command(label="📋 Copy File Name", command=self._copy_file_name)
        self.context_menu.add_command(label="ℹ️ File Properties", command=self._show_file_properties)
        self.context_menu.add_command(label="🔍 Extract Text (OCR)", command=self._show_extracted_text, state=tk.DISABLED)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="❌ Exclude File", command=self._exclude_selected_file)

        # Bind right-click event to show context menu
        self.files_tree.bind("<Button-3>", self._show_context_menu)

        # Grid layout for treeview and scrollbars
        self.files_tree.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        y_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        x_scroll.grid(row=1, column=0, sticky=(tk.E, tk.W))

        self.results_frame.grid_columnconfigure(0, weight=1)
        self.results_frame.grid_rowconfigure(0, weight=1)

        # Status and progress bar
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, padx=5, pady=5)

        self.progress_bar = ttk.Progressbar(
            status_frame, 
            variable=self.progress_var,
            mode="determinate",
            length=200
        )
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)

        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.pack(side=tk.LEFT, padx=5, pady=5)

        # Configure grid weights to make the UI responsive
        main_frame.columnconfigure(0, weight=1)

    def _browse_folder(self):
        """Open a directory browser dialog and automatically load matching files."""
        folder = filedialog.askdirectory(title="Select Directory")
        if folder:
            self.folder_path.set(folder)
            # Automatically find matching files after selecting a directory
            self._find_files()

    def _find_files(self):
        """Find files matching the pattern in the selected directory."""
        directory = self.folder_path.get().strip()
        pattern = self.pattern_var.get().strip()
        exclude_pattern = self.exclude_pattern_var.get().strip()
        recursive = self.recursive_var.get()

        # Validate inputs
        if not directory:
            messagebox.showwarning("Missing Directory", "Please select a directory.")
            return

        if not pattern:
            messagebox.showwarning("Missing Pattern", "Please enter a file pattern.")
            return

        if not os.path.isdir(directory):
            messagebox.showerror("Invalid Directory", "The specified directory does not exist.")
            return

        # Update UI for search operation
        self.status_var.set("Searching for files...")
        self.progress_var.set(0)
        self._clear_file_list()
        
        # Show busy cursor
        self.root.config(cursor="wait")
        self.find_btn.config(state=tk.DISABLED)
        self.root.update()

        # Find matching files in a separate thread
        threading.Thread(target=self._find_files_thread, 
                         args=(directory, pattern, recursive, exclude_pattern), 
                         daemon=True).start()

    def _find_files_thread(self, directory: str, pattern: str, recursive: bool, exclude_pattern: str = ""):
        """
        Thread function to find matching files.

        Args:
            directory: Directory to search
            pattern: File pattern to match
            recursive: Whether to search recursively
            exclude_pattern: Pattern of files to exclude
        """
        try:
            # Update the shredder passes
            self.shredder.passes = self.passes_var.get()

            # Parse date filters
            created_after = None
            created_before = None
            modified_after = None
            modified_before = None

            # Convert date strings to timestamps if provided
            if self.created_after_var.get().strip():
                try:
                    created_after = self._parse_date(self.created_after_var.get())
                except ValueError as e:
                    self.root.after(0, lambda: self._show_error(f"Invalid 'Created After' date: {str(e)}"))
                    return

            if self.created_before_var.get().strip():
                try:
                    created_before = self._parse_date(self.created_before_var.get())
                except ValueError as e:
                    self.root.after(0, lambda: self._show_error(f"Invalid 'Created Before' date: {str(e)}"))
                    return

            if self.modified_after_var.get().strip():
                try:
                    modified_after = self._parse_date(self.modified_after_var.get())
                except ValueError as e:
                    self.root.after(0, lambda: self._show_error(f"Invalid 'Modified After' date: {str(e)}"))
                    return

            if self.modified_before_var.get().strip():
                try:
                    modified_before = self._parse_date(self.modified_before_var.get())
                except ValueError as e:
                    self.root.after(0, lambda: self._show_error(f"Invalid 'Modified Before' date: {str(e)}"))
                    return

            # Get owner pattern if provided
            owner_pattern = self.owner_pattern_var.get().strip() or None

            # Get content filtering parameters
            content_pattern = self.content_pattern_var.get().strip() or None
            content_min_occurrences = self.content_min_occurrences_var.get()

            # Get exclude content filtering parameters
            exclude_content_pattern = self.exclude_content_pattern_var.get().strip() or None
            exclude_content_min_occurrences = self.exclude_content_min_occurrences_var.get()

            # Find matching files and get excluded count
            self.matching_files, self.excluded_count = self.shredder.find_files(
                directory, 
                pattern, 
                recursive, 
                exclude_pattern, 
                return_excluded_count=True,
                owner_pattern=owner_pattern,
                created_after=created_after,
                created_before=created_before,
                modified_after=modified_after,
                modified_before=modified_before,
                content_pattern=content_pattern,
                content_min_occurrences=content_min_occurrences,
                exclude_content_pattern=exclude_content_pattern,
                exclude_content_min_occurrences=exclude_content_min_occurrences,
                ocr_enabled=self.ocr_enabled.get()
            )

            # Update UI from main thread
            self.root.after(0, self._update_file_list)

        except Exception as e:
            # Show error on main thread
            self.root.after(0, lambda: self._show_error(f"Error finding files: {str(e)}"))
        finally:
            # Reset cursor and button state in main thread
            self.root.after(0, lambda: self._reset_search_ui())

    def _reset_search_ui(self):
        """Reset the UI after search operation completes."""
        self.root.config(cursor="")
        self.find_btn.config(state=tk.NORMAL)

    def _update_file_list(self):
        """Update the file list treeview with matching files."""
        self._clear_file_list()

        if not self.matching_files:
            self.status_var.set("No matching files found.")
            self.shred_btn.configure(state=tk.DISABLED)
            return

        # Add files to the treeview
        for file_info in self.matching_files:
            file_path = file_info[0]  # First element is the file path
            content_match_info = file_info[1]  # Second element is the match info dictionary

            # Format content matches information
            matches_display = ""
            if content_match_info:
                if 'include' in content_match_info:
                    pattern = content_match_info['include']['pattern']
                    occurrences = content_match_info['include']['occurrences']
                    matches_display = f"'{pattern}': {occurrences}x"
                elif 'exclude' in content_match_info:
                    pattern = content_match_info['exclude']['pattern']
                    occurrences = content_match_info['exclude']['occurrences']
                    matches_display = f"Excluded: '{pattern}': {occurrences}x"

            try:
                size = os.path.getsize(file_path)
                # Format the size
                if size < 1024:
                    size_str = f"{size} bytes"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} MB"

                self.files_tree.insert("", tk.END, values=(file_path, size_str, "Pending", matches_display))
            except Exception:
                # If we can't get the size (e.g., permission error), show unknown
                self.files_tree.insert("", tk.END, values=(file_path, "Unknown", "Pending", matches_display))

        # Update status and results frame title
        file_count = len(self.matching_files)
        self.status_var.set(f"Found matching: {file_count}, Excluded: {self.excluded_count}.")
        self.results_frame_text.set(f"Matching Files ({file_count})")
        self.results_frame.configure(text=f"Matching Files ({file_count})")

        self.shred_btn.configure(state=tk.NORMAL)

        # Enable excluded files button if there are excluded files
        if self.excluded_count > 0:
            self.excluded_btn.configure(state=tk.NORMAL)
        else:
            self.excluded_btn.configure(state=tk.DISABLED)

    def _clear_file_list(self):
        """Clear the file list treeview."""
        for item in self.files_tree.get_children():
            self.files_tree.delete(item)
        self.results_frame_text.set("Matching Files (0)")
        self.results_frame.configure(text="Matching Files (0)")

    def _clear_results(self):
        """Clear the matching files list and reset the UI."""
        if self.is_shredding:
            messagebox.showwarning(
                "Operation in Progress",
                "Cannot clear results while an operation is in progress."
            )
            return

        self._clear_file_list()
        self.matching_files = []
        self.excluded_count = 0
        self.progress_var.set(0)
        self.status_var.set("Ready")
        self.shred_btn.configure(state=tk.DISABLED)

    def _confirm_shred(self):
        """Show confirmation dialog before shredding files."""
        if not self.matching_files:
            return

        response = messagebox.askokcancel(
            title="Confirm File Shredding",
            message=f"Are you sure you want to permanently shred {len(self.matching_files)} files?\n\n"
                    "This operation CANNOT be undone and the files will be unrecoverable.",
            icon=messagebox.WARNING
        )

        if response:
            self._shred_files()

    def _shred_files(self):
        """Start the file shredding process."""
        if self.is_shredding:
            return

        # Update UI for shredding operation
        self.is_shredding = True
        self.find_btn.configure(state=tk.DISABLED)
        self.shred_btn.configure(state=tk.DISABLED)
        self.cancel_btn.configure(state=tk.NORMAL)
        self.status_var.set("Shredding files...")
        self.progress_var.set(0)

        # Mark all files as pending
        for item in self.files_tree.get_children():
            self.files_tree.item(item, values=(
                self.files_tree.item(item)['values'][0],
                self.files_tree.item(item)['values'][1],
                "Pending"
            ))

        self.root.update()

        # Start shredding in a separate thread
        threading.Thread(target=self._shred_files_thread, daemon=True).start()

    def _shred_files_thread(self):
        """Thread function to shred files."""
        try:
            # Extract just the file paths from the matching_files list
            files_to_shred = [file_info[0] for file_info in self.matching_files]

            # Shred the files
            self.shredder.shred_files(
                files_to_shred,
                progress_callback=self._update_progress,
                file_complete_callback=self._file_complete
            )

            # Update UI from main thread when complete
            self.root.after(0, self._shredding_complete)

        except Exception as e:
            # Show error on main thread
            self.root.after(0, lambda: self._show_error(f"Error shredding files: {str(e)}"))
            self.root.after(0, self._shredding_complete)

    def _update_progress(self, progress: float, current_file: str):
        """
        Update progress bar and status.

        Args:
            progress: Overall progress value (0.0 to 1.0)
            current_file: Path of the file currently being processed
        """
        # Update UI from main thread
        self.root.after(0, lambda: self._update_ui_progress(progress, current_file))

    def _update_ui_progress(self, progress: float, current_file: str):
        """Update the UI with progress information (called from main thread)."""
        self.progress_var.set(progress * 100)

        # Truncate file path if too long
        if len(current_file) > 40:
            short_path = "..." + current_file[-40:]
        else:
            short_path = current_file

        self.status_var.set(f"Shredding: {short_path}")

    def _file_complete(self, file_path: str, success: bool):
        """
        Update file status in the treeview when shredding completes.

        Args            file_path: Path of the processed file
            success: Whether shredding was successful
        """
        # Update UI from main thread
        self.root.after(0, lambda: self._update_file_status(file_path, success))

    def _update_file_status(self, file_path: str, success: bool):
        """Update file status in the treeview (called from main thread)."""
        # Find the item in the treeview
        for item in self.files_tree.get_children():
            if self.files_tree.item(item)['values'][0] == file_path:
                status = "Completed" if success else "Failed"
                values = self.files_tree.item(item)['values']
                # Preserve the original matches column value
                matches = values[3] if len(values) > 3 else ""
                self.files_tree.item(item, values=(
                    file_path,
                    values[1],  # Size
                    status,
                    matches
                ))
                break

    def _shredding_complete(self):
        """Update UI when shredding operation is complete."""
        self.is_shredding = False
        self.find_btn.configure(state=tk.NORMAL)
        self.shred_btn.configure(state=tk.DISABLED)  # Disable until new search
        self.cancel_btn.configure(state=tk.DISABLED)
        self.progress_var.set(100)
        self.status_var.set("Shredding complete")

        # Count successful and failed files
        success_count = 0
        failed_count = 0
        for item in self.files_tree.get_children():
            status = self.files_tree.item(item)['values'][2]
            if status == "Completed":
                success_count += 1
            elif status == "Failed":
                failed_count += 1

        # Clear the matching files list since they've been processed
        self.matching_files = []

        # Show summary
        messagebox.showinfo(
            "Shredding Complete", 
            f"Shredding operation complete.\n\n"
            f"Successfully shredded: {success_count} files\n"
            f"Failed: {failed_count} files"
        )

    def _parse_date(self, date_str: str) -> float:
        """
        Parse a date string in YYYY-MM-DD format and return Unix timestamp.

        Args:
            date_str: Date string in YYYY-MM-DD format

        Returns:
            Unix timestamp

        Raises:
            ValueError: If the date string is invalid
        """
        import datetime
        try:
            # Parse the date string
            date_obj = datetime.datetime.strptime(date_str.strip(), "%Y-%m-%d")
            # Convert to timestamp
            return date_obj.timestamp()
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")

    def _on_method_change(self, event=None):
        """Handle shredding method change."""
        # Extract the actual method value from the selected text
        selected_text = self.method_var.get()
        if "Basic" in selected_text:
            method = ShreddingMethod.BASIC
        elif "DoD" in selected_text:
            method = ShreddingMethod.DOD_5220_22_M
        else:
            return  # Invalid selection
        
        # Set passes to 7 for DoD method
        if method == ShreddingMethod.DOD_5220_22_M:
            self.passes_var.set(7)
        
        # Show/hide passes spinbox based on method
        if method == ShreddingMethod.BASIC:
            for control in self.passes_controls:
                control.grid()
        else:
            for control in self.passes_controls:
                control.grid_remove()
        
        # Update shredder configuration
        self._update_shredder_config()

    def _update_shredder_config(self):
        """Update the shredder configuration based on UI settings."""
        # Extract the actual method value from the selected text
        selected_text = self.method_var.get()
        if "Basic" in selected_text:
            method = ShreddingMethod.BASIC
        elif "DoD" in selected_text:
            method = ShreddingMethod.DOD_5220_22_M
        else:
            return  # Invalid selection
        
        passes = self.passes_var.get() if method == ShreddingMethod.BASIC else 7
        verify = self.verify_var.get()
        
        self.shredder = FileShredder(method=method, passes=passes, verify=verify)
        
        # Update status
        method_name = "DoD 5220.22-M (7-pass)" if method == ShreddingMethod.DOD_5220_22_M else f"Basic ({passes}-pass)"
        verify_status = "with verification" if verify else "without verification"
        self.status_var.set(f"Shredding method set to: {method_name} {verify_status}")

    def _cancel_operation(self):
        """Cancel the current operation."""
        if not self.is_shredding:
            return

        # We'll implement a simple cancel flag that the threads can check
        response = messagebox.askokcancel(
            "Cancel Operation",
            "Are you sure you want to cancel the current operation?\n\n"
            "This will stop the shredding process, but any files that have already been processed cannot be recovered."
        )

        if response:
            self.status_var.set("Cancelling operation...")
            self.is_shredding = False

    def _show_error(self, message: str):
        """Display an error message dialog."""
        messagebox.showerror("Error", message)

        # Reset status
        self.status_var.set("Ready")
        self.is_shredding = False
        self.find_btn.configure(state=tk.NORMAL)
        self.shred_btn.configure(state=tk.DISABLED)
        self.cancel_btn.configure(state=tk.DISABLED)

    def _show_context_menu(self, event):
        """Display the context menu on right-click."""
        # Get the selected item
        item = self.files_tree.identify_row(event.y)
        if item:
            # Select the item user right-clicked on
            self.files_tree.selection_set(item)

            # Check if the selected file is an image to enable/disable OCR option
            file_path = self._get_selected_file_path()
            if file_path:
                # Get file extension
                _, ext = os.path.splitext(file_path.lower())
                # Check if it's a supported image format and OCR is available and enabled
                ocr_supported = ocr_lib_available and self.ocr_enabled.get() and ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']

                # Update menu state
                self.context_menu.entryconfig("🔍 Extract Text (OCR)", 
                                             state=tk.NORMAL if ocr_supported else tk.DISABLED)

            # Show context menu
            self.context_menu.post(event.x_root, event.y_root)

    def _get_selected_file_path(self):
        """Get the file path of the selected item in the treeview."""
        selected_items = self.files_tree.selection()
        if not selected_items:
            return None

        # Get the file path from the first column of the selected item
        item_values = self.files_tree.item(selected_items[0])['values']
        if item_values:
            return item_values[0]
        return None

    def _open_file_location(self):
        """Open the containing folder of the selected file."""
        file_path = self._get_selected_file_path()
        if not file_path:
            return

        try:
            if os.path.exists(file_path):
                # Get the directory containing the file
                directory = os.path.dirname(file_path)

                # Open the directory in the file explorer
                if sys.platform == 'win32':
                    os.startfile(directory)
                elif sys.platform == 'darwin':  # macOS
                    import subprocess
                    subprocess.run(['open', directory])
                else:  # Linux
                    import subprocess
                    subprocess.run(['xdg-open', directory])

        except Exception as e:
            messagebox.showerror("Error", f"Could not open file location: {str(e)}")

    def _open_file(self):
        """Open the selected file with the default application."""
        file_path = self._get_selected_file_path()
        if not file_path:
            return

        try:
            if os.path.exists(file_path):
                if sys.platform == 'win32':
                    os.startfile(file_path)
                elif sys.platform == 'darwin':  # macOS
                    import subprocess
                    subprocess.run(['open', file_path])
                else:  # Linux
                    import subprocess
                    subprocess.run(['xdg-open', file_path])

        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {str(e)}")

    def _show_file_properties(self):
        """Display properties of the selected file."""
        file_path = self._get_selected_file_path()
        if not file_path:
            return

        try:
            if os.path.exists(file_path):
                # Get file statistics
                stat_info = os.stat(file_path)

                # Format creation and modification times
                from datetime import datetime
                created_time = datetime.fromtimestamp(stat_info.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
                modified_time = datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                accessed_time = datetime.fromtimestamp(stat_info.st_atime).strftime('%Y-%m-%d %H:%M:%S')

                # Format file size
                size_bytes = stat_info.st_size
                if size_bytes < 1024:
                    size_str = f"{size_bytes} bytes"
                elif size_bytes < 1024 * 1024:
                    size_str = f"{size_bytes / 1024:.2f} KB"
                elif size_bytes < 1024 * 1024 * 1024:
                    size_str = f"{size_bytes / (1024 * 1024):.2f} MB"
                else:
                    size_str = f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

                # Try to get owner information (platform-specific)
                owner = "Unknown"
                try:
                    if sys.platform != 'win32':
                        import pwd
                        owner = pwd.getpwuid(stat_info.st_uid).pw_name
                    else:
                        import win32security
                        sd = win32security.GetFileSecurity(file_path, win32security.OWNER_SECURITY_INFORMATION)
                        owner_sid = sd.GetSecurityDescriptorOwner()
                        name, domain, type = win32security.LookupAccountSid(None, owner_sid)
                        owner = f"{domain}\\{name}"
                except (ImportError, PermissionError, OSError):
                    pass

                # Get content matches information
                matches_info = ""
                for item in self.files_tree.selection():
                    values = self.files_tree.item(item)['values']
                    if values[0] == file_path and values[3]:  # Check path and matches column
                        matches_info = f"Content Matches: {values[3]}\n"
                        break

                # Create a custom dialog
                dialog = tk.Toplevel(self.root)
                dialog.title("File Properties")
                dialog.geometry("500x400")
                dialog.transient(self.root)
                dialog.grab_set()
                dialog.resizable(True, True)
                dialog.minsize(400, 300)

                # Create main frame
                frame = ttk.Frame(dialog, padding=10)
                frame.pack(fill=tk.BOTH, expand=True)

                # Add file name header
                ttk.Label(frame, text=os.path.basename(file_path),
                         font=("", 12, "bold")).pack(pady=(0, 10))

                # Create text widget with scrollbar
                text_frame = ttk.Frame(frame)
                text_frame.pack(fill=tk.BOTH, expand=True)

                scrollbar = ttk.Scrollbar(text_frame)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

                text_widget = tk.Text(text_frame, wrap=tk.WORD, width=50,
                                    yscrollcommand=scrollbar.set)
                text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                scrollbar.config(command=text_widget.yview)

                # Insert properties information
                properties_text = (
                    f"Location: {os.path.dirname(file_path)}\n"
                    f"Size: {size_str} ({stat_info.st_size:,} bytes)\n"
                    f"Owner: {owner}\n"
                    f"Created: {created_time}\n"
                    f"Modified: {modified_time}\n"
                    f"Accessed: {accessed_time}\n"
                    f"Permissions: {oct(stat_info.st_mode)[-3:]}\n"
                    f"{matches_info}"
                )

                text_widget.insert(tk.END, properties_text)
                text_widget.configure(state=tk.DISABLED)  # Make read-only

                # Button frame
                button_frame = ttk.Frame(frame)
                button_frame.pack(fill=tk.X, pady=10)

                # Copy button
                def copy_text():
                    dialog.clipboard_clear()
                    dialog.clipboard_append(text_widget.get("1.0", tk.END))
                    self.status_var.set("Properties copied to clipboard")

                copy_btn = ttk.Button(button_frame, text="📋 Copy All", command=copy_text)
                copy_btn.pack(side=tk.LEFT, padx=5)

                # Close button
                close_btn = ttk.Button(button_frame, text="Close", command=dialog.destroy)
                close_btn.pack(side=tk.RIGHT, padx=5)

                # Center the dialog relative to the main window
                dialog.update_idletasks()
                x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
                y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
                dialog.geometry(f"+{x}+{y}")

            else:
                messagebox.showwarning("File Not Found", "The selected file no longer exists.")

        except Exception as e:
            messagebox.showerror("Error", f"Could not get file properties: {str(e)}")

    def _show_extracted_text(self):
        """Show extracted text from an image using OCR in a modal dialog."""
        if not ocr_lib_available:
            messagebox.showwarning("OCR Not Available", 
                                 "OCR functionality is not available. Please install pytesseract and PIL.")
            return

        if not self.ocr_enabled.get():
            messagebox.showinfo("OCR Disabled", 
                               "OCR is currently disabled. Enable it in the Options menu.")
            return

        file_path = self._get_selected_file_path()
        if not file_path:
            return

        # Check if it's an image file
        _, ext = os.path.splitext(file_path.lower())
        if ext not in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']:
            messagebox.showinfo("Not an Image", "The selected file is not a supported image format.")
            return

        # Show a loading indicator
        self.status_var.set("Extracting text from image...")
        self.root.update()

        # Create and configure the modal dialog
        dialog = tk.Toplevel(self.root)
        dialog.title(f"OCR Text: {os.path.basename(file_path)}")
        dialog.geometry("600x500")
        dialog.transient(self.root)  # Make dialog modal
        dialog.grab_set()  # Modal behavior
        dialog.resizable(True, True)
        dialog.minsize(400, 300)

        # Run OCR in a separate thread to avoid freezing the UI
        def extract_text_thread():
            try:
                from ocr_processor import OCRProcessor
                success, text, char_count = OCRProcessor.extract_text_from_image(file_path)

                # Update UI from main thread
                self.root.after(0, lambda: self._update_ocr_dialog(dialog, success, text, char_count, file_path))
            except Exception as e:
                self.root.after(0, lambda: self._update_ocr_dialog(
                    dialog, False, f"Error extracting text: {str(e)}", None, file_path))

        # Show loading indicator in dialog
        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        progress = ttk.Progressbar(frame, mode="indeterminate")
        progress.pack(fill=tk.X, padx=50, pady=10)
        progress.start()

        # Start extraction in separate thread
        threading.Thread(target=extract_text_thread, daemon=True).start()

        # Reset status after dialog is closed
        dialog.protocol("WM_DELETE_WINDOW", lambda: self._on_ocr_dialog_close(dialog))

        # Center the dialog relative to the main window
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

    def _update_ocr_dialog(self, dialog, success, text, char_count, file_path):
        """Update the OCR dialog with extracted text."""
        # Clear the dialog
        for widget in dialog.winfo_children():
            widget.destroy()

        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        if success:
            # Header with file info
            header_frame = ttk.Frame(frame)
            header_frame.pack(fill=tk.X, pady=5)

            ttk.Label(header_frame, text=f"File: {os.path.basename(file_path)}", 
                     font=("", 10, "bold")).pack(side=tk.LEFT)

            if char_count is not None:
                ttk.Label(header_frame, text=f"Characters: {char_count}", 
                         font=("", 10)).pack(side=tk.RIGHT)

            # Create a text area with scrollbar for the extracted text
            text_frame = ttk.Frame(frame)
            text_frame.pack(fill=tk.BOTH, expand=True, pady=5)

            # Add scrollbars
            y_scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL)
            y_scroll.pack(side=tk.RIGHT, fill=tk.Y)

            x_scroll = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL)
            x_scroll.pack(side=tk.BOTTOM, fill=tk.X)

            # Add text widget
            text_widget = tk.Text(text_frame, wrap=tk.NONE, yscrollcommand=y_scroll.set, 
                                 xscrollcommand=x_scroll.set)
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            # Connect scrollbars to text widget
            y_scroll.config(command=text_widget.yview)
            x_scroll.config(command=text_widget.xview)

            # Insert the extracted text
            if text and text.strip():
                text_widget.insert(tk.END, text)
            else:
                text_widget.insert(tk.END, "No text was extracted from this image.")

            # Focus on text for immediate keyboard navigation
            text_widget.focus_set()

            # Button frame
            button_frame = ttk.Frame(frame)
            button_frame.pack(fill=tk.X, pady=10)

            # Copy button
            def copy_text():
                dialog.clipboard_clear()
                dialog.clipboard_append(text_widget.get("1.0", tk.END))
                self.status_var.set("Text copied to clipboard")

            copy_btn = ttk.Button(button_frame, text="📋 Copy Text", command=copy_text)
            copy_btn.pack(side=tk.LEFT, padx=5)

            # Close button
            close_btn = ttk.Button(button_frame, text="Close", command=dialog.destroy)
            close_btn.pack(side=tk.RIGHT, padx=5)

        else:
            # Error message
            ttk.Label(frame, text="Error Extracting Text", 
                     font=("", 12, "bold")).pack(pady=10)

            error_text = ttk.Label(frame, text=text, wraplength=400, justify=tk.LEFT)
            error_text.pack(fill=tk.BOTH, expand=True, pady=10)

            # Close button
            close_btn = ttk.Button(frame, text="Close", command=dialog.destroy)
            close_btn.pack(pady=10)

        # Reset status
        self.status_var.set("Ready")

    def _on_ocr_dialog_close(self, dialog):
        """Handle OCR dialog close event."""
        self.status_var.set("Ready")
        dialog.destroy()

    def _show_excluded_files(self):
        """Display a modal dialog showing files that were excluded from the search."""
        if self.excluded_count <= 0:
            messagebox.showinfo("No Excluded Files", "No files were excluded by the search criteria.")
            return

        # Create a modal dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Excluded Files")
        dialog.geometry("600x400")
        dialog.transient(self.root)  # Make dialog modal
        dialog.grab_set()  # Modal behavior

        # Make it resizable
        dialog.resizable(True, True)
        dialog.minsize(500, 300)

        # Explanation text
        ttk.Label(dialog, text="Files excluded by the search criteria:", padding=10).pack(fill=tk.X)

        # Create a frame for the explanation of exclusion criteria
        criteria_frame = ttk.LabelFrame(dialog, text="Exclusion Criteria Used", padding=5)
        criteria_frame.pack(fill=tk.X, padx=10, pady=5)

        criteria_text = ""
        if self.exclude_pattern_var.get().strip():
            criteria_text += f"• File pattern: {self.exclude_pattern_var.get()}\n"
        if self.owner_pattern_var.get().strip():
            criteria_text += f"• Owner pattern: {self.owner_pattern_var.get()}\n"
        if self.exclude_content_pattern_var.get().strip():
            criteria_text += f"• Content contains: '{self.exclude_content_pattern_var.get()}' (min {self.exclude_content_min_occurrences_var.get()} times)\n"
        if self.content_pattern_var.get().strip():
            criteria_text += f"• Does NOT contain: '{self.content_pattern_var.get()}' (min {self.content_min_occurrences_var.get()} times)\n"
        if self.created_after_var.get().strip():
            criteria_text += f"• Created before: {self.created_after_var.get()}\n"
        if self.created_before_var.get().strip():
            criteria_text += f"• Created after: {self.created_before_var.get()}\n"
        if self.modified_after_var.get().strip():
            criteria_text += f"• Modified before: {self.modified_after_var.get()}\n"
        if self.modified_before_var.get().strip():
            criteria_text += f"• Modified after: {self.modified_before_var.get()}\n"

        if not criteria_text:
            criteria_text = "No specific exclusion criteria applied."

        ttk.Label(criteria_frame, text=criteria_text, justify=tk.LEFT, padding=5).pack(fill=tk.X)

        # Add disclaimer
        ttk.Label(dialog, text="Note: The specific list of excluded files is not available due to efficiency reasons.", 
                 foreground="gray", padding=10).pack(fill=tk.X)

        # Summary
        ttk.Label(dialog, text=f"Total excluded files: {self.excluded_count}", 
                 font=("", 10, "bold"), padding=5).pack(fill=tk.X)

        # Close button
        close_btn = ttk.Button(dialog, text="Close", command=dialog.destroy)
        close_btn.pack(pady=10)

        # Center the dialog relative to the main window
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        # Wait until the dialog is closed
        dialog.wait_window()

    def _on_close(self):
        """Handle window close event."""
        if self.is_shredding:
            response = messagebox.askokcancel(
                "Confirm Exit",
                "An operation is in progress. Are you sure you want to exit?"
            )
            if not response:
                return

        # Save settings before closing
        self._save_settings()

        self.root.destroy()

    def _save_settings(self):
        """Save current settings to a JSON file."""
        settings = {
            "folder_path": self.folder_path.get(),
            "recursive": self.recursive_var.get(),
            "method": self.method_var.get(),
            "verify": self.verify_var.get(),
            "pattern": self.pattern_var.get(),
            "exclude_pattern": self.exclude_pattern_var.get(),
            "owner_pattern": self.owner_pattern_var.get(),
            "content_pattern": self.content_pattern_var.get(),
            "content_min_occurrences": self.content_min_occurrences_var.get(),
            "exclude_content_pattern": self.exclude_content_pattern_var.get(),
            "exclude_content_min_occurrences": self.exclude_content_min_occurrences_var.get(),
            "created_after": self.created_after_var.get(),
            "created_before": self.created_before_var.get(),
            "modified_after": self.modified_after_var.get(),
            "modified_before": self.modified_before_var.get(),
            "ocr_enabled": self.ocr_enabled.get()
        }
        with open(self.SETTINGS_FILE, "w") as f:
            json.dump(settings, f)

    def _load_settings(self):
        """Load settings from a JSON file."""
        try:
            with open(self.SETTINGS_FILE, "r") as f:
                settings = json.load(f)
                self.folder_path.set(settings.get("folder_path", ""))
                self.recursive_var.set(settings.get("recursive", False))
                self.method_var.set(settings.get("method", ShreddingMethod.BASIC.value))
                self.verify_var.set(settings.get("verify", True))
                self.pattern_var.set(settings.get("pattern", "*.*"))
                self.exclude_pattern_var.set(settings.get("exclude_pattern", ""))
                self.owner_pattern_var.set(settings.get("owner_pattern", ""))
                self.content_pattern_var.set(settings.get("content_pattern", ""))
                self.content_min_occurrences_var.set(settings.get("content_min_occurrences", 1))
                self.exclude_content_pattern_var.set(settings.get("exclude_content_pattern", ""))
                self.exclude_content_min_occurrences_var.set(settings.get("exclude_content_min_occurrences", 1))
                self.created_after_var.set(settings.get("created_after", ""))
                self.created_before_var.set(settings.get("created_before", ""))
                self.modified_after_var.set(settings.get("modified_after", ""))
                self.modified_before_var.set(settings.get("modified_before", ""))
                self.ocr_enabled.set(settings.get("ocr_enabled", False))
        except FileNotFoundError:
            pass  # No settings file exists yet

    def _clear_settings(self):
        """Clear saved settings by deleting the settings file."""
        try:
            os.remove(self.SETTINGS_FILE)
            messagebox.showinfo("Settings Cleared", "All saved settings have been cleared.")
        except FileNotFoundError:
            messagebox.showinfo("No Settings Found", "No saved settings to clear.")

    def _create_tooltip(self, widget, text):
        """Create a tooltip for a widget."""
        tooltip = tk.Label(self.root, text=text, justify=tk.LEFT,
                         relief="solid", borderwidth=1)
        tooltip.configure(bg="lightyellow", padx=5, pady=2)
        
        def enter(event):
            tooltip.lift()
            x = widget.winfo_rootx()
            y = widget.winfo_rooty() + widget.winfo_height() + 2
            tooltip.place(x=x, y=y)
            
        def leave(event):
            tooltip.place_forget()
            
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    def _show_method_info(self):
        """Show detailed information about shredding methods."""
        method = ShreddingMethod(self.method_var.get())
        description = ShreddingMethod.get_description(method)
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Shredding Method Information")
        dialog.geometry("500x400")  # Increased size
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(True, True)  # Allow resizing
        dialog.minsize(400, 300)  # Set minimum size
        
        # Main frame with padding
        main_frame = ttk.Frame(dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Method name header
        method_name = "Basic Multi-pass Random" if method == ShreddingMethod.BASIC else "DoD 5220.22-M (7-pass)"
        header = ttk.Label(main_frame, text=method_name, font=("", 12, "bold"))
        header.pack(anchor=tk.W, pady=(0, 10))
        
        # Create a frame for scrollable content
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(content_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create text widget for content
        text_widget = tk.Text(content_frame, wrap=tk.WORD, width=50, height=15,
                            yscrollcommand=scrollbar.set)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text_widget.yview)
        
        # Insert description
        text_widget.insert(tk.END, "Description:\n", "heading")
        text_widget.insert(tk.END, f"{description}\n\n")
        
        # Insert security information
        text_widget.insert(tk.END, "Security Note:\n", "heading")
        if method == ShreddingMethod.BASIC:
            security_info = (
                "The Basic method is suitable for most personal data deletion needs. "
                "Increasing the number of passes provides additional security at the "
                "cost of longer processing time."
            )
        else:
            security_info = (
                "The DoD 5220.22-M standard is designed for military-grade data sanitization. "
                "It ensures data cannot be recovered even with advanced forensic tools."
            )
        text_widget.insert(tk.END, f"{security_info}\n\n")
        
        # Insert verification info
        text_widget.insert(tk.END, "Verification:\n", "heading")
        verify_info = (
            "When verification is enabled, each overwrite pass is checked to ensure "
            "the data was written correctly. This doubles the processing time but "
            "provides additional security assurance."
        )
        text_widget.insert(tk.END, verify_info)
        
        # Configure tags for headings
        text_widget.tag_configure("heading", font=("", 10, "bold"))
        
        # Make text widget read-only
        text_widget.configure(state=tk.DISABLED)
        
        # Close button in its own frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        close_btn = ttk.Button(button_frame, text="Close", command=dialog.destroy)
        close_btn.pack(side=tk.RIGHT)
        
        # Center dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

    def _copy_file_name(self):
        """Copy the name of the selected file to clipboard."""
        file_path = self._get_selected_file_path()
        if not file_path:
            return

        # Get just the file name without path
        file_name = os.path.basename(file_path)
        
        # Copy to clipboard
        self.root.clipboard_clear()
        self.root.clipboard_append(file_name)
        self.status_var.set(f"Copied: {file_name}")

    def _show_packages(self):
        """Display a message box with package information."""
        messagebox.showinfo("Packages", "Package information is not available.")

    def _exclude_selected_file(self):
        """Add the selected file's name pattern to the exclude pattern and refresh."""
        file_path = self._get_selected_file_path()
        if not file_path:
            return

        # Get just the file name without path
        file_name = os.path.basename(file_path)
        
        # Add wildcard before and after to match similar files
        file_pattern = f"*{file_name}*"
        
        # Get current exclude pattern
        current_pattern = self.exclude_pattern_var.get().strip()
        
        # Combine patterns if there's an existing pattern
        if current_pattern:
            new_pattern = f"{current_pattern};{file_pattern}"
        else:
            new_pattern = file_pattern
            
        # Update exclude pattern
        self.exclude_pattern_var.set(new_pattern)
        
        # Refresh the file list
        self._find_files()


def main():
    root = tk.Tk()
    app = FileShredderApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()