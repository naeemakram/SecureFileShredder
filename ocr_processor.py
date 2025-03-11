
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
OCR Processing Module
--------------------
Handles optical character recognition for image files.
"""

import os
import logging
from typing import Tuple, Optional
import importlib.util

# Check if required libraries are available
pillow_available = importlib.util.find_spec("PIL") is not None
tesseract_available = importlib.util.find_spec("pytesseract") is not None

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize PIL and pytesseract if available
if pillow_available and tesseract_available:
    from PIL import Image
    import pytesseract
    logger.info("OCR support is enabled (PIL and pytesseract available)")
else:
    logger.warning("OCR support is disabled (PIL or pytesseract not available)")

class OCRProcessor:
    """Process images with OCR to extract text content."""
    
    @staticmethod
    def is_ocr_available() -> bool:
        """Check if OCR functionality is available."""
        return pillow_available and tesseract_available
    
    @staticmethod
    def get_supported_formats() -> list:
        """Get a list of supported image formats for OCR."""
        if not OCRProcessor.is_ocr_available():
            return []
        return ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']
    
    @staticmethod
    def extract_text_from_image(image_path: str) -> Tuple[bool, str, Optional[int]]:
        """
        Extract text from an image file using OCR.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Tuple containing:
                - Success status (bool)
                - Extracted text or error message (str)
                - Character count or None if failed (Optional[int])
        """
        if not OCRProcessor.is_ocr_available():
            return False, "OCR support is not available (PIL or pytesseract missing)", None
        
        # Check if the file exists and is accessible
        if not os.path.exists(image_path):
            return False, f"Image file not found: {image_path}", None
        
        try:
            # Open the image using PIL
            image = Image.open(image_path)
            
            # Perform OCR using pytesseract
            extracted_text = pytesseract.image_to_string(image)
            
            # Clean up the text (remove excessive whitespace)
            extracted_text = ' '.join(extracted_text.split())
            
            # Check if any text was extracted
            if not extracted_text.strip():
                return True, "", 0
            
            # Return success, text, and character count
            return True, extracted_text, len(extracted_text)
            
        except Exception as e:
            logger.error(f"Error extracting text from image {image_path}: {str(e)}")
            return False, f"Error extracting text: {str(e)}", None
    
    @staticmethod
    def search_text_in_image(image_path: str, search_pattern: str) -> Tuple[bool, int]:
        """
        Search for a pattern in the text extracted from an image.
        
        Args:
            image_path: Path to the image file
            search_pattern: Text pattern to search for
            
        Returns:
            Tuple containing:
                - Whether the pattern was found (bool)
                - Number of occurrences found (int)
        """
        success, text, _ = OCRProcessor.extract_text_from_image(image_path)
        
        if not success or not text:
            return False, 0
        
        # Count occurrences of the pattern in the extracted text
        occurrences = text.lower().count(search_pattern.lower())
        logger.info(f"{text} - {search_pattern} - {occurrences}")        
        return occurrences > 0, occurrences
