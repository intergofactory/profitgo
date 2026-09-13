from __future__ import annotations
import pandas as pd

def _num(s):
    return pd.to_numeric(s, errors='coerce').fillna(0.0)

def build(lines, settlements, cargo, platform_total=0.0, shared_operational_total=0.0, costs=None):
    """SKU profitability. Direct commission/cargo are matched to SKU; non-direct costs are allocated by revenue."""
    costs=costs or {}
    if lines is None or lines.empty:return pd.DataFrame()
    l=lines.copy()
    for c in ['Sipariş No','Barkod','Model Kodu','Ürün Adı']:
        if c not in l:l[c]=''
        l[c]=l[c].fillna('').astype(str).str.strip()
    l['Ürün Adedi']=_num(l.get('Ürün Adedi',0)); l['Satış']=_num(l.get('Teslim Ciro',0)); l['Satıcı İndirimi']=_num(l.get('Satıcı İndirimi',0))
    key=['Sipariş No','Barkod']
    s=settlements.copy() if settlements is not None else pd.DataFrame(); comm=pd.DataFrame(columns=key+['Gerçek Komisyon'])
    if not s.empty and 'orderNumber' in s:
        s['Sipariş No']=s['orderNumber'].fillna('').astype(str).str.strip(); s['Barkod']=s.get('barcode','').fillna('').astype(str).str.strip(); s['commissionAmount']=_num(s.get('commissionAmount',0))
        typ=s.get('_sourceTransactionType',pd.Series('',index=s.index)).astype(str); s['_c']=0.0
        for t,sg in {'Sale':1,'Return':-1,'CommissionPositive':1,'CommissionNegative':-1,'CommissionPositiveCancel':-1,'CommissionNegativeCancel':1}.items():s.loc[typ.eq(t),'_c']=s.loc[typ.eq(t),'commissionAmount'].abs()*sg
        comm=s.groupby(key,as_index=False)['_c'].sum().rename(columns={'_c':'Gerçek Komisyon'})
    # IMPORTANT: Barkod is already in key. Build unique group columns to avoid pandas "column already exists" reset_index failure.
    group_cols=[]
    for c in ['Model Kodu','Barkod','Ürün Adı']+key:
        if c not in group_cols:group_cols.append(c)
    base=l.groupby(group_cols,as_index=False).agg({'Ürün Adedi':'sum','Satış':'sum','Satıcı İndirimi':'sum'})
    base=base.merge(comm,on=key,how='left'); base['Gerçek Komisyon']=_num(base.get('Gerçek Komisyon',0))
    order_cargo=pd.DataFrame(columns=['Sipariş No','Kargo'])
    if cargo is not None and not cargo.empty and 'orderNumber' in cargo:
        c=cargo.copy(); c['Sipariş No']=c['orderNumber'].fillna('').astype(str).str.strip(); c['Kargo']=_num(c.get('amount',0)).abs(); order_cargo=c.groupby('Sipariş No',as_index=False)['Kargo'].sum()
    order_sales=base.groupby('Sipariş No')['Satış'].transform('sum'); base=base.merge(order_cargo,on='Sipariş No',how='left'); base['Kargo']=_num(base.get('Kargo',0)); base['Kargo Payı']=base['Kargo']*(base['Satış']/order_sales.replace(0,pd.NA)).fillna(0)
    sku=base.groupby(['Model Kodu','Barkod','Ürün Adı'],as_index=False).agg(Adet=('Ürün Adedi','sum'),Satış=('Satış','sum'),Satıcı_İndirimi=('Satıcı İndirimi','sum'),Gerçek_Komisyon=('Gerçek Komisyon','sum'),Kargo=('Kargo Payı','sum'))
    total_sales=float(sku['Satış'].sum()); sku['Gelir Payı']=sku['Satış']/total_sales if total_sales else 0; sku['Platform Payı']=sku['Gelir Payı']*float(platform_total); sku['Reklam/Diğer Payı']=sku['Gelir Payı']*float(shared_operational_total)
    sku['Birim Maliyet']=sku.apply(lambda r:float(costs.get(str(r['Model Kodu']),costs.get(str(r['Barkod']),0.0)) or 0.0),axis=1); sku['Ürün Maliyeti']=sku['Birim Maliyet']*sku['Adet']
    sku['Katkı Kârı']=sku['Satış']-sku['Gerçek_Komisyon']-sku['Kargo']-sku['Platform Payı']-sku['Reklam/Diğer Payı']; sku['Gerçek Net Kâr']=sku['Katkı Kârı']-sku['Ürün Maliyeti']; sku['Net Marj %']=(sku['Gerçek Net Kâr']/sku['Satış'].replace(0,pd.NA)*100).fillna(0)
    sku['Maliyet Durumu']=sku['Birim Maliyet'].gt(0).map({True:'✅ Maliyet Var',False:'⚠️ Maliyet Eksik'}); sku['Kârlılık']=sku.apply(lambda r:'⚪ Maliyet Girilmeli' if r['Birim Maliyet']<=0 else ('🔴 Zarar' if r['Gerçek Net Kâr']<0 else ('🟠 Düşük Marj' if r['Net Marj %']<10 else '🟢 Kârlı')),axis=1)
    return sku.sort_values(['Maliyet Durumu','Gerçek Net Kâr'],ascending=[True,True]).reset_index(drop=True)

def summary(df):
    if df is None or df.empty:return {'sales':0,'profit':0,'margin':0,'costed_skus':0,'missing_skus':0,'loss_skus':0}
    costed=df['Birim Maliyet']>0; sales=float(df.loc[costed,'Satış'].sum()); profit=float(df.loc[costed,'Gerçek Net Kâr'].sum()); return {'sales':sales,'profit':profit,'margin':profit/sales*100 if sales else 0,'costed_skus':int(costed.sum()),'missing_skus':int((~costed).sum()),'loss_skus':int((costed & (df['Gerçek Net Kâr']<0)).sum())}
