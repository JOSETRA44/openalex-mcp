"""`openalex` command-line interface.

Split into focused modules: `parser` (the command surface and single source of
truth for `describe`), `render` (formats + envelope), `errors` (exit codes),
`rows` (tabular projection), `harvest` (cursor paging) and `main` (dispatch).
"""

from .main import main, run

__all__ = ["main", "run"]
