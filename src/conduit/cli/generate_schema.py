#!/usr/bin/env python3
"""
Schema Generator CLI for Conduit Pipeline Elements

This script automatically generates a JSON schema for Conduit pipeline YAML/JSON configurations
by introspecting the Python classes and their type hints, docstrings, and signatures.
"""

import sys
from conduit.schema_generator import main

if __name__ == '__main__':
    main()