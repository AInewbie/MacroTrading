import { normaliseEvidence, normaliseThemeSettings } from '../domain/themes.js';

const clamp = (value, minimum=0, maximum=1) => Math.min(maximum, Math.max(minimum, value));
const average = (values) => values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;

export function evidenceFreshness(publishedAt, now, halfLifeDays) {
  const ageDays = Math.max(0, (now.getTime() - Date.parse(publishedAt)) / 86_400_000);
  return 2 ** (-ageDays / halfLifeDays);
}

export function scoreThemeEvidence(items, settings, now=new Date()) {
  const config = normaliseThemeSettings(settings), evidence = items.map(normaliseEvidence);
  const sources = new Set(evidence.map((item) => item.source.toLowerCase()));
  const types = new Set(evidence.map((item) => item.type));
  const reliability = average(evidence.map((item) => item.reliability));
  const freshness = average(evidence.map((item) => evidenceFreshness(item.publishedAt, now, config.halfLifeDays)));
  const novelty = average(evidence.map((item) => item.novelty));
  const breadth = clamp((sources.size / Math.max(config.minimumSources, 1)) * 0.65 + (types.size / 6) * 0.35);
  const catalyst = evidence.some((item) => item.type === 'Catalyst') ? 1 : 0;
  const components = { reliability, freshness, novelty, breadth, catalyst };
  const score = Object.entries(config.weights).reduce((total, [key, weight]) => total + components[key] * weight, 0) * 100;
  const confidence = clamp(Math.min(1, sources.size / config.minimumSources) * average([reliability, breadth]));
  return { score:Number(score.toFixed(1)), confidence:Number(confidence.toFixed(3)), components, sourceCount:sources.size, typeCount:types.size };
}

export function detectThemes(evidence, definitions, instruments, settings, now=new Date()) {
  const cleanEvidence = evidence.map(normaliseEvidence), instrumentIds = new Set(instruments.map((item) => item.id));
  return definitions.flatMap((definition) => {
    const items = cleanEvidence.filter((item) => item.themes.includes(definition.id));
    if (!items.length) return [];
    const scored = scoreThemeEvidence(items, settings, now);
    if (scored.sourceCount < settings.minimumSources) return [];
    const sentiment = average(items.map((item) => item.sentiment));
    return [{
      id:definition.id, name:definition.name, thesis:definition.thesis,
      direction:Math.abs(sentiment) < 0.12 ? 'Mixed' : sentiment > 0 ? 'Bullish' : 'Bearish',
      horizon:definition.horizon, score:scored.score, confidence:scored.confidence,
      components:scored.components, evidenceIds:items.map((item) => item.id),
      catalysts:definition.catalysts, invalidation:definition.invalidation,
      expressions:definition.expressions.filter((item) => instrumentIds.has(item.instrumentId)),
      generatedBy:'Deterministic demo', detectedAt:now.toISOString(),
    }];
  }).sort((left, right) => right.score - left.score);
}

export function buildEvidenceDigest(evidence) {
  return evidence.map((item) => ({
    evidence_id:item.id, type:item.type, source:item.source, title:item.title,
    summary:item.summary, published_at:item.publishedAt, data_timestamp:item.dataTimestamp,
    reliability:item.reliability, novelty:item.novelty, sentiment:item.sentiment,
    entities:item.entities,
  }));
}
