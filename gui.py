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
import datetime
from typing import List, Dict, Any

from file_shredder import FileShredder
from utils import resource_path

# Check if tkcalendar is available, if not show error message
try:
    from tkcalendar import DateEntry
    calendar_available = True
except ImportError:
    calendar_available = False
    print("tkcalendar is not available. Date picker will be disabled.")

# Check if PyPDF2 is available
pdf_support_available = importlib.util.find_spec("PyPDF2") is not None
if not pdf_support_available:
    print("PyPDF2 is not available. PDF content search will be disabled.")
    # You might want to log this or display a notification that PDF search is disabled

class FileShredderApp:
    """Main application window for File Shredder."""
    
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
        
        # Initialize file shredder
        self.shredder = FileShredder(passes=3)
        
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
        
        # UI Components
        self._create_ui()
        
        # Bind window close event to clean exit
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Create menu bar
        self._create_menu()
    
    def _create_menu(self):
        """Create the application menu bar."""
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)
        
        # About menu
        about_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Help", menu=about_menu)
        about_menu.add_command(label="About", command=self._show_about)
    
    def _show_about(self):
        """Display the About dialog with version and author information."""
        about_text = (
            "Secure File Shredder v1.1\n\n"
            "Created by Naeem Akram Malik, Sr. Test Engineer\n\n"
            "LinkedIn: https://www.linkedin.com/in/naeemakrammalik/\n"
            "Gmail: naeem.akram.malik@gmail.com"
        )
        messagebox.showinfo("About Secure File Shredder", about_text)
    
    def _create_ui(self):
        """Create and layout the UI components."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
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
        
        ttk.Label(options_frame, text="File Pattern:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.pattern_var = tk.StringVar(value="*.*")
        pattern_entry = ttk.Entry(options_frame, textvariable=self.pattern_var, width=20)
        pattern_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        pattern_entry.bind("<Return>", lambda e: self._find_files())
        
        ttk.Label(options_frame, text="(e.g., *.txt, secret*, document?.pdf)").grid(
            row=0, column=2, sticky=tk.W, padx=5, pady=5)
            
        # Exclude pattern
        ttk.Label(options_frame, text="Exclude File Pattern:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.exclude_pattern_var = tk.StringVar(value="")
        exclude_pattern_entry = ttk.Entry(options_frame, textvariable=self.exclude_pattern_var, width=20)
        exclude_pattern_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        exclude_pattern_entry.bind("<Return>", lambda e: self._find_files())
        
        # Adjust the row for the recursive option
        ttk.Label(options_frame, text="(e.g., *.log, *.exe)").grid(
            row=1, column=2, sticky=tk.W, padx=5, pady=5)
        
        # Add metadata filtering section
        metadata_frame = ttk.LabelFrame(options_frame, text="Metadata Filters", padding=5)
        metadata_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=5)
        
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
        date_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Created after/before
        ttk.Label(date_frame, text="Created After:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.created_after_var = tk.StringVar(value="")
        
        if calendar_available:
            created_after_entry = DateEntry(
                date_frame, 
                selectmode='day', 
                textvariable=self.created_after_var,
                date_pattern='yyyy-mm-dd',
                width=14,
                state="readonly",
                command=lambda e: self._on_date_selected(self.created_after_var)
            )
            # Clear button for date fields
            created_after_clear = ttk.Button(
                date_frame, 
                text="×", 
                width=2, 
                command=lambda: self._clear_date(created_after_entry, self.created_after_var)
            )
            created_after_clear.grid(row=0, column=1, sticky=tk.E, padx=(0, 5), pady=5)
        else:
            created_after_entry = ttk.Entry(date_frame, textvariable=self.created_after_var, width=16)
            created_after_entry.bind("<Return>", lambda e: self._find_files())
        
        created_after_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(date_frame, text="Created Before:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.created_before_var = tk.StringVar(value="")
        
        if calendar_available:
            created_before_entry = DateEntry(
                date_frame, 
                selectmode='day', 
                textvariable=self.created_before_var,
                date_pattern='yyyy-mm-dd',
                width=14,
                state="readonly",
                command=lambda e: self._on_date_selected(self.created_before_var)
            )
            # Clear button for date fields
            created_before_clear = ttk.Button(
                date_frame, 
                text="×", 
                width=2, 
                command=lambda: self._clear_date(created_before_entry, self.created_before_var)
            )
            created_before_clear.grid(row=0, column=3, sticky=tk.E, padx=(0, 5), pady=5)
        else:
            created_before_entry = ttk.Entry(date_frame, textvariable=self.created_before_var, width=16)
            created_before_entry.bind("<Return>", lambda e: self._find_files())
            
        created_before_entry.grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)
        
        # Modified after/before
        ttk.Label(date_frame, text="Modified After:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.modified_after_var = tk.StringVar(value="")
        
        if calendar_available:
            modified_after_entry = DateEntry(
                date_frame, 
                selectmode='day', 
                textvariable=self.modified_after_var,
                date_pattern='yyyy-mm-dd',
                width=14,
                state="readonly",
                command=lambda e: self._on_date_selected(self.modified_after_var)
            )
            # Clear button for date fields
            modified_after_clear = ttk.Button(
                date_frame, 
                text="×", 
                width=2, 
                command=lambda: self._clear_date(modified_after_entry, self.modified_after_var)
            )
            modified_after_clear.grid(row=1, column=1, sticky=tk.E, padx=(0, 5), pady=5)
        else:
            modified_after_entry = ttk.Entry(date_frame, textvariable=self.modified_after_var, width=16)
            modified_after_entry.bind("<Return>", lambda e: self._find_files())
            
        modified_after_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(date_frame, text="Modified Before:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        self.modified_before_var = tk.StringVar(value="")
        
        if calendar_available:
            modified_before_entry = DateEntry(
                date_frame, 
                selectmode='day', 
                textvariable=self.modified_before_var,
                date_pattern='yyyy-mm-dd',
                width=14,
                state="readonly",
                command=lambda e: self._on_date_selected(self.modified_before_var)
            )
            # Clear button for date fields
            modified_before_clear = ttk.Button(
                date_frame, 
                text="×", 
                width=2, 
                command=lambda: self._clear_date(modified_before_entry, self.modified_before_var)
            )
            modified_before_clear.grid(row=1, column=3, sticky=tk.E, padx=(0, 5), pady=5)
        else:
            modified_before_entry = ttk.Entry(date_frame, textvariable=self.modified_before_var, width=16)
            modified_before_entry.bind("<Return>", lambda e: self._find_files())
            
        modified_before_entry.grid(row=1, column=3, sticky=tk.W, padx=5, pady=5)
        
        if calendar_available:
            ttk.Label(date_frame, text="(Click calendar icon to select date)").grid(row=2, column=0, columnspan=4, sticky=tk.W, padx=5, pady=2)
        else:
            ttk.Label(date_frame, text="(Format: YYYY-MM-DD)").grid(row=2, column=0, columnspan=4, sticky=tk.W, padx=5, pady=2)
        
        # Number of passes
        ttk.Label(options_frame, text="Shredding Passes:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.passes_var = tk.IntVar(value=3)
        passes_combo = ttk.Combobox(
            options_frame, 
            textvariable=self.passes_var,
            values=[1, 3, 7],
            width=5,
            state="readonly"
        )
        passes_combo.grid(row=3, column=1, sticky=tk.W, padx=1, pady=5)
        ttk.Label(options_frame, text="(higher = more secure, but slower)").grid(
            row=3, column=2, sticky=tk.W, padx=1, pady=5)
        
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
        results_frame = ttk.LabelFrame(main_frame, text="Matching Files (0)", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create a treeview for files
        self.files_tree = ttk.Treeview(
            results_frame, 
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
        y_scroll = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.files_tree.yview)
        self.files_tree.configure(yscrollcommand=y_scroll.set)
        
        x_scroll = ttk.Scrollbar(results_frame, orient=tk.HORIZONTAL, command=self.files_tree.xview)
        self.files_tree.configure(xscrollcommand=x_scroll.set)
        
        # Set up right-click context menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="📂 Open File Location", command=self._open_file_location)
        self.context_menu.add_command(label="📄 Open File", command=self._open_file)
        self.context_menu.add_command(label="ℹ️ File Properties", command=self._show_file_properties)
        
        # Bind right-click event to show context menu
        self.files_tree.bind("<Button-3>", self._show_context_menu)
        
        # Grid layout for treeview and scrollbars
        self.files_tree.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        y_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        x_scroll.grid(row=1, column=0, sticky=(tk.E, tk.W))
        
        results_frame.grid_columnconfigure(0, weight=1)
        results_frame.grid_rowconfigure(0, weight=1)
        
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
                exclude_content_min_occurrences=exclude_content_min_occurrences
            )
            
            # Update UI from main thread
            self.root.after(0, self._update_file_list)
            
        except Exception as e:
            # Show error on main thread
            self.root.after(0, lambda: self._show_error(f"Error finding files: {str(e)}"))
    
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
        
        # Update status, results frame title, and enable shred button
        file_count = len(self.matching_files)
        self.status_var.set(f"Found {file_count} matching files. Excluded: {self.excluded_count}")
        self.results_frame_text.set(f"Matching Files ({file_count})")
        results_frame.configure(text=f"Matching Files ({file_count})")
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
        # Update the actual frame text
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.LabelFrame):
                        child.configure(text="Matching Files (0)")
                        break
            
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
        
        Args:
            file_path: Path of the processed file
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
        
        # Clear the file list
        self._clear_file_list()
    
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
                
                # Display file properties in a dialog
                messagebox.showinfo(
                    "File Properties",
                    f"File: {os.path.basename(file_path)}\n"
                    f"Location: {os.path.dirname(file_path)}\n"
                    f"Size: {size_str} ({stat_info.st_size:,} bytes)\n"
                    f"Owner: {owner}\n"
                    f"Created: {created_time}\n"
                    f"Modified: {modified_time}\n"
                    f"Accessed: {accessed_time}\n"
                    f"Permissions: {oct(stat_info.st_mode)[-3:]}\n"
                    f"{matches_info}"
                )
            else:
                messagebox.showwarning("File Not Found", "The selected file no longer exists.")
                
        except Exception as e:
            messagebox.showerror("Error", f"Could not get file properties: {str(e)}")
    
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
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Wait until the dialog is closed
        dialog.wait_window()
    
    def _on_date_selected(self, var):
        """Callback when a date is selected from the date picker."""
        # Trigger a file search when a date is selected
        self._find_files()
        
    def _clear_date(self, date_entry, var):
        """Clear a date field."""
        var.set("")
        if calendar_available:
            # Reset to current date (but don't set the var)
            date_entry.set_date(datetime.datetime.now().date())
        self._find_files()
    
    def _on_close(self):
        """Handle window close event."""
        if self.is_shredding:
            response = messagebox.askokcancel(
                "Confirm Exit",
                "An operation is in progress. Are you sure you want to exit?"
            )
            if not response:
                return
        
        self.root.destroy()
