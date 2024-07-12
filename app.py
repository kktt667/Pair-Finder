import streamlit as st
import requests
import pandas as pd
import os
import hmac
import hashlib
import time

# Function to create the signature for Bybit API
def create_signature(secret, params):
    param_str = "&".join([f"{key}={value}" for key, value in sorted(params.items())])
    return hmac.new(secret.encode('utf-8'), param_str.encode('utf-8'), hashlib.sha256).hexdigest()

# Function to fetch market data from API
def make_df():
    url = "https://api.bybit.com/v5/market/tickers"
    
    # Retrieve API key and secret from environment variables
    api_key = os.getenv('BYBIT_API_KEY')
    api_secret = os.getenv('BYBIT_API_SECRET')
    
    if not api_key or not api_secret:
        st.error("API key or secret not found in environment variables.")
        return pd.DataFrame()
    
    params = {
        'category': 'linear',
        'timestamp': str(int(time.time() * 1000)),
    }
    
    params['sign'] = create_signature(api_secret, params)
    
    headers = {
        'Content-Type': 'application/json',
        'X-BYBIT-APIKEY': api_key
    }
    
    df = pd.DataFrame(columns=['Symbol', '24h Turnover', 'Last Price', 'Open Interest Value', 'Funding Rate', '24h High Price', '24h Low Price', '% Change Price'])
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        if 'ret_code' in data and data['ret_code'] == 0:
            tickers = data['result']
            
            rows = []
            for ticker in tickers:
                rows.append({
                    'Symbol': ticker['symbol'],
                    'Last Price': round(float(ticker['last_price']), 2),
                    '24h Turnover': round(float(ticker['turnover_24h']), 2),
                    'Open Interest Value': round(float(ticker['open_interest_value']), 2),
                    'Funding Rate': ticker['funding_rate'],
                    '24h High Price': round(float(ticker['high_price_24h']), 2),
                    '24h Low Price': round(float(ticker['low_price_24h']), 2),
                    '% Change Price': float(ticker['price_24h_pcnt']),
                })
            df = pd.DataFrame(rows)
        
        else:
            st.error(f"Error: {data.get('ret_msg', 'Unknown error')}")
    
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data: {e}")
    
    return df

# Function to filter DataFrame based on minimum volume
def filter_df(df, min_volume):
    if min_volume is None:
        st.warning("No minimum volume entered. Skipping filtering.")
        return df
    
    filtered_df = df[df['24h Turnover'] >= min_volume * 1_000_000]
    return filtered_df

# Function to run analysis based on selected checkboxes
def run_analysis(selected_symbols):
    st.write("Selected symbols:", selected_symbols)

# Streamlit app
def main():
    st.set_page_config(page_title="Pair Identifier", layout="wide")

    # Sidebar
    st.sidebar.title("Pair Identifier")
    st.sidebar.markdown("---")
    if st.sidebar.button("Home"):
        st.session_state['page'] = 'home'
    
    # Check if Volume Analysis button is clicked
    if st.sidebar.button("Volume Analysis"):
        st.session_state['page'] = 'volume_analysis'
    
    # Display the appropriate page
    if st.session_state.get('page') == 'volume_analysis':
        display_volume_analysis()
    else:
        display_welcome_page()

# Function to display volume analysis section
def display_volume_analysis():
    st.title("Volume Analysis")
    min_volume_million = st.number_input("Specify Volume Filter (in millions):", min_value=0.0, step=0.1, key='volume_input')
    
    if st.button("Apply Filter"):
        st.session_state['min_volume_million'] = min_volume_million
        st.session_state['filtered_data'] = filter_df(make_df(), min_volume_million)
    
    if 'filtered_data' in st.session_state:
        filtered_data = st.session_state['filtered_data']
        if not filtered_data.empty:
            select_all_option = 'Select All Symbols'
            symbols = filtered_data['Symbol'].tolist()
            selected_symbols = st.multiselect("Select Symbols for Analysis", [select_all_option] + symbols)
            
            if select_all_option in selected_symbols:
                selected_symbols = symbols

            st.dataframe(filtered_data)

            if st.button("Run Analysis"):
                run_analysis(selected_symbols)
        else:
            st.info("No tokens found with 24h turnover above the minimum volume.")

# Function to display welcome page
def display_welcome_page():
    st.title("Welcome to the Pair Identifier Tool")
    st.markdown("This tool helps you analyze trading pairs based on various metrics.")
    st.markdown("---")

# Main function to run the app
if __name__ == "__main__":
    main()
