"""
FraudGuard API v2 — Main Flask Application
==========================================
Features: JWT Auth · PostgreSQL/SQLite DB · SHAP · Rate Limiting
          Swagger Docs · Email Alerts · CSV Upload · Batch Predict
"""
import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flasgger import Swagger
from dotenv import load_dotenv

from api.database import db
from api.utils.email_helper import mail
from api.auth import auth_bp
from api.routes.predictions import predictions_bp
from api.routes.shap_routes import shap_bp
from api.routes.alerts import alerts_bp
from api.routes.retrain import retrain_bp

load_dotenv()

BASE_DIR     = os.path.dirname(os.path.dirname(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')
RESULTS_DIR  = os.path.join(BASE_DIR, 'results')
MODEL_PATH   = os.path.join(BASE_DIR, 'models', 'xgboost.pkl')

# ── Model Performance (static stats for /stats endpoint) ──────────
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
]


def create_app():
    app = Flask(__name__)

    # ── Config ────────────────────────────────────────────────────
    app.config['SECRET_KEY']     = os.getenv('SECRET_KEY', 'dev-secret-CHANGE-ME')
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-CHANGE-ME')

    # Database — PostgreSQL in production, SQLite locally
    db_url = os.getenv('DATABASE_URL', f'sqlite:///{os.path.join(BASE_DIR, "fraud_detection.db")}')
    if db_url.startswith('postgres://'):   # Render uses postgres://, SQLAlchemy needs postgresql://
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI']        = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Email (Flask-Mail via Gmail SMTP)
    app.config['MAIL_SERVER']         = 'smtp.gmail.com'
    app.config['MAIL_PORT']           = 587
    app.config['MAIL_USE_TLS']        = True
    app.config['MAIL_USERNAME']       = os.getenv('MAIL_USERNAME', '')
    app.config['MAIL_PASSWORD']       = os.getenv('MAIL_PASSWORD', '')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME', '')

    # ── Extensions ────────────────────────────────────────────────
    CORS(app, supports_credentials=True)
    db.init_app(app)
    mail.init_app(app)
    JWTManager(app)

    Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["500 per day", "100 per hour"],
        storage_uri="memory://"
    )

    Swagger(app, template={
        "info":  {"title": "FraudGuard API", "description": "Credit Card Fraud Detection API v2", "version": "2.0.0"},
        "securityDefinitions": {
            "Bearer": {"type": "apiKey", "name": "Authorization", "in": "header",
                       "description": "JWT token. Format: Bearer <token>"}
        }
    })

    # Create DB tables on startup
    with app.app_context():
        db.create_all()

    # ── Blueprints ────────────────────────────────────────────────
    app.register_blueprint(auth_bp)
    app.register_blueprint(predictions_bp)
    app.register_blueprint(shap_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(retrain_bp)

    # ── Static / Frontend Routes ──────────────────────────────────
    @app.route('/')
    @app.route('/app')
    def frontend():
        return send_from_directory(FRONTEND_DIR, 'index.html')

    @app.route('/frontend/<path:filename>')
    def frontend_static(filename):
        return send_from_directory(FRONTEND_DIR, filename)

    @app.route('/results/<filename>')
    def serve_result(filename):
        return send_from_directory(RESULTS_DIR, filename)

    # ── Core API Routes ───────────────────────────────────────────
    @app.route('/health')
    def health():
        """Health check endpoint.
        ---
        tags: [System]
        responses:
          200: {description: API is healthy}
        """
        return jsonify({'status': 'healthy', 'model_loaded': os.path.exists(MODEL_PATH), 'version': '2.0.0'})

    @app.route('/stats')
    def stats():
        """Project statistics for the dashboard.
        ---
        tags: [System]
        responses:
          200: {description: Dataset and model statistics}
        """
        return jsonify({
            'dataset': {'total_transactions': 284807, 'fraud_cases': 492,
                        'legitimate_cases': 284315, 'fraud_rate_percent': 0.17, 'features': 29},
            'model_performance':  MODEL_PERFORMANCE,
            'feature_importance': FEATURE_IMPORTANCE,
            'best_model':         'Random Forest',
            'best_roc_auc':       0.978,
            'model_loaded':       os.path.exists(MODEL_PATH),
            'available_results':  ['confusion_matrix.png', 'roc_curves.png', 'feature_analysis.png',
                                   'amount_analysis.png', 'correlation_matrix.png', 'boxplots.png'],
        })

    @app.route('/model-info')
    def model_info():
        """Model metadata.
        ---
        tags: [System]
        responses:
          200: {description: Model type and feature list}
        """
        if not os.path.exists(MODEL_PATH):
            return jsonify({'error': 'Model not loaded. Run: python src/main.py'}), 503
        import joblib
        model = joblib.load(MODEL_PATH)
        return jsonify({'model_type': type(model).__name__,
                        'features': [f'V{i}' for i in range(1, 29)] + ['Amount'],
                        'n_features': 29})

    # ── JWT Error Handlers ────────────────────────────────────────

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({'error': 'Authorization required. Please login.'}), 401

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Endpoint not found'}), 404

    @app.errorhandler(429)
    def rate_limited(e):
        return jsonify({'error': 'Rate limit exceeded. Try again later.'}), 429

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({'error': 'Internal server error'}), 500

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
