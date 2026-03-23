import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    precision_score, recall_score, f1_score, 
    roc_auc_score, confusion_matrix, classification_report,
    precision_recall_curve, roc_curve
)
import joblib
import os


class ModelEvaluator:
    def __init__(self):
        self.results = {}
        
    def evaluate_model(self, model, X_test, y_test, model_name):
        """Evaluate a single model"""
        print(f"\n=== Evaluating {model_name} ===")
        
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1] if hasattr(model, 'predict_proba') else None
        
        metrics = {
            'precision': precision_score(y_test, y_pred),
            'recall': recall_score(y_test, y_pred),
            'f1': f1_score(y_test, y_pred),
            'roc_auc': roc_auc_score(y_test, y_pred_proba) if y_pred_proba is not None else None
        }
        
        print(f"Precision: {metrics['precision']:.4f}")
        print(f"Recall: {metrics['recall']:.4f}")
        print(f"F1 Score: {metrics['f1']:.4f}")
        print(f"ROC-AUC: {metrics['roc_auc']:.4f}")
        
        print(f"\nClassification Report:")
        print(classification_report(y_test, y_pred, target_names=['Legitimate', 'Fraud']))
        
        print(f"\nConfusion Matrix:")
        cm = confusion_matrix(y_test, y_pred)
        print(cm)
        
        self.results[model_name] = {
            'metrics': metrics,
            'confusion_matrix': cm,
            'y_pred': y_pred,
            'y_pred_proba': y_pred_proba
        }
        
        return metrics
    
    def evaluate_all_models(self, models, X_test, y_test):
        """Evaluate all trained models"""
        print("\n" + "="*60)
        print("MODEL EVALUATION")
        print("="*60)
        
        for model_name, model in models.items():
            self.evaluate_model(model, X_test, y_test, model_name)
        
        return self.results
    
    def compare_models(self):
        """Compare all models and select the best one"""
        print("\n=== Model Comparison ===")
        
        comparison_data = []
        for model_name, result in self.results.items():
            metrics = result['metrics']
            comparison_data.append({
                'Model': model_name,
                'Precision': metrics['precision'],
                'Recall': metrics['recall'],
                'F1 Score': metrics['f1'],
                'ROC-AUC': metrics['roc_auc']
            })
        
        comparison_df = pd.DataFrame(comparison_data)
        print(comparison_df.to_string(index=False))
        
        best_model_name = max(self.results.keys(), 
                             key=lambda x: self.results[x]['metrics']['recall'])
        
        print(f"\n*** Best Model (by Recall): {best_model_name} ***")
        print(f"Recall: {self.results[best_model_name]['metrics']['recall']:.4f}")
        
        return best_model_name
    
    def plot_confusion_matrix(self, model_name, save_path=None):
        """Plot confusion matrix for a model"""
        cm = self.results[model_name]['confusion_matrix']
        
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                   xticklabels=['Legitimate', 'Fraud'],
                   yticklabels=['Legitimate', 'Fraud'])
        plt.xlabel('Predicted')
        plt.ylabel('Actual')
        plt.title(f'Confusion Matrix - {model_name}')
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"Confusion matrix saved to {save_path}")
        
        plt.close()
    
    def plot_roc_curves(self, y_test, save_path=None):
        """Plot ROC curves for all models"""
        plt.figure(figsize=(10, 8))
        
        for model_name, result in self.results.items():
            if result['y_pred_proba'] is not None:
                fpr, tpr, _ = roc_curve(y_test, result['y_pred_proba'])
                auc = result['metrics']['roc_auc']
                plt.plot(fpr, tpr, label=f'{model_name} (AUC = {auc:.4f})')
        
        plt.plot([0, 1], [0, 1], 'k--', label='Random Classifier')
        plt.xlabel('False Positive Rate')
        plt.ylabel('True Positive Rate')
        plt.title('ROC Curves Comparison')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"ROC curves saved to {save_path}")
        
        plt.close()
    
    def plot_precision_recall_curves(self, y_test, save_path=None):
        """Plot Precision-Recall curves for all models"""
        plt.figure(figsize=(10, 8))
        
        for model_name, result in self.results.items():
            if result['y_pred_proba'] is not None:
                precision, recall, _ = precision_recall_curve(y_test, result['y_pred_proba'])
                plt.plot(recall, precision, label=model_name)
        
        plt.xlabel('Recall')
        plt.ylabel('Precision')
        plt.title('Precision-Recall Curves Comparison')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"PR curves saved to {save_path}")
        
        plt.close()
    
    def save_results(self, output_dir='results', y_test=None):
        """Save evaluation results"""
        os.makedirs(output_dir, exist_ok=True)
        
        self.plot_confusion_matrix('xgboost', os.path.join(output_dir, 'confusion_matrix.png'))
        if y_test is not None:
            self.plot_roc_curves(y_test, os.path.join(output_dir, 'roc_curves.png'))
        
        print(f"\nResults saved to {output_dir}/")


if __name__ == "__main__":
    import pandas as pd
    from data_preprocessing import DataPreprocessor
    from model_training import ModelTrainer
    
    preprocessor = DataPreprocessor()
    preprocessor.load_data()
    preprocessor.preprocess()
    X_train, X_test, y_train, y_test = preprocessor.get_processed_data()
    
    trainer = ModelTrainer()
    X_train_resampled, y_train_resampled = trainer.apply_smote(X_train, y_train)
    trainer.train_all_models(X_train_resampled, y_train_resampled)
    
    evaluator = ModelEvaluator()
    evaluator.evaluate_all_models(trainer.models, X_test, y_test)
    best_model = evaluator.compare_models()
    evaluator.save_results()
