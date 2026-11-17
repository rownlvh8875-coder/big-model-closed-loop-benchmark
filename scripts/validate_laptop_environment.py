"""Read-only local inventory; no dependencies, model downloads, or server mutation."""
from pathlib import Path
import argparse,json,sys
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bigbench.validation_resources import collect_resources

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path);p.add_argument('--calibration',type=Path);p.add_argument('--carla-host');p.add_argument('--carla-port',type=int,default=2000);p.add_argument('--dedicated-carla',action='store_true');a=p.parse_args();r=collect_resources(calibration=a.calibration,carla_host=a.carla_host,carla_port=a.carla_port,dedicated_server=a.dedicated_carla);text=json.dumps(r,indent=2,allow_nan=False)+'\n'
 if a.out:a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(text)
 else:print(text,end='')
 return 0
if __name__=='__main__':raise SystemExit(main())
