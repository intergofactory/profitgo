from __future__ import annotations
from datetime import date,timedelta
import importlib
import pandas as pd
import streamlit as st
import trendyol_api_v1_4 as ty
ty=importlib.reload(ty); TrendyolCredentials=ty.TrendyolCredentials
st.set_page_config(page_title="ProfitGO V1.4 - API Finans Merkezi",page_icon="◈",layout="wide",initial_sidebar_state="expanded")
st.markdown('''<style>:root{--bg:#f4f7fb;--ink:#0b1220;--line:#e5eaf0}[data-testid="stAppViewContainer"]{background:var(--bg);color:var(--ink)}.block-container{max-width:1500px;padding-top:1.4rem;padding-bottom:4rem}[data-testid="stSidebar"]{background:#0b1220}[data-testid="stSidebar"] *{color:#e2e8f0}.pg-card{background:#fff;border:1px solid var(--line);border-radius:18px;padding:20px;margin-bottom:14px}.pg-eyebrow{font-size:9px;font-weight:800;color:#059669;letter-spacing:.13em}.pg-hero{background:linear-gradient(125deg,#09111f,#101b30 62%,#073d32);border-radius:24px;padding:32px 38px;color:#fff;margin-bottom:16px}.pg-hero h1{color:#fff;font-size:38px}.pg-hero em{font-style:normal;color:#6ee7b7}[data-testid="stMetric"],[data-testid="stDataFrame"]{background:#fff;border:1px solid var(--line);border-radius:14px;padding:10px}</style>''',unsafe_allow_html=True)
def money(v): return f"{v:,.2f} TL".replace(",","X").replace(".",",").replace("X",".")
with st.sidebar:
 st.markdown("## ProfitGO"); st.caption("V1.4 • API Finance Development"); st.divider(); st.write("**Komisyon + Kesinti Motoru**"); st.caption("Order API + Finance API + Platform Hizmet Bedeli")
st.markdown('''<div class="pg-hero"><div>PROFITGO V1.4 • FINANCE ENGINE</div><h1>Komisyonu ve <em>platform kesintisini ayrı</em> gör.</h1><p>Komisyon farkı, platform hizmet bedeli ve diğer kesintiler ayrı finansal kalemler olarak izlenir. Böylece tek bir toplam içindeki gerçek maliyet görünür hale gelir.</p></div>''',unsafe_allow_html=True)
try:
 seller_id=int(st.secrets["TRENDYOL_SELLER_ID"]); creds=TrendyolCredentials(seller_id,str(st.secrets["TRENDYOL_API_KEY"]),str(st.secrets["TRENDYOL_API_SECRET"]),str(st.secrets.get("TRENDYOL_USER_AGENT",f"{seller_id} - ProfitGO")))
except Exception: st.error("Trendyol API bağlantısı yapılandırılmadı."); st.stop()
st.success(f"API yapılandırması aktif • Satıcı ID: {seller_id}")
c1,c2=st.columns(2)
with c1: start_date=st.date_input("Başlangıç",value=date.today()-timedelta(days=13),max_value=date.today())
with c2: end_date=st.date_input("Bitiş",value=date.today(),min_value=start_date,max_value=date.today())
if (end_date-start_date).days>14: st.warning("15 gün veya daha kısa bir aralık seç."); st.stop()
if st.button("Trendyol'dan sipariş + finans verilerini çek",type="primary",width="stretch"):
 try:
  with st.spinner("Siparişler alınıyor..."): packages=ty.fetch_order_packages(creds,start_date,end_date); lines=ty.packages_to_lines(packages)
  with st.spinner("Cari hesap ve komisyon hareketleri alınıyor..."): settlements=ty.fetch_settlements(creds,start_date,end_date)
  with st.spinner("Kesinti/fatura hareketleri alınıyor..."): deductions=ty.fetch_other_financials(creds,start_date,end_date,"DeductionInvoices")
  with st.spinner("Platform hizmet bedelleri ayrıştırılıyor..."):
   try: platform_fees=ty.fetch_other_financials(creds,start_date,end_date,"DeductionInvoices","PlatformServiceFee")
   except Exception: platform_fees=pd.DataFrame()
  st.session_state.v14_api_lines=lines; st.session_state.v14_finance_settlements=settlements; st.session_state.v14_finance_deductions=deductions; st.session_state.v14_platform_fees=platform_fees
  st.success(f"{len(packages):,} paket • {len(lines):,} ürün satırı • {len(settlements):,} finans hareketi • {len(deductions):,} kesinti hareketi".replace(",","."))
 except Exception as exc: st.error(f"Entegrasyon hatası: {type(exc).__name__}: {exc}")
if "v14_api_lines" not in st.session_state: st.info("Tarih aralığını seç ve verileri getir."); st.stop()
lines=st.session_state.v14_api_lines.copy(); settlements=st.session_state.get("v14_finance_settlements",pd.DataFrame()).copy(); deductions=st.session_state.get("v14_finance_deductions",pd.DataFrame()).copy(); platform_fees=st.session_state.get("v14_platform_fees",pd.DataFrame()).copy()
if lines.empty: st.info("Sipariş bulunamadı."); st.stop()
revenue=float(pd.to_numeric(lines["Teslim Ciro"],errors="coerce").fillna(0).sum()); estimated=float(pd.to_numeric(lines["Tahmini Komisyon"],errors="coerce").fillna(0).sum()); seller_discount=float(pd.to_numeric(lines["Satıcı İndirimi"],errors="coerce").fillna(0).sum()); ty_discount=float(pd.to_numeric(lines["Trendyol İndirimi"],errors="coerce").fillna(0).sum())
fin=ty.settlement_summary(settlements); ded=ty.other_financial_summary(deductions); pf=ty.other_financial_summary(platform_fees); audit=ty.commission_reconciliation(lines,settlements)
matched_expected=float(audit["Beklenen Komisyon"].sum()) if not audit.empty else 0.; matched_actual=float(audit["Gerçek Net Komisyon"].sum()) if not audit.empty else 0.; advantage=float(audit["Komisyon Avantajı"].sum()) if not audit.empty else 0.; potential_over=float(audit.loc[audit["Durum"].eq("🔴 Fazla Komisyon?"),"Fark TL"].clip(lower=0).sum()) if not audit.empty else 0.; campaign_count=int(audit["Durum"].eq("💚 İndirimli Komisyon / Avantaj").sum()) if not audit.empty else 0; over_count=int(audit["Durum"].eq("🔴 Fazla Komisyon?").sum()) if not audit.empty else 0
platform_fee=pf["net_deduction"]; other_deductions=ded["net_deduction"]-platform_fee
st.markdown('<div class="pg-card"><div class="pg-eyebrow">KESİNTİ HARİTASI</div><h3>Platform hizmet bedelini komisyonun içinden çıkar</h3><p>Platform Hizmet Bedeli, Finance API\'de ayrı bir kesinti türüdür. Aşağıdaki tutar komisyon hesabına eklenmez; Net Kesinti/Fatura toplamının içinde ayrı gösterilir.</p></div>',unsafe_allow_html=True)
k1,k2,k3,k4=st.columns(4); k1.metric("Net Kesinti/Fatura",money(ded["net_deduction"])); k2.metric("Platform Hizmet Bedeli",money(platform_fee)); k3.metric("Diğer Kesintiler",money(other_deductions)); k4.metric("Platform Payı",f"%{(platform_fee/ded['net_deduction']*100 if ded['net_deduction'] else 0):.2f}")
if platform_fee>0: st.success(f"Platform Hizmet Bedeli ayrı yakalandı: {money(platform_fee)}. Bu tutar komisyon farkı olarak değerlendirilmemeli.")
else: st.info("Bu tarih aralığında PlatformServiceFee filtresiyle ayrı bir kayıt dönmedi. Kesinti açıklamalarını ayrıca sınıflandıracağız.")
st.markdown('<div class="pg-card"><div class="pg-eyebrow">KAMPANYA / TARİFE MOTORU</div><h3>İndirimli komisyonu anomali sanma</h3><p>Finance API komisyon oranı sipariş oranından düşükse veya CommissionNegative düzeltmesi varsa bu kayıt avantaj olarak ayrılır. Yalnızca gerçekleşen net komisyon beklenenden yüksekse fazla komisyon adayı oluşturulur.</p></div>',unsafe_allow_html=True)
k1,k2,k3,k4=st.columns(4); k1.metric("Eşleşen Beklenen",money(matched_expected)); k2.metric("Eşleşen Gerçek",money(matched_actual)); k3.metric("Komisyon Avantajı",money(advantage),f"{campaign_count} satır"); k4.metric("Açıklanamayan Komisyon Farkı",money(potential_over),f"{over_count} satır")
if campaign_count: st.success(f"{campaign_count} sipariş/ürün satırında indirimli komisyon veya komisyon iadesi/düzeltmesi sinyali bulundu. Toplam avantaj: {money(advantage)}")
if over_count: st.warning(f"{over_count} satırda henüz açıklanamayan komisyon farkı var: {money(potential_over)}. Bu tutar 'fazla kesinti' olarak kesinleştirilmedi.")
elif not audit.empty: st.info("Eşleşen kayıtlarda beklenenden yüksek net komisyon adayı görünmüyor.")
a,b,c,d=st.columns(4); a.metric("Dönem Tahmini Komisyon",money(estimated)); b.metric("Satış Komisyonu",money(fin["sale_commission"])); c.metric("Komisyon İade/Düzeltme Kredisi",money(fin["return_commission"]+fin.get("commission_credit",0))); d.metric("Platform Hizmet Bedeli",money(platform_fee))
st.caption("Dönem toplamları bilgi amaçlıdır. Alarm motoru yalnızca Order ve Finance API'de aynı sipariş+barkod eşleşen kayıtları kullanır. Trendyol indirimi: "+money(ty_discount)+" • Satıcı indirimi: "+money(seller_discount))
with st.expander("💚 Komisyon kampanyası / tarife denetçisi",expanded=True):
 if audit.empty: st.info("Eşleşen kayıt yok.")
 else:
  st.dataframe(audit,width="stretch",hide_index=True,column_config={"Sipariş Oranı %":st.column_config.NumberColumn(format="%.2f%%"),"Uygulanan Oran %":st.column_config.NumberColumn(format="%.2f%%"),"Beklenen Komisyon":st.column_config.NumberColumn(format="%.2f TL"),"Satış Komisyonu":st.column_config.NumberColumn(format="%.2f TL"),"Komisyon Düzeltmesi":st.column_config.NumberColumn(format="%.2f TL"),"Gerçek Net Komisyon":st.column_config.NumberColumn(format="%.2f TL"),"Komisyon Avantajı":st.column_config.NumberColumn(format="%.2f TL"),"Fark TL":st.column_config.NumberColumn(format="%.2f TL")})
with st.expander("🧾 Platform hizmet bedeli kayıtları",expanded=True):
 if platform_fees.empty: st.info("PlatformServiceFee filtresiyle kayıt dönmedi.")
 else:
  cols=[c for c in ["transactionDate","transactionType","transactionSubType","description","debt","credit","id","paymentOrderId"] if c in platform_fees.columns]; st.dataframe(platform_fees[cols],width="stretch",hide_index=True) if cols else st.dataframe(platform_fees,width="stretch",hide_index=True)
with st.expander("Finans hareketleri"):
 cols=[c for c in ["transactionDate","_sourceTransactionType","orderNumber","barcode","sellerRevenue","commissionRate","commissionAmount","debt","credit"] if c in settlements.columns]; st.dataframe(settlements[cols],width="stretch",hide_index=True) if cols else st.info("Finans hareketi yok.")
with st.expander("Tüm kesinti / fatura hareketleri"):
 cols=[c for c in ["transactionDate","transactionType","transactionSubType","description","debt","credit","id","paymentOrderId"] if c in deductions.columns]; st.dataframe(deductions[cols],width="stretch",hide_index=True) if cols else st.info("Kesinti hareketi yok.")
