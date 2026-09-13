from __future__ import annotations
import pandas as pd

# Current Account Statement signs documented by Trendyol.
SETTLEMENT_SIGN={
 'Sale':1,'Return':-1,'Discount':-1,'DiscountCancel':1,'Coupon':1,'CouponCancel':-1,
 'ProvisionPositive':1,'ProvisionNegative':-1,'TYDiscount':-1,'TYDiscountCancel':1,
 'TYCoupon':-1,'TYCouponCancel':1,'ManuelRefund':-1,'ManuelRefundCancel':1,
 'SellerRevenuePositive':1,'SellerRevenueNegative':-1,'CommissionPositive':-1,'CommissionNegative':1,
 'SellerRevenuePositiveCancel':-1,'SellerRevenueNegativeCancel':1,'CommissionPositiveCancel':1,'CommissionNegativeCancel':-1,
}

def _n(s): return pd.to_numeric(s,errors='coerce').fillna(0.0)

def settlement_effect(df):
    if df is None or df.empty:return 0.0,pd.DataFrame()
    w=df.copy(); typ=w.get('_sourceTransactionType',w.get('transactionType',pd.Series('',index=w.index))).astype(str)
    w['Etki']=0.0
    # sellerRevenue is the seller-side net amount for settlement lifecycle rows.
    rev=_n(w.get('sellerRevenue',pd.Series(0,index=w.index)))
    for t,sgn in SETTLEMENT_SIGN.items():w.loc[typ.eq(t),'Etki']=rev.loc[typ.eq(t)].abs()*sgn
    # Pure commission correction rows have sellerRevenue=0; use commissionAmount.
    pure=typ.str.startswith('Commission'); ca=_n(w.get('commissionAmount',pd.Series(0,index=w.index)))
    for t,sgn in SETTLEMENT_SIGN.items():
        m=typ.eq(t)&pure; w.loc[m,'Etki']=ca.loc[m].abs()*sgn
    w['Tür']=typ
    return float(w['Etki'].sum()),w

def other_effect(df):
    if df is None or df.empty:return 0.0,pd.DataFrame()
    w=df.copy(); debt=_n(w.get('debt',pd.Series(0,index=w.index))); credit=_n(w.get('credit',pd.Series(0,index=w.index)))
    # Current-account convention: credit increases seller receivable; debt reduces it.
    w['Etki']=credit-debt
    w['Tür']=w.get('_sourceTransactionType',w.get('transactionType',pd.Series('',index=w.index))).astype(str)
    return float(w['Etki'].sum()),w

def audit(payment_order,settlements,other_financials):
    se,srows=settlement_effect(settlements); oe,orows=other_effect(other_financials)
    expected=se+oe; paid=float(payment_order.get('amount') or 0); diff=paid-expected
    return {'paymentOrderId':payment_order.get('id'),'payoutDate':payment_order.get('payoutDate'),'paid':paid,'settlement_effect':se,'other_effect':oe,'expected':expected,'difference':diff,'status':'🟢 MUTABIK' if abs(diff)<=0.05 else '🟠 FARK VAR','settlement_rows':srows,'other_rows':orows}
