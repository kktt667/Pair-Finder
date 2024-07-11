import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# Function to fetch market data from API
def make_df():
    url = "https://api.bybit.com/v5/market/tickers?category=linear"
    df = pd.DataFrame(columns=['Symbol', '24h Turnover', 'Last Price', 'Open Interest Value', 'Funding Rate', '24h High Price', '24h Low Price', '% Change Price'])
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if 'result' in data and 'list' in data['result']:
            tickers = data['result']['list']
            
            for ticker in tickers:
                symbol = ticker['symbol']
                last_price = float(ticker['lastPrice'])
                turnover_24h = float(ticker['turnover24h'])
                OI_val = float(ticker['openInterestValue'])
                FR = ticker['fundingRate']
                high = float(ticker['highPrice24h'])
                low = float(ticker['lowPrice24h'])
                pcp = float(ticker['price24hPcnt'])
                
                df = df._append({
                    'Symbol': symbol,
                    'Last Price': round(last_price, 2),
                    '24h Turnover': round(turnover_24h, 2),
                    'Open Interest Value': round(OI_val, 2),
                    'Funding Rate': FR,
                    '24h High Price': round(high, 2),
                    '24h Low Price': round(low, 2),
                    '% Change Price': pcp,
                }, ignore_index=True)
        
        else:
            st.error("Error: Data structure is not as expected.")
    
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
def run_analysis(df, selected_symbols):
    st.write("Selected symbols:", selected_symbols)

# Streamlit app
def main():
    st.title("Pair Identifier")

    min_volume_million = st.number_input("Specify Volume Filter (in millions):", min_value=0.0, step=0.1)

    if st.button("GO"):
        market_data = make_df()
        filtered_data = filter_df(market_data, min_volume_million)
        
        if not filtered_data.empty:
            selected_symbols = st.multiselect("Select Symbols for Analysis", filtered_data['Symbol'])
            
            st.dataframe(filtered_data)

            if st.button("Run Analysis"):
                run_analysis(filtered_data, selected_symbols)
        else:
            st.info("No tokens found with 24h turnover above the minimum volume.")

if __name__ == "__main__":
    main()
