"""Run the pinned official SDK format checks, without claiming certification."""
import argparse,json,subprocess,sys
from pathlib import Path
from build_stake_bundle import SDK_REVISION
p=argparse.ArgumentParser();p.add_argument('--sdk',type=Path,required=True);p.add_argument('--publish',type=Path,default=Path('release/math'));a=p.parse_args()
sha=subprocess.check_output(['git','-C',str(a.sdk),'rev-parse','HEAD'],text=True).strip();assert sha==SDK_REVISION,'SDK revision mismatch'
sys.path.insert(0,str(a.sdk.resolve()))
from utils.rgs_verification import verify_lookup_format,verify_books_and_payout_mults,compare_payout_values
results=[]
for mode in ['base','bonus']:
 _,lut,_,_,_=verify_lookup_format(str(a.publish/f'lookUpTable_{mode}.csv'))
 books,events=verify_books_and_payout_mults(str(a.publish/f'books_{mode}.jsonl.zst'))
 compare_payout_values(books,lut)
 results.append(dict(mode=mode,books=len(books),events=events,format_checks_passed=True))
 print('PASS official SDK format checks:',mode,flush=True)
(a.publish/'sdk_verification.json').write_text(json.dumps(dict(sdk_revision=sha,results=results),indent=2))
