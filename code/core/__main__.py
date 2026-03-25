import sys
import os

# Ensure the code directory is in the path for the core package
core_pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if core_pkg_dir not in sys.path:
    sys.path.insert(0, core_pkg_dir)

from core.cli import main

if __name__ == "__main__":
    main()
