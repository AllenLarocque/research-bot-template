#!/usr/bin/env python3
import importlib
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def reload_paths(env):
    for k in ("RESEARCH_DOSSIERS", "FORESTWIKI_DOSSIERS", "RESEARCH_SCRATCH",
              "FORESTWIKI_SCRATCH", "RESEARCH_SRC_CACHE", "FORESTWIKI_SRC_CACHE"):
        os.environ.pop(k, None)
    os.environ.update(env)
    import research_core.paths as p
    return importlib.reload(p)


class TestPaths(unittest.TestCase):
    def test_new_env_name_is_honoured(self):
        self.assertEqual(reload_paths({"RESEARCH_DOSSIERS": "/new"}).DOSSIERS, "/new")

    def test_old_env_name_still_works(self):
        self.assertEqual(reload_paths({"FORESTWIKI_DOSSIERS": "/old"}).DOSSIERS, "/old")

    def test_new_name_wins_over_old(self):
        p = reload_paths({"RESEARCH_DOSSIERS": "/new", "FORESTWIKI_DOSSIERS": "/old"})
        self.assertEqual(p.DOSSIERS, "/new")

    def test_default_is_dossiers(self):
        self.assertEqual(reload_paths({}).DOSSIERS, "/dossiers")

    def test_ledger_underscores_spaces(self):
        p = reload_paths({"RESEARCH_DOSSIERS": "/d"})
        self.assertEqual(p.ledger_path("Powell River"), "/d/Powell_River/sources.md")

    # --- DOSSIERS / SCRATCH: presence, not truthiness ---------------------
    # os.environ.get(NAME, default) honours an explicitly-set "" as a real
    # value. These lock that in for both RESEARCH_* and FORESTWIKI_* names,
    # so an `or`-chain regression (which would silently substitute the
    # default for "") gets caught.

    def test_dossiers_neither_set_uses_default(self):
        self.assertEqual(reload_paths({}).DOSSIERS, "/dossiers")

    def test_dossiers_only_new_set(self):
        self.assertEqual(reload_paths({"RESEARCH_DOSSIERS": "/new"}).DOSSIERS, "/new")

    def test_dossiers_only_old_set(self):
        self.assertEqual(reload_paths({"FORESTWIKI_DOSSIERS": "/old"}).DOSSIERS, "/old")

    def test_dossiers_both_set_new_wins(self):
        p = reload_paths({"RESEARCH_DOSSIERS": "/new", "FORESTWIKI_DOSSIERS": "/old"})
        self.assertEqual(p.DOSSIERS, "/new")

    def test_dossiers_new_set_to_empty_string_is_honoured(self):
        p = reload_paths({"RESEARCH_DOSSIERS": ""})
        self.assertEqual(p.DOSSIERS, "")

    def test_dossiers_old_set_to_empty_string_is_honoured(self):
        p = reload_paths({"FORESTWIKI_DOSSIERS": ""})
        self.assertEqual(p.DOSSIERS, "")

    def test_dossiers_new_empty_wins_over_old_nonempty(self):
        # Presence of RESEARCH_DOSSIERS="" must still beat FORESTWIKI_DOSSIERS
        # being set to a real value -- new-name-wins is unconditional on
        # presence, not on truthiness.
        p = reload_paths({"RESEARCH_DOSSIERS": "", "FORESTWIKI_DOSSIERS": "/old"})
        self.assertEqual(p.DOSSIERS, "")

    def test_scratch_neither_set_uses_default(self):
        self.assertEqual(reload_paths({}).SCRATCH, "/tmp/research")

    def test_scratch_only_new_set(self):
        self.assertEqual(reload_paths({"RESEARCH_SCRATCH": "/new"}).SCRATCH, "/new")

    def test_scratch_only_old_set(self):
        self.assertEqual(reload_paths({"FORESTWIKI_SCRATCH": "/old"}).SCRATCH, "/old")

    def test_scratch_both_set_new_wins(self):
        p = reload_paths({"RESEARCH_SCRATCH": "/new", "FORESTWIKI_SCRATCH": "/old"})
        self.assertEqual(p.SCRATCH, "/new")

    def test_scratch_new_set_to_empty_string_is_honoured(self):
        p = reload_paths({"RESEARCH_SCRATCH": ""})
        self.assertEqual(p.SCRATCH, "")

    def test_scratch_old_set_to_empty_string_is_honoured(self):
        p = reload_paths({"FORESTWIKI_SCRATCH": ""})
        self.assertEqual(p.SCRATCH, "")

    # --- CACHE: truthiness semantics, preserved from the original ---------
    # The original already used `os.environ.get("FORESTWIKI_SRC_CACHE") or
    # os.path.join(SCRATCH, "srccache")`, so "" falling through to the
    # derived path is the CORRECT, pre-existing behaviour for this one
    # variable -- do not "fix" it to presence-based semantics.

    def test_cache_defaults_to_derived_path(self):
        p = reload_paths({})
        self.assertEqual(p.CACHE, os.path.join("/tmp/research", "srccache"))

    def test_cache_new_set_is_honoured(self):
        p = reload_paths({"RESEARCH_SRC_CACHE": "/cache"})
        self.assertEqual(p.CACHE, "/cache")

    def test_cache_old_set_is_honoured(self):
        p = reload_paths({"FORESTWIKI_SRC_CACHE": "/cache"})
        self.assertEqual(p.CACHE, "/cache")

    def test_cache_new_wins_over_old(self):
        p = reload_paths({"RESEARCH_SRC_CACHE": "/new", "FORESTWIKI_SRC_CACHE": "/old"})
        self.assertEqual(p.CACHE, "/new")

    def test_cache_new_empty_falls_through_to_old(self):
        p = reload_paths({"RESEARCH_SRC_CACHE": "", "FORESTWIKI_SRC_CACHE": "/old"})
        self.assertEqual(p.CACHE, "/old")

    def test_cache_new_empty_and_old_unset_falls_through_to_derived(self):
        p = reload_paths({"RESEARCH_SRC_CACHE": "", "RESEARCH_SCRATCH": "/scratch"})
        self.assertEqual(p.CACHE, os.path.join("/scratch", "srccache"))

    def test_cache_old_empty_falls_through_to_derived(self):
        p = reload_paths({"FORESTWIKI_SRC_CACHE": "", "RESEARCH_SCRATCH": "/scratch"})
        self.assertEqual(p.CACHE, os.path.join("/scratch", "srccache"))

    def test_cache_derived_path_uses_scratch_from_fallback_var(self):
        # SCRATCH itself resolved via the FORESTWIKI_* fallback; CACHE's
        # derived path must be built from that resolved value, not /tmp/research.
        p = reload_paths({"FORESTWIKI_SCRATCH": "/old-scratch"})
        self.assertEqual(p.SCRATCH, "/old-scratch")
        self.assertEqual(p.CACHE, os.path.join("/old-scratch", "srccache"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
