'use strict';
const assert=require('node:assert/strict');global.StakeMoney=require('../static/money.js');const RGS=require('../static/rgs.js');
const calls=[];let failure=false;const round={betID:1,amount:10000,payout:1000,payoutMultiplier:.1,active:true,state:[{index:0,type:'finalWin',amount:10}]};
const mock=async(url,options)=>{const body=JSON.parse(options.body);calls.push([url,body]);if(failure)throw Error('network');const result=url.endsWith('authenticate')?{balance:{amount:123456,currency:'BTC'},config:{minBet:10000,maxBet:100000000,stepBet:10000,defaultBetLevel:10000,betLevels:[10000,100000000]},round:null}:url.endsWith('play')?{balance:{amount:113456,currency:'BTC'},round}:url.endsWith('end-round')?{balance:{amount:114456,currency:'BTC'}}:{};return{ok:true,json:async()=>result};};
(async()=>{
 assert.equal(StakeMoney.format(1,'BTC'),'BTC 0.000001');assert.equal(StakeMoney.payout(10,10000),1000);assert.throws(()=>StakeMoney.safe(NaN));
 const client=new RGS(new URLSearchParams('sessionID=test&rgs_url=https://example.test'),mock);await client.authenticate();assert.throws(()=>client.validBet(20000));assert.throws(()=>client.validBet(100000001));
 const played=await client.play(10000,'bonus');assert.equal(calls.at(-1)[1].amount,10000);assert.equal(client.events(played.round)[0].amount,10);await assert.rejects(()=>client.play(10000,'base'));await client.checkpoint(0);await client.finish();assert.equal(client.round,null);
 const count=calls.length;failure=true;await assert.rejects(()=>client.play(10000,'base'));assert.equal(calls.length,count+1);await assert.rejects(()=>client.play(10000,'base'));assert.equal(calls.length,count+1);
 console.log('PASS RGS contract: crypto precision, limits, ordinary bonus bet, settlement, no duplicate wager');
})().catch(error=>{console.error(error);process.exitCode=1;});
