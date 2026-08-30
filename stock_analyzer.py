import pandas as pd
import yfinance as yf
import numpy as np

#settings
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)     
pd.set_option('display.width', None)
pd.set_option('display.expand_frame_repr', False)

    

#Funktionen 
def show_stock_overview(tickersymbol, period):
    info = yf.Ticker(tickersymbol).info
    pa = yf.Ticker(tickersymbol).history(period)
        
    df_info = pd.DataFrame([
        ['Name', info.get('longName', 'N/A')],
        ['Sector', info.get('sector', 'N/A')],
        ['Industry', info.get('industry', 'N/A')],
        ['Current value', f"${info.get('currentPrice', 0):.2f}"],
        ['Market Cap', f"${info.get('marketCap', 0):.2f}"],
        ['52 week high', f'${info.get("fiftyTwoWeekHigh",0):.2f}'],
        ['52 week low', f"${info.get('fiftyTwoWeekLow',0):.2f}"],
    ])


    if pa.empty:
        print(f'Unfortunately it is not possible to analyse {tickersymbol}. Please correct the tickersymbol.')
        return False 
    else:
        print(f'\n======= Overview about {tickersymbol} ========\n\n{df_info.to_string(header=False, index=False)}\n\n{pa.tail(20)}\n\n')
        return True


def rsi_calc(pa):
    print('\n\n==================== RSI ====================\n')
    print('RSI = 100 - 100 / (1 + (avg_gain / avg_loss))')
    print('Buy if RSI < 30, stock is oversold')
    print('Sell if RSI > 70, stock is overbought')
    rsi_period = int(input('Which RSI period (in days) should be used? '))
    
    daily_diff = pa['Close'].diff(1)
    gain = daily_diff.where(daily_diff > 0, 0)
    loss = daily_diff.where(daily_diff < 0, 0)
    
    avg_gain = gain.rolling(window=rsi_period).mean()
    avg_loss = (-1)*loss.rolling(window=rsi_period).mean()
    rsi = 100 - (100 / (1 + (avg_gain / avg_loss)))
    
    signal = rsi.apply(lambda x: 'buy' if x<30 else ('sell' if x>70 else '-'))
    
    df_rsi = pd.DataFrame({
        'Price': pa['Close'],
        f'RSI ({rsi_period}d)': rsi,
        'Signal': signal
        })
        
    rsi_only_signals = df_rsi[df_rsi['Signal'].isin(['buy','sell'])]
    
    return rsi, avg_gain, avg_loss, daily_diff, signal, df_rsi, rsi_only_signals, rsi_period


def macd_calc(pa):
    print("\n\n============ MACD Signals ============\n")
    print("MACD = small EMA - big EMA")
    print("Buy when MACD > Signal line")
    print("Sell when MACD < Signal line")
    
    period_ema_small = int(input("\nTime Period for small EMA in days: "))
    period_ema_big = int(input("Time Period for big EMA in days: "))
    period_ema_signal = int(input("Time Period for Signal EMA in days: "))
    
    ema_small = pa['Close'].ewm(span=period_ema_small).mean()
    ema_big = pa['Close'].ewm(span=period_ema_big).mean()
    macd = ema_small - ema_big
    ema_signal = macd.ewm(span=period_ema_signal).mean()
    
    macd_diff_crossunder = (ema_signal > macd) & (ema_signal.shift(1) < macd.shift(1))
    macd_diff_crossover = (ema_signal < macd) & (ema_signal.shift(1) > macd.shift(1))
    
    df_macd = pd.DataFrame({
        'Price': pa['Close'],
        'Small EMA': ema_small,
        'Big EMA': ema_big,
        'MACD': macd,
        'Signal EMA': ema_signal,
        'MACD crossunder': macd_diff_crossunder,
        'MACD crossover': macd_diff_crossover
        })
    
    df_macd['Signal'] = df_macd.apply(show_buy_sell_signals_macd, axis=1)
    df_macd_only_signals = df_macd[df_macd['Signal'].isin(['buy','sell'])]

    return ema_small, ema_big, ema_signal, macd, macd_diff_crossunder, macd_diff_crossover, df_macd, df_macd_only_signals


def show_buy_sell_signals_macd(df_macd):
    if df_macd['MACD crossunder']:
        return 'sell'
    elif df_macd['MACD crossover']:
        return 'buy'
    else:
        return '-'


def bb_calc(pa):
    print("\n\n=================================== Bollinger Bands ================================\n")
    std_dev = float(input('Which value should be used as standard deveation? '))
    middle_bb_period = int(input('Which time period (in days) should be used to calculate the middle Bollinger Band? '))
    
    middle_bb = pa['Close'].rolling(window=middle_bb_period).mean()
    applic_dev = pa['Close'].rolling(window=middle_bb_period).std()
    upper_bb = middle_bb + (std_dev * applic_dev)
    lower_bb = middle_bb - (std_dev * applic_dev)
    
    bb_signals = np.where(pa['Close'] >= upper_bb,'sell', np.where(pa['Close'] <= lower_bb,'buy','-'))
    df_bb = pd.DataFrame({
        'Price': pa['Close'],
        'Lower BB': lower_bb,
        'Middle BB': middle_bb,
        'Upper BB': upper_bb,
        'Signal': bb_signals
        })
    
    df_bb_only_signals = df_bb[df_bb['Signal'].isin(['buy','sell'])]
    
    return std_dev, applic_dev, middle_bb, upper_bb, lower_bb, bb_signals, df_bb, df_bb_only_signals


def df_signals_calc(pa, df_rsi, df_macd, df_bb):
    print('\n\n==================================  All indicators ===================================')
    df_all_signals = pd.DataFrame({
        'Price' : pa['Close'],
        'RSI signals' : df_rsi['Signal'],
        'MACD signals' : df_macd['Signal'],
        'BB signals' : df_bb['Signal']
        })
    
    df_only_signals = df_all_signals[
        (df_all_signals['RSI signals'].isin(['buy', 'sell'])) | 
        (df_all_signals['MACD signals'].isin(['buy', 'sell'])) | 
        (df_all_signals['BB signals'].isin(['buy', 'sell']))
    ]    
    return df_all_signals, df_only_signals


#mainprogramm
while True:

    tickersymbol = input("\nWhich stock should be researched? Please specify the ticker symbol, e.g. AAPL.\n").upper()
    period = input("Over what time period should the stock be researched, e.g. 1y, 3mo?\n")
    
    xyz = show_stock_overview(tickersymbol, period)

    
    if xyz is False:
        continue

    pa = yf.Ticker(tickersymbol).history(period)
    
    
    choice1 = input("\nWhich indicator should be used? (RSI, MACD, Bollinger Bands, All Indicators): ").upper()
    if choice1 not in ['RSI', 'MACD', 'BOLLINGER BANDS', 'ALL INDICATORS']:
        print("Invalid input. Please try again.")
        continue
    
    
    elif choice1 == 'RSI':
        rsi, avg_gain, avg_loss, daily_diff, signal, df_rsi, rsi_only_signals, rsi_period = rsi_calc(pa)

        print(f'\n{df_rsi.tail(50).to_string(col_space=15)}')
        
        choice1_1 = input('\nDo you just want to see the signals?(yes/no)').lower()
        if choice1_1 == 'yes':
            print(f'\n{rsi_only_signals}')
            
            
#             choice1_1_1 = input('\nDo you want to analyze the stock with all possible indicators?(yes/no)').lower()
#             if choice1_1_1 == 'yes':
#                 
#                 
#             else:
#                 continue

            
        else:
            continue

        continue
    
    
    elif choice1 == 'MACD':
        
        ema_small, ema_big, ema_signal, macd, macd_diff_crossunder, macd_diff_crossover, df_macd, df_macd_only_signals = macd_calc(pa)
        
        #df_macd['Signal'] = df_macd.apply(show_buy_sell_signals_macd, axis=1)
        print(f'\n{df_macd.tail(50).to_string(col_space=15)}')
        #df_macd_only_signals = df_macd[df_macd['Signal'].isin(['buy','sell'])]
        
        choice1_2 = input('\nDo you just want to see the signals?(yes/no)').lower()
        if choice1_2 == 'yes':
            print(f'\n{df_macd_only_signals.to_string(col_space=15)}')
                            
        
    elif choice1 == 'BOLLINGER BANDS':
        
        std_dev, applic_dev, middle_bb, upper_bb, lower_bb, bb_signals, df_bb, bb_only_signals = bb_calc(pa)
    
        print(f'\n{df_bb.tail(50).to_string(col_space=15)}')
        
        choice1_4 = input('Do you just want to see the signals?(yes/no)').lower()
        if choice1_4 == 'yes':
            print(f'{bb_only_signals.to_string()}')

        else:
            continue


    elif choice1 == 'ALL INDICATORS':
        rsi, avg_gain, avg_loss, daily_diff, signal, df_rsi, rsi_only_signals,rsi_period = rsi_calc(pa)
        ema_small, ema_big, ema_signal, macd, macd_diff_crossunder, macd_diff_crossover, df_macd, df_macd_only_signals = macd_calc(pa)
        std_dev, applic_dev, middle_bb, upper_bb, lower_bb, bb_signal, df_bb, df_bb_only_signals = bb_calc(pa)
        
        df_all_signals, df_only_signals = df_signals_calc(pa, df_rsi, df_macd, df_bb)
        
        #xyz = df_signals_calc(pa, rsi_only_signals, df_macd_only_signals, bb_only_signals)
        print(f'\n{df_only_signals}')
