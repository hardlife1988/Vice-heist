'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),net=require('node:net');
const {spawn}=require('node:child_process'),{once}=require('node:events'),{chromium}=require('playwright');
(async()=>{
 const root=path.resolve(__dirname,'..');const socket=net.createServer().listen(0,'127.0.0.1');await once(socket,'listening');const port=socket.address().port;await new Promise(r=>socket.close(r));
 const server=spawn('python',['-m','http.server',String(port),'--bind','127.0.0.1','--directory',path.join(root,'dist')],{stdio:'ignore'});
 let browser;
 try{
  for(let i=0;i<100;i++){try{if((await fetch(`http://127.0.0.1:${port}/`)).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
  browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{})});
  const ctx=await browser.newContext({reducedMotion:'reduce',viewport:{width:390,height:844}});
  const books=JSON.parse(fs.readFileSync(path.join(root,'dist/books_base.json')));const book=books.find(b=>b.payoutMultiplier>0&&!b.events.some(e=>e.type==='freeSpinTrigger'));
  const balanceStart=100000000;let balance=balanceStart;const calls=[];let pending=null;
  const page=await ctx.newPage();await page.addInitScript(()=>{Math.random=()=>{throw Error('Local RNG used in a Stake session');};HTMLMediaElement.prototype.play=()=>Promise.resolve();});
  await page.route('https://mock-rgs.test/**',async route=>{
   const req=route.request(),name=new URL(req.url()).pathname;
   if(req.method()==='OPTIONS') { await route.fulfill({status:204,headers:{'Access-Control-Allow-Origin':'*','Access-Control-Allow-Methods':'GET, POST, OPTIONS','Access-Control-Allow-Headers':'Content-Type'}}); return; }
   const body=req.method()==='POST'?req.postDataJSON():{};calls.push({name,body});let data;
   if(name==='/wallet/authenticate')data={balance:{amount:balance,currency:'BTC'},config:{minBet:10000,maxBet:100000000,stepBet:10000,defaultBetLevel:10000,betLevels:[10000,1000000,100000000]},jurisdictionFlags:{displayRTP:body.sessionID!=='rtp-hidden'},round:pending};
   else if(name==='/wallet/play'){balance-=body.amount*(body.mode==='bonus'?100:1);pending={betID:1,amount:body.amount,payout:Math.round(book.payoutMultiplier*body.amount/100),payoutMultiplier:book.payoutMultiplier/100,mode:body.mode,active:true,state:book.events};data={balance:{amount:balance,currency:'BTC'},round:pending};}
   else if(name==='/wallet/end-round'){balance+=pending.payout;pending=null;data={balance:{amount:balance,currency:'BTC'}};}
   else if(name==='/bet/event'){pending.event=body.event;data={event:body.event};}
   else if(name.startsWith('/bet/replay/'))data={state:book.events,payoutMultiplier:book.payoutMultiplier/100,costMultiplier:1};
   else throw Error('Unexpected RGS request '+name);
   await route.fulfill({json:data,headers:{'Access-Control-Allow-Origin':'*'}});
  });
  const url=`http://127.0.0.1:${port}/?sessionID=test&rgs_url=https%3A%2F%2Fmock-rgs.test`;
  page.on('pageerror',err=>console.error('Browser page error:',err.message));
  page.on('console',msg=>{if(msg.type()==='error')console.error('Browser console error:',msg.text());});
  page.on('requestfailed',req=>console.error('Browser request failed:',req.url(),req.failure()?.errorText));
  await page.goto(url);await page.waitForFunction(()=>!document.querySelector('#btn-spin').disabled).catch(async err=>{console.error('RGS initialization diagnostic:',JSON.stringify({calls,body:(await page.locator('body').innerText()).slice(0,1500)}));throw err;});
  assert.equal(await page.locator('#bet-select option').count(),3);assert.equal(await page.locator('.demo-tools').isVisible(),false);assert.equal(await page.locator('#top-payouts .payout-symbol').count(),10);
  await page.locator('#btn-spin').click();await page.waitForFunction(()=>!document.querySelector('#btn-spin').disabled);assert.equal(calls.filter(c=>c.name==='/wallet/play').length,1);assert.equal(balance,balanceStart-10000+Math.round(book.payoutMultiplier*10000/100));assert.match(await page.locator('#total-win').innerText(),/^BTC /);
  await page.locator('#btn-bonus-buy').click();await page.locator('#bonus-cancel').click();assert.equal(calls.filter(c=>c.name==='/wallet/play').length,1);
  await page.locator('#btn-bonus-buy').click();await page.locator('#bonus-accept').click();await page.waitForFunction(()=>!document.querySelector('#btn-spin').disabled);assert.deepEqual(calls.filter(c=>c.name==='/wallet/play').at(-1).body,{sessionID:'test',amount:10000,mode:'bonus'});
  const before=calls.length;await page.goto(`http://127.0.0.1:${port}/?replay=true&game=test&version=1&mode=base&event=1&currency=ETH&amount=10000&rgs_url=https%3A%2F%2Fmock-rgs.test`);await page.waitForFunction(()=>!document.querySelector('#btn-spin').disabled);await page.locator('#btn-spin').click();await page.waitForFunction(()=>!document.querySelector('#btn-spin').disabled);assert.equal(calls.length,before+1);assert.match(await page.locator('#total-win').innerText(),/^ETH /);
  await page.goto(`http://127.0.0.1:${port}/?sessionID=rtp-hidden&rgs_url=https%3A%2F%2Fmock-rgs.test`);await page.waitForFunction(()=>!document.querySelector('#btn-spin').disabled);
  assert.equal(await page.locator('.header-badge-rtp').isVisible(),false);
  assert.equal(await page.locator('#rtp-details').isVisible(),false);
  assert.equal(await page.locator('.info-badges span').filter({hasText:'RTP'}).isVisible(),false);
  assert.doesNotMatch(await page.locator('.paytable-note').innerText(),/96% RTP target|RTP is a long-run/i);
  console.log('PASS browser RGS: server outcomes, crypto wallet, bonus confirmation, replay and hidden RTP jurisdiction');
 }finally{if(browser)await browser.close();server.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
