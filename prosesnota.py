import re
import sys
import os

def proses_file(path_input):
    """
    Fungsi untuk memproses file nota sesuai aturan yang ditentukan.
    """
    # Membuat nama file output secara otomatis
    nama_folder, nama_file_lengkap = os.path.split(path_input)
    nama_file, ekstensi_file = os.path.splitext(nama_file_lengkap)
    path_output = os.path.join(nama_folder, f"{nama_file}_final{ekstensi_file}")

    try:
        # Membuka file input untuk dibaca dan file output untuk ditulis
        with open(path_input, 'r', encoding='utf-8') as f_in, open(path_output, 'w', encoding='utf-8') as f_out:
            print(f"Membaca file: '{nama_file_lengkap}'...")
            
            for line in f_in:
                line = line.strip()
                if not line:
                    f_out.write('\n')
                    continue

                new_line = line
                # Periksa apakah baris diawali dengan angka
                if line and line[0].isdigit():
                    # Jika diawali angka tapi bukan '0', tambahkan '0' di depan
                    if not line.startswith('0'):
                        new_line = '0' + line
                else:
                    # Jika diawali huruf, cari angka di dalamnya
                    match = re.search(r'\d+', line)
                    if match:
                        number_str = match.group(0)
                        # Jika angka yang ditemukan tidak diawali '0', perbaiki
                        if not number_str.startswith('0'):
                            # Ganti hanya kemunculan pertama dari angka tersebut
                            new_line = line.replace(number_str, '0' + number_str, 1)
                
                f_out.write(new_line + '\n')
        
        print(f"✅ Berhasil! File hasil koreksi telah disimpan sebagai '{os.path.basename(path_output)}'")

    except Exception as e:
        print(f"❌ Terjadi error: {e}")


# Program Utama
if __name__ == "__main__":
    # Cek apakah file diseret ke skrip (ada argumen baris perintah)
    if len(sys.argv) > 1:
        # Gunakan path file dari argumen pertama yang diberikan
        file_path_input = sys.argv[1]
        if os.path.exists(file_path_input):
            proses_file(file_path_input)
        else:
            print(f"❌ Error: File yang Anda seret tidak ditemukan di path: {file_path_input}")
    else:
        # Jika tidak ada file yang diseret, coba cari file default
        print("💡 Tips: Anda bisa langsung drag & drop file .txt ke ikon skrip ini untuk memprosesnya.")
        default_file = 'nomor_nota.txt'
        if os.path.exists(default_file):
            print(f"Mencoba memproses file default '{default_file}'...")
            proses_file(default_file)
        else:
            print(f"❌ File '{default_file}' tidak ditemukan di folder ini.")
            
    # Menjaga agar window tidak langsung tertutup setelah selesai
    input("\nTekan Enter untuk keluar...")