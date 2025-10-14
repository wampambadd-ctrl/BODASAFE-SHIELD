import streamlit as st
import requests
import joblib
import xgboost as xgb
import numpy as np
from datetime import datetime, timedelta
import os # Keep os import, but change usage

# Set up page config for a wider, better look
st.set_page_config(layout="wide")
st.title("🛡️ BodaSafe Shield Quote Tool")
st.markdown("Calculate the estimated monthly insurance premium based on location and daily usage.")

# --- 1. Model Loading ---
# @st.cache_resource to load the model only once when the app starts.
# Significantly improves performance and reduces memory usage.
@st.cache_resource
def load_model():
    # Assuming 'python_gbm_model.pkl' is located in the current working directory.
    model_path = 'python_gbm_model.pkl'
    
    try:
        # Load the model directly using the filename
        gbm = joblib.load(model_path)
        return gbm
    except FileNotFoundError:
        # This error handles the case where the file is missing in the CWD
        st.error(f"Deployment Error: Model file not found at '{model_path}'. "
                 "Please ensure 'python_gbm_model.pkl' is present in the same directory as your application file.")
        return None
    except Exception as e:
        st.error(f"Error loading model: {e}")
        return None

gbm = load_model()

# --- 2. Inputs ---
st.sidebar.header("Quote Parameters")

lat= st.sidebar.number_input("Latitude (e.g., Kampala: 0.3476):", value=0.3476, format="%.4f", key="lat_input")
lon = st.sidebar.number_input("Longitude (e.g., Kampala: 32.5825):", value=32.5825, format="%.4f", key="lon_input")
# Note: You can change st.sidebar.slider to st.sidebar.number_input if you prefer direct input over a slider
hours = st.sidebar.slider("Daily Hours of Operation:", 1, 12, 8, key="hours_slider")
# --- 3. Feature Definition (CRUCIAL FIX) ---
# The model expects 13 features in this exact order due to one-hot encoding used during training.
EXPECTED_FEATURES = [
    'risk_trigger', 'month_1', 'month_2', 'month_3', 'month_4', 
    'month_5', 'month_6', 'month_7', 'month_8', 'month_9', 
    'month_10', 'month_11', 'month_12'
]


# --- 4. Calculation Logic ---
if st.sidebar.button("Get Quote",key = "qoute button") and gbm is not None:
    # Spinner for a better user experience during the API call
    with st.spinner("Fetching forecast and calculating premium..."):
        try:
            # 4.1. Fetch Tomorrow's Forecast (API call)
            url = "https://api.open-meteo.com/v1/forecast"
            
            params = {
                "latitude": lat, 
                "longitude": lon, 
                "daily": "precipitation_sum",
                "timezone": "auto",
                "forecast_days": 1 # Get data for tomorrow, which often appears at index 0
            }
            
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status() # Check for bad HTTP status codes
            data = resp.json()
            
            # Fetch precipitation sum for the next forecast day
            precip = data['daily']['precipitation_sum'][0]
            
            # 4.2. Determine Rain Trigger (1 if precipitation > 10mm)
            trigger = 1 if precip > 10 else 0
            
            # 4.3. Get Month Feature (Tomorrow's month)
            tomorrow = datetime.now() + timedelta(days=1)
            month = tomorrow.month 

            # 4.4. Predict Frequency & Calculate Premium (FIXED SECTION)
            
            # Initialize the feature array to all zeros (13 elements)
            feature_array = [0] * len(EXPECTED_FEATURES)
            
            # 1. Set the risk_trigger (first element, index 0)
            feature_array[0] = trigger
            
            # 2. Set the one-hot encoded month (index 1 to 12)
            if 1 <= month <= 12:
                # feature_array[0] is 'risk_trigger'. Month features start at index 1.
                feature_array[month] = 1 
            
            # Convert the list to a DMatrix for prediction
            dnew = xgb.DMatrix(np.array([feature_array]))
            
            # CRITICAL FIX: Explicitly assign feature names to the DMatrix
            # This satisfies the requirement from the trained model.
            dnew.feature_names = EXPECTED_FEATURES
            
            # Predict the accident frequency
            pred_freq = gbm.predict(dnew)[0]
            
            # Calculate Monthly Premium: Frequency * Daily_Hours * Rate_Per_Hour_Day * Days_in_Month
            # Assuming 3000 UGX is the daily rate per hour of operation
            premium = pred_freq * hours * 3000 * 30 
            
            # Display Results
            st.success(f"Estimated Monthly Premium: **UGX {round(premium):,}**")
            
            st.info(f"**Risk Factors Used:**\n"
                    f"- **Tomorrow's Expected Rain:** {precip:.2f} mm (Risk Trigger: {'YES' if trigger == 1 else 'NO'})\n"
                    f"- **Operational Hours:** {hours} hours/day\n"
                    f"- **Month of Year:** {tomorrow.strftime('%B')} ({month})"
            )
            
            st.balloons()

        except requests.exceptions.RequestException as e:
            st.error(f"Connection Error: Failed to fetch weather data. Details: {e}")
        except KeyError:
            st.error("Error: Could not parse weather response. Check latitude/longitude accuracy or API data structure.")
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")

# --- 5. Context ---
st.markdown("---")
st.caption("Data provided by Open-Meteo. Prediction based on proprietary BodaSafe risk model.")

