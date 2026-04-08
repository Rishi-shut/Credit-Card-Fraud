"""
Prediction routes:
  POST /predict          — single prediction (saves to DB, sends alert)
  POST /batch-predict    — batch predictions
  GET  /predict/history  — user's history (JWT required)
  POST /predict/csv      — CSV upload → downloadable results (JWT required)
"""
import os, io, json
import numpy as np
import pandas as pd
import joblib
from flask import Blueprint, request, jsonify, send_file, g
from api.auth import clerk_required
from api.database import db
from api.models import Prediction, User


predictions_bp = Blueprint('predictions', __name__)

# ── Paths ──────────────────────────────────────────────────────────
_BASE    = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_MODEL   = os.path.join(_BASE, 'models', 'xgboost.pkl')
_SCALER  = os.path.join(_BASE, 'models', 'scaler.pkl')

FEATURE_NAMES = [f'V{i}' for i in range(1, 29)] + ['Amount']

# ── Background Loading (Prevents Render Deployment Timeouts) ──────
_models = {}
_scaler = None
_explainers = {}

def start_background_loading():
    """Triggers the heavy ML loading in a separate thread."""
    import threading
    thread = threading.Thread(target=_load_models_task)
    thread.daemon = True
    thread.start()

def _load_models_task():
    global _models, _scaler, _explainers
    import time
    
    # Force Matplotlib to non-interactive mode before importing SHAP
    # This prevents the "Building font cache" hang on Render
    try:
        import matplotlib
        matplotlib.use('Agg')
        import os
        os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib'
    except Exception: pass

    print("[INIT] Background Loading: Starting ML model pre-load...")
    try:
        _models['xgboost'] = joblib.load(_MODEL)
        _models['random_forest'] = joblib.load(os.path.join(_BASE, 'models', 'random_forest.pkl'))
        _models['logistic_regression'] = joblib.load(os.path.join(_BASE, 'models', 'logistic_regression.pkl'))
        _scaler = joblib.load(_SCALER)
        print("[INIT] Background Loading: Models loaded.")
    except Exception as e:
        print(f"[INIT] Background Loading Error (Models): {e}")

    # Give the server a few seconds to breathe and respond to health checks
    time.sleep(5)

    try:
        import shap
        if 'xgboost' in _models:
            _explainers['xgboost'] = shap.TreeExplainer(_models['xgboost'])
        if 'random_forest' in _models:
            _explainers['random_forest'] = shap.TreeExplainer(_models['random_forest'])
        print("[INIT] Background Loading: SHAP explainers initialized.")
    except Exception as e:
        print(f"[INIT] Background Loading Error (SHAP): {e}")

def get_model(model_id='xgboost'):
    global _models
    if model_id not in _models:
        path = os.path.join(_BASE, 'models', f'{model_id}.pkl')
        try:
            _models[model_id] = joblib.load(path)
        except Exception: return None
    return _models.get(model_id)

def get_scaler():
    global _scaler
    if _scaler is None:
        try: _scaler = joblib.load(_SCALER)
        except Exception:
            from sklearn.preprocessing import StandardScaler
            _scaler = StandardScaler()
    return _scaler

def get_explainer(model, model_id):
    global _explainers
    if model_id not in _explainers:
        try:
            import shap
            if model_id == 'logistic_regression':
                _explainers[model_id] = shap.LinearExplainer(model, get_scaler().transform(np.zeros((1, 29))))
            else:
                _explainers[model_id] = shap.TreeExplainer(model)
        except Exception: return None
    return _explainers.get(model_id)

# ── Core prediction logic ──────────────────────────────────────────
def make_prediction(features: list, model_id='xgboost') -> dict:
    model = get_model(model_id)
    if model is None:
        raise ValueError(f'Model "{model_id}" not found.')

    arr = np.array(features, dtype=float).reshape(1, -1)
    # Scale Amount (last column)
    try: arr[0, -1] = get_scaler().transform([[arr[0, -1]]])[0, 0]
    except Exception: pass

    pred  = int(model.predict(arr)[0])
    proba = model.predict_proba(arr)[0]

    # SHAP values (best-effort)
    shap_dict = None
    try:
        exp = get_explainer(model, model_id)
        if exp:
            sv = exp.shap_values(arr)
            # Handle list output for some models
            if isinstance(sv, list): sv = sv[1] if len(sv) > 1 else sv[0]
            if len(sv.shape) > 1: sv = sv[0]
            shap_dict = {FEATURE_NAMES[i]: float(sv[i]) for i in range(len(FEATURE_NAMES))}
    except Exception: pass

    return {
        'prediction':             pred,
        'prediction_label':       'Fraud' if pred == 1 else 'Legitimate',
        'fraud_probability':      float(proba[1]),
        'legitimate_probability': float(proba[0]),
        'confidence':             float(max(proba)),
        'shap_values':            shap_dict,
        'model_used':             model_id
    }

# ── Helper: optional JWT user ──────────────────────────────────────
def _optional_user_id():
    """
    Checks if a Clerk user is signed in. 
    If they are, ensures they exist in our local database (sync) and returns their ID.
    """
    try:
        from api.clerk_client import clerk_client
        from clerk_backend_api.security import AuthenticateRequestOptions
        
        # We need to pass empty options or specific ones for basic auth check
        request_state = clerk_client.authenticate_request(request, AuthenticateRequestOptions())
        
        if request_state.is_signed_in:
            clerk_id = request_state.payload.get('sub')
            
            # Use a fresh query to ensure we're looking in the right scope
            user = User.query.filter_by(clerk_id=clerk_id).first()
            
            if not user:
                # Pro-active sync: if user is logged in but not in our DB, create them.
                # Use a default email if we can't fetch it easily here (auth_bp handles full sync)
                email = request_state.payload.get('email', f'user_{clerk_id[:8]}@clerk.user')
                user = User(clerk_id=clerk_id, email=email)
                db.session.add(user)
                db.session.commit()
            
            return user.id if user else None
    except Exception as e:
        print(f"[PREDICT DEBUG] Optional user sync failed: {str(e)}")
        pass
    return None

# ── Routes ────────────────────────────────────────────────────────
@predictions_bp.route('/predict', methods=['POST'])
def predict():
    """Single transaction prediction.
    ---
    tags: [Predictions]
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            features:
              type: array
              items: {type: number}
              description: 29 values (V1-V28 + Amount)
            Amount:
              type: number
              description: Shorthand — only Amount provided
    responses:
      200: {description: Prediction result with SHAP values}
      400: {description: Bad input}
      503: {description: Model not loaded}
    """
    try:
        data = request.get_json() or {}
        if 'features' in data:
            features = data['features']
        elif 'Amount' in data:
            features = [data.get(f'V{i}', 0) for i in range(1, 29)] + [data['Amount']]
        else:
            return jsonify({'error': 'Provide a features array or Amount field'}), 400

        if len(features) != 29:
            return jsonify({'error': f'Expected 29 features, got {len(features)}'}), 400

        model_id = data.get('model', 'xgboost')
        result   = make_prediction(features, model_id)
        user_id  = _optional_user_id()

        # Save to DB
        try:
            p = Prediction(
                user_id=user_id, amount=features[-1],
                prediction=result['prediction'], prediction_label=result['prediction_label'],
                fraud_probability=result['fraud_probability'],
                legitimate_probability=result['legitimate_probability'],
                confidence=result['confidence'],
                features_json=json.dumps(features),
                shap_values_json=json.dumps(result['shap_values']) if result['shap_values'] else None,
                ip_address=request.remote_addr, source='manual'
            )
            db.session.add(p)
            db.session.commit()
            result['prediction_id'] = p.id
        except Exception: pass

        return jsonify(result)

    except ValueError as e:
        return jsonify({'error': str(e)}), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@predictions_bp.route('/batch-predict', methods=['POST'])
def batch_predict():
    """Batch transaction predictions (max 1000).
    ---
    tags: [Predictions]
    """
    try:
        data = request.get_json() or {}
        transactions = data.get('transactions', [])
        if not transactions:
            return jsonify({'error': 'No transactions provided'}), 400
        if len(transactions) > 1000:
            return jsonify({'error': 'Max 1000 transactions per batch'}), 400

        user_id = _optional_user_id()
        results = []

        model_id = data.get('model', 'xgboost')
        for txn in transactions:
            features = txn.get('features', [])
            if len(features) != 29:
                results.append({'error': f'Expected 29 features, got {len(features)}'}); continue
            try:
                r = make_prediction(features, model_id)
                results.append(r)
                try:
                    db.session.add(Prediction(
                        user_id=user_id, amount=features[-1],
                        prediction=r['prediction'], prediction_label=r['prediction_label'],
                        fraud_probability=r['fraud_probability'],
                        legitimate_probability=r['legitimate_probability'],
                        confidence=r['confidence'],
                        features_json=json.dumps(features),
                        ip_address=request.remote_addr, source='batch'
                    ))
                except Exception: pass
            except Exception as e:
                results.append({'error': str(e)})

        try: db.session.commit()
        except Exception: pass

        fraud_count = sum(1 for r in results if r.get('prediction') == 1)
        return jsonify({'results': results, 'total': len(results),
                        'fraud_detected': fraud_count, 'legitimate': len(results) - fraud_count})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@predictions_bp.route('/predict/history', methods=['GET'])
@clerk_required
def history():
    """Get prediction history for logged-in user (paginated).
    ---
    tags: [Predictions]
    security: [{Bearer: []}]
    parameters:
      - {name: page,     in: query, type: integer, default: 1}
      - {name: per_page, in: query, type: integer, default: 20}
      - {name: filter,   in: query, type: string,  enum: [all, fraud, legitimate], default: all}
    responses:
      200: {description: Paginated prediction list}
    """
    user_id  = g.user.id
    page     = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    filt     = request.args.get('filter', 'all')

    q = Prediction.query.filter_by(user_id=user_id)
    if filt == 'fraud':     q = q.filter_by(prediction=1)
    elif filt == 'legitimate': q = q.filter_by(prediction=0)
    q = q.order_by(Prediction.timestamp.desc())

    pg = q.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'predictions':   [p.to_dict() for p in pg.items],
        'total':         pg.total,
        'pages':         pg.pages,
        'current_page':  page,
        'fraud_total':   Prediction.query.filter_by(user_id=user_id, prediction=1).count(),
        'legit_total':   Prediction.query.filter_by(user_id=user_id, prediction=0).count(),
    })

@predictions_bp.route('/predict/history', methods=['DELETE'])
@clerk_required
def clear_history():
    """Clear all prediction history for logged-in user.
    ---
    tags: [Predictions]
    security: [{Bearer: []}]
    responses:
      200: {description: History cleared successfully}
    """
    user_id = g.user.id
    try:
        Prediction.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        return jsonify({'message': 'History cleared successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@predictions_bp.route('/predict/csv', methods=['POST'])
@clerk_required
def predict_csv():
    """Upload a CSV file for batch predictions. Returns results CSV.
    ---
    tags: [Predictions]
    security: [{Bearer: []}]
    consumes: [multipart/form-data]
    parameters:
      - {in: formData, name: file, type: file, required: true,
         description: 'CSV with columns V1-V28 and Amount'}
    responses:
      200: {description: Predictions CSV file download}
    """
    user_id = g.user.id
    if 'file' not in request.files:
        return jsonify({'error': 'No file — send as multipart/form-data key "file"'}), 400

    f = request.files['file']
    if not f.filename.lower().endswith('.csv'):
        return jsonify({'error': 'Only .csv files accepted'}), 400

    try:
        df = pd.read_csv(io.StringIO(f.read().decode('utf-8')))
        if len(df) > 10_000:
            return jsonify({'error': 'Max 10,000 rows per CSV'}), 400

        preds    = []
        model_id = request.form.get('model', 'xgboost')
        for _, row in df.iterrows():
            features = [float(row.get(f'V{i}', 0)) for i in range(1, 29)] + [float(row.get('Amount', 0))]
            try:
                r = make_prediction(features, model_id)
                preds.append(r)
                db.session.add(Prediction(
                    user_id=user_id, amount=features[-1],
                    prediction=r['prediction'], prediction_label=r['prediction_label'],
                    fraud_probability=r['fraud_probability'],
                    legitimate_probability=r['legitimate_probability'],
                    confidence=r['confidence'],
                    features_json=json.dumps(features),
                    ip_address=request.remote_addr, source='csv'
                ))
            except Exception as e:
                preds.append({'error': str(e)})

        try: db.session.commit()
        except Exception: pass

        out = df.copy()
        out['prediction']        = [p.get('prediction', '')        for p in preds]
        out['prediction_label']  = [p.get('prediction_label', p.get('error', '')) for p in preds]
        out['fraud_probability'] = [p.get('fraud_probability', '') for p in preds]
        out['confidence']        = [p.get('confidence', '')        for p in preds]

        buf = io.BytesIO()
        out.to_csv(buf, index=False)
        buf.seek(0)

        return send_file(buf, mimetype='text/csv', as_attachment=True,
                         download_name='fraud_predictions.csv')
    except pd.errors.EmptyDataError:
        return jsonify({'error': 'CSV is empty'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
