#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
File Shredder GUI
----------------
A user interface for the file shredding application.
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
from typing import List, Dict, Any

from file_shredder import FileShredder
from utils import resource_path

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
            icon_path = resource_path("icons/shredder_icon.svg")
            self.root.iconbitmap(icon_path)
        except Exception:
            # Icon not critical, continue without it
            pass
        
        # Status variables
        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0.0)
        self.is_shredding = False
        self.matching_files = []
        
        # UI Components
        self._create_ui()
        
        # Bind window close event to clean exit
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
    
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
        
        browse_btn = ttk.Button(folder_frame, text="Browse...", command=self._browse_folder)
        browse_btn.grid(row=0, column=2, sticky=tk.E, padx=5, pady=5)
        
        # Create pattern and options frame
        options_frame = ttk.LabelFrame(main_frame, text="Shredding Options", padding=10)
        options_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(options_frame, text="File Pattern:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.pattern_var = tk.StringVar(value="*.*")
        pattern_entry = ttk.Entry(options_frame, textvariable=self.pattern_var, width=20)
        pattern_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Label(options_frame, text="(e.g., *.txt, secret*, document?.pdf)").grid(
            row=0, column=2, sticky=tk.W, padx=5, pady=5)
            
        # Exclude pattern
        ttk.Label(options_frame, text="Exclude File Pattern:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.exclude_pattern_var = tk.StringVar(value="")
        exclude_pattern_entry = ttk.Entry(options_frame, textvariable=self.exclude_pattern_var, width=20)
        exclude_pattern_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Adjust the row for the recursive option
        ttk.Label(options_frame, text="(e.g., *.log, *.exe)").grid(
            row=1, column=2, sticky=tk.W, padx=5, pady=5)
        
        # Recursive option
        self.recursive_var = tk.BooleanVar(value=False)
        recursive_chk = ttk.Checkbutton(
            options_frame, 
            text="Include subdirectories (recursive)",
            variable=self.recursive_var
        )
        recursive_chk.grid(row=2, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5)
        
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
        passes_combo.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(options_frame, text="(higher = more secure, but slower)").grid(
            row=3, column=2, sticky=tk.W, padx=5, pady=5)
        
        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.find_btn = ttk.Button(
            button_frame, 
            text="Find Matching Files", 
            command=self._find_files
        )
        self.find_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.shred_btn = ttk.Button(
            button_frame, 
            text="Shred Files", 
            command=self._confirm_shred,
            state=tk.DISABLED
        )
        self.shred_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.cancel_btn = ttk.Button(
            button_frame, 
            text="Cancel", 
            command=self._cancel_operation,
            state=tk.DISABLED
        )
        self.cancel_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.clear_btn = ttk.Button(
            button_frame, 
            text="Clear", 
            command=self._clear_results
        )
        self.clear_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Results frame
        results_frame = ttk.LabelFrame(main_frame, text="Matching Files", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create a treeview for files
        self.files_tree = ttk.Treeview(
            results_frame, 
            columns=("path", "size", "status"),
            show="headings",
            selectmode="none"
        )
        
        # Define columns
        self.files_tree.heading("path", text="File Path")
        self.files_tree.heading("size", text="Size")
        self.files_tree.heading("status", text="Status")
        
        self.files_tree.column("path", width=350, stretch=True)
        self.files_tree.column("size", width=100, anchor=tk.E)
        self.files_tree.column("status", width=100)
        
        # Add scrollbars
        y_scroll = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.files_tree.yview)
        self.files_tree.configure(yscrollcommand=y_scroll.set)
        
        x_scroll = ttk.Scrollbar(results_frame, orient=tk.HORIZONTAL, command=self.files_tree.xview)
        self.files_tree.configure(xscrollcommand=x_scroll.set)
        
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
        """Open a directory browser dialog."""
        folder = filedialog.askdirectory(title="Select Directory")
        if folder:
            self.folder_path.set(folder)
    
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
            
            # Find matching files
            self.matching_files = self.shredder.find_files(directory, pattern, recursive, exclude_pattern)
            
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
        for file_path in self.matching_files:
            try:
                size = os.path.getsize(file_path)
                # Format the size
                if size < 1024:
                    size_str = f"{size} bytes"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                
                self.files_tree.insert("", tk.END, values=(file_path, size_str, "Pending"))
            except Exception:
                # If we can't get the size (e.g., permission error), show unknown
                self.files_tree.insert("", tk.END, values=(file_path, "Unknown", "Pending"))
        
        # Update status and enable shred button
        self.status_var.set(f"Found {len(self.matching_files)} matching files.")
        self.shred_btn.configure(state=tk.NORMAL)
    
    def _clear_file_list(self):
        """Clear the file list treeview."""
        for item in self.files_tree.get_children():
            self.files_tree.delete(item)
            
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
            # Copy the list to avoid modification issues
            files_to_shred = self.matching_files.copy()
            
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
                self.files_tree.item(item, values=(
                    file_path,
                    self.files_tree.item(item)['values'][1],
                    status
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
