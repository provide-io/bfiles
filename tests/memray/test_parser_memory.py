"""Memory profiling tests for BundleParser hot paths."""

import pytest
from wrknv.memray.runner import run_memray_stress

pytestmark = [pytest.mark.memray, pytest.mark.slow]


def test_parser_allocations(memray_output_dir, memray_baseline, memray_baselines_path):
    run_memray_stress(
        script="scripts/memray/memray_parser_stress.py",
        baseline_key="parser_total_allocations",
        output_dir=memray_output_dir,
        baselines=memray_baseline,
        baselines_path=memray_baselines_path,
    )
