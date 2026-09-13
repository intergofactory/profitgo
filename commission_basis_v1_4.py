from __future__ import annotations
import pandas as pd


def _num(s):
    return pd.to_numeric(s, errors="coerce").fillna(0.0)


def _weighted_rate(group):
    if group.empty or "commissionRate" not in group.columns:
        return 0.0
    rates=pd.to_numeric(group["commissionRate"],errors="coerce")
    amounts=_num(group.get("commissionAmount",pd.Series(0.0,index=group.index))).abs()
    m=rates.notna() & (rates>0)
    if not m.any(): return 0.0
    return float((rates[m]*amounts[m]).sum()/amounts[m].sum()) if amounts[m].sum()>0 else float(rates[m].mean())


def reconcile(lines, settlements):
    """Reconcile Trendyol commission using the undiscounted line gross amount.

    Trendyol Finance Sale rows can show commission calculated from the pre-seller-discount
    commercial base while seller-funded discounts are separate settlement movements.
    Therefore seller discount must not be subtracted a second time from commission base.
    """
    cols=["Sipariş No","Barkod","Sipariş Oranı %","Uygulanan Oran %","Brüt Komisyon Matrahı","Satıcı İndirimi","Beklenen Komisyon","Gerçek Net Komisyon","Fark TL","Durum"]
    if lines is None or lines.empty or settlements is None or settlements.empty or "orderNumber" not in settlements.columns:
        return pd.DataFrame(columns=cols)

    l=lines.copy()
    l["Sipariş No"]=l["Sipariş No"].astype(str).str.strip()
    l["Barkod"]=l.get("Barkod","").astype(str).str.strip()
    qty=_num(l.get("Ürün Adedi",pd.Series(1.0,index=l.index)))
    gross=_num(l.get("Birim Brüt Fiyat",pd.Series(0.0,index=l.index)))
    l["Brüt Komisyon Matrahı"]=gross*qty
    l["Satıcı İndirimi"]=_num(l.get("Satıcı İndirimi",pd.Series(0.0,index=l.index)))
    l["Sipariş Oranı %"]=_num(l.get("Sipariş Komisyon Oranı %",pd.Series(0.0,index=l.index)))
    l["Beklenen Komisyon"]=l["Brüt Komisyon Matrahı"]*l["Sipariş Oranı %"]/100.0
    keys=["Sipariş No","Barkod"]
    order=l.groupby(keys,as_index=False).agg({"Brüt Komisyon Matrahı":"sum","Satıcı İndirimi":"sum","Beklenen Komisyon":"sum","Sipariş Oranı %":"mean"})

    s=settlements.copy()
    s["Sipariş No"]=s["orderNumber"].astype(str).str.strip()
    s["Barkod"]=s.get("barcode","").astype(str).str.strip()
    s["commissionAmount"]=_num(s.get("commissionAmount",pd.Series(0.0,index=s.index)))
    typ=s.get("_sourceTransactionType",pd.Series("",index=s.index)).astype(str)
    s["signed"]=0.0
    signs={"Sale":1,"Return":-1,"CommissionPositive":1,"CommissionNegative":-1,"CommissionPositiveCancel":-1,"CommissionNegativeCancel":1}
    for t,sign in signs.items():
        s.loc[typ.eq(t),"signed"]=s.loc[typ.eq(t),"commissionAmount"].abs()*sign

    rows=[]
    for (order_no,barcode),g in s.groupby(keys,dropna=False):
        gt=g.get("_sourceTransactionType",pd.Series("",index=g.index)).astype(str)
        rows.append({"Sipariş No":order_no,"Barkod":barcode,"Gerçek Net Komisyon":float(g["signed"].sum()),"Uygulanan Oran %":_weighted_rate(g.loc[gt.eq("Sale")])})
    actual=pd.DataFrame(rows)
    out=order.merge(actual,on=keys,how="inner")
    if out.empty: return pd.DataFrame(columns=cols)
    out["Fark TL"]=out["Gerçek Net Komisyon"]-out["Beklenen Komisyon"]
    tol=out["Beklenen Komisyon"].abs().clip(lower=1)*0.005
    out["Durum"]="🟢 Uyumlu"
    out.loc[out["Fark TL"]>tol,"Durum"]="🟠 İncele"
    out.loc[out["Fark TL"]<-tol,"Durum"]="💚 Komisyon Avantajı / Düzeltme"
    return out[cols].sort_values(["Durum","Fark TL"],ascending=[True,False]).reset_index(drop=True)


def summary(audit):
    if audit is None or audit.empty:
        return {"expected":0.0,"actual":0.0,"positive":0.0,"negative":0.0,"positive_rows":0,"ok_rows":0,"total_rows":0}
    diff=_num(audit["Fark TL"])
    return {
        "expected":float(_num(audit["Beklenen Komisyon"]).sum()),
        "actual":float(_num(audit["Gerçek Net Komisyon"]).sum()),
        "positive":float(diff.clip(lower=0).sum()),
        "negative":float((-diff.clip(upper=0)).sum()),
        "positive_rows":int(audit["Durum"].eq("🟠 İncele").sum()),
        "ok_rows":int(audit["Durum"].eq("🟢 Uyumlu").sum()),
        "total_rows":int(len(audit)),
    }
