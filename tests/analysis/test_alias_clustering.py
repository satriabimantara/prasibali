"""Alias clustering must give the same groups in every process (the package dedupes through a set)."""

import json
import os
import subprocess
import sys
from pathlib import Path

from apps.analysis.services.pipeline import cluster_aliases

CHARACTERS = ["I Kancil", "I Siput", "I Siputane", "Kancil", "Siput", "Siput ane malunan", "semut buaya",
              "sipute liu pesan", "timpalne"]
SRC = Path(__file__).resolve().parents[2] / "src"
CODE = (
    "import json, sys, django; django.setup(); from apps.analysis.services.pipeline import cluster_aliases; "
    "print(json.dumps(cluster_aliases(json.loads(sys.argv[1]), 'jaro-distance', 0.85)))"
)


def test_same_groups_for_any_input_order():
    expected = cluster_aliases(CHARACTERS, "jaro-distance", 0.85)
    assert cluster_aliases(list(reversed(CHARACTERS)), "jaro-distance", 0.85) == expected


def test_same_groups_across_hash_seeds():
    results = set()
    for seed in ("1", "2", "3", "4"):
        env = {**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": str(SRC),
               "DJANGO_SETTINGS_MODULE": "config.settings.test"}
        out = subprocess.run(  # noqa: S603 - fixed interpreter and code
            [sys.executable, "-c", CODE, json.dumps(CHARACTERS)], env=env, capture_output=True, text=True, check=True,
        ).stdout
        results.add(out.strip().splitlines()[-1])
    assert len(results) == 1
