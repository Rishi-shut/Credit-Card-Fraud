import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import os


class DataPreprocessor:
    def __init__(self, data_path='creditcard.csv'):
        self.data_path = data_path
        self.df = None
        self.X = None
        self.y = None
        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None
        self.scaler = StandardScaler()
        
    def load_data(self):
        """Load the credit card fraud dataset"""
        print(f"Loading data from {self.data_path}...")
        self.df = pd.read_csv(self.data_path)
        print(f"Dataset shape: {self.df.shape}")
        print(f"Columns: {list(self.df.columns)}")
        return self.df
    
    def explore_data(self):
        """Perform exploratory data analysis"""
        print("\n=== Data Exploration ===")
        print(f"Shape: {self.df.shape}")
        print(f"\nData types:\n{self.df.dtypes}")
        print(f"\nMissing values:\n{self.df.isnull().sum().sum()}")
        print(f"\nClass distribution:")
        print(self.df['Class'].value_counts())
        print(f"\nFraud percentage: {self.df['Class'].mean()*100:.2f}%")
        print(f"\nStatistical summary:")
        print(self.df.describe())
        
    def handle_missing_values(self):
        """Remove any null values"""
        before = len(self.df)
        self.df = self.df.dropna()
        after = len(self.df)
        if before != after:
            print(f"Removed {before - after} rows with missing values")
        return self.df
    
    def preprocess(self, test_size=0.2, random_state=42):
        """Preprocess the data: separate features and target, scale Amount"""
        print("\n=== Preprocessing ===")
        
        self.X = self.df.drop(['Class', 'Time'], axis=1)
        self.y = self.df['Class']
        
        self.X['Amount'] = self.scaler.fit_transform(self.X['Amount'].values.reshape(-1, 1))
        
        print(f"Features shape: {self.X.shape}")
        print(f"Target shape: {self.y.shape}")
        
        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            self.X, self.y, 
            test_size=test_size, 
            random_state=random_state, 
            stratify=self.y
        )
        
        print(f"Training set: {self.X_train.shape[0]} samples")
        print(f"Test set: {self.X_test.shape[0]} samples")
        print(f"Training fraud rate: {self.y_train.mean()*100:.2f}%")
        print(f"Test fraud rate: {self.y_test.mean()*100:.2f}%")
        
        return self.X_train, self.X_test, self.y_train, self.y_test
    
    def get_processed_data(self):
        """Return preprocessed data"""
        return self.X_train, self.X_test, self.y_train, self.y_test


if __name__ == "__main__":
    preprocessor = DataPreprocessor()
    preprocessor.load_data()
    preprocessor.explore_data()
    preprocessor.handle_missing_values()
    preprocessor.preprocess()
    print("\nPreprocessing complete!")
