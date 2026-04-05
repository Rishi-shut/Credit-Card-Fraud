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
from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from api.database import db
from api.models import Prediction, User
from api.utils.email_helper import send_fraud_alert

predictions_bp = Blueprint('predictions', __name__)

# ── Paths ──────────────────────────────────────────────────────────
_BASE    = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_MODEL   = os.path.join(_BASE, 'models', 'xgboost.pkl')
_SCALER  = os.path.join(_BASE, 'models', 'scaler.pkl')

FEATURE_NAMES = [f'V{i}' for i in range(1, 29)] + ['Amount']

# ── Lazy-load singletons ───────────────────────────────────────────
_model = _scaler = _explainer = None

def get_model():
    global _model
    if _model is None:
        try: _model = joblib.load(_MODEL)
        except FileNotFoundError: pass
    return _model

def get_scaler():
    global _scaler
    if _scaler is None:
        try: _scaler = joblib.load(_SCALER)
        except FileNotFoundError:
            from sklearn.preprocessing import StandardScaler
            _scaler = StandardScaler()
    return _scaler

def get_explainer():
    global _explainer
    if _explainer is None:
        try:
            import shap
            m = get_model()
            if m: _explainer = shap.TreeExplainer(m)
        except Exception: pass
    return _explainer

# ── Core prediction logic ──────────────────────────────────────────
def make_prediction(features: list) -> dict:
    model = get_model()
    if model is None:
        raise ValueError('Model not loaded. Run python src/main.py first.')

    arr = np.array(features, dtype=float).reshape(1, -1)
    # Scale Amount (last column)
    try: arr[0, -1] = get_scaler().transform([[arr[0, -1]]])[0, 0]
    except Exception: pass

    pred  = int(model.predict(arr)[0])
    proba = model.predict_proba(arr)[0]

    # SHAP values (best-effort)
    shap_dict = None
    try:
        exp = get_explainer()
        if exp:
            sv = exp.shap_values(arr)
            shap_dict = {FEATURE_NAMES[i]: float(sv[0][i]) for i in range(len(FEATURE_NAMES))}
    except Exception: pass

    return {
        'prediction':             pred,
        'prediction_label':       'Fraud' if pred == 1 else 'Legitimate',
        'fraud_probability':      float(proba[1]),
        'legitimate_probability': float(proba[0]),
        'confidence':             float(max(proba)),
        'shap_values':            shap_dict,
    }

# ── Helper: optional JWT user ──────────────────────────────────────
def _optional_user_id():
    try:
        verify_jwt_in_request(optional=True)
        uid = get_jwt_identity()
        return int(uid) if uid else None
    except Exception:
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

        result   = make_prediction(features)
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

        # Email alert
        if result['prediction'] == 1 and user_id:
            try:
                user = User.query.get(user_id)
                if user and user.alerts_enabled and result['fraud_probability'] >= user.alert_threshold:
                    send_fraud_alert(user.alert_email or user.email,
                                     result['fraud_probability'], features[-1])
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

        for txn in transactions:
            features = txn.get('features', [])
            if len(features) != 29:
                results.append({'error': f'Expected 29 features, got {len(features)}'}); continue
            try:
                r = make_prediction(features)
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
@jwt_required()
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
    user_id  = int(get_jwt_identity())
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
@jwt_required()
def clear_history():
    """Clear all prediction history for logged-in user.
    ---
    tags: [Predictions]
    security: [{Bearer: []}]
    responses:
      200: {description: History cleared successfully}
    """
    user_id = int(get_jwt_identity())
    try:
        Prediction.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        return jsonify({'message': 'History cleared successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@predictions_bp.route('/predict/csv', methods=['POST'])
@jwt_required()
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
    user_id = int(get_jwt_identity())
    if 'file' not in request.files:
        return jsonify({'error': 'No file — send as multipart/form-data key "file"'}), 400

    f = request.files['file']
    if not f.filename.lower().endswith('.csv'):
        return jsonify({'error': 'Only .csv files accepted'}), 400

    try:
        df = pd.read_csv(io.StringIO(f.read().decode('utf-8')))
        if len(df) > 10_000:
            return jsonify({'error': 'Max 10,000 rows per CSV'}), 400

        preds = []
        for _, row in df.iterrows():
            features = [float(row.get(f'V{i}', 0)) for i in range(1, 29)] + [float(row.get('Amount', 0))]
            try:
                r = make_prediction(features)
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
