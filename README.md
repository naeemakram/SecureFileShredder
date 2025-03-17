# Secure File Shredder

A secure file deletion application that implements pattern-based file shredding.

## Version Information

Current Version: 1.1.0
- Release Level: Final
- Build Date: 2024-03-19
- Build Number: 1

### Version History
- 1.1.0 (2024-03-19)
  - Added pattern-based file selection
  - Added recursive directory shredding
  - Added PDF text extraction and verification
  - Improved progress tracking and logging

- 1.0.0 (2024-03-18)
  - Initial release
  - Basic file shredding functionality
  - Multiple shredding methods including DoD 5220.22-M

## Requirements

### System Requirements
- Windows 10 or later
- Python 3.8 or later (if running from source)
- At least 4GB RAM
- 500MB free disk space

### Software Dependencies
- Tesseract OCR (for PDF text extraction)
  - Download and install from: https://github.com/UB-Mannheim/tesseract/wiki
  - Add Tesseract to your system PATH
  - Default installation path: `C:\Program Files\Tesseract-OCR`

### Python Dependencies (if running from source)
- PyPDF2>=3.0.0
- pytesseract>=0.3.10
- Pillow>=10.2.0
- pywin32>=306
- tomli>=2.2.1

## Installation

### Option 1: Using the MSI Installer (Recommended)
1. Download the latest MSI installer from the releases page
2. Double-click the MSI file to start the installation
3. Follow the installation wizard
4. A desktop shortcut will be created automatically

### Option 2: Running from Source
1. Clone the repository
2. Install Python 3.8 or later
3. Install Tesseract OCR
4. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Run the application:
   ```bash
   python gui.py
   ```

## Usage

1. Launch Secure File Shredder from the desktop shortcut or start menu
2. Select files or folders to shred
3. Choose your preferred shredding method
4. Click "Shred Files" to begin the secure deletion process

## Features

- Multiple shredding methods including DoD 5220.22-M
- Pattern-based file selection
- Recursive directory shredding
- PDF text extraction and verification
- Progress tracking
- Detailed logging

## License

This project is licensed under the MIT License - see the LICENSE file for details. 

