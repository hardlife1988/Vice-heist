/* Wallet values stay in integer micro-units, including cryptocurrency. */
(function(root){
'use strict';
const safe = value => {if(!Number.isSafeInteger(value)||value<0)throw Error('Invalid wallet amount');return value;};
const payout=(units,bet)=>{safe(units);safe(bet);const result=(BigInt(units)*BigInt(bet)+50n)/100n;if(result>BigInt(Number.MAX_SAFE_INTEGER))throw Error('Wallet amount exceeds safe precision');return Number(result);};
const format=(amount,currency='USD')=>{safe(amount);const whole=Math.floor(amount/1000000).toLocaleString('en-US');const fraction=String(amount%1000000).padStart(6,'0').replace(/0+$/,'').padEnd(2,'0');return (currency==='USD'?'$':currency+' ')+whole+'.'+fraction;};
const api={safe,payout,format}; root.StakeMoney=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
