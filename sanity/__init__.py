"""
Python wrapper around the Sanity.io HTTP API

Homepage: https://github.com/nc9/python-sanity
PyPI: https://pypi.org/project/python-sanity/
Documentation: https://python-sanity.readthedocs.io/

MIT License

Copyright (c) 2025 Nik Cubrilovic, OmniPro-Group

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
"""

from sanity.client import Client, SanityClient
from sanity.exceptions import SanityIOError

__version__ = "0.1.1"

__all__ = ["Client", "SanityClient", "SanityIOError"]
