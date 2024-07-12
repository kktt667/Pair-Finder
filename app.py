import streamlit as st
import requests
import pandas as pd

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