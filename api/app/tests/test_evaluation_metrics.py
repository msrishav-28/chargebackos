import pytest
from sklearn.metrics import auc, precision_recall_curve, roc_auc_score

from app.domain.evaluation import brier, classification_metrics, pr_auc, roc_auc


@pytest.mark.parametrize(
    ("labels", "probabilities"),
    [
        ([0, 1], [0.5, 0.5]),
        ([1, 0], [0.5, 0.5]),
        ([0, 1, 0, 1, 1, 0], [0.8, 0.8, 0.5, 0.5, 0.2, 0.2]),
        ([0, 1, 0, 1], [0.1, 0.9, 0.2, 0.8]),
    ],
)
def test_auc_matches_reference_with_tied_probabilities(labels, probabilities):
    precision, recall, _ = precision_recall_curve(labels, probabilities)
    assert roc_auc(labels, probabilities) == pytest.approx(roc_auc_score(labels, probabilities))
    assert pr_auc(labels, probabilities) == pytest.approx(auc(recall, precision))


@pytest.mark.parametrize("metric", [roc_auc, pr_auc, brier])
@pytest.mark.parametrize(
    ("labels", "probabilities"),
    [([0, 1], [0.3]), ([0, 2], [0.3, 0.8]), ([0, 1], [0.3, float("nan")])],
)
def test_invalid_metric_inputs_are_rejected(metric, labels, probabilities):
    with pytest.raises(ValueError):
        metric(labels, probabilities)


def test_classification_does_not_silently_discard_missing_predictions():
    with pytest.raises(ValueError):
        classification_metrics(["friendly_fraud_likely"], [])


def test_brier_matches_known_forecast_error():
    assert brier([0, 1], [0.25, 0.75]) == pytest.approx(0.0625)
