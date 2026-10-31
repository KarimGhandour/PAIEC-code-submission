"""Small deterministic checks for the new numerical component. No downloads."""
import unittest
import numpy as np
from experiments.inductive_mf_001.model import adapt, metadata_matrix, train_factor, DIM
from experiments.inductive_mf_001.calibration import calibrate
from experiments.inductive_mf_001.model import logit


class FactorChecks(unittest.TestCase):
    def test_unseen_configuration_reuses_known_metadata(self):
        subjects = [{"provider": "P", "harness": "source", "reasoning_effort": "medium"}]
        x, vocabulary = metadata_matrix(subjects, ["model/m"])
        changed = [{**subjects[0], "harness": "new-target-harness"}]
        y, same_vocabulary = metadata_matrix(changed, ["model/m"], vocabulary)
        self.assertEqual(vocabulary, same_vocabulary)
        self.assertEqual(int(np.count_nonzero(x)), 4)
        self.assertEqual(int(np.count_nonzero(y)), 3)
        self.assertEqual(y[0, vocabulary.index("model=model/m")], 0.5)

    def test_no_item_variation_equals_calibrated_baseline(self):
        z = np.zeros((11, DIM)); z[:, 0] = 1
        vectors = np.ones((2, DIM))
        acquired = list(range(7))
        labels = np.array([[0, 1], [0, 0], [1, 0], [1, 1], [0, 1], [0, 1], [1, 1]])
        prior = logit(np.array([0.3, 0.6]))
        prediction, records = adapt(z, vectors, acquired, labels, prior)
        baseline, _ = calibrate(np.tile(prior, (11, 1)), acquired, labels, prior)
        np.testing.assert_allclose(prediction, baseline, atol=1e-10)
        self.assertTrue(all(r["vector_delta_norm"] == 0 for r in records))

    def test_strong_vector_prior_matches_intercept_only(self):
        rng = np.random.default_rng(42)
        z = rng.normal(size=(12, DIM)); z /= np.linalg.norm(z, axis=1)[:, None]
        vectors = rng.normal(size=(2, DIM))
        labels = rng.integers(0, 2, size=(7, 2))
        prior = np.array([0.5, -0.2])
        prediction, _ = adapt(z, vectors, list(range(7)), labels, prior, vector_precision=1e6)
        reference, _ = calibrate(z @ vectors.T + np.array([10, -10]), list(range(7)), labels, prior)
        np.testing.assert_allclose(prediction, reference, atol=2e-6)

    def test_missing_edges_do_not_become_failures(self):
        rng = np.random.default_rng(42)
        x = rng.normal(size=(3, 768)).astype(np.float32)
        x /= np.linalg.norm(x, axis=1)[:, None]
        metadata = np.eye(2, dtype=np.float32)
        y = np.array([[1, np.nan], [0, 1], [np.nan, 0]])
        _, _, components, info = train_factor(x, metadata,
            [(np.arange(3), np.arange(2), y)], "cpu")
        self.assertEqual(info["training_observations"], 4)
        self.assertTrue(all(np.isfinite(a).all() for a in components))


if __name__ == "__main__":
    unittest.main()
