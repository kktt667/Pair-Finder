import streamlit as st
import requests
import pandas as pd
import hashlib
import hmac
import time
import os

# Function to create the signature for Bybit API
def create_signature(secret, params):
    param_str = "&".join([f"{key}={value}" for key, value in sorted(params.items())])
    return hmac.new(secret.encode('utf-8'), param_str.encode('utf-8'), hashlib.sha256).hexdigest()

# Class to manage API requests and rate limits
class BybitAPI:
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.rate_limit = 50  # Example: Bybit allows 50 requests per minute
        self.rate_limit_period = 60  # Example: Bybit rate limit period in seconds
        self.last_request_time = 0
        self.request_count = 0

    def request(self, endpoint, params=None):
        self._check_rate_limit()
        
        # Make API request using requests library or similar
        response = requests.get(endpoint, params=params)
        
        # Update rate limit counters
        self.last_request_time = time.time()
        self.request_count += 1
        
        return response

    def _check_rate_limit(self):
        current_time = time.time()
        
        if current_time - self.last_request_time > self.rate_limit_period:
            # Reset counters if rate limit period has passed
            self.last_request_time = current_time
            self.request_count = 0
        
        if self.request_count >= self.rate_limit:
            # Handle rate limit exceeded scenario, wait or implement backoff
            time_to_wait = self.last_request_time + self.rate_limit_period - current_time
            time.sleep(max(0, time_to_wait))
            self._check_rate_limit()  # Recursively check again after waiting

# Function to fetch market data from Bybit API
def make_df(api_key, api_secret):
    url = "https://api.bybit.com/v5/market/tickers"
    
    params = {
        'category': 'linear',
        'api_key': api_key,
        'timestamp': str(int(time.time() * 1000)),
    }
    
    params['sign'] = create_signature(api_secret, params)
    
    try:
        bybit_api = BybitAPI(api_key, api_secret)
        response = bybit_api.request(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if 'result' in data and 'list' in data['result']:
            tickers = data['result']['list']
            
            df = pd.DataFrame(columns=['Symbol', '24h Turnover', 'Last Price', 'Open Interest Value', 'Funding Rate', '24h High Price', '24h Low Price', '% Change Price'])
            
            for ticker in tickers:
                symbol = ticker['symbol']
                last_price = float(ticker['lastPrice'])
                turnover_24h = float(ticker['turnover24h'])
                OI_val = float(ticker['openInterestValue'])
                FR = ticker['fundingRate']
                high = float(ticker['highPrice24h'])
                low = float(ticker['lowPrice24h'])
                pcp = float(ticker['price24hPcnt'])
                
                df = df.append({
                    'Symbol': symbol,
                    'Last Price': round(last_price, 2),
                    '24h Turnover': round(turnover_24h, 2),
                    'Open Interest Value': round(OI_val, 2),
                    'Funding Rate': FR,
                    '24h High Price': round(high, 2),
                    '24h Low Price': round(low, 2),
                    '% Change Price': pcp,
                }, ignore_index=True)
            
            return df
        
        else:
            st.error("Error: Data structure is not as expected.")
            return pd.DataFrame()
    
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

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
        api_key = os.getenv('BYBIT_API_KEY')
        api_secret = os.getenv('BYBIT_API_SECRET')
        st.session_state['filtered_data'] = filter_df(make_df(api_key, api_secret), min_volume_million)
    
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
