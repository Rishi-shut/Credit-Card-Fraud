"""
Tests for core API endpoints — health, stats, predict, batch-predict.
Run with: pytest tests/test_api.py -v
"""
import pytest

LEGIT_FEATURES = [0.0] * 28 + [50.0]   # 29 features — likely legitimate
FRAUD_FEATURES = [-9.5, 0, 0, -2.1, 0, 0, 0, 0, 0, -7.8,
                   0, -9.2, 0, 0, 0, 0, -8.4, 0, 0, 0,
                   0, 0, 0, 0, 0, 0, 0, 0, 329.0]


class TestHealth:
    def test_health_returns_200(self, client):
        r = client.get('/health')
        assert r.status_code == 200

    def test_health_has_status_field(self, client):
        data = client.get('/health').get_json()
        assert data['status'] == 'healthy'

    def test_health_has_version(self, client):
        data = client.get('/health').get_json()
        assert 'version' in data


class TestStats:
    def test_stats_returns_200(self, client):
        r = client.get('/stats')
        assert r.status_code == 200

    def test_stats_has_dataset(self, client):
        data = client.get('/stats').get_json()
        assert 'dataset' in data
        assert data['dataset']['total_transactions'] == 284807


class TestPredict:
    def test_predict_requires_features(self, client):
        r = client.post('/predict', json={})
        assert r.status_code == 400

    def test_predict_wrong_feature_count(self, client):
        r = client.post('/predict', json={'features': [1, 2, 3]})
        assert r.status_code == 400

    def test_predict_with_amount_shorthand(self, client):
        r = client.post('/predict', json={'Amount': 100})
        # Either 200 (model loaded) or 503 (model not present in test env)
        assert r.status_code in (200, 503)

    def test_predict_returns_probabilities(self, client):
        r = client.post('/predict', json={'features': LEGIT_FEATURES})
        if r.status_code == 200:
            data = r.get_json()
            assert 'fraud_probability' in data
            assert 'legitimate_probability' in data
            assert 'confidence' in data
            assert 'prediction_label' in data
            assert data['prediction'] in (0, 1)


class TestBatchPredict:
    def test_batch_requires_transactions(self, client):
        r = client.post('/batch-predict', json={})
        assert r.status_code == 400

    def test_batch_returns_results_list(self, client):
        payload = {'transactions': [{'features': LEGIT_FEATURES}]}
        r = client.post('/batch-predict', json=payload)
        assert r.status_code in (200, 503)
        if r.status_code == 200:
            data = r.get_json()
            assert 'results' in data
            assert 'total' in data

    def test_batch_rejects_over_limit(self, client):
        payload = {'transactions': [{'features': LEGIT_FEATURES}] * 1001}
        r = client.post('/batch-predict', json=payload)
        assert r.status_code == 400
