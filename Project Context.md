# Project Context: Credit Card Fraud Detection System

## Overview
A machine learning-based solution for detecting fraudulent credit card transactions in real-time. It handles highly imbalanced datasets (using SMOTE), trains multiple ML models (Logistic Regression, Random Forest, XGBoost), and serves predictions via a real-time REST API.

## Tech Stack
- **Language**: Python 3.10+
- **API Framework**: Flask
- **Machine Learning**: Scikit-learn, XGBoost, Imbalanced-learn (SMOTE)
- **Data & Visualization**: Pandas, NumPy, Matplotlib, Seaborn
- **Serialization**: Joblib

## Core Project Structure
- `api/app.py`: Flask REST API serving endpoints (`/predict`, `/batch-predict`, etc.) on port 5000.
- `src/main.py`: Main entry point to run the ML pipeline.
- `src/data_preprocessing.py`: Handles CSV loading, data cleaning, and scaling.
- `src/model_training.py`: Uses SMOTE to handle the imbalanced dataset (99.83% legitimate vs 0.17% fraud) and trains models.
- `src/model_evaluation.py`: Evaluates and logs model performance (Precision, Recall, F1, ROC-AUC).
- `src/feature_analysis.py`: Generates insights on individual feature importance.
- `models/`: Directory where compiled model artifacts (`.pkl`) are saved.
- `results/`: Output directory for generated evaluation plots/charts.
- `tests/`: Directory containing test scripts (e.g., `test_real.py`).
- `requirements.txt`: Python dependencies.

## Key Insights
- The dataset is extremely imbalanced (492 frauds out of 284,807 transactions).
- Random Forest achieves the best F1 Score, while XGBoost achieves very high recall.
- Higher recall is preferred to catch fraudulent transactions, with a slight trade-off in precision.

## Agent Instructions
- If reading this document due to context constraints, use the overview and structure above to re-familiarize yourself with the project.
- To execute training, run `python src/main.py` from the project root.
- To run the web service, run `python api/app.py`.


























# Credit Card Fraud Detection System - Technical Documentation

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Data Pipeline](#data-pipeline)
3. [Feature Engineering](#feature-engineering)
4. [Handling Class Imbalance](#handling-class-imbalance)
5. [Model Training](#model-training)
6. [Model Evaluation](#model-evaluation)
7. [API Working](#api-working)
8. [Prediction Flow](#prediction-flow)
9. [Key Components](#key-components)
10. [Technical Details](#technical-details)

---

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CREDIT CARD FRAUD DETECTION                   │
│                         SYSTEM ARCHITECTURE                       │
└─────────────────────────────────────────────────────────────────┘

    ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
    │    Raw      │      │   Data       │      │   Feature    │
    │  Transaction│ ───► │ Preprocessing│ ───► │ Engineering  │
    │    Data     │      │              │      │              │
    └──────────────┘      └──────────────┘      └──────────────┘
                                                            │
                                                            ▼
    ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
    │   Real-time  │ ◄─── │    Model     │ ◄─── │    SMOTE     │
    │  Prediction  │      │  Evaluation  │      │   (Balance)  │
    │    (API)     │      │              │      │              │
    └──────────────┘      └──────────────┘      └──────────────┘
         │                        │
         │                        │
         ▼                        ▼
    ┌──────────────┐      ┌──────────────┐
    │   Flask API  │      │   Models     │
    │   (port 5000)│      │ (XGBoost,RF) │
    └──────────────┘      └──────────────┘
```

---

## 2. Data Pipeline

### 2.1 Data Loading

```python
# From data_preprocessing.py
df = pd.read_csv('creditcard.csv')
```

**Dataset Details:**
- **Source:** Kaggle - Credit Card Fraud Detection
- **Total Rows:** 284,807
- **Total Columns:** 31
- **Target Variable:** `Class` (0 = Legitimate, 1 = Fraud)

### 2.2 Data Exploration

```python
# Check shape
df.shape  # (284807, 31)

# Check missing values
df.isnull().sum().sum()  # 0

# Class distribution
df['Class'].value_counts()
# 0: 284315 (99.83%)
# 1: 492 (0.17%)
```

### 2.3 Data Preprocessing Steps

1. **Remove Time column** (not useful for prediction)
2. **Separate features and target**
3. **Scale Amount using StandardScaler**

```python
# Feature selection
X = df.drop(['Class', 'Time'], axis=1)  # V1-V28 + Amount
y = df['Class']

# Scale Amount
X['Amount'] = scaler.fit_transform(X['Amount'].values.reshape(-1, 1))
```

### 2.4 Train-Test Split

```python
X_train, X_test, y_train, y_test = train_test_split(
    X, y, 
    test_size=0.2, 
    random_state=42, 
    stratify=y  # Maintain class ratio
)

# Results:
# Training: 227,845 samples (80%)
# Test: 56,962 samples (20%)
# Training fraud rate: 0.17%
# Test fraud rate: 0.17%
```

---

## 3. Feature Engineering

### 3.1 Feature Description

The dataset contains **29 features**:

| Feature | Description | Type |
|---------|-------------|------|
| V1-V28 | PCA-transformed features | float64 |
| Amount | Transaction amount | float64 |

### 3.2 What Are V1-V28?

These are **Principal Components** generated using PCA (Principal Component Analysis) from the original transaction data.

**Original data (before PCA):**
- Transaction time
- Transaction amount
- Merchant type
- Location
- Card usage patterns
- ...and more

**Why PCA?**
- The original data contained sensitive customer information
- PCA transforms it into uncorrelated components
- Preserves important variance while anonymizing data

### 3.3 Feature Importance (XGBoost)

```
Top 10 Most Important Features:
1. V14  - 29.8% (MOST IMPORTANT)
2. V10  - 29.2%
3. V4   - 6.2%
4. V17  - 3.3%
5. V8   - 3.0%
6. V12  - 2.7%
7. V13  - 2.0%
8. V3   - 1.7%
9. V19  - 1.7%
10. V18 - 1.4%
```

**Key Finding:** V14 and V10 together account for ~59% of fraud detection power!

### 3.4 Statistical Patterns

| Metric | Legitimate | Fraud | Difference |
|--------|-----------|-------|------------|
| Amount Mean | $88.29 | $122.21 | Higher for fraud |
| Amount Median | $22.00 | $9.25 | Lower for fraud |
| V14 Mean | 0.0121 | -6.9717 | Much more negative for fraud |
| V14 Std | 0.90 | 4.28 | Much more variance for fraud |

---

## 4. Handling Class Imbalance

### 4.1 The Problem

```
Class Distribution:
- Legitimate: 284,315 (99.83%)
- Fraud: 492 (0.17%)

This is EXTREME IMBALANCE!
If we train on this, model will just predict "legitimate" for everything.
```

### 4.2 Solution: SMOTE

**SMOTE = Synthetic Minority Oversampling Technique**

```python
from imblearn.over_sampling import SMOTE

smote = SMOTE(random_state=42)
X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)
```

**Before SMOTE:**
```
X_train: (227845, 29)
Class distribution: [227451, 394]
```

**After SMOTE:**
```
X_train: (454902, 29)
Class distribution: [227451, 227451]
Balancing ratio: 1.00:1
```

### 4.3 How SMOTE Works

```
Original Fraud Samples:  ■ ■ ■ (394)

SMOTE creates synthetic samples between existing fraud cases:
        
   ■───────────■───────────■───────────■
   ▲     ▲     ▲     ▲     ▲     ▲
Synthetic fraud samples created!
```

SMOTE interpolates new fraud cases between existing ones in feature space.

---

## 5. Model Training

### 5.1 Models Used

#### Model 1: Logistic Regression (Baseline)

```python
from sklearn.linear_model import LogisticRegression

lr = LogisticRegression(
    max_iter=1000,
    random_state=42,
    class_weight='balanced'
)
lr.fit(X_train, y_train)
```

**Pros:**
- Fast training
- Easy to interpret
- Good baseline

**Cons:**
- Linear decision boundary
- May not capture complex patterns

#### Model 2: Random Forest

```python
from sklearn.ensemble import RandomForestClassifier

rf = RandomForestClassifier(
    n_estimators=100,       # 100 trees
    max_depth=10,          # Max depth per tree
    min_samples_split=5,
    min_samples_leaf=2,
    random_state=42,
    n_jobs=-1,              # Use all CPU cores
    class_weight='balanced'
)
rf.fit(X_train, y_train)
```

**Pros:**
- Handles non-linear patterns
- Good with imbalanced data
- Feature importance built-in

**Cons:**
- Can overfit
- Slower than logistic regression

#### Model 3: XGBoost (Final Model)

```python
from xgboost import XGBClassifier

# Calculate scale_pos_weight for imbalance
scale_pos_weight = non_fraud_count / fraud_count  # ~577

xgb = XGBClassifier(
    n_estimators=100,
    max_depth=6,
    learning_rate=0.1,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=scale_pos_weight,
    random_state=42,
    use_label_encoder=False,
    eval_metric='logloss'
)
xgb.fit(X_train, y_train)
```

**Pros:**
- Best handling of imbalance
- High recall
- Robust to overfitting
- Best overall performance

**Cons:**
- More hyperparameters to tune

---

## 6. Model Evaluation

### 6.1 Metrics Explained

#### Accuracy (NOT USEFUL HERE!)
```
Accuracy = Correct Predictions / Total Predictions

Why not useful for fraud detection?
- If we predict all as "legitimate", accuracy = 99.83%!
- But we miss ALL fraud cases!
```

#### Precision
```
Precision = True Positives / (True Positives + False Positives)

If Precision = 0.5:
- Out of all predicted frauds, 50% are actually fraud
- High precision = fewer false alarms
```

#### Recall (Most Important!)
```
Recall = True Positives / (True Positives + False Negatives)

If Recall = 0.90:
- We catch 90% of all actual fraud cases
- High recall = better fraud detection
```

#### F1 Score
```
F1 = 2 × (Precision × Recall) / (Precision + Recall)

Balanced measure of precision and recall
```

#### ROC-AUC
```
ROC-AUC = Area Under ROC Curve

Measures overall model performance across all thresholds
- 0.5 = random guessing
- 1.0 = perfect
```

### 6.2 Our Results

| Model | Precision | Recall | F1 Score | ROC-AUC |
|-------|-----------|--------|----------|---------|
| Logistic Regression | 0.056 | **0.918** | 0.106 | 0.970 |
| Random Forest | **0.424** | 0.857 | **0.568** | **0.978** |
| XGBoost | 0.332 | 0.898 | 0.485 | 0.976 |

### 6.3 Confusion Matrix (XGBoost)

```
                 Predicted
              Legit    Fraud
Actual  Legit  56687    177
        Fraud    10      88

True Positives (caught fraud): 88
False Positives (false alarms): 177
False Negatives (missed fraud): 10
True Negatives (correct legit): 56687
```

### 6.4 Visualization Charts Generated

1. **confusion_matrix.png** - Heatmap of confusion matrix
2. **roc_curves.png** - ROC curves for all models
3. **feature_analysis.png** - Feature importance + distributions
4. **amount_analysis.png** - Amount distribution by class
5. **correlation_matrix.png** - Feature correlations
6. **boxplots.png** - Top 8 feature box plots

---

## 7. API Working

### 7.1 Flask API Structure

```python
# api/app.py

from flask import Flask, request, jsonify
import joblib
import numpy as np

app = Flask(__name__)

# Load model on startup
model = joblib.load('models/xgboost.pkl')
scaler = joblib.load('models/scaler.pkl')
```

### 7.2 API Endpoints

#### GET /
```python
@app.route('/')
def index():
    return jsonify({
        'service': 'Credit Card Fraud Detection API',
        'version': '1.0',
        'endpoints': {...}
    })
```

#### GET /health
```python
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'model_loaded': model is not None
    })
```

#### GET /model-info
```python
@app.route('/model-info', methods=['GET'])
def model_info():
    return jsonify({
        'model_type': type(model).__name__,
        'features': FEATURE_NAMES,
        'n_features': 29
    })
```

#### POST /predict (Main Endpoint)
```python
@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()
    
    # Extract features
    features = [data.get(f'V{i}', 0) for i in range(1, 29)]
    features.append(data['Amount'])
    
    # Reshape and scale
    features = np.array(features).reshape(1, -1)
    features[0, -1] = scaler.transform([[features[0, -1]]])[0, 0]
    
    # Predict
    prediction = model.predict(features)[0]
    probability = model.predict_proba(features)[0]
    
    return jsonify({
        'prediction': int(prediction),
        'prediction_label': 'Fraud' if prediction == 1 else 'Legitimate',
        'fraud_probability': float(probability[1]),
        'legitimate_probability': float(probability[0]),
        'confidence': float(max(probability))
    })
```

#### POST /batch-predict
```python
@app.route('/batch-predict', methods=['POST'])
def batch_predict():
    data = request.get_json()
    transactions = data.get('transactions', [])
    
    results = []
    for txn in transactions:
        # Same prediction logic
        results.append({...})
    
    return jsonify({'results': results})
```

### 7.3 API Flow Diagram

```
Client Request
      │
      ▼
┌─────────────┐
│  Flask API  │
│  (app.py)   │
└─────────────┘
      │
      ▼
┌─────────────┐
│ Parse JSON  │
│  Request    │
└─────────────┘
      │
      ▼
┌─────────────┐
│ Extract     │
│  Features   │
└─────────────┘
      │
      ▼
┌─────────────┐
│ Scale Amount│
│  (scaler)   │
└─────────────┘
      │
      ▼
┌─────────────┐
│   XGBoost   │
│   Predict   │
└─────────────┘
      │
      ▼
┌─────────────┐
│  Return     │
│   JSON      │
└─────────────┘
      │
      ▼
   Client
```

---

## 8. Prediction Flow

### 8.1 Complete Prediction Pipeline

```
1. INPUT
   {
     "V1": -1.2, "V2": 0.5, ..., "V28": 0.1,
     "Amount": 150
   }

2. PREPROCESSING
   - Extract V1-V28 and Amount
   - Scale Amount using saved scaler
   - Amount = (150 - mean) / std

3. MODEL PREDICTION
   - XGBoost model processes 29 features
   - Outputs probability scores
   - [P(legitimate), P(fraud)]

4. POST-PROCESSING
   - If P(fraud) > 0.5 → Predict Fraud
   - Else → Predict Legitimate

5. OUTPUT
   {
     "prediction": 0,
     "prediction_label": "Legitimate",
     "fraud_probability": 0.023,
     "legitimate_probability": 0.977,
     "confidence": 0.977
   }
```

### 8.2 How Model Makes Decision

```
                    XGBoost Decision Tree Ensemble
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
    Feature < -2.0?       Feature < 0?         Feature > 1.5?
         │                     │                     │
    ┌────┴────┐          ┌────┴────┐          ┌────┴────┐
    │         │          │         │          │         │
   Yes       No         Yes       No         Yes       No
    │         │          │         │          │         │
    ▼         ▼          ▼         ▼          ▼         ▼
 Fraud     ...        ...      Legit       Fraud      ...
 
(Repeats for ~100 trees, then averages probability)
```

---

## 9. Key Components

### 9.1 File Structure

```
Credit-Card-Fraud/
├── api/
│   └── app.py              # Flask API server
├── models/
│   ├── xgboost.pkl        # Trained XGBoost model
│   ├── random_forest.pkl  # Trained Random Forest
│   ├── logistic_regression.pkl
│   └── scaler.pkl         # StandardScaler for Amount
├── results/
│   ├── confusion_matrix.png
│   ├── roc_curves.png
│   ├── feature_analysis.png
│   ├── amount_analysis.png
│   ├── correlation_matrix.png
│   └── boxplots.png
├── src/
│   ├── data_preprocessing.py  # Data loading & cleaning
│   ├── model_training.py       # SMOTE & model training
│   ├── model_evaluation.py     # Metrics & visualization
│   ├── feature_analysis.py    # Feature importance analysis
│   └── main.py                # Main pipeline runner
├── creditcard.csv            # Kaggle dataset
├── requirements.txt          # Python dependencies
├── .gitignore                # Git ignore rules
└── README.md                 # Project README
```

### 9.2 Dependencies

```
pandas          # Data manipulation
numpy           # Numerical computing
scikit-learn    # ML algorithms
xgboost         # Gradient boosting
imbalanced-learn# SMOTE implementation
flask           # Web API
joblib          # Model saving/loading
matplotlib     # Plotting
seaborn         # Advanced plotting
```

### 9.3 Key Functions

#### data_preprocessing.py
```python
class DataPreprocessor:
    def load_data()         # Load creditcard.csv
    def explore_data()       # Print EDA statistics
    def handle_missing_values()  # Remove nulls
    def preprocess()         # Scale, split, return data
```

#### model_training.py
```python
class ModelTrainer:
    def apply_smote()       # Balance classes
    def train_logistic_regression()
    def train_random_forest()
    def train_xgboost()
    def train_all_models()  # Train all 3
    def save_all_models()   # Save to models/
```

#### model_evaluation.py
```python
class ModelEvaluator:
    def evaluate_model()    # Get metrics
    def evaluate_all_models() # Compare models
    def compare_models()     # Find best model
    def plot_confusion_matrix()
    def plot_roc_curves()
    def save_results()
```

---

## 10. Technical Details

### 10.1 Hyperparameters

#### XGBoost
```python
{
    'n_estimators': 100,
    'max_depth': 6,
    'learning_rate': 0.1,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'scale_pos_weight': 577  # Handle imbalance
}
```

#### Random Forest
```python
{
    'n_estimators': 100,
    'max_depth': 10,
    'min_samples_split': 5,
    'min_samples_leaf': 2,
    'class_weight': 'balanced'
}
```

#### StandardScaler
```python
# Fitted on training data
mean = 88.35
std = 250.12

# For new Amount:
scaled_amount = (amount - 88.35) / 250.12
```

### 10.2 Memory & Performance

| Metric | Value |
|--------|-------|
| Dataset Size | 66 MB |
| Training Time | ~2 minutes |
| Model Size | ~5 MB (each) |
| API Response Time | ~50ms |
| RAM Usage | ~500 MB |

### 10.3 Version Info

```python
Python: 3.10+
pandas: latest
numpy: latest
scikit-learn: latest
xgboost: 1.7+
flask: 2.0+
```

---

## Summary

1. **Data Pipeline:** Load → Clean → Scale → Split
2. **Imbalance:** Use SMOTE to balance classes
3. **Training:** Train XGBoost, Random Forest, Logistic Regression
4. **Evaluation:** Use precision, recall, F1, ROC-AUC
5. **API:** Flask REST API for real-time predictions
6. **Key Features:** V14 and V10 are most important

---

*End of Technical Documentation*


