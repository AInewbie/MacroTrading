export const ORDER_TYPES = Object.freeze(['Market', 'Limit', 'Stop']);
export const ORDER_SIDES = Object.freeze(['Buy', 'Sell']);

export function createOrder(input, instrument) {
  const quantity = Number(input.quantity);
  if (!instrument) throw new Error('Select a valid instrument.');
  if (!ORDER_SIDES.includes(input.side)) throw new Error('Invalid order side.');
  if (!ORDER_TYPES.includes(input.orderType)) throw new Error('Invalid order type.');
  if (!Number.isFinite(quantity) || quantity <= 0) throw new Error('Quantity must be positive.');
  const limitPrice = input.orderType === 'Limit' ? Number(input.limitPrice) : null;
  if (input.orderType === 'Limit' && (!Number.isFinite(limitPrice) || limitPrice <= 0)) throw new Error('A positive limit price is required.');
  return {
    id: crypto.randomUUID(), instrumentId: instrument.id, symbol: instrument.symbol,
    assetClass: instrument.assetClass, side: input.side, quantity,
    orderType: input.orderType, limitPrice, status: 'Staged',
    createdAt: new Date().toISOString(), source: input.source || 'Trade ticket',
  };
}
