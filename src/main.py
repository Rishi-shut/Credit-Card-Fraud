import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_preprocessing import DataPreprocessor
from model_training import ModelTrainer
from model_evaluation import ModelEvaluator
import joblib


def main():
    print("="*60)
    print("CREDIT CARD FRAUD DETECTION SYSTEM")
    print("="*60)
    
    print("\n[1/5] Loading and preprocessing data...")
    preprocessor = DataPreprocessor()
    preprocessor.load_data()
    preprocessor.explore_data()
    preprocessor.handle_missing_values()
    preprocessor.preprocess()
    
    X_train, X_test, y_train, y_test = preprocessor.get_processed_data()
    
    print("\n[2/5] Applying SMOTE for class imbalance...")
    trainer = ModelTrainer()
    X_train_resampled, y_train_resampled = trainer.apply_smote(X_train, y_train)
    
    print("\n[3/5] Training models...")
    models = trainer.train_all_models(X_train_resampled, y_train_resampled)
    
    print("\n[4/5] Evaluating models...")
    evaluator = ModelEvaluator()
    evaluator.evaluate_all_models(models, X_test, y_test)
    best_model_name = evaluator.compare_models()
    
    print("\n[5/5] Saving models and results...")
    os.makedirs('models', exist_ok=True)
    trainer.save_all_models('models', preprocessor.scaler)
    evaluator.save_results('results', y_test)
    
    print("\n" + "="*60)
    print("TRAINING COMPLETE!")
    print("="*60)
    print(f"\nBest model: {best_model_name}")
    print(f"Models saved in: models/")
    print(f"Results saved in: results/")
    
    return trainer, evaluator, best_model_name


if __name__ == "__main__":
    main()
