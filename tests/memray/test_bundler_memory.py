"""Memory profiling tests for bundler hot paths."""

import pytest
from wrknv.memray.runner import run_memray_stress

pytestmark = [pytest.mark.memray, pytest.mark.slow]


def test_bundler_allocations(memray_output_dir, memray_baseline, memray_baselines_path):
    run_memray_stress(
        script="scripts/memray/memray_bundler_stress.py",
        baseline_key="bundler_total_allocations",
        output_dir=memray_output_dir,
        baselines=memray_baseline,
        baselines_path=memray_baselines_path,
    )
