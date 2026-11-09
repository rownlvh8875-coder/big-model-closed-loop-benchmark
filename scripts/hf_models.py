"""Optional Hugging Face discovery/download CLI. Network runs only on request."""
import argparse
import json
from pathlib import Path
from bigbench.model_inventory import discover_official, download_checked


def main():
    parser=argparse.ArgumentParser(description='Official commaai ONNX model inventory (no automatic download)')
    sub=parser.add_subparsers(dest='command', required=True)
    sub.add_parser('list',help='Query official HF tree; model files are NOT downloaded')
    dl=sub.add_parser('download',help='Explicit hash-pinned single ONNX download')
    dl.add_argument('--path',required=True,help='Relative ONNX path copied from inventory')
    dl.add_argument('--sha256',required=True,help='Expected original file SHA256')
    dl.add_argument('--max-bytes',type=int,default=2_000_000_000)
    dl.add_argument('--out',type=Path,default=Path('output/models'))
    args=parser.parse_args()
    if args.command=='list':
        rows=discover_official()
        print(json.dumps({'repository':'commaai/openpilot_driving_models','candidates':rows,
                          'note':'Availability metadata only. No model has been downloaded or tested.'},
                         indent=2,ensure_ascii=False))
    else:
        result=download_checked(path=args.path,sha256=args.sha256,
                                output_dir=args.out,max_bytes=args.max_bytes)
        print(json.dumps({'downloaded':str(result),'verified_sha256':args.sha256,
                          'model_inference_tested':False},ensure_ascii=False))


if __name__=='__main__':main()
