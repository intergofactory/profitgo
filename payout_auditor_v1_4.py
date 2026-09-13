from __future__ import annotations
import pandas as pd

SETTLEMENT_SIGN={
 'Sale':1,'Return':-1,'Discount':-1,'DiscountCancel':1,'Coupon':1,'CouponCancel':-1,
 'ProvisionPositive':1,'ProvisionNegative':-1,'TYDiscount':-1,'TYDiscountCancel':1,
 'TYCoupon':-1,'TYCouponCancel':1,'ManuelRefund':-1,'ManuelRefundCancel':1,
 'SellerRevenuePositive':1,'SellerRevenueNegative':-1,
 'SellerRevenuePositiveCancel':-1,'SellerRevenueNegativeCancel':1,
}
COMMISSION_SIGN={'CommissionPositive':-1,'CommissionNegative':1,'CommissionPositiveCancel':1,'CommissionNegativeCancel':-1}

def _n(s):return pd.to_numeric(s,errors='coerce').fillna(0.0)

def settlement_effect(df):
 if df is None or df.empty:return 0.0,pd.DataFrame(),pd.DataFrame()
 w=df.copy();typ=w.get('_sourceTransactionType',w.get('transactionType',pd.Series('',index=w.index))).astype(str)
 rev=_n(w.get('sellerRevenue',pd.Series(0,index=w.index)));comm=_n(w.get('commissionAmount',pd.Series(0,index=w.index))).abs()
 w['Etki']=0.0
 for t,sgn in SETTLEMENT_SIGN.items():
  m=typ.eq(t);w.loc[m,'Etki']=rev.loc[m].abs()*sgn
 for t,sgn in COMMISSION_SIGN.items():
  m=typ.eq(t);w.loc[m,'Etki']=comm.loc[m]*sgn
 w['Tür']=typ
 by=w.groupby('Tür',as_index=False).agg(Etki=('Etki','sum'),Kayıt=('Etki','size')).sort_values('Etki',ascending=False)
 return float(w['Etki'].sum()),w,by

def other_effect(df):
 if df is None or df.empty:return 0.0,pd.DataFrame(),pd.DataFrame()
 w=df.copy();debt=_n(w.get('debt',pd.Series(0,index=w.index)));credit=_n(w.get('credit',pd.Series(0,index=w.index)))
 w['Tür']=w.get('_sourceTransactionType',w.get('transactionType',pd.Series('',index=w.index))).astype(str);w['Etki']=credit-debt
 pre=w.loc[~w['Tür'].eq('PaymentOrder')].copy()
 by=pre.groupby('Tür',as_index=False).agg(Etki=('Etki','sum'),Kayıt=('Etki','size')).sort_values('Etki',ascending=False) if not pre.empty else pd.DataFrame()
 return float(pre['Etki'].sum()),w,by

def audit(payment_order,settlements,other_financials):
 se,srows,sby=settlement_effect(settlements);oe,orows,oby=other_effect(other_financials)
 expected=se+oe;paid=float(payment_order.get('amount') or 0);diff=paid-expected
 return {'paymentOrderId':payment_order.get('id'),'payoutDate':payment_order.get('payoutDate'),'paid':paid,'settlement_effect':se,'other_effect':oe,'expected':expected,'difference':diff,'status':'🟢 MUTABIK' if abs(diff)<=0.05 else '🟠 FARK VAR','settlement_rows':srows,'other_rows':orows,'settlement_by_type':sby,'other_by_type':oby}
