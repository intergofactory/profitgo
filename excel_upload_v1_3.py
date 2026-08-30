import streamlit as st
import pandas as pd


def render_excel_upload_v13(on_complete=None):
    st.markdown('<div class="pg-section-head"><div><div class="pg-eyebrow">VERİ MERKEZİ</div><h2>Trendyol raporunu yükle</h2><p>Satıcı panelinden indirdiğin Sipariş Kayıtları Excel dosyasını yükle. ProfitGO dosyayı doğrular ve denetim motorunu hazırlar.</p></div><div class="pg-secure">🔒 Geçici oturumda işlenir</div></div>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Sipariş Kayıtları Excel dosyası",
        type=["xlsx", "xls"],
        label_visibility="collapsed",
        help="Trendyol Satıcı Paneli > Raporlar > Sipariş Kayıtları"
    )

    if uploaded_file is None:
        st.markdown('''
        <div class="pg-upload-hint">
          <div class="pg-upload-icon">↑</div>
          <div><strong>.xlsx veya .xls dosyanı buraya bırak</strong><br><span>ProfitGO raporu otomatik tanır ve finansal denetimi hazırlar.</span></div>
        </div>
        ''', unsafe_allow_html=True)
        st.caption("V1.3 canlı demoda dosya yalnızca aktif Streamlit oturumunda bellekte tutulur; kalıcı müşteri depolaması yapılmaz.")
        return

    try:
        excel_file = pd.ExcelFile(uploaded_file)
        sheet_name = st.selectbox("Analiz edilecek sayfa", excel_file.sheet_names)
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        df.columns = [str(col).strip().replace("\n", " ") for col in df.columns]

        required = {"Sipariş No", "Sipariş Tutarı", "Net Tutar"}
        missing = sorted(required.difference(df.columns))
        if missing:
            st.error("Bu dosya Trendyol Sipariş Kayıtları raporuna benzemiyor. Eksik alanlar: " + ", ".join(missing))
            return

        previous_name = st.session_state.get("profitgo_filename")
        if previous_name != uploaded_file.name:
            st.session_state.pop("pg_last_audit_report", None)

        st.session_state["trendyol_orders"] = df
        st.session_state["profitgo_filename"] = uploaded_file.name

        st.markdown('<div class="pg-success"><div class="pg-success-dot">✓</div><div><strong>Rapor hazır</strong><br><span>Dosya başarıyla doğrulandı. Finansal Denetim artık kullanılabilir.</span></div></div>', unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("Kayıt", f"{len(df):,}".replace(",", "."))
        c2.metric("Veri alanı", f"{len(df.columns):,}".replace(",", "."))
        c3.metric("Sayfa", sheet_name)

        if on_complete is not None:
            if st.button("Finansal denetime geç →", type="primary", width="stretch"):
                on_complete()

        with st.expander("Dosya önizlemesi"):
            st.dataframe(df.head(12), width="stretch", hide_index=True)

    except Exception as e:
        st.error(f"Excel okunurken hata oluştu: {e}")
