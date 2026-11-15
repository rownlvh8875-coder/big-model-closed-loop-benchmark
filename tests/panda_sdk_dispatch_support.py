"""Handwritten CPU target only; never load the installed SDK."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
def cpu_library(out,native_dir=None):
 out=Path(out);out.mkdir();native=Path(native_dir) if native_dir else ROOT/'native/panda_sdk_routes_v2';objects=[]
 for name,compiler,source in [('cache','/usr/bin/gcc','readback_command_state.c'),('activity','/usr/bin/g++','panda_source_activity.cxx'),('adapter','/usr/bin/g++','panda_cache_adapter.cxx')]:
  obj=out/(name+'.o');cmd=[compiler,'-O2','-fPIC','-pthread','-I',str(native),'-c',str(native/source),'-o',str(obj)];subprocess.run(cmd,capture_output=True,check=True,timeout=30);objects.append(str(obj))
 lib=out/'libdispatch_fixture.so';subprocess.run(['/usr/bin/g++','-shared','-pthread',*objects,'-Wl,-z,defs','-o',str(lib)],capture_output=True,check=True,timeout=30);return lib
