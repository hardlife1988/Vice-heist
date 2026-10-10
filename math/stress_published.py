"""Sample actual weighted published rounds: four million per bet AND mode.
The exhaustive book audit separately checks every outcome. Samples use independent
reproducible seeds per bet; confidence bounds reflect high-volatility rare caps.
"""
import argparse,csv,json,hashlib,time
from pathlib import Path
import numpy as np
from build_stake_bundle import BET_MICROS,MAX_UNITS

def main():
 p=argparse.ArgumentParser();p.add_argument('--publish',type=Path,default=Path('release/math'));p.add_argument('--rounds',type=int,default=4000000);a=p.parse_args();assert a.rounds>=4000000
 results=[];start=time.time()
 for mode,cost in [('base',1),('bonus',100)]:
  rows=np.array([tuple(map(int,r)) for r in csv.reader((a.publish/f'lookUpTable_{mode}.csv').open())],dtype=np.int64)
  weights=rows[:,1];payouts=rows[:,2];cdf=np.cumsum(weights);prob=weights/cdf[-1];expected=float(prob@payouts)/(100*cost)
  variance=float(prob@((payouts/(100*cost)-expected)**2));se=(variance/a.rounds)**.5
  for j,bet in enumerate(BET_MICROS):
   # Every possible payout at this bet is exact in RGS micro-units.
   assert np.all((payouts*bet)%100==0)
   assert int(payouts.max())*bet//100<=2**53-1
   rng=np.random.default_rng(1988+j+(100 if mode=='bonus' else 0));total=0;caps=0;wins=0;digest=hashlib.sha256()
   for batch in range(0,a.rounds,250000):
    indexes=np.searchsorted(cdf,rng.integers(0,int(cdf[-1]),size=min(250000,a.rounds-batch)),side='right')
    values=payouts[indexes];cash=values*bet//100
    assert np.all(cash*100==values*bet)
    total+=int(values.sum());caps+=int(np.count_nonzero(values==MAX_UNITS));wins+=int(np.count_nonzero(values));digest.update(indexes.tobytes())
   observed=total/(a.rounds*100*cost);assert abs(expected-.96)<1e-6 and abs(observed-expected)<=8*se
   result=dict(mode=mode,bet_micros=bet,rounds=a.rounds,seed=1988+j+(100 if mode=='bonus' else 0),expected_rtp=expected,observed_rtp=observed,standard_error=se,cap_hits=caps,winning_rounds=wins,precision_errors=0,sample_digest=digest.hexdigest(),pass_checks=True)
   results.append(result);print(f'{mode} bet {bet/1000000:g}: {a.rounds:,} rounds; RTP {observed:.5%}; caps {caps}; PASS',flush=True)
 report=dict(total_rounds=sum(r['rounds'] for r in results),seconds=time.time()-start,results=results)
 (a.publish/'four_million_report.json').write_text(json.dumps(report,indent=2))
 print(f"PASS {report['total_rounds']:,} wagering rounds",flush=True)
if __name__=='__main__':main()
