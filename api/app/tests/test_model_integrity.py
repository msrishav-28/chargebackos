import numpy as np
import pytest

from app.domain.model import permutation_contributions
from app.tests.test_policy import _base
from app.domain.generate import generate_world
from collections import Counter


def test_explanations_follow_model_and_sum_to_prediction_difference():
    sample = np.array([0.8, 0.3, 0.7])
    baseline = np.zeros(3)
    def predict(rows):
        return rows[:, 0] * 0.4 + rows[:, 1] * 0.2 + rows[:, 0] * rows[:, 1] * 0.3
    result = permutation_contributions(predict, sample, baseline)
    assert result[2] == 0
    assert result.sum() == pytest.approx(predict(sample[None, :])[0] - predict(baseline[None, :])[0])
    assert np.array_equal(result, permutation_contributions(predict, sample, baseline))


def test_policy_hash_changes_when_economics_or_conflicts_change():
    base = _base()["inputSnapshotHash"]
    assert _base(expected_recovered=2001)["inputSnapshotHash"] != base
    assert _base(refund_requested=1)["inputSnapshotHash"] != base


def test_policy_rejects_invalid_state_and_uncalibrated_model():
    assert not _base(case_state="closed")["allowed"]
    assert not _base(calibrated=False)["allowed"]
    assert not _base(missing_required=["transaction_record"])["allowed"]
    with pytest.raises(ValueError):
        _base(fight_worthiness=float("nan"))


def test_frozen_split_has_exact_counts_and_reserved_demo_cases():
    first = generate_world(42, 1500)["cases"]
    second = generate_world(42, 1500)["cases"]
    assert Counter(c["split"] for c in first) == {"train": 1050, "validation": 225, "test": 225}
    assert all(c["split"] == "test" for c in first if c["isDemo"])
    assert [(c["id"], c["split"], c["features"]) for c in first] == [(c["id"], c["split"], c["features"]) for c in second]
