"""Top-level package for cdp_backend."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("cdp-backend")
except PackageNotFoundError:
    __version__ = "uninstalled"

__author__ = "Eva Maxfield Brown, To Huynh, Isaac Na, Council Data Project Contributors"
__email__ = "evamaxfieldbrown@gmail.com"
