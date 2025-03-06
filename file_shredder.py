#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
File Shredding Module
---------------------
Implements secure file deletion by overwriting file data multiple times
before deletion to prevent recovery.
"""

import os
import random
import fnmatch
import time
import logging
from typing import List, Tuple, Callable, Optional, Generator

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FileShredder:
    """
    Securely delete files by overwriting their contents multiple times
    before deleting them.
    """
    
    def __init__(self, passes: int = 3):
        """
        Initialize the file shredder.
        
        Args:
            passes: Number of overwrite passes (default: 3)
        """
        self.passes = passes
    
    def find_files(self, directory: str, pattern: str, recursive: bool = False) -> List[str]:
        """
        Find files matching the pattern in the specified directory.
        
        Args:
            directory: The directory to search in
            pattern: File pattern to match (e.g., "*.txt", "secret*")
            recursive: Whether to search subdirectories
            
        Returns:
            A list of full paths to matching files
        """
        matching_files = []
        
        try:
            if recursive:
                for root, _, files in os.walk(directory):
                    for filename in fnmatch.filter(files, pattern):
                        matching_files.append(os.path.join(root, filename))
            else:
                for filename in fnmatch.filter(os.listdir(directory), pattern):
                    file_path = os.path.join(directory, filename)
                    if os.path.isfile(file_path):
                        matching_files.append(file_path)
                        
            logger.info(f"Found {len(matching_files)} files matching pattern '{pattern}'")
            return matching_files
        
        except Exception as e:
            logger.error(f"Error finding files: {str(e)}")
            raise
    
    def shred_file(self, file_path: str, callback: Optional[Callable[[float], None]] = None) -> bool:
        """
        Securely shred a single file by overwriting its contents multiple times.
        
        Args:
            file_path: Path to the file to shred
            callback: Optional callback function to report progress
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(file_path):
                logger.warning(f"File not found: {file_path}")
                return False
                
            # Get file size for progress reporting
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                # Handle empty files
                os.remove(file_path)
                logger.info(f"Removed empty file: {file_path}")
                return True
                
            # Perform secure overwrite passes
            for pass_num in range(1, self.passes + 1):
                with open(file_path, "rb+") as f:
                    # Determine the pattern for this pass
                    if pass_num == 1:
                        # First pass: all ones
                        pattern = b'\xFF'
                    elif pass_num == 2:
                        # Second pass: all zeros
                        pattern = b'\x00'
                    else:
                        # Remaining passes: random data
                        pattern = bytes([random.randint(0, 255)])
                    
                    # Track progress within this pass
                    bytes_written = 0
                    chunk_size = min(1024 * 1024, file_size)  # 1MB chunks or file size
                    
                    # Create a buffer with the pattern
                    buffer = pattern * chunk_size
                    
                    # Overwrite file contents
                    while bytes_written < file_size:
                        remaining = file_size - bytes_written
                        if remaining < chunk_size:
                            # Last chunk might be smaller
                            this_chunk = pattern * remaining
                            f.write(this_chunk)
                            bytes_written += remaining
                        else:
                            f.write(buffer)
                            bytes_written += chunk_size
                        
                        # Ensure data is written to disk
                        f.flush()
                        os.fsync(f.fileno())
                        
                        # Report progress if callback provided
                        if callback:
                            # Calculate overall progress (each pass contributes 1/passes of total)
                            overall_progress = ((pass_num - 1) + (bytes_written / file_size)) / self.passes
                            callback(overall_progress)
                
                logger.debug(f"Completed pass {pass_num}/{self.passes} for {file_path}")
            
            # After overwriting, delete the file
            os.remove(file_path)
            logger.info(f"Successfully shredded file: {file_path}")
            
            # Final progress update
            if callback:
                callback(1.0)
                
            return True
            
        except Exception as e:
            logger.error(f"Error shredding file {file_path}: {str(e)}")
            return False
    
    def shred_files(self, 
                   files: List[str], 
                   progress_callback: Optional[Callable[[float, str], None]] = None,
                   file_complete_callback: Optional[Callable[[str, bool], None]] = None) -> Tuple[int, int]:
        """
        Shred multiple files.
        
        Args:
            files: List of file paths to shred
            progress_callback: Optional callback for overall progress (progress, current_file)
            file_complete_callback: Optional callback called when each file is processed (path, success)
            
        Returns:
            Tuple of (successful_count, failed_count)
        """
        total_files = len(files)
        if total_files == 0:
            return 0, 0
            
        successful = 0
        failed = 0
        
        for i, file_path in enumerate(files):
            try:
                # Create a callback for this specific file
                def file_progress_callback(file_progress: float):
                    if progress_callback:
                        # Overall progress combines file count and current file progress
                        overall_progress = (i + file_progress) / total_files
                        progress_callback(overall_progress, file_path)
                
                # Shred the file
                result = self.shred_file(file_path, file_progress_callback)
                
                # Update counters and call callback
                if result:
                    successful += 1
                else:
                    failed += 1
                    
                if file_complete_callback:
                    file_complete_callback(file_path, result)
                    
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {str(e)}")
                failed += 1
                if file_complete_callback:
                    file_complete_callback(file_path, False)
        
        logger.info(f"Shredding complete. Success: {successful}, Failed: {failed}")
        return successful, failed
