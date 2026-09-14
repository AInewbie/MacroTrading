export const THEME_RESEARCH_FORMAT = 'macrotrading-theme-research';
export const THEME_RESEARCH_SCHEMA_VERSION = 1;
export const SOURCE_TYPES = Object.freeze(['Alternative data','News','Blog','Macro data','Financials','Research','Catalyst']);
export const THEME_STANCES = Object.freeze(['Long','Short','Watch']);

const limits = Object.freeze({ evidence:500, themes:100, mappings:50, references:100 });
function fail(message) { throw new Error(`Theme research rejected: ${message}`); }
function object(value, label) { if (!value || typeof value !== 'object' || Array.isArray(value)) fail(`${label} must be an object.`); return value; }
function array(value, label, maximum) { if (!Array.isArray(value)) fail(`${label} must be an array.`); if (value.length > maximum) fail(`${label} exceeds the ${maximum} item limit.`); return value; }
function text(value, label, maximum=300) { if (typeof value !== 'string' || !value.trim()) fail(`${label} is required.`); if (value.length > maximum) fail(`${label} exceeds ${maximum} characters.`); return value.trim(); }
function unit(value, label) { if (!Number.isFinite(value) || value < 0 || value > 1) fail(`${label} must be between 0 and 1.`); return value; }
function isoDate(value, label) { const result=text(value,label,40); if (!Number.isFinite(Date.parse(result))) fail(`${label} is not a valid date.`); return new Date(result).toISOString(); }
function safeId(value, label) { const result=text(value,label,80); if (!/^[A-Za-z0-9._:-]+$/.test(result)) fail(`${label} is unsafe.`); return result; }

function normaliseEvidence(value, index) {
  const source=object(value,`evidence ${index+1}`);
  const sourceType=text(source.sourceType,`evidence ${index+1} source type`,40);
  if(!SOURCE_TYPES.includes(sourceType))fail(`evidence ${index+1} has an unsupported source type.`);
  return {
    id:safeId(source.id,`evidence ${index+1} id`),
    title:text(source.title,`evidence ${index+1} title`,180),
    sourceName:text(source.sourceName,`evidence ${index+1} source name`,160),
    sourceType,
    observedAt:isoDate(source.observedAt,`evidence ${index+1} observed time`),
    reliability:unit(source.reliability,`evidence ${index+1} reliability`),
    novelty:unit(source.novelty,`evidence ${index+1} novelty`),
    summary:text(source.summary,`evidence ${index+1} summary`,800),
  };
}

function uniqueReferences(value, label, evidenceIds) {
  const result=[...new Set(array(value??[],label,limits.references).map((id,index)=>safeId(id,`${label} ${index+1}`)))];
  for(const id of result)if(!evidenceIds.has(id))fail(`${label} references missing evidence ${id}.`);
  return result;
}

function normaliseTheme(value, index, evidenceIds) {
  const source=object(value,`theme ${index+1}`);
  const mappings=array(source.mappings??[],`theme ${index+1} mappings`,limits.mappings).map((value,mappingIndex)=>{
    const mapping=object(value,`theme ${index+1} mapping ${mappingIndex+1}`);
    const stance=text(mapping.stance,`theme ${index+1} mapping ${mappingIndex+1} stance`,20);
    if(!THEME_STANCES.includes(stance))fail(`theme ${index+1} mapping ${mappingIndex+1} has an unsupported stance.`);
    return { instrumentId:safeId(mapping.instrumentId,`theme ${index+1} mapping ${mappingIndex+1} instrument id`), stance, rationale:text(mapping.rationale,`theme ${index+1} mapping ${mappingIndex+1} rationale`,400) };
  });
  if(new Set(mappings.map((item)=>item.instrumentId)).size!==mappings.length)fail(`theme ${index+1} contains duplicate instrument mappings.`);
  return {
    id:safeId(source.id,`theme ${index+1} id`),
    title:text(source.title,`theme ${index+1} title`,180),
    thesis:text(source.thesis,`theme ${index+1} thesis`,1000),
    horizon:text(source.horizon,`theme ${index+1} horizon`,80),
    modelConfidence:unit(source.modelConfidence,`theme ${index+1} model confidence`),
    evidenceIds:uniqueReferences(source.evidenceIds,`theme ${index+1} supporting evidence`,evidenceIds),
    contradictingEvidenceIds:uniqueReferences(source.contradictingEvidenceIds,`theme ${index+1} contradicting evidence`,evidenceIds),
    catalystEvidenceIds:uniqueReferences(source.catalystEvidenceIds,`theme ${index+1} catalysts`,evidenceIds),
    invalidation:text(source.invalidation,`theme ${index+1} invalidation`,500),
    mappings,
  };
}

function scoreTheme(theme, evidenceMap, asOf) {
  const supporting=theme.evidenceIds.map((id)=>evidenceMap.get(id));
  const contradicting=theme.contradictingEvidenceIds.map((id)=>evidenceMap.get(id));
  const all=[...supporting,...contradicting];
  const ages=all.map((item)=>Math.max(0,(Date.parse(asOf)-Date.parse(item.observedAt))/86400000));
  const freshness=ages.length?ages.reduce((sum,age)=>sum+Math.max(0,1-age/90),0)/ages.length:0;
  const reliability=all.length?all.reduce((sum,item)=>sum+item.reliability,0)/all.length:0;
  const novelty=all.length?all.reduce((sum,item)=>sum+item.novelty,0)/all.length:0;
  const breadth=Math.min(new Set(all.map((item)=>item.sourceType)).size/4,1);
  const evidenceDepth=Math.min(supporting.length/5,1);
  const catalyst=Math.min(theme.catalystEvidenceIds.length/2,1);
  const contradictionPenalty=Math.min(contradicting.length/Math.max(all.length,1),1)*15;
  const evidenceScore=Math.max(0,Math.min(100,Math.round((freshness*25+reliability*25+breadth*15+novelty*15+evidenceDepth*10+catalyst*10-contradictionPenalty)*10)/10));
  const status=evidenceScore>=72&&breadth>=0.75&&theme.catalystEvidenceIds.length?'Research ready':evidenceScore>=52?'Needs corroboration':'Watch only';
  return {...theme,evidenceScore,status,sourceBreadth:new Set(all.map((item)=>item.sourceType)).size,supportingCount:supporting.length,contradictingCount:contradicting.length};
}

export function createThemeResearch({ evidence, themes, model, detectedAt }) {
  return normaliseThemeResearch({ format:THEME_RESEARCH_FORMAT, schemaVersion:THEME_RESEARCH_SCHEMA_VERSION, evidence, themes, model, detectedAt });
}

export function normaliseThemeResearch(value) {
  const source=object(value,'research document');
  if(source.format!==THEME_RESEARCH_FORMAT)fail(`expected format ${THEME_RESEARCH_FORMAT}.`);
  if(source.schemaVersion!==THEME_RESEARCH_SCHEMA_VERSION)fail(`schema version ${source.schemaVersion??'missing'} is not supported.`);
  const detectedAt=isoDate(source.detectedAt,'detection time');
  const evidence=array(source.evidence,'evidence',limits.evidence).map(normaliseEvidence);
  const evidenceIds=new Set(evidence.map((item)=>item.id));
  if(evidenceIds.size!==evidence.length)fail('evidence ids must be unique.');
  const themes=array(source.themes,'themes',limits.themes).map((item,index)=>normaliseTheme(item,index,evidenceIds));
  if(new Set(themes.map((item)=>item.id)).size!==themes.length)fail('theme ids must be unique.');
  const modelSource=object(source.model,'model disclosure');
  const model={ provider:text(modelSource.provider,'model provider',120), name:text(modelSource.name,'model name',120), mode:text(modelSource.mode,'model mode',80) };
  const evidenceMap=new Map(evidence.map((item)=>[item.id,item]));
  for(const theme of themes){
    for(const id of theme.catalystEvidenceIds)if(evidenceMap.get(id).sourceType!=='Catalyst')fail(`theme ${theme.id} catalyst ${id} must use the Catalyst source type.`);
    for(const id of theme.contradictingEvidenceIds)if(theme.evidenceIds.includes(id))fail(`theme ${theme.id} cannot use ${id} as both supporting and contradicting evidence.`);
  }
  return { format:THEME_RESEARCH_FORMAT, schemaVersion:THEME_RESEARCH_SCHEMA_VERSION, detectedAt, model, evidence, themes:themes.map((theme)=>scoreTheme(theme,evidenceMap,detectedAt)) };
}
