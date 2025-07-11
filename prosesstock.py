import pandas as pd
import sys
import os

# --- KONFIGURASI ---
# Ganti tulisan di dalam tanda kutip (') sesuai dengan nama kolom di file Anda.
# Perhatikan huruf besar/kecil dan spasi.
NAMA_KOLOM_HARGA_BELI = 'harga1'  # Contoh: 'Harga Beli', 'harga_pokok'
NAMA_KOLOM_HARGA_JUAL = 'harga2'  # Contoh: 'Harga Jual', 'hargajual'
# -----------------

def proses_update_harga(path_input):
    """
    Fungsi untuk membaca file, mencari harga jual yang nol,
    dan mengisinya dengan harga beli + 100,000.
    """
    try:
        bersih_path = path_input.strip().strip('"')
        if not os.path.exists(bersih_path):
            print(f"❌ File tidak ditemukan di '{bersih_path}'.")
            return

        nama_file, ekstensi = os.path.splitext(bersih_path)
        if ekstensi.lower() == '.csv':
            df = pd.read_csv(bersih_path)
        elif ekstensi.lower() in ['.xls', '.xlsx']:
            df = pd.read_excel(bersih_path)
        else:
            print(f"❌ Format file '{ekstensi}' tidak didukung. Harap gunakan .csv atau .xlsx.")
            return

        # Menggunakan nama kolom dari konfigurasi
        kondisi = (df[NAMA_KOLOM_HARGA_JUAL].isna()) | (df[NAMA_KOLOM_HARGA_JUAL] == 0)
        jumlah_update = kondisi.sum()

        if jumlah_update > 0:
            print(f"✅ Ditemukan {jumlah_update} produk untuk diupdate.")
            
            # Update harga jual = harga beli + 100000
            df.loc[kondisi, NAMA_KOLOM_HARGA_JUAL] = df.loc[kondisi, NAMA_KOLOM_HARGA_BELI] + 100000
            
            path_output = f"{nama_file}_updated{ekstensi}"
            
            if ekstensi.lower() == '.csv':
                df.to_csv(path_output, index=False, encoding='utf-8-sig')
            else:
                df.to_excel(path_output, index=False)
                
            print(f"🚀 Sukses! Data baru disimpan di: '{os.path.basename(path_output)}'")
        else:
            print("👍 Tidak ada data yang perlu diupdate.")

    except KeyError as e:
        print(f"❌ Error: Kolom {e} tidak ditemukan.")
        print("💡 Pastikan nama kolom di bagian KONFIGURASI skrip sudah sesuai dengan nama kolom di file Anda.")
    except Exception as e:
        print(f"❌ Terjadi kesalahan: {e}")

# --- Program Utama ---
if __name__ == "__main__":
    if len(sys.argv) > 1:
        proses_update_harga(sys.argv[1])
    else:
        print("--- Program Update Harga Interaktif ---")
        while True:
            print("\nSilakan seret file (drag & drop) ke jendela ini, lalu tekan Enter.")
            path_file = input(f"File akan diproses dengan kolom: '{NAMA_KOLOM_HARGA_BELI}' dan '{NAMA_KOLOM_HARGA_JUAL}'\n(Ketik 'keluar' untuk berhenti): ")

            if path_file.lower() == 'keluar':
                break
            if path_file:
                proses_update_harga(path_file)
            else:
                print("Tidak ada input. Coba lagi.")

    print("\nProgram selesai.")