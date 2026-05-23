"""Backward-compatible launcher — prefer: python -m gitmr"""

from gitmr.cli import main

if __name__ == "__main__":
    main()
