'use strict';
const assert=require('node:assert/strict');global.StakeMoney=require('../static/money.js');const RGS=require('../static/rgs.js');
const calls=[];let failure=false;const round={betID:1,amount:10000,payout:1000,payoutMultiplier:.1,active:true,state:[{index:0,type:'finalWin',amount:10}]};
const mock=async(url,options)=>{const body=JSON.parse(options.body);calls.push([url,body]);if(failure)throw Error('network');const result=url.endsWith('authenticate')?{balance:{amount:123456,currency:'BTC'},config:{minBet:10000,maxBet:100000000,stepBet:10000,defaultBetLevel:10000,betLevels:[10000,100000000]},round:null}:url.endsWith('play')?{balance:{amount:113456,currency:'BTC'},round}:url.endsWith('end-round')?{balance:{amount:114456,currency:'BTC'}}:{};return{ok:true,json:async()=>result};};
(async()=>{
 assert.equal(StakeMoney.format(1,'BTC'),'BTC 0.000001');assert.equal(StakeMoney.payout(10,10000),1000);assert.throws(()=>StakeMoney.safe(NaN));
 for(const endpoint of ['https://user:pass@example.test','https://example.test/?token=secret','https://example.test/#fragment','http://example.test'])assert.throws(()=>new RGS(new URLSearchParams({sessionID:'test',rgs_url:endpoint}),mock),/RGS URL|Invalid RGS URL/);
 const allBetLevels=[10000,20000,50000,100000,200000,400000,1000000,2000000,5000000,10000000,20000000,50000000,100000000];
 const levelClient=new RGS(new URLSearchParams('sessionID=levels&rgs_url=https://example.test'),mock);
 levelClient.config={minBet:10000,maxBet:100000000,stepBet:10000,defaultBetLevel:1000000,betLevels:allBetLevels};
 for(const bet of allBetLevels){levelClient.validBet(bet);assert.equal(StakeMoney.payout(100,bet),bet,'1x payout exact at '+bet);assert.equal(StakeMoney.payout(1000000,bet),bet*10000,'10,000x max payout at '+bet);assert.equal(StakeMoney.safe(bet*100),bet*100,'bonus buy exact at '+bet);}
 for(const invalid of [9999,30000,100000001])assert.throws(()=>levelClient.validBet(invalid),/outside Stake limits|Invalid wallet/);
 assert.equal(StakeMoney.format(1,'BTC'),'BTC 0.000001');assert.equal(StakeMoney.format(1234567,'ETH'),'ETH 1.234567');
 const client=new RGS(new URLSearchParams('sessionID=test&rgs_url=https://example.test'),mock);await client.authenticate();assert.throws(()=>client.validBet(20000));assert.throws(()=>client.validBet(100000001));
 const played=await client.play(10000,'bonus');assert.equal(calls.at(-1)[1].amount,10000);assert.equal(client.events(played.round)[0].amount,10);assert.throws(()=>client.events({...round,payout:999}),/cash payout/);assert.throws(()=>client.events({...round,payoutMultiplier:0.2}),/payout does not match/);assert.throws(()=>client.events({...round,state:[{index:0,type:'finalWin',amount:-10}]}),/payout does not match/);await assert.rejects(()=>client.play(10000,'base'));await client.checkpoint(0);await client.finish();assert.equal(client.round,null);
 const zeroCalls=[];const zeroRound={betID:2,amount:10000,payout:0,payoutMultiplier:0,active:true,state:[{index:0,type:'finalWin',amount:0}]};
 const zeroMock=async(url,options)=>{zeroCalls.push(url);const result=url.endsWith('authenticate')?{balance:{amount:100000,currency:'USD'},config:{minBet:10000,maxBet:100000,stepBet:10000,defaultBetLevel:10000,betLevels:[10000]},round:null}:url.endsWith('play')?{balance:{amount:90000,currency:'USD'},round:zeroRound}:{};return {ok:true,json:async()=>result};};
 const zeroClient=new RGS(new URLSearchParams('sessionID=zero&rgs_url=https://example.test'),zeroMock);await zeroClient.authenticate();await zeroClient.play(10000,'base');assert.equal(zeroClient.events(zeroClient.round)[0].amount,0);await zeroClient.finish();assert.equal(zeroClient.round,null);assert.equal(zeroCalls.filter(x=>x.endsWith('/wallet/end-round')).length,0,'zero payout must not send end-round');
 let endFailures=0;const endRound={betID:3,amount:10000,payout:1000,payoutMultiplier:0.1,active:true,state:[{index:0,type:'finalWin',amount:10}]};
 const interrupted=async(url,options)=>{const result=url.endsWith('authenticate')?{balance:{amount:100000,currency:'BTC'},config:{minBet:10000,maxBet:10000,stepBet:10000,defaultBetLevel:10000,betLevels:[10000]},round:null}:url.endsWith('play')?{balance:{amount:90000,currency:'BTC'},round:endRound}:url.endsWith('end-round')?(++endFailures,Promise.reject(Error('end-round network failure'))):{};return {ok:true,json:async()=>result};};
 const interruptedClient=new RGS(new URLSearchParams('sessionID=interrupted&rgs_url=https://example.test'),interrupted);await interruptedClient.authenticate();await interruptedClient.play(10000,'base');await assert.rejects(()=>interruptedClient.finish(),/end-round network failure/);assert.equal(interruptedClient.recovery,true);assert.equal(interruptedClient.round,endRound);await assert.rejects(()=>interruptedClient.play(10000,'base'),/Finish or recover/);assert.equal(endFailures,1);
 const count=calls.length;failure=true;await assert.rejects(()=>client.play(10000,'base'));assert.equal(calls.length,count+1);await assert.rejects(()=>client.play(10000,'base'));assert.equal(calls.length,count+1);
 // An interrupted response can still represent an accepted wager. Abort the
 // transport, then require authentication/recovery rather than repeating it.
 const timeoutCalls=[];
 const stalled=async(url,options)=>{timeoutCalls.push(url);return new Promise((resolve,reject)=>{options.signal.addEventListener('abort',()=>reject(Error('aborted transport')),{once:true});});};
 const timeoutClient=new RGS(new URLSearchParams('sessionID=timeout&rgs_url=https://example.test'),stalled,{timeoutMs:10});
 timeoutClient.config=levelClient.config;
 await assert.rejects(()=>timeoutClient.play(10000,'base'),/RGS request timed out/);
 assert.equal(timeoutClient.busy,false);assert.equal(timeoutClient.recovery,true);
 await assert.rejects(()=>timeoutClient.play(10000,'base'),/Finish or recover/);
 assert.equal(timeoutCalls.length,1,'timed-out wager must not be resent');
 timeoutClient.round=endRound;
 await assert.rejects(()=>timeoutClient.finish(),/RGS request timed out/);
 assert.equal(timeoutClient.round,endRound,'timed-out settlement must retain the pending round');
 assert.equal(timeoutClient.recovery,true);
 assert.equal(timeoutCalls.length,2,'timed-out settlement must not retry automatically');
 // The timeout also covers reading a response body after headers arrive.
 const bodyClient=new RGS(new URLSearchParams('sessionID=body-timeout&rgs_url=https://example.test'),async(url,options)=>({ok:true,json:()=>new Promise((resolve,reject)=>{options.signal.addEventListener('abort',()=>reject(Error('aborted body')),{once:true});})}),{timeoutMs:10});
 await assert.rejects(()=>bodyClient.authenticate(),/RGS request timed out/);
 console.log('PASS RGS contract: crypto precision, limits, ordinary bonus bet, settlement, bounded requests, no duplicate wager');
})().catch(error=>{console.error(error);process.exitCode=1;});
