import unittest
from macrotrading.portfolio import validate_workspace,analyse_portfolio,stress_portfolio
from macrotrading.execution import create_order,execute_paper,rebalance_orders,pre_trade_checks,proposal
from helpers import workspace,AT

class AccountingTests(unittest.TestCase):
 def fill(self,w,side,q,**extra):
  w=validate_workspace(w);o=create_order(w,{'instrument_id':'asset','side':side,'quantity':q,'order_type':'Market',**extra},AT);w['orders'].append(o);return execute_paper(w,o['id'],AT)
 def test_buy_debits_cash_and_does_not_create_nav(self):
  w=workspace();before=analyse_portfolio(w,AT)['nav'];w,r=self.fill(w,'Buy',10)
  self.assertEqual(r['status'],'Filled');self.assertEqual(w['cash']['USD'],99000);self.assertEqual(w['positions'][0]['average_price'],100);self.assertEqual(analyse_portfolio(w,AT)['nav'],before)
 def test_add_close_and_flip_cost_basis(self):
  w,_=self.fill(workspace(),'Buy',10);w['instruments'][0]['price']=120;w,_=self.fill(w,'Buy',10)
  self.assertEqual(w['positions'][0]['average_price'],110)
  w,_=self.fill(w,'Sell',5);self.assertEqual(w['positions'][0]['average_price'],110);self.assertEqual(w['realized_pnl']['USD'],50)
  w,_=self.fill(w,'Sell',20);self.assertEqual(w['positions'][0]['quantity'],-5);self.assertEqual(w['positions'][0]['average_price'],120);self.assertEqual(w['realized_pnl']['USD'],200)
 def test_repeated_fill_is_idempotent(self):
  w,r=self.fill(workspace(),'Buy',10);again,result=execute_paper(w,r['fill']['order_id'],AT)
  self.assertEqual(again,w);self.assertEqual(result['status'],'Already filled');self.assertEqual(len(again['fills']),1)
 def test_limit_includes_slippage_and_cannot_cross_limit(self):
  w=workspace();w['policy']['slippage_bps']=2;w,r=self.fill(w,'Buy',10,order_type='Limit',limit_price=100)
  self.assertEqual(r['status'],'Unfilled');self.assertEqual(w['cash']['USD'],100000);self.assertEqual(w['fills'],[])
 def test_fees_and_slippage_reduce_nav(self):
  w=workspace();w['policy'].update(slippage_bps=2,commission_bps=1);w,r=self.fill(w,'Buy',10)
  self.assertAlmostEqual(analyse_portfolio(w,AT)['nav'],100000-.2-.10002,places=8)
 def test_future_uses_unrealized_value_and_realizes_on_close(self):
  w=workspace('future');w,_=self.fill(w,'Buy',2);self.assertEqual(w['cash']['USD'],100000);self.assertEqual(analyse_portfolio(w,AT)['nav'],100000)
  w['instruments'][0]['price']=110;self.assertEqual(analyse_portfolio(w,AT)['nav'],101000)
  w,r=self.fill(w,'Sell',2);self.assertEqual(r['status'],'Filled');self.assertEqual(w['cash']['USD'],101000);self.assertEqual(w['realized_pnl']['USD'],1000)
 def test_insufficient_cash_and_stale_marks_block(self):
  w=workspace();w['cash']['USD']=50;after,r=self.fill(w,'Buy',1);self.assertEqual(r['status'],'Blocked');self.assertEqual(after['cash'],w['cash'])
  w=workspace();w['instruments'][0]['price_at']='2026-01-01';after,r=self.fill(w,'Buy',1);self.assertEqual(r['status'],'Blocked')
 def test_missing_fx_is_unavailable_not_one_to_one(self):
  w=workspace();w['instruments'][0]['currency']='EUR';w['positions']=[{'instrument_id':'asset','quantity':1,'average_price':100}]
  r=analyse_portfolio(w,AT);self.assertIsNone(r['nav']);self.assertFalse(r['complete'])
  w['fx_rates']=[{'from':'EUR','to':'USD','rate':1.1,'as_of':AT}];self.assertEqual(analyse_portfolio(w,AT)['nav'],100110)
 def test_zero_position_can_rebalance(self):
  w=workspace();w['positions']=[{'instrument_id':'asset','quantity':0,'average_price':0,'target_weight':.1}]
  orders=rebalance_orders(w,AT);self.assertEqual(orders[0]['quantity'],100);self.assertEqual(orders[0]['side'],'Buy')
 def test_options_require_greeks_and_use_point_vega(self):
  w=workspace('option');w['positions']=[{'instrument_id':'asset','quantity':2,'average_price':5}]
  self.assertEqual(analyse_portfolio(w,AT)['vega'],20);self.assertEqual(analyse_portfolio(w,AT)['gamma_1pct_pnl'],1)
  del w['instruments'][0]['gamma'];self.assertFalse(analyse_portfolio(w,AT)['complete']);self.assertIsNone(stress_portfolio(w,AT)[0]['pnl'])
 def test_option_proposal_uses_a_valid_limit(self):
  r=proposal(workspace('option'),{'instrument_id':'asset','side':'Buy','quantity':1},as_of=AT)
  self.assertTrue(r['eligible_for_review']);self.assertEqual(r['order']['order_type'],'Limit');self.assertEqual(r['after']['nav'],100000)
 def test_expired_option_and_unstaged_import_are_blocked(self):
  w=workspace('option');w['instruments'][0]['expiry']='2026-01-01';after,r=self.fill(w,'Buy',1,order_type='Limit',limit_price=6);self.assertEqual(r['status'],'Blocked')
  w=validate_workspace(workspace());o=create_order(w,{'instrument_id':'asset','side':'Buy','quantity':1,'order_type':'Market'},AT);o['status']='Imported';w['orders']=[o]
  with self.assertRaisesRegex(ValueError,'freshly staged'):execute_paper(w,o['id'],AT)
 def test_stop_orders_and_fractional_lots_are_rejected(self):
  for extra in [{'order_type':'Stop'},{'quantity':.5}]:
   with self.assertRaises(ValueError):create_order(validate_workspace(workspace()),{'instrument_id':'asset','side':'Buy','quantity':1,'order_type':'Market',**extra},AT)
 def test_bond_price_units_and_dv01(self):
  w=workspace('bond');w['positions']=[{'instrument_id':'asset','quantity':2,'average_price':99}];a=analyse_portfolio(w,AT)
  self.assertEqual(a['rows'][0]['market_value'],2000);self.assertEqual(a['dv01'],1)
