import pandas as pd
import requests
import json

df = pd.read_csv('creditcard.csv')

legit_samples = df[df['Class'] == 0].sample(3, random_state=42)
fraud_samples = df[df['Class'] == 1].sample(3, random_state=42)

url = "http://localhost:5000/predict"

def test_transaction(name, row):
    features = {f'V{i}': round(row[f'V{i}'], 6) for i in range(1, 29)}
    features['Amount'] = round(row['Amount'], 2)
    
    response = requests.post(url, json=features)
    result = response.json()
    
    print(f"\n{name}:")
    print(f"  Amount: ${row['Amount']:.2f}")
    print(f"  Actual: {'Fraud' if row['Class'] == 1 else 'Legitimate'}")
    print(f"  Prediction: {result.get('prediction_label', 'ERROR')}")
    print(f"  Fraud Probability: {result.get('fraud_probability', 0):.4f}")

print("="*50)
print("LEGITIMATE TESTS")
print("="*50)
for idx, (_, row) in enumerate(legit_samples.iterrows()):
    test_transaction(f"Test Legitimate {idx+1}", row)

print("\n" + "="*50)
print("FRAUD TESTS")
print("="*50)
for idx, (_, row) in enumerate(fraud_samples.iterrows()):
    test_transaction(f"Test Fraud {idx+1}", row)
