import pandas as pd
import os

print("Memulai proses pembuatan file seed untuk supplier...")

# Data ditranskripsikan dari gambar Anda
data_supplier = [
    {'nama_supplier': 'JAWARA COM (P BUDI KASIR)', 'nama_kontak': 'BUDI PURNOMO', 'no_rekening': 'BCA 400-015-2311'},
    {'nama_supplier': 'IMAM TOBA', 'nama_kontak': 'IMAM SUHADI', 'no_rekening': 'BCA 011-263-6879'},
    {'nama_supplier': 'SAK (M-FH) SAK (SC)', 'nama_kontak': 'PT SURYA ARTA KOMPUTER BAMBANG TRI ATMADJA', 'no_rekening': 'BCA 440-345-1111 BCA 088-807-5111'},
    {'nama_supplier': 'DATA BARU', 'nama_kontak': 'DB KLIK', 'no_rekening': 'BCA 788-103-1888'},
    {'nama_supplier': 'MSC', 'nama_kontak': 'MULTI SARANA COMPUTER', 'no_rekening': 'BCA 816-113-0133'},
    {'nama_supplier': 'ANDALAS', 'nama_kontak': 'BINTORO', 'no_rekening': 'BCA 393-060-1178'},
    {'nama_supplier': 'SOLUDEA', 'nama_kontak': 'NURDIANA LATIFAH', 'no_rekening': 'BCA 746-026-0803'},
    {'nama_supplier': 'ALAM RAYA', 'nama_kontak': 'RACHMAT SOEGIHARTO', 'no_rekening': 'BCA 472-032-8882'},
    {'nama_supplier': 'ESA', 'nama_kontak': 'TSALIST RIFAI ST', 'no_rekening': 'BCA 816-077-0555'},
    {'nama_supplier': 'DUTA SARANA', 'nama_kontak': 'DUTA SARANA SEJAHTERA CV', 'no_rekening': 'BCA 385-480-8899'},
    {'nama_supplier': 'GASOL', 'nama_kontak': 'ROZIKIN', 'no_rekening': 'BCA 315-172-8781'},
    {'nama_supplier': 'DISCOUNT NOTEBOOK', 'nama_kontak': 'ERIC MOELJONO', 'no_rekening': 'BCA 506-071-6767'},
    {'nama_supplier': 'LAPTOP POINT', 'nama_kontak': 'DELA PUTRI ARTIKASARI', 'no_rekening': 'BCA 448-080-7583'},
    {'nama_supplier': 'ASLAM PRINTER', 'nama_kontak': 'MUHAMMAD FAUZI PERDANA', 'no_rekening': 'BCA 267-035-4957'},
    {'nama_supplier': 'SCK', 'nama_kontak': 'CV SARANA CIPTA COMPUTER', 'no_rekening': 'BCA 454-031-6886'},
    {'nama_supplier': 'V-GEN', 'nama_kontak': 'SLAMET ARIFIN', 'no_rekening': 'BCA 011-120-6669'},
    {'nama_supplier': 'LILIK PC MASTER', 'nama_kontak': 'PT TRIPERWIRA MULTI PAMENANG', 'no_rekening': 'BCA 107-049-2233'},
    {'nama_supplier': 'OXYGEN', 'nama_kontak': 'DENIS DARINSAH', 'no_rekening': 'BCA 440-122-6057'},
    {'nama_supplier': 'PT ANGKASA CERAH JAYA', 'nama_kontak': 'ANGKASA CERAH JAYA PT', 'no_rekening': 'BCA 454-024-7531'},
    {'nama_supplier': 'CGM SURABAYA', 'nama_kontak': 'RACHMAD MULIA', 'no_rekening': 'BCA 215-016-2192'},
    {'nama_supplier': 'AMTECH SURABAYA', 'nama_kontak': 'PT ASIAMAS TEKNOLOGI', 'no_rekening': 'BCA 872-512-1314'},
    {'nama_supplier': 'PT ANUGERAH TUMBUH', 'nama_kontak': 'PT ANUGERAH TUMBUH KHARUNIA', 'no_rekening': 'BCA 088-880-9000'},
    {'nama_supplier': 'CV NOAH SURABAYA', 'nama_kontak': 'TINO GUNAWAN', 'no_rekening': 'BCA 258-182-1982'},
    {'nama_supplier': 'SMKI SURABAYA', 'nama_kontak': 'SOEMADI', 'no_rekening': 'BCA 385-427-2727'},
    {'nama_supplier': 'CUN SURABAYA', 'nama_kontak': 'SIE JUNAEDI SIDHARTA', 'no_rekening': 'BCA 388-034-2699'},
    {'nama_supplier': 'SPAREPART SURABAYA', 'nama_kontak': 'YOSI ERAWATI', 'no_rekening': 'BCA 465-225-0878'},
    {'nama_supplier': 'IT TALK', 'nama_kontak': 'SHINTA CAHYANING TYAS', 'no_rekening': 'BCA 130-199-9203'},
    {'nama_supplier': 'WAHANA LAPTOP', 'nama_kontak': 'MASUD', 'no_rekening': 'BCA 8161353027'},
]

# Buat DataFrame dan simpan ke CSV
df = pd.DataFrame(data_supplier)
output_path = 'suppliers_seed.csv'
df.to_csv(output_path, index=False)

print(f"File '{output_path}' berhasil dibuat dengan {len(df)} data supplier.")
print("Anda sekarang bisa melanjutkan dengan memperbarui file app.py.")
