import streamlit as st
import pandas as pd
import numpy as np
import xgboost as xgb
import pickle
import json
import os
import shap
import matplotlib.pyplot as plt
import seaborn as sns

# --- Layout and Configuration ---
st.set_page_config(page_title="Customer Churn Dashboard", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    .high-risk { color: #d32f2f; font-weight: bold; font-size: 1.2rem; }
    .medium-risk { color: #f57c00; font-weight: bold; font-size: 1.2rem; }
    .low-risk { color: #388e3c; font-weight: bold; font-size: 1.2rem; }
    .kpi-card { background-color: #f8f9fa; padding: 20px; border-radius: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); text-align: center; color: #000000; }
    .kpi-value { font-size: 2rem; font-weight: bold; color: #1f77b4; }
    .profile-card { background-color: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #e0e0e0; color: #000000; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

st.title("📈 Telecom Customer Churn Dashboard")

# --- Load Assets ---
@st.cache_resource
def load_assets():
    if not os.path.exists('xgboost_model.pkl') or not os.path.exists('preprocessor.pkl'):
        return None, None, None, None
    
    with open('xgboost_model.pkl', 'rb') as f:
        model = pickle.load(f)
    with open('preprocessor.pkl', 'rb') as f:
        preprocessor = pickle.load(f)
        
    try:
        with open('expected_columns.json', 'r') as f:
            expected_columns = json.load(f)
    except:
        expected_columns = []
        
    try:
        processed_customers = pd.read_csv('processed_customers.csv')
    except:
        processed_customers = pd.DataFrame()
        
    return model, preprocessor, expected_columns, processed_customers

model, preprocessor, expected_columns, processed_customers = load_assets()

if model is None:
    st.error("⚠️ Model or Preprocessor not found. Please run `python train_model.py` first.")
    st.stop()

# --- Preprocessing Function ---
def preprocess_data(df_raw, preprocessor_dict):
    df = df_raw.copy()
    
    # Drop irrelevant columns
    drop_cols = ['Customer ID','Total Refunds','Zip Code','Latitude', 'Longitude','Churn Category', 'Churn Reason']
    if 'Customer Status' in df.columns:
        drop_cols.append('Customer Status')
    if 'Customer_Status' in df.columns:
        drop_cols.append('Customer_Status')
        
    df = df.drop(columns=[col for col in drop_cols if col in df.columns], errors='ignore')
    
    pd.set_option('future.no_silent_downcasting', True)
    if 'Gender' in df.columns:
        df = df.replace({"Gender": {'Female': 0, 'Male': 1}}).infer_objects(copy=False)
        
    df = df.replace({'No': 0, 'Yes': 1}).infer_objects(copy=False)
    
    if 'Phone Service' in df.columns:
        df = df.replace({"Phone Service": {'Yes': 1, 'No': 0}}).infer_objects(copy=False)
        
    cat_cols = preprocessor_dict['cat_cols']
    df = pd.get_dummies(data=df, columns=[c for c in cat_cols if c in df.columns])
    
    model_columns = preprocessor_dict['model_columns']
    for c in model_columns:
        if c not in df.columns:
            df[c] = 0
            
    df = df[model_columns]
    
    cols_to_scale = preprocessor_dict['cols_to_scale']
    scaler = preprocessor_dict['scaler']
    
    # Fill NAs to avoid scaler errors on raw uploaded data
    df[cols_to_scale] = df[cols_to_scale].fillna(0)
    df[cols_to_scale] = scaler.transform(df[cols_to_scale])
    
    return df

def get_retention_action(top_features, customer_data):
    actions = []
    for feat in top_features:
        if 'Contract_Month-to-month' in feat and customer_data.get('Contract') == 'Month-to-month':
            actions.append("Customer is on a month-to-month contract. Consider offering a discounted annual plan.")
        elif 'Tenure in Months' in feat and customer_data.get('Tenure in Months', 100) < 12:
            actions.append("Customer is new (low tenure). Send a welcome gift or satisfaction survey.")
        elif 'Monthly Charge' in feat:
            actions.append("High monthly charges detected. Review plan to see if a more cost-effective bundle applies.")
        elif 'Internet Type_Fiber optic' in feat and customer_data.get('Internet Type') == 'Fiber Optic':
            actions.append("Fiber optic customer at risk. Check for local service outages or offer a complimentary speed boost.")
        elif 'Premium Tech Support' in feat and customer_data.get('Premium Tech Support') == 'No':
            actions.append("Lacks premium tech support. Offer a free 3-month trial of technical support.")
            
    if not actions:
        actions.append("Reach out with a general satisfaction check-in and promotional discount.")
    
    return actions[0] # Return the most relevant rule

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["👤 Select Existing Customer", "📁 Upload New Data", "📊 Custom Visualizations"])

# ==========================================
# MODE A: SELECT EXISTING CUSTOMER
# ==========================================
with tab1:
    if processed_customers.empty or 'Customer ID' not in processed_customers.columns:
        st.warning("Processed customers data not available. Please ensure `processed_customers.csv` exists and contains 'Customer ID'.")
    else:
        st.sidebar.header("👤 Select Customer")
        customer_ids = processed_customers['Customer ID'].dropna().unique()
        selected_id = st.sidebar.selectbox("Search or Select Customer ID", customer_ids)
        
        if selected_id:
            # Get raw customer data
            cust_raw = processed_customers[processed_customers['Customer ID'] == selected_id].iloc[0]
            cust_df = processed_customers[processed_customers['Customer ID'] == selected_id].copy()
            
            # Preprocess for model
            cust_features = preprocess_data(cust_df, preprocessor)
            
            # Predict
            # XGBoost multi:softprob returns probability for each class.
            # Classes are alphabetically sorted by LabelEncoder: 0='Churned', 1='Joined', 2='Stayed'
            probas = model.predict_proba(cust_features)[0]
            churn_prob = probas[0]
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.subheader("Customer Profile")
                profile_html = f"""
                <div class="profile-card">
                    <p><b>Customer ID:</b> {selected_id}</p>
                    <p><b>Tenure:</b> {cust_raw.get('Tenure in Months', 'N/A')} Months</p>
                    <p><b>Contract Type:</b> {cust_raw.get('Contract', 'N/A')}</p>
                    <p><b>Monthly Charges:</b> ${cust_raw.get('Monthly Charge', 'N/A')}</p>
                    <p><b>Internet Type:</b> {cust_raw.get('Internet Type', 'N/A')}</p>
                    <p><b>City:</b> {cust_raw.get('City', 'N/A')}</p>
                </div>
                """
                st.markdown(profile_html, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                st.subheader("Churn Probability")
                if churn_prob > 0.7:
                    st.markdown(f'<div class="high-risk">CRITICAL RISK: {churn_prob:.1%}</div>', unsafe_allow_html=True)
                elif churn_prob > 0.4:
                    st.markdown(f'<div class="medium-risk">MODERATE RISK: {churn_prob:.1%}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="low-risk">LOW RISK: {churn_prob:.1%}</div>', unsafe_allow_html=True)
                    
            with col2:
                st.subheader("Top Risk Factors (SHAP)")
                
                # Compute SHAP values for this specific customer
                explainer = shap.TreeExplainer(model)
                shap_values = explainer.shap_values(cust_features)
                
                # Extract SHAP values robustly regardless of SHAP/XGBoost version
                if isinstance(shap_values, list):
                    churn_shap = shap_values[0]
                else:
                    churn_shap = shap_values
                    
                churn_shap = np.array(churn_shap)
                
                # Handle different array shapes
                if churn_shap.ndim == 3: # shape: (1, n_features, n_classes)
                    churn_shap = churn_shap[0, :, 0]
                elif churn_shap.ndim == 2:
                    if churn_shap.shape[0] == 1: # shape: (1, n_features)
                        churn_shap = churn_shap[0, :]
                    else: # shape: (n_features, n_classes)
                        churn_shap = churn_shap[:, 0]
                        
                feature_names = cust_features.columns
                churn_shap = churn_shap.ravel()[:len(feature_names)]
                
                # Combine feature names and their shap values
                shap_df = pd.DataFrame({
                    'Feature': feature_names,
                    'SHAP Value': churn_shap
                })
                
                # Filter to top 5 positive drivers of churn
                top_shap = shap_df.sort_values(by='SHAP Value', ascending=False).head(5)
                
                fig, ax = plt.subplots(figsize=(8, 4))
                ax.barh(top_shap['Feature'][::-1], top_shap['SHAP Value'][::-1], color='#d32f2f')
                ax.set_xlabel("Impact on Churn Probability")
                ax.set_title("Top 5 Features Driving Churn")
                st.pyplot(fig)
                
                # Suggested Action
                st.subheader("💡 Suggested Retention Action")
                action = get_retention_action(top_shap['Feature'].tolist(), cust_raw.to_dict())
                st.info(action)

# ==========================================
# MODE B: UPLOAD NEW DATA
# ==========================================
with tab2:
    st.header("Upload New Data for Batch Prediction")
    st.markdown("Upload a CSV or Excel file containing customer data. The file must match the original raw dataset schema.")
    
    uploaded_file = st.file_uploader("Upload File", type=["csv", "xlsx"])
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                new_data = pd.read_csv(uploaded_file)
            else:
                new_data = pd.read_excel(uploaded_file)
                
            st.subheader("Data Preview")
            st.dataframe(new_data.head())
            
            # Validation
            missing_cols = [c for c in expected_columns if c not in new_data.columns and c not in ['Customer Status', 'Customer_Status']]
            if missing_cols:
                st.error("### ❌ Schema Validation Failed")
                st.write("Your uploaded file is missing the following required columns:")
                for col in missing_cols:
                    st.write(f"- `{col}`")
                st.stop()
                
            st.success("Schema validation passed. Generating predictions...")
            
            # Predict
            features = preprocess_data(new_data, preprocessor)
            probas = model.predict_proba(features)
            churn_probs = probas[:, 0] # Class 0 is 'Churned'
            
            results_df = new_data.copy()
            results_df['Churn Probability'] = churn_probs
            
            def assign_risk(prob):
                if prob > 0.7: return "High"
                elif prob > 0.4: return "Medium"
                else: return "Low"
                
            results_df['Risk Level'] = results_df['Churn Probability'].apply(assign_risk)
            
            # KPIs
            total_customers = len(results_df)
            high_risk_count = len(results_df[results_df['Risk Level'] == 'High'])
            churn_pct = (high_risk_count / total_customers) * 100 if total_customers > 0 else 0
            
            kpi1, kpi2, kpi3 = st.columns(3)
            with kpi1:
                st.markdown(f'<div class="kpi-card"><h3 style="color: #000000;">Total Customers</h3><div class="kpi-value">{total_customers}</div></div>', unsafe_allow_html=True)
            with kpi2:
                st.markdown(f'<div class="kpi-card"><h3 style="color: #000000;">High Risk Count</h3><div class="kpi-value" style="color: #d32f2f;">{high_risk_count}</div></div>', unsafe_allow_html=True)
            with kpi3:
                st.markdown(f'<div class="kpi-card"><h3 style="color: #000000;">High Risk %</h3><div class="kpi-value">{churn_pct:.1f}%</div></div>', unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Filter and Table
            st.subheader("Prediction Results")
            risk_filter = st.multiselect("Filter by Risk Level", ["High", "Medium", "Low"], default=["High", "Medium", "Low"])
            
            filtered_df = results_df[results_df['Risk Level'].isin(risk_filter)]
            
            # Move probability and risk level to front for visibility
            cols = ['Churn Probability', 'Risk Level'] + [c for c in filtered_df.columns if c not in ['Churn Probability', 'Risk Level']]
            filtered_df = filtered_df[cols]
            
            st.dataframe(filtered_df.sort_values(by='Churn Probability', ascending=False))
            
            # Download
            csv = results_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Full Predictions as CSV",
                data=csv,
                file_name="batch_churn_predictions.csv",
                mime="text/csv",
            )
            
        except Exception as e:
            st.error(f"An error occurred while processing the file: {str(e)}")

# ==========================================
# MODE C: CUSTOM VISUALIZATIONS
# ==========================================
with tab3:
    st.header("📊 Interactive Visualizations")
    st.markdown("Explore your dataset by creating custom interactive charts.")
    
    # Choose dataset
    vis_data = processed_customers
    if uploaded_file is not None and 'new_data' in locals():
        use_uploaded = st.checkbox("Use uploaded data instead of default dataset", value=True)
        if use_uploaded:
            vis_data = new_data
            
    if vis_data.empty:
        st.warning("No data available for visualization. Please ensure 'processed_customers.csv' exists or upload a new file.")
    else:
        col_type, col_x, col_y = st.columns(3)
        with col_type:
            chart_type = st.selectbox("Select Chart Type", ["Bar Graph", "Histogram", "Line Graph", "Scatter Plot"])
        with col_x:
            x_col = st.selectbox("Select X-Axis Feature", vis_data.columns, index=0)
        with col_y:
            y_col = st.selectbox("Select Y-Axis Feature (Numeric)", vis_data.columns, index=min(1, len(vis_data.columns)-1))
            
        st.markdown("---")
        
        try:
            fig, ax = plt.subplots(figsize=(10, 5))
            
            if chart_type == "Bar Graph":
                st.subheader(f"Average of {y_col} by {x_col}")
                # Group by X and take mean of Y, sort by value to show the highest
                agg_data = vis_data.groupby(x_col)[y_col].mean().dropna().sort_values(ascending=False).head(20)
                ax.bar(agg_data.index.astype(str), agg_data.values, color='#1f77b4')
                ax.set_xlabel(x_col)
                ax.set_ylabel(f"Average {y_col}")
                plt.xticks(rotation=45, ha='right')
                st.pyplot(fig)
                
            elif chart_type == "Histogram":
                st.subheader(f"Distribution of {x_col}")
                # If numeric, use standard histogram
                if pd.api.types.is_numeric_dtype(vis_data[x_col]):
                    sns.histplot(vis_data[x_col].dropna(), kde=True, color='#ff7f0e', ax=ax)
                else:
                    # If categorical, show top 15 most frequent categories
                    top_cats = vis_data[x_col].value_counts().head(15)
                    sns.barplot(x=top_cats.index.astype(str), y=top_cats.values, color='#ff7f0e', ax=ax)
                    ax.set_title(f"Top 15 Most Frequent {x_col}")
                
                ax.set_xlabel(x_col)
                ax.set_ylabel("Frequency")
                plt.xticks(rotation=45, ha='right')
                st.pyplot(fig)
                
            elif chart_type == "Line Graph":
                st.subheader(f"Trend of {y_col} over {x_col}")
                # For line graphs, sort index if numeric, otherwise it's just categories
                if pd.api.types.is_numeric_dtype(vis_data[x_col]):
                    agg_data = vis_data.groupby(x_col)[y_col].mean().dropna().sort_index()
                else:
                    agg_data = vis_data.groupby(x_col)[y_col].mean().dropna().head(20)
                ax.plot(agg_data.index.astype(str), agg_data.values, marker='o', color='#2ca02c', linewidth=2)
                ax.set_xlabel(x_col)
                ax.set_ylabel(f"Average {y_col}")
                plt.xticks(rotation=45, ha='right')
                ax.grid(True, linestyle='--', alpha=0.7)
                st.pyplot(fig)
                
            elif chart_type == "Scatter Plot":
                st.subheader(f"Relationship between {x_col} and {y_col}")
                sns.scatterplot(data=vis_data, x=x_col, y=y_col, alpha=0.6, color='#d62728', ax=ax)
                ax.set_xlabel(x_col)
                ax.set_ylabel(y_col)
                st.pyplot(fig)
                
        except Exception as e:
            st.error(f"⚠️ Could not generate a {chart_type} for the selected columns.")
            st.info("Tip: Bar Graphs, Line Graphs, and Scatter Plots require the Y-Axis to be a numeric column (like Total Charges or Tenure).")
