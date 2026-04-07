"""
Model retraining route — admin only.
Accepts a labeled CSV (must have V1-V28, Amount, Class columns).
"""
import os, io
import pandas as pd
import joblib
from flask import Blueprint, request, jsonify, g
from api.auth import clerk_required
from api.database import db
from api.models import User

retrain_bp = Blueprint('retrain', __name__)

_BASE       = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_MODEL_PATH = os.path.join(_BASE, 'models', 'xgboost.pkl')


@retrain_bp.route('/retrain', methods=['POST'])
@clerk_required
def retrain():
    """Retrain the XGBoost model with new labeled data (admin only).
    ---
    tags: [Admin]
    security: [{Bearer: []}]
    consumes: [multipart/form-data]
    parameters:
      - in: formData
        name: file
        type: file
        required: true
        description: 'CSV with columns V1-V28, Amount, Class (0=legit, 1=fraud)'
    responses:
      200: {description: Model retrained successfully}
      403: {description: Admin access required}
      400: {description: Invalid file}
    """
    user = g.user
    if not user or not user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    f = request.files['file']
    if not f.filename.lower().endswith('.csv'):
        return jsonify({'error': 'Only .csv files accepted'}), 400

    try:
        df = pd.read_csv(io.StringIO(f.read().decode('utf-8')))

        required = [f'V{i}' for i in range(1, 29)] + ['Amount', 'Class']
        missing  = [c for c in required if c not in df.columns]
        if missing:
            return jsonify({'error': f'Missing columns: {missing}'}), 400

        feature_cols = [f'V{i}' for i in range(1, 29)] + ['Amount']
        X = df[feature_cols].values
        y = df['Class'].values

        # Load existing model for reference
        from xgboost import XGBClassifier
        model = XGBClassifier(n_estimators=100, max_depth=6, use_label_encoder=False,
                              eval_metric='logloss', random_state=42)
        model.fit(X, y)

        joblib.dump(model, _MODEL_PATH)

        # Reset the cached singleton so next request reloads the new model
        import api.routes.predictions as pred_module
        pred_module._model     = None
        pred_module._explainer = None

        return jsonify({
            'message':      'Model retrained and saved successfully',
            'rows_used':    len(df),
            'fraud_in_data': int(y.sum()),
            'legit_in_data': int((y == 0).sum()),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
