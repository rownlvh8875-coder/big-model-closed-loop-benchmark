"""Explicit Windows RTX 3050 Ti stock-Panda hardware/MSAA readback probe."""
from pathlib import Path
import argparse,json,sys
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',action='store_true',help='create one real Windows GPU context and render four 8x8 uniform/edge challenges');p.add_argument('--samples',type=int,default=4);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if not a.run:p.error('--run is required for actual context creation')
 from bigbench.laptop_gpu import run_gpu_probe,ATTEMPT_PROTOCOL,CONSTRUCTION
 try:r=run_gpu_probe(requested_samples=a.samples)
 except Exception as e:r=dict(protocol=ATTEMPT_PROTOCOL,framebuffer_construction=CONSTRUCTION,status='ERROR',passed=False,error=type(e).__name__+': '+str(e),model_loaded=False)
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n');return 0 if r.get('validation',{}).get('passed') else 2
if __name__=='__main__':raise SystemExit(main())
