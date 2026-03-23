import numpy as np
from imblearn.over_sampling import SMOTE
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.linear_model import LogisticRegression
import joblib
import os


class ModelTrainer:
    def __init__(self, random_state=42):
        self.random_state = random_state
        self.models = {}
        self.smote = SMOTE(random_state=random_state)
        self.X_train_resampled = None
        self.y_train_resampled = None
        
    def apply_smote(self, X_train, y_train):
        """Apply SMOTE to handle class imbalance"""
        print("\n=== Applying SMOTE ===")
        print(f"Before SMOTE - X_train shape: {X_train.shape}")
        print(f"Before SMOTE - Class distribution: {np.bincount(y_train)}")
        
        self.X_train_resampled, self.y_train_resampled = self.smote.fit_resample(X_train, y_train)
        
        print(f"After SMOTE - X_train shape: {self.X_train_resampled.shape}")
        print(f"After SMOTE - Class distribution: {np.bincount(self.y_train_resampled)}")
        print(f"Balancing ratio: {np.bincount(self.y_train_resampled)[0]/np.bincount(self.y_train_resampled)[1]:.2f}:1")
        
        return self.X_train_resampled, self.y_train_resampled
    
    def train_logistic_regression(self, X_train, y_train):
        """Train Logistic Regression baseline model"""
        print("\n=== Training Logistic Regression ===")
        lr = LogisticRegression(
            max_iter=1000,
            random_state=self.random_state,
            class_weight='balanced'
        )
        lr.fit(X_train, y_train)
        self.models['logistic_regression'] = lr
        print("Logistic Regression trained successfully")
        return lr
    
    def train_random_forest(self, X_train, y_train):
        """Train Random Forest model"""
        print("\n=== Training Random Forest ===")
        rf = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=self.random_state,
            n_jobs=-1,
            class_weight='balanced'
        )
        rf.fit(X_train, y_train)
        self.models['random_forest'] = rf
        print("Random Forest trained successfully")
        return rf
    
    def train_xgboost(self, X_train, y_train):
        """Train XGBoost model"""
        print("\n=== Training XGBoost ===")
        
        fraud_count = np.sum(y_train == 1)
        non_fraud_count = np.sum(y_train == 0)
        scale_pos_weight = non_fraud_count / fraud_count
        
        xgb = XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_pos_weight,
            random_state=self.random_state,
            use_label_encoder=False,
            eval_metric='logloss'
        )
        xgb.fit(X_train, y_train)
        self.models['xgboost'] = xgb
        print("XGBoost trained successfully")
        return xgb
    
    def train_all_models(self, X_train, y_train):
        """Train all models"""
        self.train_logistic_regression(X_train, y_train)
        self.train_random_forest(X_train, y_train)
        self.train_xgboost(X_train, y_train)
        return self.models
    
    def save_model(self, model_name, filepath):
        """Save a trained model to disk"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump(self.models[model_name], filepath)
        print(f"Model saved to {filepath}")
        
    def save_all_models(self, model_dir='models', scaler=None):
        """Save all trained models"""
        os.makedirs(model_dir, exist_ok=True)
        for name, model in self.models.items():
            filepath = os.path.join(model_dir, f'{name}.pkl')
            joblib.dump(model, filepath)
            print(f"Saved {name} to {filepath}")
        
        if scaler is not None:
            scaler_path = os.path.join(model_dir, 'scaler.pkl')
            joblib.dump(scaler, scaler_path)
            print(f"Saved scaler to {scaler_path}")
    
    def get_model(self, model_name):
        """Get a trained model by name"""
        return self.models.get(model_name)


if __name__ == "__main__":
    from data_preprocessing import DataPreprocessor
    
    preprocessor = DataPreprocessor()
    preprocessor.load_data()
    preprocessor.preprocess()
    
    X_train, X_test, y_train, y_test = preprocessor.get_processed_data()
    
    trainer = ModelTrainer()
    X_train_resampled, y_train_resampled = trainer.apply_smote(X_train, y_train)
    
    models = trainer.train_all_models(X_train_resampled, y_train_resampled)
    trainer.save_all_models()
    print("\nAll models trained and saved!")
