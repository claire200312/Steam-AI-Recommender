import pandas as pd

try:
    df = pd.read_csv(r'c:\Users\clair\Desktop\Final Project\reviewdata\popgame.csv', encoding='cp949')
    print("Columns:", df.columns.tolist())
    print("\nFirst 3 rows:")
    print(df.head(3))
except Exception as e:
    print("Error with cp949:", e)
    try:
        df = pd.read_csv(r'c:\Users\clair\Desktop\Final Project\reviewdata\popgame.csv', encoding='utf-8')
        print("Columns:", df.columns.tolist())
        print("\nFirst 3 rows:")
        print(df.head(3))
    except Exception as e:
        print("Error with utf-8:", e)
