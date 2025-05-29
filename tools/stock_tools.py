# # tools/stock_tools.py
# import yfinance as yf

# def get_stock_info(ticker: str) -> str:

#     if not ticker.endswith('.NS') and not ticker.endswith('.BO') and not '.' in ticker:
#         ticker += '.NS'
#     stock = yf.Ticker(ticker)
#     info = stock.info
#     return f"""
#     Ticker: {ticker}
#     Name: {info.get('longName', 'N/A')}
#     Sector: {info.get('sector', 'N/A')}
#     Market Cap: {info.get('marketCap', 'N/A')}
#     52 Week High: {info.get('fiftyTwoWeekHigh', 'N/A')}
#     52 Week Low: {info.get('fiftyTwoWeekLow', 'N/A')}
#     PE Ratio: {info.get('trailingPE', 'N/A')}
#     """

# def get_recent_trends(ticker: str, days=int(5)) -> str:
#     if not ticker.endswith('.NS') and not ticker.endswith('.BO') and not '.' in ticker:
#         ticker += '.NS'

#     stock = yf.Ticker(ticker)
#     hist = stock.history(period="6mo")
#     if hist.empty:
#         return "No historical data available."
#     recent_close = hist['Close'][-days:]
#     trend = "upward" if recent_close[-1] > recent_close[0] else "downward"
#     return f"The stock has shown a {trend} trend over the last {days} days:\n{recent_close.to_string()}"




 # ALPHA VANTAGE API based stock analysis tool

import requests
import os
import pandas as pd
from datetime import datetime, timedelta

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "MJFO0QR6XRDSDTMT")

def get_stock_info(ticker: str) -> str:
    # Ensure ticker has .BO (BSE) or .NS (NSE) suffix
    if not ticker.endswith('.NS') and not ticker.endswith('.BO'):
        ticker += '.BO'  # Default to BSE
    
    # Get company overview (fundamental data)
    overview_url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}"
    overview = requests.get(overview_url).json()
    
    # Get latest price data
    quote_url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}"
    quote = requests.get(quote_url).json().get('Global Quote', {})
    
    return f"""
    Ticker: {ticker}
    Name: {overview.get('01. symbol', 'N/A')}
    Sector: {overview.get('Sector', 'N/A')}
    Market Cap: {overview.get('MarketCapitalization', 'N/A')}
    Current Price: {quote.get('05. price', 'N/A')}
    52 Week High: {overview.get('03. high', 'N/A')}
    52 Week Low: {overview.get('04. low', 'N/A')}
    PE Ratio: {overview.get('PERatio', 'N/A')}
    """

def get_recent_trends(ticker: str, days: int = 5) -> str:
    if not ticker.endswith('.NS') and not ticker.endswith('.BO'):
        ticker += '.BO'  # Default to BSE
    
    # Get daily time series (last 30 days)
    timeseries_url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}&outputsize=compact"
    data = requests.get(timeseries_url).json()
    
    # Process time series data
    time_series = data.get('Time Series (Daily)', {})
    if not time_series:
        return "No historical data available."
    
    # Convert to DataFrame
    df = pd.DataFrame.from_dict(time_series, orient='index')
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    df['4. close'] = df['4. close'].astype(float)
    
    # Get last N days
    recent_data = df['4. close'].tail(days)
    
    # Determine trend
    trend = "upward" if recent_data[-1] > recent_data[0] else "downward"
    
    return f"The stock has shown a {trend} trend over the last {days} days:\n{recent_data.to_string()}"


