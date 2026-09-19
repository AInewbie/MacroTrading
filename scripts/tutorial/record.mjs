// Real browser interactions against a disposable local server on the CI runner.
// No changes to application source, real holdings, credentials or live providers.
import {chromium} from 'playwright';
import {spawn, execFileSync} from 'node:child_process';
import {mkdir, writeFile, mkdtemp} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import assert from 'node:assert/strict';

const output='tutorial-output';
await mkdir(output+'/screenshots',{recursive:true});
const stateDir=await mkdtemp(join(tmpdir(),'macrotrading-tutorial-'));
execFileSync('python3',['scripts/tutorial/seed.py',stateDir],{stdio:'inherit'});
const server=spawn('python3',['run.py','--port','4179','--data-dir',stateDir],{stdio:['ignore','pipe','pipe']});
server.stdout.on('data',b=>process.stdout.write(b));
server.stderr.on('data',b=>process.stderr.write(b));
const base='http://127.0.0.1:4179';
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
let ready=false;
for(let n=0;n<60;n++){
  try{if((await fetch(base+'/api/health')).ok){ready=true;break;}}catch{}
  await delay(250);
}
assert.ok(ready,'Demo server did not start');

const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_BIN});
const context=await browser.newContext({viewport:{width:1600,height:800},deviceScaleFactor:1});
// The browser cannot call any external source or AI endpoint while recording.
await context.route('**/*',route=>route.request().url().startsWith(base+'/')?route.continue():route.abort());
const page=await context.newPage();
page.setDefaultTimeout(20000);
const errors=[];
page.on('pageerror',e=>errors.push(String(e)));
await page.goto(base);
await page.locator('#nav a').first().waitFor();
await page.getByRole('button',{name:'Load historical example',exact:true}).waitFor();

// Capture the rendered browser via CDP, then hold each real frame at 12 fps.
// This avoids dependency on a separately downloaded browser video encoder.
const cdp=await context.newCDPSession(page);
let latestFrame=await page.screenshot({type:'jpeg',quality:88});
cdp.on('Page.screencastFrame',event=>{
  latestFrame=Buffer.from(event.data,'base64');
  cdp.send('Page.screencastFrameAck',{sessionId:event.sessionId}).catch(()=>{});
});
await cdp.send('Page.startScreencast',{format:'jpeg',quality:88,maxWidth:1600,maxHeight:800,everyNthFrame:1});
const encoder=spawn('ffmpeg',['-y','-loglevel','warning','-f','image2pipe','-framerate','12','-vcodec','mjpeg','-i','pipe:0','-an','-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p',output+'/raw.mp4'],{stdio:['pipe','ignore','pipe']});
encoder.stderr.on('data',b=>process.stderr.write(b));
let encoderError=null;
encoder.stdin.on('error',e=>{encoderError=e;});
let frames=0;
const frameTimer=setInterval(()=>{
  if(!encoder.stdin.destroyed&&encoder.stdin.writableLength<4_000_000){encoder.stdin.write(latestFrame);frames++;}
},1000/12);
const scenes=[];
const highlights=[];
const clock=()=>frames/12;
async function snapshot(){return (await (await fetch(base+'/api/state')).json());}
async function click(locator){
  await locator.scrollIntoViewIfNeeded();
  const box=await locator.boundingBox();
  if(box)highlights.push({...box,start:clock(),end:clock()+1.25});
  await delay(550);
  await locator.click();
  await delay(450);
}
async function nav(id){await click(page.locator('#nav a[href="#'+id+'"]'));await page.evaluate(()=>scrollTo(0,0));}
async function closeModal(){await click(page.getByRole('button',{name:'Close',exact:true}));}
async function scene(chapter,text,action=null,seconds=7){
  const row={chapter,text,start:clock()};
  scenes.push(row);
  console.log('SCENE',scenes.length,chapter);
  if(action)await action();
  await delay(300);
  await page.screenshot({path:output+'/screenshots/'+String(scenes.length).padStart(2,'0')+'.jpg',type:'jpeg',quality:90});
  await delay(seconds*1000);
  row.end=clock();
}
const japanCard=()=>page.locator('.theme-card').filter({has:page.locator('[data-action="decision"][data-id="japan_normalization"]')});
let beforeOrder,filledOrder;
try{
  await scene('01 / WELCOME','Start here after launching the app. This walkthrough uses a disposable demo portfolio, not live trading.',null,7);
  await scene('02 / FIRST REVIEW','Click Load historical example. The dated research fixture and synthetic portfolio are for learning only.',async()=>{
    await click(page.getByRole('button',{name:'Load historical example',exact:true}));
    await page.getByRole('link',{name:'Open full HTML report ↗',exact:true}).waitFor();
  },8);
  await scene('03 / RESEARCH THEMES','Open Research themes. Read WATCH, evidence freshness, market coverage and lifecycle as separate signals.',async()=>{await nav('themes');},7);
  await scene('03 / RESEARCH THEMES','Expand the evidence trail. Inspect classification, timestamps and sources before changing conviction.',async()=>{
    await japanCard().scrollIntoViewIfNeeded();
    await click(japanCard().locator('summary').filter({hasText:'Evidence and contradictions'}));
    await japanCard().locator('.evidence').first().scrollIntoViewIfNeeded();
  },8);
  await scene('04 / EVIDENCE INBOX','Sources & evidence contains incoming items. This seeded example is synthetic; no external source is fetched here.',async()=>{await nav('sources');},8);
  await scene('04 / REVIEW BEFORE ACCEPTING','Click Review & accept. Choose the theme and classification, then write the claim you actually reviewed.',async()=>{
    await click(page.locator('[data-action="review-candidate"]'));
    await page.locator('form[data-form="evidence"] select[name="kind"]').selectOption('inference');
    await page.locator('form[data-form="evidence"] select[name="direction"]').selectOption('neutral');
    await page.locator('form[data-form="evidence"] textarea[name="summary"]').fill('Tutorial-only inference: require another corroborating observation before changing this thesis. Not a real market claim.');
  },8);
  await scene('04 / SAVE REVIEWED EVIDENCE','Accepting evidence creates a research run. Blank component fields preserve accepted values; AI never approves itself.',async()=>{
    await click(page.getByRole('button',{name:'Accept evidence & run review',exact:true}));
    await page.locator('#modal').waitFor({state:'hidden'});
    assert.equal((await snapshot()).inbox.find(c=>c.id==='tutorial-policy-candidate').status,'accepted');
    await japanCard().scrollIntoViewIfNeeded();
  },7);
  await scene('05 / RECORD A DECISION','Use Record decision to suspend a thesis with a clear reason. This does not create a position or an order.',async()=>{
    await click(page.locator('[data-action="decision"][data-id="japan_normalization"]'));
    await page.locator('form[data-form="decision"] select[name="action"]').selectOption('suspend');
    await page.locator('form[data-form="decision"] textarea[name="reason"]').fill('Tutorial decision: pause the thesis until a new independently reviewed observation resolves the uncertainty.');
  },8);
  await scene('05 / PERSISTENT JOURNAL','Save the decision. Suspension persists across later runs; resuming requires an explicit reviewed transition.',async()=>{
    await click(page.getByRole('button',{name:'Save decision & run review',exact:true}));
    await page.locator('#modal').waitFor({state:'hidden'});
    assert.equal((await snapshot()).research.themes.japan_normalization.lifecycle,'suspended');
  },8);
  await scene('06 / PORTFOLIO','Open Portfolio. Check cash, NAV, cost basis and holdings before assessing any new quantity.',async()=>{await nav('portfolio');beforeOrder=await snapshot();},7);
  await scene('07 / PORTFOLIO RISK','Review DV01, option sensitivities and scenario losses. These use supplied assumptions, not full broker risk models.',async()=>{await nav('risk');},8);
  await scene('07 / ASSESS A QUANTITY','Scroll to Assess a proposed expression. For this independent demo trade, select AAPL and a quantity of five.',async()=>{
    const form=page.locator('form[data-form="proposal"]');await form.scrollIntoViewIfNeeded();
    await form.locator('[name="instrument_id"]').selectOption('stk-aapl');
    await form.locator('[name="quantity"]').fill('5');
    await form.locator('[name="theme_id"]').selectOption('');
  },7);
  await scene('07 / COMPARE BEFORE AND AFTER','Calculate portfolio impact. Read incremental stress loss, estimated costs and the pre-trade controls.',async()=>{
    await click(page.getByRole('button',{name:'Calculate portfolio impact',exact:true}));
    await page.getByRole('button',{name:'Stage this paper proposal',exact:true}).waitFor();
    await page.getByText('Incremental worst loss',{exact:true}).scrollIntoViewIfNeeded();
  },9);
  await scene('08 / STAGE, THEN EXECUTE','Stage this paper proposal only after reviewing it. Staging records the order but does not change holdings.',async()=>{
    await click(page.getByRole('button',{name:'Stage this paper proposal',exact:true}));
    await page.getByRole('heading',{name:'Paper order staged',exact:true}).waitFor();
    const s=await snapshot();assert.equal(s.workspace.fills.length,beforeOrder.workspace.fills.length);
    assert.equal(s.workspace.cash.USD,beforeOrder.workspace.cash.USD);
  },8);
  await scene('08 / CHECK EVERY CONTROL','Inspect the control table. A staged order is checked again against current prices and holdings at execution.',async()=>{
    await page.locator('#modal-body details').scrollIntoViewIfNeeded();
  },7);
  await scene('08 / PAPER EXECUTION','Close the checks, then click Paper execute. This is a simulation; there is no live broker route.',async()=>{
    await closeModal();await click(page.getByRole('button',{name:'Paper execute',exact:true}));
    await page.getByText('Paper order: Filled.',{exact:true}).waitFor();
    const s=await snapshot();filledOrder=s.workspace.fills.at(-1);assert.ok(filledOrder);
    assert.equal(s.workspace.fills.length,beforeOrder.workspace.fills.length+1);
    assert.ok(s.workspace.cash.USD<beforeOrder.workspace.cash.USD);
  },8);
  await scene('08 / VERIFY THE FILL','Review the fill price and commission. A limit order would stay unfilled if the simulated price crossed its limit.',async()=>{
    await page.getByRole('heading',{name:'Fills',exact:true}).scrollIntoViewIfNeeded();
  },7);
  await scene('09 / VERIFY ACCOUNTING','Return to Portfolio. Cash and holdings moved together; the trade did not create artificial portfolio value.',async()=>{
    await nav('portfolio');const s=await snapshot();
    const q=x=>x.workspace.positions.find(p=>p.instrument_id==='stk-aapl').quantity;
    assert.equal(q(s)-q(beforeOrder),5);assert.ok(s.portfolio.nav<=beforeOrder.portfolio.nav);
  },8);
  await scene('10 / INSPECT AND EXPORT','All data shows score dimensions, rankings and accepted evidence. Use Export theme CSV for an inspectable table.',async()=>{
    await nav('data');await page.locator('#data-search').fill('Japan');
  },7);
  await scene('11 / SAVE A CURRENT SNAPSHOT','After changing the portfolio, click Run review. Keep a current cutoff and save a new immutable research report.',async()=>{
    await click(page.getByRole('button',{name:'Run review',exact:true}));
  },6);
  await scene('11 / RUN ARCHIVE','Save the review, then open Run archive. Earlier reports remain unchanged when you edit today\'s portfolio.',async()=>{
    await click(page.getByRole('button',{name:'Validate & save',exact:true}));
    await page.locator('#modal').waitFor({state:'hidden'});await nav('history');
  },7);
  await scene('11 / OPEN THE HTML REPORT','Each HTML report retains evidence, lifecycle, portfolio context and a reproduction manifest. Open any saved run.',async()=>{
    // Keep this recording in one tab while using the application's real report link.
    const link=page.getByRole('link',{name:'HTML report ↗',exact:true}).first();
    const href=await link.getAttribute('href');await page.goto(base+href);
    await page.getByRole('heading',{name:'Changes in this run',exact:true}).waitFor();
  },8);
  await scene('12 / SETTINGS AND RECOVERY','Settings contains editable policy and recovery tools. Turn off synthetic demo mode before using your own portfolio.',async()=>{
    await page.goto(base+'/#settings');await page.getByRole('heading',{name:'Workspace identity & data mode',exact:true}).waitFor();
  },8);
  await scene('12 / BACK UP YOUR WORK','Export a workspace or back up state before replacements. A complete history backup also requires the stopped database directory.',async()=>{
    await page.getByRole('heading',{name:'Workspace recovery',exact:true}).scrollIntoViewIfNeeded();
  },8);
  await scene('13 / YOUR DAILY CHECKLIST','Review evidence → record decisions → inspect risk → stage and verify paper trades → save a report and backup.',async()=>{await nav('overview');},9);
  const final=await snapshot();
  assert.deepEqual(errors,[],'Browser runtime errors');
  await writeFile(output+'/verification.json',JSON.stringify({app_revision:'04f6988a0e6db2acb29ea174c04feb2523db04ab',demo_only:true,external_browser_requests_blocked:true,ai_configured:false,accepted_fixture:true,suspension_persisted:final.research.themes.japan_normalization.lifecycle==='suspended',fills_added:final.workspace.fills.length-beforeOrder.workspace.fills.length,cash_before:beforeOrder.workspace.cash.USD,cash_after:final.workspace.cash.USD,nav_before:beforeOrder.portfolio.nav,nav_after:final.portfolio.nav,fill:filledOrder,browser_errors:errors,scenes:scenes.length},null,2));
} finally {
  clearInterval(frameTimer);
  await cdp.send('Page.stopScreencast').catch(()=>{});
  encoder.stdin.end();
  await new Promise((resolve,reject)=>encoder.on('close',code=>code===0?resolve():reject(new Error('Video encoder exited '+code))));
  await writeFile(output+'/timeline.json',JSON.stringify({fps:12,duration:clock(),scenes,highlights},null,2));
  await browser.close();server.kill('SIGTERM');
}
if(encoderError)throw encoderError;
console.log('Recording complete:',clock().toFixed(1),'seconds');
