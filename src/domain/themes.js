export const EVIDENCE_TYPES = Object.freeze([
  'News', 'Blog', 'Macro', 'Financial', 'Alternative', 'Catalyst',
]);
export const THEME_DIRECTIONS = Object.freeze(['Bullish', 'Bearish', 'Mixed']);
export const THEME_HORIZONS = Object.freeze(['Days', 'Weeks', 'Months', 'Structural']);
export const MAX_THEME_EVIDENCE = 1_000;
export const MAX_THEMES = 100;

function finite(value, label, minimum=0, maximum=1) {
  if (!Number.isFinite(value) || value < minimum || value > maximum) throw new Error(`${label} must be between ${minimum} and ${maximum}.`);
  return value;
}
function text(value, label, maximum=500) {
  if (typeof value !== 'string' || !value.trim()) throw new Error(`${label} is required.`);
  if (value.length > maximum) throw new Error(`${label} exceeds ${maximum} characters.`);
  return value.trim();
}

export function normaliseEvidence(value, index=0) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`Evidence ${index + 1} must be an object.`);
  if (!EVIDENCE_TYPES.includes(value.type)) throw new Error(`Evidence ${index + 1} has an unsupported type.`);
  const publishedAt = text(value.publishedAt, `Evidence ${index + 1} published time`, 40);
  if (!Number.isFinite(Date.parse(publishedAt))) throw new Error(`Evidence ${index + 1} has an invalid published time.`);
  const url = value.url == null ? null : text(value.url, `Evidence ${index + 1} URL`, 1_000);
  if (url && !/^https:\/\//i.test(url)) throw new Error(`Evidence ${index + 1} URL must use HTTPS.`);
  return {
    id:text(value.id, `Evidence ${index + 1} id`, 100), type:value.type,
    source:text(value.source, `Evidence ${index + 1} source`, 120), url,
    title:text(value.title, `Evidence ${index + 1} title`, 240),
    summary:text(value.summary, `Evidence ${index + 1} summary`, 1_500), publishedAt,
    reliability:finite(value.reliability, `Evidence ${index + 1} reliability`),
    novelty:finite(value.novelty, `Evidence ${index + 1} novelty`),
    sentiment:finite(value.sentiment, `Evidence ${index + 1} sentiment`, -1, 1),
    themes:[...new Set((Array.isArray(value.themes) ? value.themes : []).map((item) => text(item, `Evidence ${index + 1} theme`, 80)))].slice(0, 12),
    entities:[...new Set((Array.isArray(value.entities) ? value.entities : []).map((item) => text(item, `Evidence ${index + 1} entity`, 80)))].slice(0, 30),
    dataTimestamp:value.dataTimestamp == null ? publishedAt : text(value.dataTimestamp, `Evidence ${index + 1} data timestamp`, 40),
  };
}

export function normaliseThemeSettings(value={}) {
  const source = value && typeof value === 'object' && !Array.isArray(value) ? value : {};
  const weights = source.weights && typeof source.weights === 'object' ? source.weights : {};
  const result = {
    halfLifeDays:finite(source.halfLifeDays ?? 21, 'Theme half-life', 1, 365),
    minimumSources:finite(source.minimumSources ?? 2, 'Minimum sources', 1, 20),
    weights:{
      reliability:finite(weights.reliability ?? 0.30, 'Reliability weight'),
      freshness:finite(weights.freshness ?? 0.25, 'Freshness weight'),
      novelty:finite(weights.novelty ?? 0.15, 'Novelty weight'),
      breadth:finite(weights.breadth ?? 0.20, 'Breadth weight'),
      catalyst:finite(weights.catalyst ?? 0.10, 'Catalyst weight'),
    },
  };
  const total = Object.values(result.weights).reduce((sum, item) => sum + item, 0);
  if (Math.abs(total - 1) > 0.0001) throw new Error('Theme scoring weights must sum to 1.');
  return result;
}

export function normaliseThemeResearch(value, instruments) {
  const source = value && typeof value === 'object' && !Array.isArray(value) ? value : {};
  const evidence = (Array.isArray(source.evidence) ? source.evidence : []).slice(0, MAX_THEME_EVIDENCE).map(normaliseEvidence);
  const instrumentIds = new Set(instruments.map((item) => item.id));
  const themes = (Array.isArray(source.themes) ? source.themes : []).slice(0, MAX_THEMES).map((theme, index) => ({
    id:text(theme.id, `Theme ${index + 1} id`, 100),
    name:text(theme.name, `Theme ${index + 1} name`, 160),
    thesis:text(theme.thesis, `Theme ${index + 1} thesis`, 1_500),
    direction:THEME_DIRECTIONS.includes(theme.direction) ? theme.direction : 'Mixed',
    horizon:THEME_HORIZONS.includes(theme.horizon) ? theme.horizon : 'Weeks',
    score:finite(theme.score, `Theme ${index + 1} score`, 0, 100),
    confidence:finite(theme.confidence, `Theme ${index + 1} confidence`),
    evidenceIds:(Array.isArray(theme.evidenceIds) ? theme.evidenceIds : []).filter((id) => evidence.some((item) => item.id === id)),
    catalysts:(Array.isArray(theme.catalysts) ? theme.catalysts : []).map((item) => text(item, `Theme ${index + 1} catalyst`, 240)).slice(0, 12),
    invalidation:(Array.isArray(theme.invalidation) ? theme.invalidation : []).map((item) => text(item, `Theme ${index + 1} invalidation`, 240)).slice(0, 12),
    expressions:(Array.isArray(theme.expressions) ? theme.expressions : []).filter((item) => instrumentIds.has(item.instrumentId)).map((item) => ({
      instrumentId:item.instrumentId, stance:['Long','Short','Relative value','Hedge'].includes(item.stance) ? item.stance : 'Hedge',
      fit:finite(item.fit, `Theme ${index + 1} expression fit`), rationale:text(item.rationale, `Theme ${index + 1} expression rationale`, 500),
    })).slice(0, 20),
    generatedBy:theme.generatedBy === 'AI candidate' ? 'AI candidate' : 'Deterministic demo',
    detectedAt:text(theme.detectedAt, `Theme ${index + 1} detected time`, 40),
  }));
  return { evidence, themes, settings:normaliseThemeSettings(source.settings), lastRun:source.lastRun ?? null };
}
