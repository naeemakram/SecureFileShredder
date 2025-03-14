#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
File Shredding Module
---------------------
Implements secure file deletion by overwriting file data multiple times
before deletion to prevent recovery.
"""

import os
import sys
import random
import fnmatch
import re
import logging
import importlib.util
from enum import Enum
from typing import List, Tuple, Callable, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add file-based logging
file_handler = logging.FileHandler("shredder.log", mode="a")
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Check if OCR support is available
ocr_support_available = importlib.util.find_spec("ocr_processor") is not None
if ocr_support_available:
    from ocr_processor import OCRProcessor
    logger.info("OCR module found. Image content search will be enabled.")
else:
    logger.warning("OCR module not found. Image content search will be disabled.")

class ShreddingMethod(Enum):
    """Supported file shredding methods."""
    BASIC = "basic"  # Basic multi-pass random overwrite
    DOD_5220_22_M = "dod"  # DoD 5220.22-M 7-pass standard

    @staticmethod
    def get_description(method: 'ShreddingMethod') -> str:
        """Get a detailed description of the shredding method."""
        descriptions = {
            ShreddingMethod.BASIC: (
                "Basic multi-pass random overwrite method:\n"
                "- First pass: Write all ones\n"
                "- Second pass: Write all zeros\n"
                "- Remaining passes: Write random data\n"
                "You can configure the number of passes (default: 3)"
            ),
            ShreddingMethod.DOD_5220_22_M: (
                "DoD 5220.22-M 7-pass standard:\n"
                "1. Pass 1: Write all ones\n"
                "2. Pass 2: Write all zeros\n"
                "3. Pass 3: Write random pattern\n"
                "4. Pass 4: Write all zeros\n"
                "5. Pass 5: Write all ones\n"
                "6. Pass 6: Write random pattern\n"
                "7. Pass 7: Write all zeros\n"
                "This is a military-grade data sanitization standard."
            )
        }
        return descriptions.get(method, "Unknown method")

class FileShredder:
    """
    Securely delete files by overwriting their contents multiple times
    before deletion.
    """

    def __init__(self, method: ShreddingMethod = ShreddingMethod.BASIC, passes: int = 3, verify: bool = True):
        """
        Initialize the file shredder.

        Args:
            method: Shredding method to use (default: BASIC)
            passes: Number of overwrite passes for BASIC method (default: 3)
            verify: Whether to verify each pass (default: True)
        """
        self.method = method
        self.passes = passes
        self.verify = verify
        
        # DoD 5220.22-M pattern sequence
        self._dod_patterns = [
            (b'\xFF', "ones"),           # Pass 1: Write all ones
            (b'\x00', "zeros"),          # Pass 2: Write all zeros
            (None, "random"),            # Pass 3: Write random pattern
            (b'\x00', "zeros"),          # Pass 4: Write all zeros
            (b'\xFF', "ones"),           # Pass 5: Write all ones
            (None, "random"),            # Pass 6: Write random pattern
            (b'\x00', "zeros")           # Pass 7: Write all zeros
        ]

    def find_files(self, directory: str, pattern: str, recursive: bool = False, exclude_pattern: str = "", 
              return_excluded_count: bool = False, owner_pattern: str = None, created_after: float = None, 
              created_before: float = None, modified_after: float = None, modified_before: float = None,
              content_pattern: str = None, content_min_occurrences: int = 1, exclude_content_pattern: str = None, 
              exclude_content_min_occurrences: int = 1, ocr_enabled: bool = True) -> List[str] or Tuple[List[str], int]:
        """
        Find files matching the pattern in the specified directory.

        Args:
            directory: The directory to search in
            pattern: File pattern to match (e.g., "*.txt", "secret*")
            recursive: Whether to search subdirectories
            exclude_pattern: Pattern of files to exclude
            return_excluded_count: Whether to return the count of excluded files
            owner_pattern: Regex pattern to match file owner/user
            created_after: Unix timestamp (files created after this time)
            created_before: Unix timestamp (files created before this time)
            modified_after: Unix timestamp (files modified after this time)
            modified_before: Unix timestamp (files modified before this time)
            content_pattern: Text pattern to search for within file contents
            content_min_occurrences: Minimum number of times the pattern must appear
            exclude_content_pattern: Text pattern to exclude files based on content
            exclude_content_min_occurrences: Minimum occurrences of exclude_content_pattern to trigger exclusion

        Returns:
            A list of full paths to matching files, or a tuple of (list_of_files, excluded_count) if return_excluded_count is True
        """
        matching_files = []
        excluded_count = 0

        # Compile owner regex pattern if provided
        owner_regex = None
        if owner_pattern:
            try:
                owner_regex = re.compile(owner_pattern)
            except re.error:
                logger.error(f"Invalid owner pattern regex: {owner_pattern}")
                raise ValueError(f"Invalid owner pattern regex: {owner_pattern}")

        try:
            # Split multiple patterns if provided (comma or semicolon-separated)
            include_patterns = [p.strip() for p in re.split(r'[,;]', pattern) if p.strip()]
            exclude_patterns = [p.strip() for p in re.split(r'[,;]', exclude_pattern) if p.strip()] if exclude_pattern else []
            
            logger.info(f"Include patterns: {include_patterns}")
            logger.info(f"Exclude patterns: {exclude_patterns}")

            # Handle recursive and non-recursive search differently
            if recursive:
                # For recursive search, use os.walk to traverse all subdirectories
                for root, _, files in os.walk(directory):
                    for filename in files:
                        file_path = os.path.join(root, filename)

                        # Check if the file matches any include pattern
                        is_match = any(fnmatch.fnmatch(filename, p) for p in include_patterns)

                        # Check if the file matches any exclude pattern
                        is_excluded = any(fnmatch.fnmatch(filename, p) for p in exclude_patterns) if exclude_patterns else False

                        # If basic pattern match, check metadata criteria
                        if is_match and not is_excluded:
                            # Get file stats for metadata filtering
                            try:
                                file_stat = os.stat(file_path)

                                # Check creation time (ctime)
                                if created_after and file_stat.st_ctime < created_after:
                                    is_excluded = True
                                if created_before and file_stat.st_ctime > created_before:
                                    is_excluded = True

                                # Check modification time (mtime)
                                if modified_after and file_stat.st_mtime < modified_after:
                                    is_excluded = True
                                if modified_before and file_stat.st_mtime > modified_before:
                                    is_excluded = True

                                # Check owner (platform-specific)
                                if owner_regex:
                                    try:
                                        import pwd
                                        owner = pwd.getpwuid(file_stat.st_uid).pw_name
                                        if not owner_regex.search(owner):
                                            is_excluded = True
                                    except (ImportError, KeyError):
                                        # On Windows or if owner can't be determined
                                        pass

                                # Initialize content match info
                                content_match_info = {}

                                # Check file content if pattern is provided
                                if content_pattern and not is_excluded:
                                    # Determine which files to process based on OCR setting
                                    is_image = filename.lower().endswith(('.png', '.bmp', '.jpg', '.jpeg', '.tiff', '.gif'))
                                    is_text = filename.lower().endswith(('.txt', '.csv'))
                                    is_pdf = filename.lower().endswith('.pdf') and 'PyPDF2' in sys.modules
                                    
                                    # Process only if text file or if it's an image and OCR is enabled
                                    if is_text or is_pdf or (is_image and ocr_enabled and ocr_support_available):
                                        match_result, occurrences = self._check_file_content(file_path, content_pattern, content_min_occurrences)
                                        is_excluded = not match_result
                                        if match_result:
                                            content_match_info['include'] = {
                                                'pattern': content_pattern,
                                                'occurrences': occurrences
                                            }

                                # Check exclude content pattern if provided
                                if exclude_content_pattern and not is_excluded:
                                    # Determine which files to process based on OCR setting
                                    is_image = filename.lower().endswith(('.png', '.bmp', '.jpg', '.jpeg', '.tiff', '.gif'))
                                    is_text = filename.lower().endswith(('.txt', '.csv'))
                                    is_pdf = filename.lower().endswith('.pdf') and 'PyPDF2' in sys.modules
                                    
                                    # Process only if text file or if it's an image and OCR is enabled
                                    if is_text or is_pdf or (is_image and ocr_enabled and ocr_support_available):
                                        match_result, occurrences = self._check_file_content(file_path, exclude_content_pattern, exclude_content_min_occurrences)
                                        if match_result:
                                            is_excluded = True
                                            content_match_info['exclude'] = {
                                                'pattern': exclude_content_pattern,
                                                'occurrences': occurrences
                                            }
                            except (OSError, IOError):
                                # If we can't get file stats, exclude it
                                is_excluded = True

                        if is_match:
                            if not is_excluded:
                                # Store file path and content match info
                                matching_files.append((file_path, content_match_info))
                            else:
                                excluded_count += 1
            else:
                # For non-recursive search, only check files in the top directory
                for filename in os.listdir(directory):
                    file_path = os.path.join(directory, filename)
                    if os.path.isfile(file_path):
                        # Check if the file matches any include pattern
                        is_match = any(fnmatch.fnmatch(filename, p) for p in include_patterns)

                        # Check if the file matches any exclude pattern
                        is_excluded = any(fnmatch.fnmatch(filename, p) for p in exclude_patterns) if exclude_patterns else False

                        # If basic pattern match, check metadata criteria
                        if is_match and not is_excluded:
                            # Get file stats for metadata filtering
                            try:
                                file_stat = os.stat(file_path)

                                # Check creation time (ctime)
                                if created_after and file_stat.st_ctime < created_after:
                                    is_excluded = True
                                if created_before and file_stat.st_ctime > created_before:
                                    is_excluded = True

                                # Check modification time (mtime)
                                if modified_after and file_stat.st_mtime < modified_after:
                                    is_excluded = True
                                if modified_before and file_stat.st_mtime > modified_before:
                                    is_excluded = True

                                # Check owner (platform-specific)
                                if owner_regex:
                                    try:
                                        import pwd
                                        owner = pwd.getpwuid(file_stat.st_uid).pw_name
                                        if not owner_regex.search(owner):
                                            is_excluded = True
                                    except (ImportError, KeyError):
                                        # On Windows or if owner can't be determined
                                        pass

                                # Initialize content match info
                                content_match_info = {}

                                # Check file content if pattern is provided
                                if content_pattern and not is_excluded:
                                    # Determine which files to process based on OCR setting
                                    is_image = filename.lower().endswith(('.png', '.bmp', '.jpg', '.jpeg', '.tiff', '.gif'))
                                    is_text = filename.lower().endswith(('.txt', '.csv'))
                                    is_pdf = filename.lower().endswith('.pdf') and 'PyPDF2' in sys.modules
                                    
                                    # Process only if text file or if it's an image and OCR is enabled
                                    if is_text or is_pdf or (is_image and ocr_enabled and ocr_support_available):
                                        match_result, occurrences = self._check_file_content(file_path, content_pattern, content_min_occurrences)
                                        is_excluded = not match_result
                                        if match_result:
                                            content_match_info['include'] = {
                                                'pattern': content_pattern,
                                                'occurrences': occurrences
                                            }

                                # Check exclude content pattern if provided
                                if exclude_content_pattern and not is_excluded:
                                    # Determine which files to process based on OCR setting
                                    is_image = filename.lower().endswith(('.png', '.bmp', '.jpg', '.jpeg', '.tiff', '.gif'))
                                    is_text = filename.lower().endswith(('.txt', '.csv'))
                                    is_pdf = filename.lower().endswith('.pdf') and 'PyPDF2' in sys.modules
                                    
                                    # Process only if text file or if it's an image and OCR is enabled
                                    if is_text or is_pdf or (is_image and ocr_enabled and ocr_support_available):
                                        match_result, occurrences = self._check_file_content(file_path, exclude_content_pattern, exclude_content_min_occurrences)
                                        if match_result:
                                            is_excluded = True
                                            content_match_info['exclude'] = {
                                                'pattern': exclude_content_pattern,
                                                'occurrences': occurrences
                                            }
                            except (OSError, IOError):
                                # If we can't get file stats, exclude it
                                is_excluded = True

                        if is_match:
                            if not is_excluded:
                                # Store file path and content match info
                                matching_files.append((file_path, content_match_info))
                            else:
                                excluded_count += 1

            log_message = f"Found {len(matching_files)} files matching pattern '{pattern}'"
            if exclude_pattern:
                log_message += f" (excluding {excluded_count} files matching '{exclude_pattern}')"
            logger.info(log_message)

            if return_excluded_count:
                return matching_files, excluded_count
            return matching_files

        except Exception as e:
            logger.error(f"Error finding files: {str(e)}")
            raise

    def _check_file_content(self, file_path: str, content_pattern: str, min_occurrences: int = 1) -> Tuple[bool, int]:
        """
        Check if a file contains the specified content pattern at least min_occurrences times.

        Args:
            file_path: Path to the file to check
            content_pattern: Text pattern to search for
            min_occurrences: Minimum number of occurrences required

        Returns:
            A tuple consisting of a boolean indicating if the minimum occurrences of the pattern were found,
            and the count of occurrences of the pattern within the file.
        """
        try:
            logger.info(f"File in process {file_path}")
            # Get the file extension
            file_ext = os.path.splitext(file_path.lower())[1]
            
            # Handle PDF files
            if file_ext == '.pdf':
                try:
                    import PyPDF2
                    with open(file_path, 'rb') as pdf_file:
                        reader = PyPDF2.PdfReader(pdf_file)
                        text = ""
                        for page in reader.pages:
                            text += page.extract_text()
                        occurrences = text.count(content_pattern)
                        logger.debug(f"Found {occurrences} occurrences of '{content_pattern}' in PDF {file_path}")
                        return occurrences >= min_occurrences, occurrences
                except ImportError:
                    logger.warning("PyPDF2 not installed, skipping PDF content search")
                    return False, 0
                except Exception as e:
                    logger.error(f"Error processing PDF {file_path}: {str(e)}")
                    return False, 0
            
            # Handle image files with OCR
            elif ocr_support_available and file_ext in OCRProcessor.get_supported_formats():
                found, occurrences = OCRProcessor.search_text_in_image(file_path, content_pattern)
                logger.debug(f"OCR found {occurrences} occurrences of '{content_pattern}' in image {file_path}")
                return occurrences >= min_occurrences, occurrences
            
            # Handle text files (.txt, .csv, etc.)
            elif file_ext in ['.txt', '.csv', '.json', '.xml', '.html', '.js', '.py', '.md']:
                with open(file_path, 'r', errors='ignore') as f:
                    text = f.read()
                    occurrences = text.count(content_pattern)
                    logger.debug(f"Found {occurrences} occurrences of '{content_pattern}' in {file_path}")
                    return occurrences >= min_occurrences, occurrences
            
            # Skip other file types
            else:
                logger.debug(f"Skipping content search for unsupported file type: {file_path}")
                return False, 0

        except Exception as e:
            logger.error(f"Error checking file content for {file_path}: {str(e)}")
            return False, 0

    def _verify_pattern(self, file_handle, pattern: bytes, file_size: int, chunk_size: int) -> bool:
        """
        Verify that the file contains the expected pattern.

        Args:
            file_handle: Open file handle
            pattern: Pattern to verify
            file_size: Size of the file
            chunk_size: Size of chunks to read

        Returns:
            True if verification passes, False otherwise
        """
        try:
            file_handle.seek(0)  # Go back to start of file
            bytes_verified = 0

            while bytes_verified < file_size:
                remaining = file_size - bytes_verified
                verify_size = min(chunk_size, remaining)
                
                # Read chunk
                chunk = file_handle.read(verify_size)
                
                # For random patterns, we can't verify the exact content
                if pattern is None:
                    # Just verify the chunk is not all zeros or all ones
                    if chunk == b'\x00' * len(chunk) or chunk == b'\xFF' * len(chunk):
                        logger.error("Verification failed: Random pattern contains all zeros or ones")
                        return False
                else:
                    # For fixed patterns, verify each byte
                    expected = pattern * (verify_size // len(pattern))
                    if remaining % len(pattern) != 0:
                        expected += pattern[:remaining % len(pattern)]
                    
                    if chunk != expected:
                        logger.error("Verification failed: Pattern mismatch")
                        return False
                
                bytes_verified += verify_size

            return True
        except Exception as e:
            logger.error(f"Verification error: {str(e)}")
            return False

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

            # Determine total passes based on method
            total_passes = len(self._dod_patterns) if self.method == ShreddingMethod.DOD_5220_22_M else self.passes
            
            # Double the passes if verification is enabled
            progress_passes = total_passes * 2 if self.verify else total_passes

            # Perform secure overwrite passes
            for pass_num in range(1, total_passes + 1):
                with open(file_path, "rb+") as f:
                    # Determine the pattern for this pass
                    if self.method == ShreddingMethod.DOD_5220_22_M:
                        pattern, pattern_type = self._dod_patterns[pass_num - 1]
                        if pattern is None:  # Random pattern
                            pattern = bytes([random.randint(0, 255)])
                        logger.debug(f"DoD pass {pass_num}: Writing {pattern_type} pattern")
                    else:  # BASIC method
                        if pass_num == 1:
                            pattern = b'\xFF'  # First pass: all ones
                        elif pass_num == 2:
                            pattern = b'\x00'  # Second pass: all zeros
                        else:
                            pattern = bytes([random.randint(0, 255)])  # Random data

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
                            # Calculate overall progress including verification passes
                            write_progress = bytes_written / file_size
                            pass_progress = (pass_num - 1 + write_progress) / progress_passes
                            callback(pass_progress)

                    # Verify the pass if enabled
                    if self.verify:
                        logger.debug(f"Verifying pass {pass_num}")
                        if not self._verify_pattern(f, pattern, file_size, chunk_size):
                            logger.error(f"Verification failed for pass {pass_num}")
                            return False
                        
                        # Update progress after verification
                        if callback:
                            verify_progress = (pass_num - 0.5) / total_passes
                            callback(verify_progress)

                logger.debug(f"Completed pass {pass_num}/{total_passes} for {file_path}")

            # After overwriting, delete the file
            os.remove(file_path)
            logger.info(f"Successfully shredded file: {file_path} using {self.method.value} method")

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