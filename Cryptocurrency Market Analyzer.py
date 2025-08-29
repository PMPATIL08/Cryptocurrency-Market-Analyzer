from binance.client import Client
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
import time
import os

#Binance API credentials
api_key = 'your api key from binance'
api_secret = 'your api secert key from binance'

#Initialize client
client = Client(api_key, api_secret)

#Create output directory
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_dir = f"crypto_analysis_{timestamp}"
os.makedirs(output_dir, exist_ok=True)

#Get top USDT pairs by volume
exchange_info = client.get_exchange_info()
symbols = [s['symbol'] for s in exchange_info['symbols']
           if s['status'] == 'TRADING' and s['symbol'].endswith('USDT')]

ticker_info = client.get_ticker()
volume_dict = {item['symbol']: float(item['quoteVolume']) for item in ticker_info if item['symbol'] in symbols}
sorted_symbols = sorted(volume_dict.items(), key=lambda x: x[1], reverse=True)
top_symbols = [s[0] for s in sorted_symbols[:400]]

#Fetching candle data
def fetch_candle(symbol):
    try:
        candles = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_1HOUR, limit=1)
        if candles:
            ohlcv = candles[0]
            return {
                'Symbol': symbol,
                'Time': pd.to_datetime(ohlcv[0], unit='ms'),
                'Open': float(ohlcv[1]),
                'High': float(ohlcv[2]),
                'Low': float(ohlcv[3]),
                'Close': float(ohlcv[4]),
                'Volume': float(ohlcv[5])
            }
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
    return None

#Multithreaded data fetching
all_data = []
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(fetch_candle, symbol) for symbol in top_symbols]
    for future in as_completed(futures):
        result = future.result()
        if result:
            all_data.append(result)
        time.sleep(0.05)  # Avoid rate limits

#Creating DataFrame
df = pd.DataFrame(all_data)

# Calculations
df['Percentage Change'] = ((df['Close'] - df['Open']) / df['Open']) * 100
df['High-Low % Spread'] = ((df['High'] - df['Low']) / df['Low']) * 100
df['Close/Open Ratio'] = df['Close'] / df['Open']
df['Volume (USDT)'] = df['Volume'] * df['Close']

#Sorting top gainers/losers
top_10_gainers = df.sort_values(by='Percentage Change', ascending=False).head(10)
top_10_losers = df.sort_values(by='Percentage Change', ascending=True).head(10)
sudden_movers = df[abs(df['Percentage Change']) > 3]

#Save CSVs
df.to_csv(os.path.join(output_dir, "all_data.csv"), index=False)
top_10_gainers.to_csv(os.path.join(output_dir, "top_10_gainers.csv"), index=False)
top_10_losers.to_csv(os.path.join(output_dir, "top_10_losers.csv"), index=False)
if not sudden_movers.empty:
    sudden_movers.to_csv(os.path.join(output_dir, "sudden_movers.csv"), index=False)

#Styling the seaborn
sns.set(style='whitegrid', palette='muted', font_scale=1.1)

# Save plots to PDF
pdf_path = os.path.join(output_dir, f"crypto_report_{timestamp}.pdf")
with PdfPages(pdf_path) as pdf:

    # Plot 1: Top Gainers
    plt.figure(figsize=(12, 6))
    sns.barplot(data=top_10_gainers, x='Symbol', y='Percentage Change', palette='Greens_r')
    plt.title('Top 10 Crypto Gainers (Last 1 Hour)')
    plt.ylabel('Percentage Change (%)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    pdf.savefig()
    plt.close()

    # Plot 2: Top Losers
    plt.figure(figsize=(12, 6))
    sns.barplot(data=top_10_losers, x='Symbol', y='Percentage Change', palette='Reds')
    plt.title('Top 10 Crypto Losers (Last 1 Hour)')
    plt.ylabel('Percentage Change (%)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    pdf.savefig()
    plt.close()

    # Plot 3: Spread in Gainers
    plt.figure(figsize=(12, 6))
    sns.barplot(data=top_10_gainers, x='Symbol', y='High-Low % Spread', palette='Blues')
    plt.title('Volatility Spread (High - Low %) - Top Gainers')
    plt.ylabel('High-Low % Spread')
    plt.xticks(rotation=45)
    plt.tight_layout()
    pdf.savefig()
    plt.close()

    # Plot 4: Volume in Gainers
    plt.figure(figsize=(12, 6))
    sns.barplot(data=top_10_gainers, x='Symbol', y='Volume (USDT)', palette='Purples')
    plt.title('Volume (USDT) - Top Gainers')
    plt.ylabel('Volume in USDT')
    plt.xticks(rotation=45)
    plt.tight_layout()
    pdf.savefig()
    plt.close()

    # Plot 5: Sudden Movers
    if not sudden_movers.empty:
        plt.figure(figsize=(12, 6))
        sns.barplot(data=sudden_movers, x='Symbol', y='Percentage Change', palette='coolwarm')
        plt.title('Sudden Movers (>|3%| change)')
        plt.ylabel('Percentage Change (%)')
        plt.xticks(rotation=45)
        plt.tight_layout()
        pdf.savefig()
        plt.close()

print(f"\n Analysis complete. Files saved in: {output_dir}")
