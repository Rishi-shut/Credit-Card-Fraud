from flask import Flask, request, jsonify
import joblib
import numpy as np
import os
from sklearn.preprocessing import StandardScaler

app = Flask(__name__)

MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models', 'xgboost.pkl')
SCALER_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models', 'scaler.pkl')

model = None
scaler = None

FEATURE_NAMES = ['V1', 'V2', 'V3', 'V4', 'V5', 'V6', 'V7', 'V8', 'V9', 'V10',
                  'V11', 'V12', 'V13', 'V14', 'V15', 'V16', 'V17', 'V18', 'V19', 'V20',
                  'V21', 'V22', 'V23', 'V24', 'V25', 'V26', 'V27', 'V28', 'Amount']


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


@app.route('/')
def index():
    return jsonify({
        'service': 'Credit Card Fraud Detection API',
        'version': '1.0',
        'endpoints': {
            '/predict': 'POST - Make fraud prediction',
            '/health': 'GET - Health check',
            '/model-info': 'GET - Get model information'
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
            
            features = np.array(features).reshape(1, -1)
            prediction = model.predict(features)[0]
            probability = model.predict_proba(features)[0]
            
            results.append({
                'prediction': int(prediction),
                'prediction_label': 'Fraud' if prediction == 1 else 'Legitimate',
                'fraud_probability': float(probability[1])
            })
        
        return jsonify({'results': results})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    load_model()
    app.run(debug=True, host='0.0.0.0', port=5000)
