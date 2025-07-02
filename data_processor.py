import pandas as pd
from datetime import datetime

print("Memulai proses pengolahan data dari file dbodytech.xlsx...")

try:
    file_path = 'dbodytech.xlsx'
    df_stock_raw = pd.read_excel(file_path, sheet_name='Stock', dtype={'Kode': str})
    df_trans_raw = pd.read_excel(file_path, sheet_name='Transj2', dtype={'KODE': str})
    print("Berhasil membaca sheet 'Stock' dan 'Transj2'.")
except Exception as e:
    print(f"Error saat membaca file Excel: {e}")
    exit()

print("Menyesuaikan nama kolom dan membersihkan data...")

stock_df = df_stock_raw.rename(columns={'Kode': 'kode', 'Nama': 'nama', 'Harga1': 'harga1', 'Harga2': 'harga2', 'QTY': 'qty'})
stock_df.dropna(subset=['kode', 'nama'], inplace=True)
stock_df['kode'] = stock_df['kode'].str.strip()
stock_df = stock_df[['kode', 'nama', 'harga1', 'harga2', 'qty']].copy()
stock_df.drop_duplicates(subset=['kode'], keep='first', inplace=True)

trans_df = df_trans_raw.rename(columns={'TGL': 'date', 'REGNO': 'regno_old', 'KODE': 'kode', 'QTY': 'qty_sold'})
trans_df.dropna(subset=['date', 'kode', 'qty_sold'], inplace=True)
trans_df['kode'] = trans_df['kode'].str.strip()
trans_df['date'] = pd.to_datetime(trans_df['date'], errors='coerce')
trans_df.dropna(subset=['date'], inplace=True)

print("Menghitung stok akhir...")
sales_summary = trans_df.groupby('kode')['qty_sold'].sum().reset_index()
stock_final = pd.merge(stock_df, sales_summary, on='kode', how='left')
stock_final['qty_sold'] = stock_final['qty_sold'].fillna(0)
stock_final['qty'] = stock_final['qty'] - stock_final['qty_sold']
stock_final.drop(columns=['qty_sold'], inplace=True)

print("Membuat nomor nota baru yang urut...")
trans_df.sort_values(by=['date', 'regno_old'], inplace=True)
start_number = 1
current_date_str = datetime.now().strftime('%y%m%d')
trans_df['regno'] = [f"N{current_date_str}{i:04d}" for i in range(start_number, len(trans_df) + start_number)]
trans_df.rename(columns={'qty_sold': 'qty'}, inplace=True)

print("Menggabungkan data transaksi dengan detail barang...")
orders_final = pd.merge(trans_df, stock_final[['kode', 'nama', 'harga1', 'harga2']], on='kode', how='left')
orders_final['jumlah'] = orders_final['qty'] * orders_final['harga2']
orders_final['nama'].fillna('BARANG TIDAK DIKENAL', inplace=True)
orders_final[['harga1', 'harga2', 'jumlah']] = orders_final[['harga1', 'harga2', 'jumlah']].fillna(0)

orders_seed = orders_final[['date', 'regno', 'kode', 'nama', 'qty', 'harga1', 'harga2', 'jumlah']]
orders_seed.to_csv('orders_seed.csv', index=False, date_format='%Y-%m-%d')
print(f"Berhasil membuat 'orders_seed.csv' dengan {len(orders_seed)} baris.")

stock_seed = stock_final[['kode', 'nama', 'harga1', 'harga2', 'qty']]
stock_seed.to_csv('stock_seed.csv', index=False)
print(f"Berhasil membuat 'stock_seed.csv' dengan {len(stock_seed)} baris.")

print("\nProses selesai!")