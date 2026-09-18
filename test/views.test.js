import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {esc,csv,safeUrl} from '../public/js/components.js';
import {overview} from '../public/js/overview.js';
import {themes,sources,decisions,decisionForm} from '../public/js/research.js';
import {portfolio,risk,orders,ticketForm,proposalForm} from '../public/js/portfolio.js';
import {history,dataView,settings,evaluation} from '../public/js/operations.js';
const source=`from macrotrading.service import Service
from pathlib import Path
from tempfile import TemporaryDirectory
import json
with TemporaryDirectory() as t:
 s=Service(Path.cwd(),t)
 initial=s.snapshot()
 s.run(json.loads(Path('examples/integrated_research_run.json').read_text()))
 print(json.dumps({'initial':initial,'populated':s.snapshot()}))`;
const fixture=JSON.parse(execFileSync(process.env.PYTHON||'python3',['-c',source],{encoding:'utf8',env:{...process.env,PYTHONPATH:'src'}}));
test('UI escapes untrusted evidence and rejects executable URLs',()=>{
 assert.equal(esc('<script>"&'), '&lt;script&gt;&quot;&amp;');
 assert.equal(safeUrl('javascript:alert(1)'),'#');assert.equal(safeUrl('https://example.com'),'https://example.com/');
 const d=structuredClone(fixture.populated);Object.values(d.research.themes)[0].evidence[0].summary='<script>alert(1)</script>';
 assert.ok(!themes(d).includes('<script>'));assert.ok(themes(d).includes('&lt;script&gt;'));
});
test('CSV escapes formulas and embedded delimiters',()=>{
 assert.equal(csv(['Name','Value'],[['=SUM(A1)','say "hi",'],['-cmd',-3]]),'"Name","Value"\r\n"\'=SUM(A1)","say ""hi"","\r\n"\'-cmd","-3"');
});
test('every main view renders both a fresh and populated server state',()=>{
 for(const state of Object.values(fixture))for(const view of [overview,themes,sources,portfolio,risk,orders,decisions,dataView,history,evaluation,settings]){
  const html=view(state);assert.ok(html.length>100,view.name);assert.ok(!html.includes('[object Object]'),view.name);assert.ok(!html.includes('undefined'),view.name);
 }
});
test('decision and execution forms expose separate explicit actions',()=>{
 const d=fixture.populated;assert.ok(decisionForm(d,'japan_normalization').includes('Resume after review'));
 assert.ok(ticketForm(d).includes('Stage and check'));assert.ok(proposalForm(d).includes('risk_budget'));assert.ok(!ticketForm(d).includes('Live'));
});
test('exports expose coverage and source classifications alongside score',()=>{
 const html=dataView(fixture.populated);assert.ok(html.includes('Evidence quality'));assert.ok(html.includes('First known'));assert.ok(html.includes('Lifecycle'));
});
