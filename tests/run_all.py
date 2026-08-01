#!/usr/bin/env python3
"""Run every test module. Exit non-zero if any fail.

This template repo carries only the standalone unittest modules for
research_core. The differential harnesses that diff against wiki-side
originals (verify_differential.py, webarchive_differential.py,
prose_differential.py) stay with the deployable repo -- they load
originals that live outside this repo's history.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)


def main():
    loader = unittest.TestLoader()
    suite = loader.discover(HERE, pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
