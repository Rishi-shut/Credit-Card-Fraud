from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import joblib
import numpy as np
import os
from sklearn.preprocessing import StandardScaler

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

BASE_DIR     = os.path.dirname(os.path.dirname(__file__))
MODEL_PATH   = os.path.join(BASE_DIR, 'models', 'xgboost.pkl')
SCALER_PATH  = os.path.join(BASE_DIR, 'models', 'scaler.pkl')
RESULTS_DIR  = os.path.join(BASE_DIR, 'results')
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')

model = None
scaler = None

FEATURE_NAMES = ['V1', 'V2', 'V3', 'V4', 'V5', 'V6', 'V7', 'V8', 'V9', 'V10',
                  'V11', 'V12', 'V13', 'V14', 'V15', 'V16', 'V17', 'V18', 'V19', 'V20',
                  'V21', 'V22', 'V23', 'V24', 'V25', 'V26', 'V27', 'V28', 'Amount']

MODEL_PERFORMANCE = {
    "Logistic Regression": {"precision": 0.056, "recall": 0.918, "f1": 0.106, "roc_auc": 0.970},
    "Random Forest":       {"precision": 0.424, "recall": 0.857, "f1": 0.568, "roc_auc": 0.978},
    "XGBoost":             {"precision": 0.332, "recall": 0.898, "f1": 0.485, "roc_auc": 0.976},
}

FEATURE_IMPORTANCE = [
    {"feature": "V14", "importance": 29.8},
    {"feature": "V10", "importance": 29.2},
    {"feature": "V4",  "importance": 6.2},
    {"feature": "V17", "importance": 3.3},
    {"feature": "V8",  "importance": 3.0},
    {"feature": "V12", "importance": 2.7},
    {"feature": "V13", "importance": 2.0},
    {"feature": "V3",  "importance": 1.7},
    {"feature": "V19", "importance": 1.7},
    {"feature": "V18", "importance": 1.4},
]


def load_model():
    global model, scaler
    try:
        model = joblib.load(MODEL_PATH)
        print("Model loaded successfully")
    except FileNotFoundError:
        print(f"Model not found at {MODEL_PATH}")
        print("Please run training first: python src/main.py")
        model = None

    try:
        scaler = joblib.load(SCALER_PATH)
    except FileNotFoundError:
        scaler = StandardScaler()
        print("Scaler not found, using default")


@app.route('/app')
def frontend():
    """Serve the FraudGuard dashboard."""
    return send_from_directory(FRONTEND_DIR, 'index.html')


@app.route('/frontend/<path:filename>')
def frontend_static(filename):
    """Serve frontend static assets (CSS, JS)."""
    return send_from_directory(FRONTEND_DIR, filename)


@app.route('/')
def index():
    return jsonify({
        'service': 'Credit Card Fraud Detection API',
        'version': '1.0',
        'dashboard': 'http://localhost:5000/app',
        'endpoints': {
            '/app': 'GET - FraudGuard Dashboard UI',
            '/predict': 'POST - Make fraud prediction',
            '/batch-predict': 'POST - Batch fraud predictions',
            '/health': 'GET - Health check',
            '/model-info': 'GET - Get model information',
            '/stats': 'GET - Project statistics',
            '/results/<filename>': 'GET - Serve result images',
        }
    })


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'model_loaded': model is not None
    })


@app.route('/model-info', methods=['GET'])
def model_info():
    if model is None:
        return jsonify({'error': 'Model not loaded'}), 500

    return jsonify({
        'model_type': type(model).__name__,
        'features': FEATURE_NAMES,
        'n_features': len(FEATURE_NAMES)
    })


@app.route('/stats', methods=['GET'])
def stats():
    """Return high-level project statistics for the dashboard."""
    return jsonify({
        'dataset': {
            'total_transactions': 284807,
            'fraud_cases': 492,
            'legitimate_cases': 284315,
            'fraud_rate_percent': 0.17,
            'features': 29
        },
        'model_performance': MODEL_PERFORMANCE,
        'feature_importance': FEATURE_IMPORTANCE,
        'best_model': 'Random Forest',
        'best_roc_auc': 0.978,
        'model_loaded': model is not None,
        'available_results': [
            'confusion_matrix.png',
            'roc_curves.png',
            'feature_analysis.png',
            'amount_analysis.png',
            'correlation_matrix.png',
            'boxplots.png',
        ]
    })


@app.route('/results/<filename>', methods=['GET'])
def serve_result(filename):
    """Serve result images from the results directory."""
    return send_from_directory(RESULTS_DIR, filename)


@app.route('/predict', methods=['POST'])
def predict():
    if model is None:
        return jsonify({'error': 'Model not loaded. Please train the model first.'}), 500

    try:
        data = request.get_json()

        if 'features' in data:
            features = data['features']
        elif 'Amount' in data:
            features = [data.get(f'V{i}', 0) for i in range(1, 29)]
            features.append(data['Amount'])
        else:
            return jsonify({'error': 'Invalid input. Provide features or Amount.'}), 400

        if len(features) != len(FEATURE_NAMES):
            return jsonify({
                'error': f'Expected {len(FEATURE_NAMES)} features, got {len(features)}'
            }), 400

        features = np.array(features).reshape(1, -1)

        if scaler:
            features[0, -1] = scaler.transform([[features[0, -1]]])[0, 0]

        prediction = model.predict(features)[0]
        probability = model.predict_proba(features)[0]

        result = {
            'prediction': int(prediction),
            'prediction_label': 'Fraud' if prediction == 1 else 'Legitimate',
            'fraud_probability': float(probability[1]),
            'legitimate_probability': float(probability[0]),
            'confidence': float(max(probability))
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/batch-predict', methods=['POST'])
def batch_predict():
    if model is None:
        return jsonify({'error': 'Model not loaded'}), 500

    try:
        data = request.get_json()
        transactions = data.get('transactions', [])

        results = []
        for txn in transactions:
            features = txn.get('features', [])
            if len(features) != len(FEATURE_NAMES):
                results.append({'error': f'Expected {len(FEATURE_NAMES)} features'})
                continue

            feat_arr = np.array(features).reshape(1, -1)
            if scaler:
                feat_arr[0, -1] = scaler.transform([[feat_arr[0, -1]]])[0, 0]
            prediction = model.predict(feat_arr)[0]
            probability = model.predict_proba(feat_arr)[0]

            results.append({
                'prediction': int(prediction),
                'prediction_label': 'Fraud' if prediction == 1 else 'Legitimate',
                'fraud_probability': float(probability[1]),
                'legitimate_probability': float(probability[0]),
                'confidence': float(max(probability))
            })

        return jsonify({'results': results, 'total': len(results)})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    load_model()
    app.run(debug=True, host='0.0.0.0', port=5000)
