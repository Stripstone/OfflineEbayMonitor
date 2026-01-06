# html_loader.py
"""
HTML LOADER — OFFLINE INPUT QUEUE

Responsibilities:
- Treat the HTML folder as an *ephemeral input queue*
- Discover matching HTML files deterministically
- Read file contents safely (encoding-tolerant)
- Do NOT parse or interpret HTML here

Design guarantees:
- No business logic
- No market-specific assumptions
- Safe to reuse for other markets
"""

import os
from typing import List, Tuple


def discover_html_files(folder_path: str, filename_filter=None) -> List[str]:
    """
    Discover HTML files in the folder.

    Args:
        folder_path: directory to scan
        filename_filter: optional callable(filename:str)->bool

    Returns:
        Sorted list of absolute file paths.
    """
    if not os.path.isdir(folder_path):
        return []

    files = []
    for name in os.listdir(folder_path):
        if not name.lower().endswith('.html'):
            continue
        if filename_filter and not filename_filter(name):
            continue
        files.append(os.path.join(folder_path, name))

    return sorted(files)


def load_html_file(path: str) -> Tuple[str, str]:
    """
    Load an HTML file from disk.

    Returns:
        (filename_label, html_text)

    Notes:
    - Always returns *something*; html_text may be empty on error.
    - Caller decides whether empty content is actionable.
    """
    filename = os.path.basename(path)
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            html = f.read()
        return filename, html
    except Exception:
        return filename, ''


def delete_processed_files(paths: List[str]) -> None:
    """
    Delete processed HTML files.

    Failure to delete one file must not stop cleanup of others.
    """
    for p in paths:
        try:
            os.remove(p)
        except Exception:
            pass
