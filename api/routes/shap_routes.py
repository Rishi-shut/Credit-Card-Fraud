"""
SHAP explainability route — explains WHY a transaction was flagged.
Returns top contributing features ranked by absolute SHAP value.
"""
import numpy as np
from flask import Blueprint, request, jsonify
from api.routes.predictions import get_model, get_scaler, get_explainer, FEATURE_NAMES

shap_bp = Blueprint('shap', __name__)


@shap_bp.route('/explain', methods=['POST'])
def explain():
    """Get SHAP explanation for a set of features.
    ---
    tags: [Explainability]
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [features]
          properties:
            features:
              type: array
              items: {type: number}
              description: 29 features (V1-V28, Amount)
    responses:
      200:
        description: SHAP values + top feature breakdown
      503: {description: Model or SHAP not available}
    """
    try:
        data     = request.get_json() or {}
        features = data.get('features', [])

        if len(features) != 29:
            return jsonify({'error': f'Expected 29 features, got {len(features)}'}), 400

        model = get_model()
        if model is None:
            return jsonify({'error': 'Model not loaded'}), 503

        arr = np.array(features, dtype=float).reshape(1, -1)
        try: arr[0, -1] = get_scaler().transform([[arr[0, -1]]])[0, 0]
        except Exception: pass

        pred  = int(model.predict(arr)[0])
        proba = model.predict_proba(arr)[0]

        exp = get_explainer()
        if exp is None:
            return jsonify({'error': 'SHAP explainer not available'}), 503

        sv = exp.shap_values(arr)

        impacts = sorted([
            {
                'feature':      FEATURE_NAMES[i],
                'shap_value':   float(sv[0][i]),
                'abs_impact':   abs(float(sv[0][i])),
                'direction':    'increases_fraud_risk' if sv[0][i] > 0 else 'decreases_fraud_risk',
                'input_value':  float(features[i]),
            }
            for i in range(len(FEATURE_NAMES))
        ], key=lambda x: x['abs_impact'], reverse=True)

        return jsonify({
            'prediction':        pred,
            'prediction_label':  'Fraud' if pred == 1 else 'Legitimate',
            'fraud_probability': float(proba[1]),
            'base_value':        float(exp.expected_value) if hasattr(exp, 'expected_value') else 0,
            'top_features':      impacts[:10],
            'all_features':      impacts,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
