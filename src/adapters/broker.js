export const BROKER_CAPABILITIES = Object.freeze({
  paper: { marketData:'Synthetic', execution:'Paper', live:false },
  ibkr: { marketData:'Not configured', execution:'Disabled', live:false },
  alpaca: { marketData:'Not configured', execution:'Disabled', live:false },
});

export function assertLiveExecutionConfiguration(config) {
  const errors = [];
  if (!config?.broker || config.broker === 'paper') errors.push('A live broker must be selected.');
  if (!config?.accountId) errors.push('Broker account id is required.');
  if (!config?.explicitLiveApproval) errors.push('Explicit live-trading approval is required.');
  if (!config?.idempotencyKey) errors.push('An idempotency key is required.');
  if (!config?.riskPolicyVersion) errors.push('A versioned risk policy is required.');
  return errors;
}
