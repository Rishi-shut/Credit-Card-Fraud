import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
from sklearn.preprocessing import StandardScaler

# Load data
print("Loading data...")
df = pd.read_csv('creditcard.csv')

# Load model
xgb_model = joblib.load('models/xgboost.pkl')
rf_model = joblib.load('models/random_forest.pkl')

# Feature names
feature_names = [f'V{i}' for i in range(1, 29)] + ['Amount']

# ============================================
# 1. Feature Importance from XGBoost
# ============================================
print("\n" + "="*60)
print("FEATURE IMPORTANCE (XGBoost)")
print("="*60)

xgb_importance = xgb_model.feature_importances_
importance_df = pd.DataFrame({
    'Feature': feature_names,
    'Importance': xgb_importance
}).sort_values('Importance', ascending=False)

print("\nTop 10 Most Important Features:")
print(importance_df.head(10).to_string(index=False))

# ============================================
# 2. Plot Feature Importance
# ============================================
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# XGBoost Feature Importance
ax1 = axes[0, 0]
top_15 = importance_df.head(15)
colors = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, 15))
ax1.barh(top_15['Feature'], top_15['Importance'], color=colors)
ax1.set_xlabel('Importance')
ax1.set_title('XGBoost Feature Importance (Top 15)')
ax1.invert_yaxis()

# Random Forest Feature Importance
ax2 = axes[0, 1]
rf_importance = rf_model.feature_importances_
rf_imp_df = pd.DataFrame({
    'Feature': feature_names,
    'Importance': rf_importance
}).sort_values('Importance', ascending=False).head(15)
ax2.barh(rf_imp_df['Feature'], rf_imp_df['Importance'], color='forestgreen')
ax2.set_xlabel('Importance')
ax2.set_title('Random Forest Feature Importance (Top 15)')
ax2.invert_yaxis()

# ============================================
# 3. Feature Distribution: Legitimate vs Fraud
# ============================================
print("\n" + "="*60)
print("FEATURE DISTRIBUTION ANALYSIS")
print("="*60)

# Top 4 important features
top_features = ['V14', 'V17', 'V12', 'V10']

for i, feat in enumerate(top_features):
    ax = axes[1, i // 2] if i < 2 else axes[1, i - 2]
    
    legitimate = df[df['Class'] == 0][feat]
    fraud = df[df['Class'] == 1][feat]
    
    ax.hist(legitimate, bins=50, alpha=0.6, label='Legitimate', color='blue', density=True)
    ax.hist(fraud, bins=50, alpha=0.6, label='Fraud', color='red', density=True)
    ax.set_xlabel(feat)
    ax.set_ylabel('Density')
    ax.set_title(f'{feat} Distribution by Class')
    ax.legend()

plt.tight_layout()
plt.savefig('results/feature_analysis.png', dpi=150, bbox_inches='tight')
print("\nFeature analysis saved to results/feature_analysis.png")

# ============================================
# 4. Amount Distribution
# ============================================
fig2, axes2 = plt.subplots(1, 2, figsize=(14, 5))

# All transactions
ax1 = axes2[0]
ax1.hist(df[df['Class'] == 0]['Amount'], bins=50, alpha=0.7, label='Legitimate', color='blue')
ax1.hist(df[df['Class'] == 1]['Amount'], bins=50, alpha=0.7, label='Fraud', color='red')
ax1.set_xlabel('Amount ($)')
ax1.set_ylabel('Frequency')
ax1.set_title('Amount Distribution by Class (Full Range)')
ax1.legend()

# Zoomed in (under $500)
ax2 = axes2[1]
df_under_500 = df[df['Amount'] < 500]
ax2.hist(df_under_500[df_under_500['Class'] == 0]['Amount'], bins=50, alpha=0.7, label='Legitimate', color='blue')
ax2.hist(df_under_500[df_under_500['Class'] == 1]['Amount'], bins=50, alpha=0.7, label='Fraud', color='red')
ax2.set_xlabel('Amount ($)')
ax2.set_ylabel('Frequency')
ax2.set_title('Amount Distribution (Under $500)')
ax2.legend()

plt.tight_layout()
plt.savefig('results/amount_analysis.png', dpi=150, bbox_inches='tight')
print("Amount analysis saved to results/amount_analysis.png")

# ============================================
# 5. Statistical Summary by Class
# ============================================
print("\n" + "="*60)
print("STATISTICAL SUMMARY: LEGITIMATE vs FRAUD")
print("="*60)

print("\n--- Amount Statistics ---")
print("Legitimate:")
print(f"  Mean: ${df[df['Class']==0]['Amount'].mean():.2f}")
print(f"  Median: ${df[df['Class']==0]['Amount'].median():.2f}")
print(f"  Max: ${df[df['Class']==0]['Amount'].max():.2f}")

print("\nFraud:")
print(f"  Mean: ${df[df['Class']==1]['Amount'].mean():.2f}")
print(f"  Median: ${df[df['Class']==1]['Amount'].median():.2f}")
print(f"  Max: ${df[df['Class']==1]['Amount'].max():.2f}")

# Top feature stats
print("\n--- V14 Statistics (Most Important) ---")
print("Legitimate:")
print(f"  Mean: {df[df['Class']==0]['V14'].mean():.4f}")
print(f"  Std: {df[df['Class']==0]['V14'].std():.4f}")

print("\nFraud:")
print(f"  Mean: {df[df['Class']==1]['V14'].mean():.4f}")
print(f"  Std: {df[df['Class']==1]['V14'].std():.4f}")

# ============================================
# 6. Correlation Heatmap
# ============================================
fig3, ax = plt.subplots(figsize=(12, 10))
corr_matrix = df[feature_names].corr()
sns.heatmap(corr_matrix, cmap='coolwarm', center=0, 
            xticklabels=5, yticklabels=5, ax=ax)
ax.set_title('Feature Correlation Matrix')
plt.tight_layout()
plt.savefig('results/correlation_matrix.png', dpi=150, bbox_inches='tight')
print("Correlation matrix saved to results/correlation_matrix.png")

# ============================================
# 7. Box Plots for Top Features
# ============================================
fig4, axes4 = plt.subplots(2, 4, figsize=(16, 8))
top_8 = ['V14', 'V17', 'V12', 'V10', 'V4', 'V3', 'V2', 'V1']

for i, feat in enumerate(top_8):
    ax = axes4[i // 4, i % 4]
    df_plot = df.copy()
    df_plot['Class'] = df_plot['Class'].map({0: 'Legitimate', 1: 'Fraud'})
    df_plot.boxplot(column=feat, by='Class', ax=ax)
    ax.set_title(f'{feat} by Class')
    ax.set_xlabel('')

plt.suptitle('Top 8 Feature Box Plots by Class', fontsize=14)
plt.tight_layout()
plt.savefig('results/boxplots.png', dpi=150, bbox_inches='tight')
print("Box plots saved to results/boxplots.png")

print("\n" + "="*60)
print("ANALYSIS COMPLETE!")
print("="*60)
print("\nGenerated files in results/:")
print("  - feature_analysis.png")
print("  - amount_analysis.png")
print("  - correlation_matrix.png")
print("  - boxplots.png")
