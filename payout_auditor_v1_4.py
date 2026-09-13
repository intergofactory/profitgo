from __future__ import annotations
import pandas as pd

def _n(s): return pd.to_numeric(s,errors='coerce').fillna(0.0)

def settlement_effect(df):
    """Current-account effect of settlement rows.

    Hakediş mutabakatında sellerRevenue değil cari hesap debt/credit hareketi
    kullanılmalıdır. Örn. Sale satırında credit, sellerRevenue + commission
    bileşenlerini taşıyabilir; ilgili komisyon/fatura borçları cari hesapta ayrıca
    kapanır. Bu nedenle payment-order ile aynı muhasebe ekseninde credit-debt
    kullanıyoruz.
    """
    if df is None or df.empty:return 0.0,pd.DataFrame()
    w=df.copy(); debt=_n(w.get('debt',pd.Series(0,index=w.index))); credit=_n(w.get('credit',pd.Series(0,index=w.index)))
    w['Etki']=credit-debt
    w['Tür']=w.get('_sourceTransactionType',w.get('transactionType',pd.Series('',index=w.index))).astype(str)
    return float(w['Etki'].sum()),w

def other_effect(df):
    if df is None or df.empty:return 0.0,pd.DataFrame()
    w=df.copy(); debt=_n(w.get('debt',pd.Series(0,index=w.index))); credit=_n(w.get('credit',pd.Series(0,index=w.index)))
    w['Tür']=w.get('_sourceTransactionType',w.get('transactionType',pd.Series('',index=w.index))).astype(str)
    w['Etki']=credit-debt
    # PaymentOrder is the clearing/payment entry itself. Including it in the
    # pre-payment balance would subtract the payout a second time.
    pre=w.loc[~w['Tür'].eq('PaymentOrder')].copy()
    return float(pre['Etki'].sum()),w

def audit(payment_order,settlements,other_financials):
    se,srows=settlement_effect(settlements); oe,orows=other_effect(other_financials)
    expected=se+oe; paid=float(payment_order.get('amount') or 0); diff=paid-expected
    by_type=pd.DataFrame()
    if not orows.empty:
        by_type=orows.loc[~orows['Tür'].eq('PaymentOrder')].groupby('Tür',as_index=False).agg(Etki=('Etki','sum'),Kayıt=('Etki','size')).sort_values('Etki')
    return {'paymentOrderId':payment_order.get('id'),'payoutDate':payment_order.get('payoutDate'),'paid':paid,'settlement_effect':se,'other_effect':oe,'expected':expected,'difference':diff,'status':'🟢 MUTABIK' if abs(diff)<=0.05 else '🟠 FARK VAR','settlement_rows':srows,'other_rows':orows,'other_by_type':by_type}
