"""PyInstaller entry point for Screen Answer v1.

Kept at the repository root so the frozen executable can import the
`screenanswer` package normally (the package uses relative imports).
"""

import sys

from screenanswer.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
