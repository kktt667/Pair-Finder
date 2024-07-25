import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from concurrent.futures import ThreadPoolExecutor, as_completed

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

# Function to fetch kline data from API
def get_kline(token, interval, start_time):
    url = f"https://api.bybit.com/v5/market/kline?symbol={token}&interval={interval}&start={start_time}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data['retCode'] == 0:
            return data['result']['list']
        else:
            st.error(f"API Error: {data['retMsg']}")
            return []
    except requests.exceptions.RequestException as e:
        st.error(f"Request error for {token}: {e}")
        return []


# Function to calculate statistics
def calc_stats(token, interval, days, significance_level):
    start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
    st.write(f"Fetching kline data for token {token} from {start_time}")
    volume_data = get_kline(token, interval, start_time)
    
    if volume_data:
        df = pd.DataFrame(volume_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['open'] = df['open'].astype(float)
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)
        df.set_index('timestamp', inplace=True)
        
        st.write("DataFrame after conversion:")
        st.write(df.head())

        # Calculate % change in the price
        df['price_change'] = df['close'].pct_change() * 100
        
        st.write("Price changes:")
        st.write(df[['close', 'price_change']].head())

        significant_changes = df[df['price_change'].abs() >= significance_level].copy()
        st.write("Significant changes detected:")
        st.write(significant_changes[['price_change']].head())

        if not significant_changes.empty:
            significant_changes['previous_close'] = significant_changes['close'].shift(1)
            significant_changes = significant_changes.dropna(subset=['previous_close'])
            
            total_volumes = []
            for i in range(1, len(significant_changes)):
                start_time = significant_changes.index[i-1]
                end_time = significant_changes.index[i]
                total_volume = df.loc[start_time:end_time, 'volume'].sum()
                total_volumes.append(total_volume)
            
            significant_changes = significant_changes.iloc[1:]  # Drop the first row 
            significant_changes['total_volume'] = total_volumes
            
            st.write("Final significant changes with volumes:")
            st.write(significant_changes[['price_change', 'total_volume']])
            
            return significant_changes[['price_change', 'total_volume']]
        else:
            st.write("No significant price changes found.")
            return pd.DataFrame()
    else:
        st.write("No data returned from API.")
        return pd.DataFrame()


# Function to run analysis based on selected checkboxes
def run_analysis(selected_symbols, interval, days, significance_level):
    st.write("Selected symbols:", selected_symbols)
    for token in selected_symbols:
        st.subheader(f"Analysis for {token}")
        result_df = calc_stats(token, interval, days, significance_level)
        if not result_df.empty:
            st.dataframe(result_df)
        else:
            st.write(f"No significant price changes found for {token}")

def display_bottom_finder():
    st.title("Bottom Finder")

    # Parameters - default (add user accessibility on application)
    period = 21
    bblength = 50
    multiplier = 6
    lowerbound = 250
    percentilehigh = 0.99
    percentilelow = 1.01
    flip = False
    highs_not_lows = False
    str = 3
    ltLB = 45
    mtLB = 20

# Get the ticker names
    def get_tickers():
        url = "https://api.bybit.com/v5/market/tickers?category=linear"
        ticker_names = []
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if 'result' in data and 'list' in data['result']:
                tickers = data['result']['list']
                for ticker in tickers:
                    symbol = ticker['symbol']
                    ticker_names.append(symbol)
            else:
                st.error("Error: Data structure is not as expected.")
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching data: {e}")
        return ticker_names

    def get_data(ticker, interval, limit=1000):
        url = f"https://api.bybit.com/v5/market/kline?symbol={ticker}&interval={interval}&limit={limit}"
        
        try:
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('retCode') == 0:
                    result = data.get('result', {})
                    data_list = result.get('list', [])
                    if data_list:
                        df = pd.DataFrame(data_list, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                        df.set_index('timestamp', inplace=True)
                        df = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
                        return df
                    else:
                        st.warning(f"No data available for ticker {ticker}")
                else:
                    st.error(f"API response error for ticker {ticker}: {data.get('retMsg')}")
            else:
                st.error(f"Failed to fetch data for {ticker}: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            st.error(f"Request exception for ticker {ticker}: {e}")
        
        return pd.DataFrame()

    def williams_vix_fix(data, pd=period, bbl=bblength, mult=multiplier, lb=lowerbound, ph=percentilehigh, pl=percentilelow, flip=flip, highs_not_lows=highs_not_lows):
        if highs_not_lows:
            wvf = ((data['close'].rolling(window=pd).min() - data['high']) / data['close'].rolling(window=pd).min()) * 100
        else:
            wvf = ((data['close'].rolling(window=pd).max() - data['low']) / data['close'].rolling(window=pd).max()) * 100
        
        sDev = mult * wvf.rolling(window=bbl).std()
        midLine = wvf.rolling(window=bbl).mean()
        lowerBand = midLine - sDev
        upperBand = midLine + sDev
        rangeHigh = (wvf.rolling(window=lb).max() * pl) if highs_not_lows else (wvf.rolling(window=lb).max() * ph)
        rangeLow = (wvf.rolling(window=lb).min() * ph) if highs_not_lows else (wvf.rolling(window=lb).min() * pl)
        
        if flip:
            wvf *= -1
            lowerBand *= -1
            upperBand *= -1
            rangeHigh *= -1
            rangeLow *= -1

        return wvf.round(2), lowerBand.round(2), upperBand.round(2), rangeHigh.round(2), rangeLow.round(2)

    def calculate_criteria(data, wvf, lowerBand, upperBand, rangeHigh, rangeLow, str=str, ltLB=ltLB, mtLB=mtLB):
        upRange = (data['low'] > data['low'].shift(1)) & (data['close'] > data['high'].shift(1))
        upRange_Aggr = (data['close'] > data['close'].shift(1)) & (data['close'] > data['open'])
        
        dnRange = (data['high'] < data['high'].shift(1)) & (data['close'] < data['low'].shift(1))
        dnRange_Aggr = (data['close'] < data['close'].shift(1)) & (data['close'] < data['open'])
        
        bFiltered = ((wvf.shift(1) >= upperBand.shift(1)) | (wvf.shift(1) >= rangeHigh.shift(1))) & (wvf < upperBand) & (wvf < rangeHigh)
        bFiltered_Aggr = ((wvf.shift(1) >= upperBand.shift(1)) | (wvf.shift(1) >= rangeHigh.shift(1))) & ~((wvf < upperBand) & (wvf < rangeHigh))
        
        alert1 = (wvf >= upperBand) | (wvf >= rangeHigh)
        alert2 = bFiltered
        alert3 = ((~highs_not_lows & upRange & (data['close'] > data['close'].shift(str)) & 
                ((data['close'] < data['close'].shift(ltLB)) | (data['close'] < data['close'].shift(mtLB))) & bFiltered) | 
                (highs_not_lows & dnRange & (data['close'] < data['close'].shift(str)) & 
                ((data['close'] > data['close'].shift(ltLB)) | (data['close'] > data['close'].shift(mtLB))) & bFiltered))
        alert4 = ((~highs_not_lows & upRange_Aggr & (data['close'] > data['close'].shift(str)) & 
                ((data['close'] < data['close'].shift(ltLB)) | (data['close'] < data['close'].shift(mtLB))) & bFiltered_Aggr) | 
                (highs_not_lows & dnRange_Aggr & (data['close'] < data['close'].shift(str)) & 
                ((data['close'] > data['close'].shift(ltLB)) | (data['close'] > data['close'].shift(mtLB))) & bFiltered_Aggr))
        
        return alert1, alert2, alert3, alert4

    def process_ticker(ticker, interval, start_date):
        data = get_data(ticker, interval)
        
        if not data.empty:
            wvf, lowerBand, upperBand, rangeHigh, rangeLow = williams_vix_fix(data)
            data['wvf'] = wvf
            data['lowerBand'] = lowerBand
            data['upperBand'] = upperBand
            data['rangeHigh'] = rangeHigh
            data['rangeLow'] = rangeLow

            alert1, alert2, alert3, alert4 = calculate_criteria(data, wvf, lowerBand, upperBand, rangeHigh, rangeLow)
            data['alert1'] = alert1
            data['alert2'] = alert2
            data['alert3'] = alert3
            data['alert4'] = alert4

            recent_data = data.loc[data.index >= start_date]
            
            if recent_data[['alert1', 'alert2', 'alert3', 'alert4']].any().any():
                return {
                    'ticker': ticker,
                    'data': recent_data
                }
        return None

    def plot_signals(data, ticker):
        fig = make_subplots(rows=1, cols=1, shared_xaxes=True, vertical_spacing=0.01, row_heights=[1.0], specs=[[{"secondary_y": True}]])

        # Add candles + trace
        fig.add_trace(go.Candlestick(x=data.index, open=data['open'], high=data['high'], low=data['low'], close=data['close'], name='Price Candles', increasing_line_color='darkgreen', decreasing_line_color='red'), row=1, col=1)

        # Add buy signals
        buy_signals = data[data['alert1'] | data['alert2'] | data['alert3'] | data['alert4']]
        fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['low'], mode='markers', marker=dict(color='lime', size=10, symbol='triangle-up'), name='Buy Signals'), row=1, col=1)

        # Update layout
        fig.update_layout(title=f"Bottom Finder - {ticker}", xaxis_title="Date", yaxis_title="Price", xaxis_rangeslider_visible=False)

        st.plotly_chart(fig)

    # Streamlit
    
    # User inputs
    interval = st.selectbox("Select Time Frame", ['1', '5', '15', '30', '60', '240', 'D', 'W'], index=5)
    days_back = st.number_input("Number of Days to Check", min_value=1, value=7)

    # Session state for keeping track of analysis results and selected symbol
    if 'signals' not in st.session_state:
        st.session_state.signals = []
    if 'selected_symbol' not in st.session_state:
        st.session_state.selected_symbol = None

    # Add a Run button
    run_button = st.button("Run Analysis")

    if run_button:
        tickers = get_tickers()
        signals = []
        today = datetime.now()
        start_date = today - timedelta(days=days_back)
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_ticker, ticker, interval, start_date) for ticker in tickers]
            for future in as_completed(futures):
                result = future.result()
                if result:
                    signals.append(result)
        
        # Update session state with results on the main thread
        st.session_state.signals = signals

    if st.session_state.signals:
        def calculate_percentage_change(df):
            if len(df) < 2:
                return 0
            prev_close = df['close'].iloc[-2]
            curr_close = df['close'].iloc[-1]
            return ((curr_close - prev_close) / prev_close) * 100

        signals_df = pd.DataFrame([{
            'Symbol': signal['ticker'],
            'Open': signal['data']['open'].iloc[-1],
            'High': signal['data']['high'].iloc[-1],
            'Low': signal['data']['low'].iloc[-1],
            'Close': signal['data']['close'].iloc[-1],
            'Volume': signal['data']['volume'].iloc[-1],
            '% Change': calculate_percentage_change(signal['data'])
        } for signal in st.session_state.signals])
        
        # Styling the DataFrame
        styled_df = signals_df.style.set_table_styles(
            [{'selector': 'th', 'props': [('font-size', '16px'), ('text-align', 'center'), ('color', '#6d6d6d')]},
            {'selector': 'td', 'props': [('font-size', '14px'), ('text-align', 'center')]}]
        )
        st.dataframe(styled_df)

        # Select only ticker symbols for the dropdown
        ticker_symbols = [signal['ticker'] for signal in st.session_state.signals]
        selected_symbol = st.selectbox("Select a symbol to view the chart", ticker_symbols, index=ticker_symbols.index(st.session_state.selected_symbol) if st.session_state.selected_symbol in ticker_symbols else 0)

        if selected_symbol:
            st.session_state.selected_symbol = selected_symbol
            data = get_data(selected_symbol, interval)
            if not data.empty:
                wvf, lowerBand, upperBand, rangeHigh, rangeLow = williams_vix_fix(data)
                data['wvf'] = wvf
                data['lowerBand'] = lowerBand
                data['upperBand'] = upperBand
                data['rangeHigh'] = rangeHigh
                data['rangeLow'] = rangeLow
                alert1, alert2, alert3, alert4 = calculate_criteria(data, wvf, lowerBand, upperBand, rangeHigh, rangeLow)
                data['alert1'] = alert1
                data['alert2'] = alert2
                data['alert3'] = alert3
                data['alert4'] = alert4
                plot_signals(data, selected_symbol)
    else:
        st.write("--")





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

    # Check if Bottom Finder button is clicked
    if st.sidebar.button("Bottom Finder"):
        st.session_state['page'] = 'bottom_finder'

    # Display the appropriate page
    if st.session_state.get('page') == 'volume_analysis':
        display_volume_analysis()
    elif st.session_state.get('page') == 'bottom_finder':
        display_bottom_finder()
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

            interval = st.selectbox("Select Interval", ["1m", "5m", "15m", "30m", "1h", "4h", "1d"], index=4)
            days = st.slider("Select number of days for historical data", 1, 365, 90)
            significance_level = st.slider("Select significance level (%)", 0.1, 10.0, 2.0)

            if st.button("Run Analysis"):
                run_analysis(selected_symbols, interval, days, significance_level)
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
