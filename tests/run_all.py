#!/usr/bin/env python3
"""Run every test module. Exit non-zero if any fail.

This template repo carries only the standalone unittest modules for
research_core. The differential harnesses that diff against wiki-side
originals (verify_differential.py, webarchive_differential.py,
prose_differential.py) stay with the deployable repo -- they load
originals that live outside this repo's history.

Also runs eval_detection.py, the planted-defect detection eval. It is
deliberately a plain script, not a unittest.TestCase module -- unittest's
discover(pattern="test_*.py") never picks it up, so on its own it is
invisible to CI. It earns its keep by scoring the checking tools against
a committed baseline (eval_baseline.json) and failing if a class detects
fewer cases than it used to. So it runs here explicitly, as a subprocess
(it already has its own pass/fail via sys.exit).
"""
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)


def run_eval():
    """Run eval_detection.py as a subprocess, printing its scorecard.
    Returns True iff it exits 0.
    """
    print("\n" + "=" * 70)
    print("Detection eval (planted defects against the checking tools)")
    print("=" * 70)
    proc = subprocess.run(
        [sys.executable, os.path.join(HERE, "eval_detection.py")], cwd=ROOT)
    if proc.returncode != 0:
        print("[FAIL] eval_detection.py exited %d" % proc.returncode)
        return False
    print("[OK] eval_detection.py")
    return True


def main():
    loader = unittest.TestLoader()
    suite = loader.discover(HERE, pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)

    eval_ok = run_eval()

    return 0 if (result.wasSuccessful() and eval_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
