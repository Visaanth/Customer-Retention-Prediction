import pandas as pd
import numpy as np
import xgboost as xgb
import pickle
import json
import os
from sklearn.preprocessing import LabelEncoder, MinMaxScaler

def train_and_save_model():
    data_path = 'e:/Customer-Churn-Prediction/Datasets/telecom_customer_churn.csv'
    if not os.path.exists(data_path):
        data_path = 'telecom_customer_churn.csv'
        
    print(f"Loading data from {data_path}...")
    df = pd.read_csv(data_path)
    
    # Save the expected raw columns (features) for validation
    raw_cols = list(df.columns)
    with open('expected_columns.json', 'w') as f:
        json.dump(raw_cols, f)
    
    # Drop irrelevant columns for training, BUT we want to keep Customer ID for processed_customers.csv
    drop_cols = ['Total Refunds','Zip Code','Latitude', 'Longitude','Churn Category', 'Churn Reason']
    df = df.drop(columns=[col for col in drop_cols if col in df.columns], errors='ignore')
    
    # Drop NA
    df.dropna(inplace=True)
    
    # Rename target
    if 'Customer Status' in df.columns:
        df = df.rename(columns={'Customer Status':'Customer_Status'})
        
    # Save processed_customers.csv for Mode A display
    df.to_csv('processed_customers.csv', index=False)
    
    # Now separate Customer ID for training
    if 'Customer ID' in df.columns:
        df1 = df.drop(columns=['Customer ID'])
    else:
        df1 = df.copy()
        
    pd.set_option('future.no_silent_downcasting', True)
    
    # Binary Replacements
    if 'Gender' in df1.columns:
        df1 = df1.replace({"Gender": {'Female': 0, 'Male': 1}}).infer_objects(copy=False)
        
    df1 = df1.replace({'No': 0, 'Yes': 1}).infer_objects(copy=False)
    
    if 'Phone Service' in df1.columns:
        df1 = df1.replace({"Phone Service": {'Yes': 1, 'No': 0}}).infer_objects(copy=False)
        
    # Label Encode Target
    le = LabelEncoder()
    if 'Customer_Status' in df1.columns:
        df1['Customer_Status'] = le.fit_transform(df1['Customer_Status'])
    
    # Dummies
    cat_cols = ['Payment Method','Contract','Internet Type','Offer','City']
    df1 = pd.get_dummies(data=df1, columns=[col for col in cat_cols if col in df1.columns])
    
    # Scaling
    cols_to_scale = ['Age','Number of Dependents','Number of Referrals','Tenure in Months',
                     'Avg Monthly Long Distance Charges','Avg Monthly GB Download','Monthly Charge',
                     'Total Charges', 'Total Extra Data Charges', 'Total Long Distance Charges','Total Revenue']
    
    scaler = MinMaxScaler()
    df1[cols_to_scale] = scaler.fit_transform(df1[cols_to_scale])
    
    X = df1.drop('Customer_Status', axis='columns', errors='ignore')
    if 'Customer_Status' in df1.columns:
        y = df1['Customer_Status']
    else:
        y = None
    
    # Save training columns for future use
    model_columns = list(X.columns)
    
    print("Training XGBoost Classifier...")
    model = xgb.XGBClassifier(objective='multi:softprob', random_state=42)
    if y is not None:
        model.fit(X, y)
    
    print("Saving model and preprocessors...")
    with open('xgboost_model.pkl', 'wb') as f:
        pickle.dump(model, f)
        
    # Save the preprocessor components
    preprocessor = {
        'scaler': scaler,
        'label_encoder': le,
        'model_columns': model_columns,
        'cols_to_scale': cols_to_scale,
        'cat_cols': cat_cols
    }
    with open('preprocessor.pkl', 'wb') as f:
        pickle.dump(preprocessor, f)
        
    print("Done! Artifacts saved.")

if __name__ == "__main__":
    train_and_save_model()
