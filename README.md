# 🔐 Credit Card Fraud Detection System

A machine learning-based solution for detecting fraudulent credit card transactions in real-time.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Flask](https://img.shields.io/badge/Flask-2.0+-green)
![XGBoost](https://img.shields.io/badge/XGBoost-1.7+-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Dataset](#dataset)
- [Installation](#installation)
- [Usage](#usage)
- [Model Performance](#model-performance)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Future Enhancements](#future-enhancements)
- [License](#license)

---

## 🎯 Overview

This project implements a complete fraud detection pipeline that:

- ✅ Handles highly imbalanced datasets using SMOTE
- ✅ Trains multiple ML models (Logistic Regression, Random Forest, XGBoost)
- ✅ Evaluates models using precision, recall, F1-score, and ROC-AUC
- ✅ Provides a REST API for real-time predictions
- ✅ Generates visualization reports

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **SMOTE Imbalance Handling** | Synthetic oversampling for minority class |
| **Multi-Model Training** | Logistic Regression, Random Forest, XGBoost |
| **Model Evaluation** | Comprehensive metrics and visualizations |
| **REST API** | Flask-based API for real-time predictions |
| **Batch Predictions** | Process multiple transactions at once |

---

## 📊 Dataset

| Property | Value |
|----------|-------|
| Source | Kaggle Credit Card Fraud |
| Total Transactions | 284,807 |
| Features | 29 (V1-V28 + Amount) |
| Fraud Cases | 492 (0.17%) |
| Legitimate | 284,315 (99.83%) |

---

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/Credit-Card-Fraud.git
cd Credit-Card-Fraud
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 🚀 Usage

### Step 1: Train the Model
```bash
python src/main.py
```

This will:
- Load and preprocess the dataset
- Apply SMOTE for class imbalance
- Train all three models
- Evaluate and save results
- Generate visualization charts

### Step 2: Start the API
```bash
python api/app.py
```

The API will be available at: `http://localhost:5000`

### Step 3: Make Predictions

**Using Python:**
```python
import requests

url = "http://localhost:5000/predict"
data = {"Amount": 100}

response = requests.post(url, json=data)
print(response.json())
```

**Using curl:**
```bash
curl -X POST http://localhost:5000/predict -H "Content-Type: application/json" -d "{\"Amount\": 100}"
```

**Using Postman:**
- Method: POST
- URL: http://localhost:5000/predict
- Body: `{"Amount": 100}`

---

## 📈 Model Performance

| Model | Precision | Recall | F1 Score | ROC-AUC |
|-------|-----------|--------|----------|---------|
| **Logistic Regression** | 0.056 | **0.918** | 0.106 | 0.970 |
| **Random Forest** | **0.424** | 0.857 | **0.568** | **0.978** |
| **XGBoost** | 0.332 | 0.898 | 0.485 | 0.976 |

### Key Insights:
- ✅ **Recall**: XGBoost detects 90% of fraud cases
- ✅ **ROC-AUC**: All models achieve >97% AUC score
- ⚠️ **Precision Trade-off**: Higher recall means more false positives

---

## 📖 API Documentation

| Endpoint | Method | Description |
|---------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/model-info` | GET | Model details |
| `/predict` | POST | Single transaction prediction |
| `/batch-predict` | POST | Multiple predictions |

### Example Request:
```json
{
  "V1": -1.2, "V2": 0.5, "V3": -0.3,
  "V4": 1.5, "V5": -0.8, "V6": 0.2,
  ...
  "Amount": 150.00
}
```

### Example Response:
```json
{
  "prediction": 0,
  "prediction_label": "Legitimate",
  "fraud_probability": 0.023,
  "legitimate_probability": 0.977,
  "confidence": 0.977
}
```

---

## 📁 Project Structure

```
Credit-Card-Fraud/
├── api/
│   └── app.py              # Flask API
├── models/                 # Trained models (pkl files)
├── results/                # Evaluation charts
├── src/
│   ├── data_preprocessing.py
│   ├── model_training.py
│   ├── model_evaluation.py
│   ├── feature_analysis.py
│   └── main.py
├── creditcard.csv         # Dataset
├── requirements.txt       # Dependencies
├── .gitignore
└── README.md
```

---

## 🔧 Tech Stack

| Category | Technology |
|----------|------------|
| Language | Python 3.10+ |
| ML | Scikit-learn, XGBoost |
| Imbalance | Imbalanced-learn (SMOTE) |
| API | Flask |
| Visualization | Matplotlib, Seaborn |
| Deployment | Local/Cloud |

---

## 🔮 Future Enhancements

- [ ] Add Deep Learning (Autoencoders)
- [ ] Implement SHAP for model explainability
- [ ] Add Graph-based fraud detection
- [ ] Deploy on AWS/GCP
- [ ] Real-time streaming with Kafka

---

## 📝 License

This project is licensed under the MIT License.

---

## 🤝 Acknowledgments

- Dataset: [Kaggle Credit Card Fraud](https://www.kaggle.com/mlg-ulb/creditcardfraud)
- Inspired by real-world fraud detection systems

---

<div align="center">

**⭐ Star this repository if you found it helpful!**

</div>
