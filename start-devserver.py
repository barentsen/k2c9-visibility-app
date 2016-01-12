#!/usr/bin/env python
"""Starts the Flask app in debug mode.

Do not use in production.
"""
from k2c9app import c9app

if __name__ == "__main__":
    c9app.debug = True
    c9app.run(port=8042, host='0.0.0.0', processes=3)
