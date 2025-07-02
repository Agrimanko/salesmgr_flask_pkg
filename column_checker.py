import pandas as pd

print("Membaca nama kolom dari file 'dbodytech.xlsx'...\n")

try:
    file_path = 'dbodytech.xlsx'

    # Baca sheet 'Stock' dan cetak kolomnya
    df_stock = pd.read_excel(file_path, sheet_name='Stock')
    print("--- Nama Kolom di Sheet 'Stock' ---")
    print(df_stock.columns.tolist())
    print("-------------------------------------")

    # Baca sheet 'Transj2' dan cetak kolomnya
    df_trans = pd.read_excel(file_path, sheet_name='Transj2')
    print("\n--- Nama Kolom di Sheet 'Transj2' ---")
    print(df_trans.columns.tolist())
    print("--------------------------------------")

except FileNotFoundError:
    print(f"Error: File '{file_path}' tidak ditemukan. Pastikan file tersebut ada di folder yang sama.")
except Exception as e:
    print(f"Terjadi error saat membaca file: {e}")