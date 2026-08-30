import streamlit as st
import pandas as pd

def render_excel_upload():
    st.divider()
    st.subheader("📥 Trendyol Veri Yükleme")

    uploaded_file = st.file_uploader(
        "Sipariş Kayıtları Excel dosyasını yükleyin",
        type=["xlsx", "xls"]
    )

    if uploaded_file is None:
        st.info("Henüz bir Excel dosyası yüklenmedi.")
        return

    try:
        excel_file = pd.ExcelFile(uploaded_file)

        sheet_name = st.selectbox(
            "Excel sayfasını seçin",
            excel_file.sheet_names
        )

        df = pd.read_excel(
            excel_file,
            sheet_name=sheet_name
        )

        df.columns = [
            str(col).strip().replace("\n", " ")
            for col in df.columns
        ]

        st.success("Excel dosyası başarıyla okundu.")

        c1, c2, c3 = st.columns(3)

        c1.metric("Satır Sayısı", f"{len(df):,}")
        c2.metric("Sütun Sayısı", f"{len(df.columns):,}")
        c3.metric("Sayfa", sheet_name)

        st.write("### İlk 20 kayıt")

        st.dataframe(
            df.head(20),
            use_container_width=True
        )

        st.write("### Tespit edilen sütunlar")

        for column in df.columns:
            st.write(f"• {column}")

        st.session_state["trendyol_orders"] = df

    except Exception as e:
        st.error(f"Excel okunurken hata oluştu: {e}")
