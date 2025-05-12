
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Performance Deviation Detector", layout="wide")
st.title("📉 Performance Deviation Detector")
st.markdown("Deteksi penyimpangan skor KPI antar unit atau jabatan berdasarkan rata-rata dan standar deviasi.")

# Upload file
uploaded_file = st.file_uploader("📤 Upload file KPI (CSV/XLSX)", type=["csv", "xlsx"])
if not uploaded_file:
    st.stop()

# Load file
if uploaded_file.name.endswith(".csv"):
    df = pd.read_csv(uploaded_file)
else:
    df = pd.read_excel(uploaded_file)

# Validasi kolom
required_cols = ['NIPP PEKERJA', 'POSISI PEKERJA', 'PERUSAHAAN', 'BOBOT', 'REALISASI TW TERKAIT', 'TARGET TW TERKAIT', 'POLARITAS']
if not all(col in df.columns for col in required_cols):
    st.error("❌ Kolom wajib tidak ditemukan. Harus ada kolom seperti di kpi_cleaned.csv.")
    st.stop()

# Preprocessing
df['REALISASI TW TERKAIT'] = pd.to_numeric(df['REALISASI TW TERKAIT'], errors='coerce')
df['TARGET TW TERKAIT'] = pd.to_numeric(df['TARGET TW TERKAIT'], errors='coerce')
df['BOBOT'] = pd.to_numeric(df['BOBOT'], errors='coerce')
df['POLARITAS'] = df['POLARITAS'].str.strip().str.lower()

def calculate_capaian(row):
    realisasi = row['REALISASI TW TERKAIT']
    target = row['TARGET TW TERKAIT']
    polaritas = row['POLARITAS']
    if pd.isna(realisasi) or pd.isna(target) or target == 0 or realisasi == 0:
        return None
    if polaritas == 'positif':
        return (realisasi / target) * 100
    elif polaritas == 'negatif':
        return (target / realisasi) * 100
    else:
        return None

df['CAPAIAN (%)'] = df.apply(calculate_capaian, axis=1)
df['SKOR KPI'] = df['CAPAIAN (%)'] * df['BOBOT'] / 100

# Agregasi skor akhir per pekerja
summary = df.groupby(['NIPP PEKERJA', 'POSISI PEKERJA', 'PERUSAHAAN'], as_index=False).agg(
    TOTAL_SKOR=('SKOR KPI', 'sum'),
    TOTAL_BOBOT=('BOBOT', 'sum')
)
summary = summary[summary['TOTAL_BOBOT'] != 0]
summary['SKOR AKHIR'] = (summary['TOTAL_SKOR'] / summary['TOTAL_BOBOT']) * 100

# Pilih level grouping untuk deteksi deviasi
level = st.selectbox("🔍 Pilih Level untuk Deteksi Deviasi", ["PERUSAHAAN", "POSISI PEKERJA"])

# Hitung deviasi terhadap mean per grup
summary['DEV_GROUP'] = summary.groupby(level)['SKOR AKHIR'].transform('mean')
summary['STD_GROUP'] = summary.groupby(level)['SKOR AKHIR'].transform('std')

# Hitung selisih z-score
summary['Z_SCORE'] = (summary['SKOR AKHIR'] - summary['DEV_GROUP']) / summary['STD_GROUP']
summary['ANOMALI'] = summary['Z_SCORE'].apply(lambda z: '🟥 Di Bawah Normal' if z < -1.5 else ('🟩 Di Atas Normal' if z > 1.5 else 'Normal'))

st.subheader("📄 Hasil Deteksi Penyimpangan")
st.dataframe(summary[['NIPP PEKERJA', 'POSISI PEKERJA', 'PERUSAHAAN', 'SKOR AKHIR', 'DEV_GROUP', 'STD_GROUP', 'Z_SCORE', 'ANOMALI']])

# Visualisasi
st.subheader("📊 Visualisasi Deviasi Skor KPI")
fig = px.scatter(summary, x='DEV_GROUP', y='SKOR AKHIR', color='ANOMALI',
                 hover_data=['NIPP PEKERJA', 'POSISI PEKERJA'],
                 title="Scatter Plot Skor KPI vs Rata-Rata Grup")
st.plotly_chart(fig)

# Unduh hasil
st.download_button("📥 Download Hasil Deteksi (CSV)", data=summary.to_csv(index=False), file_name="deviation_results.csv", mime="text/csv")
