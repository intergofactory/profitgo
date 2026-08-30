from __future__ import annotations

import streamlit as st
import pandas as pd

from excel_upload_v1_3 import render_excel_upload_v13
from trendyol_analysis import render_trendyol_analysis
from reconciliation import render_reconciliation
from reporting_v1_3 import build_summary, build_pdf_report, load_history, save_history_item, clear_history, money

st.set_page_config(
    page_title="ProfitGO - Finans Kontrol Merkezi",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root{--bg:#f4f7fb;--surface:#fff;--ink:#0b1220;--muted:#64748b;--line:#e5eaf0;--green:#10b981;--green2:#047857;--navy:#0b1220;--soft:#ecfdf5;--orange:#f59e0b;--red:#ef4444}
html,body,[class*="css"]{font-family:'Inter',-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
[data-testid="stAppViewContainer"]{background:var(--bg);color:var(--ink)}
[data-testid="stHeader"]{background:rgba(244,247,251,.82);backdrop-filter:blur(12px)}
.block-container{max-width:1500px;padding-top:1.2rem;padding-bottom:4rem}
#MainMenu,footer{visibility:hidden} h1,h2,h3{letter-spacing:-.035em;color:var(--ink)} hr{border-color:var(--line)!important}
[data-testid="stSidebar"]{background:#0b1220;border-right:1px solid #172033}
[data-testid="stSidebar"] *{color:#e2e8f0}
[data-testid="stSidebar"] .stRadio label{padding:7px 8px;border-radius:10px}
[data-testid="stSidebar"] .stRadio label:hover{background:#131e31}
[data-testid="stSidebar"] hr{border-color:#253047!important}
.pg-side-logo{display:flex;align-items:center;gap:10px;font-size:23px;font-weight:800;margin:4px 0 20px}.pg-side-logo .mark{width:31px;height:31px;border-radius:10px;background:linear-gradient(145deg,#10b981,#047857);display:grid;place-items:center;color:#fff}.pg-side-logo b{color:#6ee7b7}
.pg-user{background:#111b2d;border:1px solid #22304a;border-radius:14px;padding:13px;margin:12px 0 8px}.pg-user .name{font-weight:700;font-size:13px}.pg-user .mail{font-size:10px;color:#94a3b8!important;margin-top:3px}.pg-plan{display:inline-block;margin-top:9px;background:#064e3b;color:#a7f3d0!important;border-radius:99px;padding:4px 7px;font-size:9px;font-weight:800;letter-spacing:.07em}
.pg-top{display:flex;align-items:center;justify-content:space-between;margin:0 0 15px}.pg-top .crumb{font-size:12px;color:#64748b;font-weight:600}.pg-top .actions{display:flex;gap:8px}.pg-pill{font-size:11px;background:#fff;border:1px solid var(--line);border-radius:999px;padding:8px 11px;color:#475569;font-weight:600}.pg-live{display:inline-block;width:7px;height:7px;border-radius:50%;background:#10b981;margin-right:6px;box-shadow:0 0 0 4px #d1fae5}
.pg-hero{position:relative;overflow:hidden;background:linear-gradient(125deg,#09111f 0%,#101b30 62%,#073d32 120%);border-radius:25px;padding:35px 39px;color:#fff;box-shadow:0 20px 48px rgba(15,23,42,.14)}.pg-hero:after{content:"";position:absolute;width:430px;height:430px;border-radius:50%;right:-160px;top:-235px;background:radial-gradient(circle,rgba(16,185,129,.4),rgba(16,185,129,0) 68%)}.pg-kicker{font-size:10px;font-weight:800;letter-spacing:.14em;color:#6ee7b7;text-transform:uppercase}.pg-title{font-size:39px;line-height:1.08;font-weight:800;letter-spacing:-1.6px;margin:10px 0 11px;position:relative;z-index:1}.pg-title em{font-style:normal;color:#6ee7b7}.pg-sub{max-width:780px;color:#cbd5e1;font-size:14px;line-height:1.65;position:relative;z-index:1}.pg-hero-row{display:flex;gap:22px;margin-top:20px;color:#cbd5e1;font-size:11px;position:relative;z-index:1}
.pg-kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:13px;margin:16px 0}.pg-kpi{background:#fff;border:1px solid var(--line);border-radius:17px;padding:17px;box-shadow:0 2px 8px rgba(15,23,42,.035)}.pg-kpi .label{font-size:11px;color:#64748b;font-weight:600}.pg-kpi .value{font-size:22px;font-weight:800;letter-spacing:-.7px;margin:5px 0}.pg-kpi .note{font-size:10px;color:#94a3b8}.pg-kpi .icon{width:31px;height:31px;border-radius:9px;background:#ecfdf5;color:#047857;display:grid;place-items:center;margin-bottom:11px}
.pg-card{background:#fff;border:1px solid var(--line);border-radius:18px;padding:20px;box-shadow:0 2px 8px rgba(15,23,42,.035);margin-bottom:14px}.pg-card h3{font-size:18px;margin:0 0 6px}.pg-card p{font-size:12px;color:#64748b;line-height:1.6;margin:0}.pg-eyebrow{font-size:9px;font-weight:800;color:#059669;letter-spacing:.13em;margin-bottom:6px}.pg-statrow{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:15px}.pg-stat{background:#f8fafc;border:1px solid #edf0f4;border-radius:12px;padding:12px}.pg-stat .v{font-weight:800;font-size:17px}.pg-stat .l{font-size:9px;color:#94a3b8;margin-top:3px}
.pg-plans{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.pg-plan-card{background:#fff;border:1px solid var(--line);border-radius:18px;padding:20px;position:relative}.pg-plan-card.current{border:2px solid #10b981;box-shadow:0 12px 28px rgba(16,185,129,.09)}.pg-plan-card .tag{position:absolute;right:14px;top:14px;background:#ecfdf5;color:#047857;border-radius:99px;padding:4px 8px;font-size:9px;font-weight:800}.pg-plan-card .price{font-size:26px;font-weight:800;margin:13px 0 4px}.pg-plan-card .desc{font-size:11px;color:#64748b;min-height:34px}.pg-plan-card ul{padding-left:18px;font-size:11px;color:#475569;line-height:1.9;margin-top:15px}
.pg-login-wrap{max-width:1060px;margin:5vh auto;display:grid;grid-template-columns:1.15fr .85fr;background:#fff;border:1px solid var(--line);border-radius:26px;overflow:hidden;box-shadow:0 28px 70px rgba(15,23,42,.12)}.pg-login-brand{background:linear-gradient(135deg,#09111f,#0f1d32 60%,#064e3b);padding:48px;color:#fff;min-height:520px}.pg-login-brand .logo{font-size:27px;font-weight:800}.pg-login-brand .logo b{color:#6ee7b7}.pg-login-brand h1{color:#fff;font-size:41px;line-height:1.08;margin:85px 0 13px}.pg-login-brand p{color:#cbd5e1;font-size:14px;line-height:1.7;max-width:460px}.pg-login-points{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:35px}.pg-login-point{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.09);border-radius:13px;padding:13px;font-size:11px;color:#cbd5e1}.pg-login-form{padding:48px;display:flex;flex-direction:column;justify-content:center}.pg-login-form h2{font-size:27px;margin:0 0 6px}.pg-login-form p{font-size:12px;color:#64748b;margin:0 0 23px}
[data-testid="stMetric"]{background:#fff;border:1px solid var(--line);padding:14px;border-radius:13px}.stButton>button{border-radius:10px;font-weight:700}.stDownloadButton>button{border-radius:10px;font-weight:700;background:#0b1220;color:#fff;border-color:#0b1220}.stAlert{border-radius:13px}[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:14px;overflow:hidden;background:#fff}[data-testid="stFileUploader"]{background:#fff;border:1px solid var(--line);border-radius:16px;padding:8px}[data-testid="stExpander"]{background:#fff;border:1px solid var(--line);border-radius:12px}
.pg-section-head{display:flex;align-items:flex-start;justify-content:space-between;gap:24px;background:#fff;border:1px solid var(--line);border-radius:18px;padding:21px 22px;margin:5px 0 14px}.pg-section-head h2{font-size:22px;margin:3px 0 6px}.pg-section-head p{font-size:13px;color:#64748b;margin:0;max-width:780px;line-height:1.55}.pg-secure{white-space:nowrap;background:#ecfdf5;color:#047857;border:1px solid #a7f3d0;border-radius:999px;padding:8px 11px;font-size:10px;font-weight:700}.pg-upload-hint{display:flex;gap:13px;align-items:center;background:#fff;border:1px dashed #cbd5e1;border-radius:15px;padding:16px 18px;margin-top:8px;color:#334155}.pg-upload-hint span{font-size:12px;color:#94a3b8}.pg-upload-icon{width:34px;height:34px;border-radius:10px;background:#ecfdf5;color:#047857;font-size:21px;display:grid;place-items:center;font-weight:700}.pg-success{display:flex;gap:12px;align-items:center;background:#ecfdf5;border:1px solid #a7f3d0;border-radius:14px;padding:13px 15px;margin:10px 0 14px;color:#065f46}.pg-success span{font-size:12px;color:#047857}.pg-success-dot{width:28px;height:28px;border-radius:50%;background:#10b981;color:#fff;display:grid;place-items:center;font-weight:800}.pg-actionbar{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:14px 0}.pg-action{background:#fff;border:1px solid var(--line);border-radius:15px;padding:15px}.pg-action .t{font-size:12px;font-weight:800}.pg-action .d{font-size:10px;color:#94a3b8;margin-top:4px;line-height:1.4}.pg-risk{display:flex;align-items:center;justify-content:space-between;gap:15px}.pg-risk-score{width:62px;height:62px;border-radius:18px;background:#ecfdf5;color:#047857;display:grid;place-items:center;font-size:20px;font-weight:800}.pg-demo-note{background:#fff7ed;border:1px solid #fed7aa;color:#9a3412;border-radius:12px;padding:10px 12px;font-size:10px;margin:8px 0 12px}
@media(max-width:900px){.pg-kpis,.pg-plans,.pg-actionbar{grid-template-columns:1fr 1fr}.pg-section-head{display:block}.pg-secure{display:inline-block;margin-top:12px}.pg-login-wrap{grid-template-columns:1fr}.pg-login-brand{display:none}.pg-title{font-size:32px}}
</style>
""", unsafe_allow_html=True)


def _num(df, col):
    if col not in df.columns:
        return 0.0
    return float(pd.to_numeric(df[col], errors="coerce").fillna(0).sum())


def _money0(v):
    return f"{abs(v):,.0f} TL".replace(",", ".")


def login_screen():
    st.markdown('''<div class="pg-login-wrap"><div class="pg-login-brand"><div class="logo">Profit<b>GO</b></div><h1>Trendyol finansını<br>kontrol altına al.</h1><p>Komisyon, kargo, iade ve cezaları tek raporla denetle. Şüpheli kesintileri ProfitGO senin için öne çıkarsın.</p><div class="pg-login-points"><div class="pg-login-point">✓ Otomatik mutabakat</div><div class="pg-login-point">✓ Ceza denetimi</div><div class="pg-login-point">✓ Rapor geçmişi</div><div class="pg-login-point">✓ PDF denetim raporu</div></div></div><div class="pg-login-form"><h2>Hesabına giriş yap</h2><p>ProfitGO V1.3 canlı demo çalışma alanı</p></div></div>''', unsafe_allow_html=True)
    # Place form visually over the right-hand card area with normal Streamlit controls below.
    _, form_col = st.columns([1.12, .88])
    with form_col:
        email = st.text_input("E-posta", value="demo@profitgo.app")
        password = st.text_input("Şifre", type="password", value="ProfitGO2026")
        c1, c2 = st.columns(2)
        if c1.button("Giriş yap", type="primary", width="stretch"):
            if email == "demo@profitgo.app" and password == "ProfitGO2026":
                st.session_state.pg_authenticated = True
                st.session_state.pg_user_email = email
                st.session_state.pg_page = "Genel Bakış"
                st.rerun()
            else:
                st.error("Demo giriş bilgileri hatalı.")
        if c2.button("Demo hesabı", width="stretch"):
            st.session_state.pg_authenticated = True
            st.session_state.pg_user_email = "demo@profitgo.app"
            st.session_state.pg_page = "Genel Bakış"
            st.rerun()
        st.caption("Demo: demo@profitgo.app / ProfitGO2026")


if "pg_authenticated" not in st.session_state:
    st.session_state.pg_authenticated = False
if not st.session_state.pg_authenticated:
    login_screen()
    st.stop()

# --- current dataset and report summary ---
has_data = "trendyol_orders" in st.session_state
if has_data:
    df = st.session_state["trendyol_orders"]
    filename = st.session_state.get("profitgo_filename", "Trendyol Sipariş Kayıtları")
    summary = build_summary(df, filename)
else:
    df = None
    summary = None

def go_to(page_name: str):
    st.session_state.pg_page = page_name
    st.rerun()


if "pg_page" not in st.session_state:
    st.session_state.pg_page = "Genel Bakış"

# --- sidebar ---
with st.sidebar:
    st.markdown('<div class="pg-side-logo"><div class="mark">G</div>Profit<b>GO</b></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pg-user"><div class="name">Demo Çalışma Alanı</div><div class="mail">{st.session_state.get("pg_user_email", "demo@profitgo.app")}</div><span class="pg-plan">PRO PLAN</span></div>', unsafe_allow_html=True)
    page = st.radio("Navigasyon", ["Genel Bakış", "Rapor Yükle", "Finansal Denetim", "Mutabakat", "Raporlar", "Hesap & Plan"], key="pg_page", label_visibility="collapsed")
    st.divider()
    st.caption("ProfitGO V1.3 • Live Demo")
    st.markdown('<div class="pg-demo-note">Demo ortamı: gerçek kullanıcı veritabanı ve ödeme sistemi henüz bağlı değildir.</div>', unsafe_allow_html=True)
    if st.button("Çıkış yap", width="stretch"):
        for k in ["trendyol_orders", "profitgo_filename", "pg_report_history"]:
            st.session_state.pop(k, None)
        st.session_state.pg_authenticated = False
        st.session_state.pg_page = "Genel Bakış"
        st.rerun()

st.markdown(f'<div class="pg-top"><div class="crumb">ProfitGO / {page}</div><div class="actions"><div class="pg-pill"><span class="pg-live"></span>Denetim motoru aktif</div><div class="pg-pill">V1.3</div></div></div>', unsafe_allow_html=True)

if page == "Genel Bakış":
    st.markdown('''<div class="pg-hero"><div class="pg-kicker">TRENDYOL FİNANS KONTROL MERKEZİ</div><div class="pg-title">Paranın nereye gittiğini <em>gör.</em><br>Şüpheli kesintiyi <em>yakala.</em></div><div class="pg-sub">ProfitGO, Trendyol sipariş raporunu finansal sinyallere dönüştürür. Komisyon, kargo, iadeler ve cezalar tek ekranda; incelemen gereken kayıtlar önde.</div><div class="pg-hero-row"><span>✓ Finansal mutabakat</span><span>✓ Ceza denetimi</span><span>✓ PDF rapor</span><span>✓ Rapor geçmişi</span></div></div>''', unsafe_allow_html=True)
    if summary:
        kpis = [("◫","Sipariş",f"{summary['orders']:,}".replace(",","."),"Rapordaki toplam kayıt"),("↗","Teslim edilen ciro",_money0(summary['delivered_revenue']),"Tamamlanan siparişler"),("◎","Net finansal tutar",_money0(summary['net_amount']),"Trendyol net tutarı"),("!","İncelenecek tutar",_money0(summary['suspicious_amount']),f"{summary['suspicious_count']} kayıt öne çıktı")]
    else:
        kpis = [("◫","Sipariş","—","Rapor yüklenmedi"),("↗","Teslim edilen ciro","—","Rapor yüklenmedi"),("◎","Net finansal tutar","—","Rapor yüklenmedi"),("!","İncelenecek tutar","—","Rapor yüklenmedi")]
    html='<div class="pg-kpis">'
    for icon,label,value,note in kpis:
        html += f'<div class="pg-kpi"><div class="icon">{icon}</div><div class="label">{label}</div><div class="value">{value}</div><div class="note">{note}</div></div>'
    html+='</div>'
    st.markdown(html, unsafe_allow_html=True)

    if summary:
        risk_label = "Düşük" if summary["suspicious_count"] == 0 else ("Orta" if summary["suspicious_count"] <= 3 else "Yüksek")
        st.markdown(f'<div class="pg-card pg-risk"><div><div class="pg-eyebrow">DENETİM SİNYALİ</div><h3>{risk_label} inceleme yoğunluğu</h3><p>{summary["suspicious_count"]} kayıt, toplam {money(summary["suspicious_amount"])} için manuel kontrol öneriliyor. Toplam finansal kesinti oranı %{summary.get("deduction_rate",0):.2f}.</p></div><div class="pg-risk-score">{summary["suspicious_count"]}</div></div>', unsafe_allow_html=True)

    c1, c2 = st.columns([1.2,.8])
    with c1:
        if summary:
            st.markdown(f'''<div class="pg-card"><div class="pg-eyebrow">SON ANALİZ</div><h3>{summary['filename']}</h3><p>Rapor ID {summary['report_id']} • {summary['orders']:,} kayıt işlendi.</p><div class="pg-statrow"><div class="pg-stat"><div class="v">{money(summary['commission'])}</div><div class="l">KOMİSYON</div></div><div class="pg-stat"><div class="v">{money(summary['shipping'])}</div><div class="l">GÖNDERİ KARGO</div></div><div class="pg-stat"><div class="v">{money(summary['penalty'])}</div><div class="l">CEZA</div></div></div></div>''', unsafe_allow_html=True)
        else:
            st.markdown('<div class="pg-card"><div class="pg-eyebrow">BAŞLANGIÇ</div><h3>İlk raporunu yükle</h3><p>Trendyol Satıcı Paneli’nden Sipariş Kayıtları raporunu indir ve ProfitGO’ya yükle. Analiz birkaç saniye içinde hazır olur.</p></div>', unsafe_allow_html=True)
            if st.button("Rapor yüklemeye git →", type="primary"):
                go_to("Rapor Yükle")
    with c2:
        history = load_history()
        count = len(history)
        st.markdown(f'''<div class="pg-card"><div class="pg-eyebrow">ÇALIŞMA ALANI</div><h3>Rapor arşivi</h3><p>V1.3 demoda arşiv yalnızca aktif oturumda tutulur.</p><div class="pg-statrow"><div class="pg-stat"><div class="v">{count}</div><div class="l">KAYITLI RAPOR</div></div><div class="pg-stat"><div class="v">Pro</div><div class="l">AKTİF PLAN</div></div><div class="pg-stat"><div class="v">50</div><div class="l">RAPOR LİMİTİ</div></div></div></div>''', unsafe_allow_html=True)

    if summary:
        st.markdown('<div class="pg-actionbar"><div class="pg-action"><div class="t">Finansal Denetim</div><div class="d">Ceza, iade ve kesinti hareketlerini detaylı incele.</div></div><div class="pg-action"><div class="t">Mutabakat</div><div class="d">Net tutar ve finansal hareketleri karşılaştır.</div></div><div class="pg-action"><div class="t">PDF Rapor</div><div class="d">Denetim özetini paylaşılabilir PDF olarak indir.</div></div></div>', unsafe_allow_html=True)
        a1,a2,a3=st.columns(3)
        if a1.button("Denetime geç →", type="primary", width="stretch"):
            go_to("Finansal Denetim")
        if a2.button("Mutabakata geç →", width="stretch"):
            go_to("Mutabakat")
        if a3.button("Rapor merkezini aç →", width="stretch"):
            go_to("Raporlar")

elif page == "Rapor Yükle":
    st.markdown('<div class="pg-card"><div class="pg-eyebrow">YENİ ANALİZ</div><h3>Trendyol raporunu içeri al</h3><p>V1.3 canlı demoda dosya aktif Streamlit oturumunda geçici olarak işlenir; kalıcı müşteri depolaması yapılmaz.</p></div>', unsafe_allow_html=True)
    render_excel_upload_v13(lambda: go_to("Finansal Denetim"))

elif page == "Finansal Denetim":
    if not has_data:
        st.info("Finansal denetim için önce bir Trendyol Sipariş Kayıtları raporu yükle.")
        if st.button("Rapor yüklemeye git →", type="primary"):
            go_to("Rapor Yükle")
    else:
        render_trendyol_analysis()

elif page == "Mutabakat":
    render_reconciliation()

elif page == "Raporlar":
    st.markdown('<div class="pg-card"><div class="pg-eyebrow">RAPOR MERKEZİ</div><h3>Denetim geçmişi ve PDF çıktısı</h3><p>Analizini arşivle, geçmiş raporlarını görüntüle ve müşteriye/muhasebeye iletilebilir PDF denetim raporu oluştur.</p></div>', unsafe_allow_html=True)
    if summary:
        c1, c2, c3 = st.columns([1,1,2])
        if c1.button("Analizi arşivle", type="primary", width="stretch"):
            if save_history_item(summary):
                st.success("Analiz rapor geçmişine eklendi.")
            else:
                st.info("Bu analiz zaten rapor geçmişinde.")
        pdf_bytes = build_pdf_report(summary)
        c2.download_button("PDF raporu indir", data=pdf_bytes, file_name=f"ProfitGO_{summary['report_id']}.pdf", mime="application/pdf", width="stretch")
        c3.caption(f"Aktif analiz: {summary['filename']} • Rapor ID {summary['report_id']}")
    else:
        st.warning("PDF raporu oluşturmak için önce bir Trendyol raporu yükle.")
        if st.button("Rapor yüklemeye git →", type="primary"):
            go_to("Rapor Yükle")

    history = load_history()
    if history:
        h1,h2 = st.columns([4,1])
        h1.caption("Demo rapor geçmişi yalnızca bu oturumda tutulur.")
        if h2.button("Geçmişi temizle", width="stretch"):
            clear_history()
            st.rerun()
        history_df = pd.DataFrame([{
            "Rapor ID": x.get("report_id"), "Tarih": x.get("generated_at"), "Dosya": x.get("filename"),
            "Sipariş": x.get("orders"), "Net Tutar": money(x.get("net_amount",0)), "İncelenecek": x.get("suspicious_count",0), "Risk Tutarı": money(x.get("suspicious_amount",0))
        } for x in history])
        st.dataframe(history_df, width="stretch", hide_index=True)
    else:
        st.info("Henüz arşivlenmiş rapor yok.")

elif page == "Hesap & Plan":
    st.markdown('<div class="pg-card"><div class="pg-eyebrow">ABONELİK</div><h3>ProfitGO planın</h3><p>V1.3 demo plan ekranı hazır; gerçek abonelik/ödeme altyapısı henüz bağlanmamıştır.</p></div>', unsafe_allow_html=True)
    st.markdown('''<div class="pg-plans"><div class="pg-plan-card"><h3>Starter</h3><div class="price">₺499<span style="font-size:11px;color:#94a3b8"> / ay</span></div><div class="desc">Küçük Trendyol mağazaları için temel finans kontrolü.</div><ul><li>10 rapor / ay</li><li>Finansal özet</li><li>Mutabakat</li></ul></div><div class="pg-plan-card current"><span class="tag">MEVCUT PLAN</span><h3>Pro</h3><div class="price">₺999<span style="font-size:11px;color:#94a3b8"> / ay</span></div><div class="desc">Aktif satıcılar için ceza ve kesinti denetimi.</div><ul><li>50 rapor / ay</li><li>Ceza denetçisi</li><li>PDF rapor</li><li>Rapor geçmişi</li></ul></div><div class="pg-plan-card"><h3>Business</h3><div class="price">₺1.999<span style="font-size:11px;color:#94a3b8"> / ay</span></div><div class="desc">Yüksek hacimli mağazalar ve ekipler için.</div><ul><li>Sınırsız rapor</li><li>Çoklu mağaza</li><li>Ekip erişimi</li><li>Öncelikli destek</li></ul></div></div>''', unsafe_allow_html=True)
    st.write("")
    with st.expander("Hesap bilgileri", expanded=True):
        st.text_input("E-posta", value=st.session_state.get("pg_user_email", "demo@profitgo.app"), disabled=True)
        st.text_input("Çalışma alanı", value="Demo Çalışma Alanı", disabled=True)
        st.text_input("Plan", value="Pro - Live Demo", disabled=True)
