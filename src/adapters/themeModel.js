import { createThemeResearch } from '../domain/themes.js';

export class ThemeModel {
  async detect() { throw new Error('Theme model adapter must implement detect().'); }
}

export class SyntheticThemeModel extends ThemeModel {
  constructor(proposals, now=()=>new Date()) { super(); this.proposals=proposals; this.now=now; }
  async detect(evidence) {
    return createThemeResearch({
      evidence,
      themes:structuredClone(this.proposals),
      model:{ provider:'Local fixture', name:'Synthetic theme proposer v1', mode:'synthetic-no-api' },
      detectedAt:this.now().toISOString(),
    });
  }
}

export class LiveThemeModelDisabled extends ThemeModel {
  async detect() { throw new Error('Live AI theme detection is disabled until a provider, data licenses, credentials and usage budget are configured.'); }
}
