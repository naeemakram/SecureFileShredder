"""
Version information for Secure File Shredder.
"""

__version__ = "1.2.0"
__author__ = "Naeem Akram Malik"
__author_email__ = "naeem.akram.malik@gmail.com"
__license__ = "MIT"
__copyright__ = "Copyright (c) 2024 Naeem Akram Malik"

# Version info
VERSION = tuple(map(int, __version__.split(".")))
MAJOR = VERSION[0]
MINOR = VERSION[1]
PATCH = VERSION[2]

# Release info
RELEASE_LEVELS = ["alpha", "beta", "rc", "final"]
RELEASE_LEVEL = "rc"  # Change this for pre-releases
RELEASE_SERIAL = 0  # Increment this for each release at the same level

# Build info
BUILD_DATE = "2024-03-19"  # Update this on each release
BUILD_NUMBER = 1  # Increment this for each build

def get_version():
    """Get the full version string."""
    if RELEASE_LEVEL == "final":
        return __version__
    return f"{__version__}{RELEASE_LEVEL}{RELEASE_SERIAL}"

def get_build_info():
    """Get build information."""
    return {
        "version": get_version(),
        "build_date": BUILD_DATE,
        "build_number": BUILD_NUMBER,
        "release_level": RELEASE_LEVEL,
        "release_serial": RELEASE_SERIAL
    } 