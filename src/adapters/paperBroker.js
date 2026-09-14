export class PaperBroker {
  constructor({ slippageBps = 2 } = {}) { this.slippageBps = slippageBps; }
  async submit(order, instrument) {
    const reference = order.limitPrice || instrument.price;
    const direction = order.side === 'Buy' ? 1 : -1;
    const fillPrice = reference * (1 + direction * this.slippageBps / 10000);
    return { broker:'Paper', brokerOrderId:`paper-${crypto.randomUUID()}`, status:'Filled',
      filledQuantity:order.quantity, averageFillPrice:Number(fillPrice.toFixed(6)), filledAt:new Date().toISOString() };
  }
}

export class LiveBrokerDisabled {
  async submit() {
    throw new Error('Live execution is disabled. Configure and approve a broker adapter before sending real orders.');
  }
}
