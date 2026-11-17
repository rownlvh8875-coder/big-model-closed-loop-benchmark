"""Read-only laptop readiness; resource presence never certifies a validation."""
from pathlib import Path
import importlib.util,json,os,platform,re,shutil,subprocess
SOFTWARE=('softpipe','llvmpipe','swiftshader','software rasterizer','basic render','gdi generic','apple software')

def endpoint(host,port):
 if not isinstance(host,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]+',host) or '@' in host or type(port) is not int or not 1<=port<=65535:raise ValueError('plain host and integer port1..65535 required')
 return dict(host=host,port=port)

def actual_hardware_msaa(observation):
 r=observation;samples=r.get('actual_samples');requested=r.get('requested_samples')
 if r.get('context_current') is not True or r.get('device_bound') is not True or not isinstance(samples,list) or not samples or not all(type(x) is int and 0<=x<=64 for x in samples) or type(requested) is not int or not 2<=requested<=64:raise ValueError('actual current device-bound GL sample measurements required')
 renderer=r.get('renderer');vendor=r.get('vendor');hardware=isinstance(renderer,str) and bool(renderer.strip()) and isinstance(vendor,str) and bool(vendor.strip()) and not any(s in renderer.lower() for s in SOFTWARE)
 passed=hardware and all(s>=requested for s in samples)
 return dict(passed=passed,hardware_renderer=hardware,actual_samples=samples,requested_samples=requested,scope='measured context only; no physical optics or CARLA claim')

def resource_readiness(o):
 def row(missing):return dict(readiness='BLOCKED' if missing else 'READY_FOR_PROBE',missing=missing,verification_status='NOT_RUN')
 full=[]
 if o.get('system')!='Linux' or o.get('machine','').lower() not in ('x86_64','amd64'):full.append('LINUX_X86_64_RUNTIME_REQUIRED')
 if type(o.get('memory_available_bytes')) is not int or o['memory_available_bytes']<12*1024**3:full.append('12_GIB_AVAILABLE_MEMORY_REQUIRED')
 if type(o.get('disk_free_bytes')) is not int or o['disk_free_bytes']<8*1024**3:full.append('8_GIB_FREE_WORKSPACE_REQUIRED')
 gpu=[]
 if not o.get('gpu_devices'):gpu.append('HARDWARE_DEVICE_REQUIRED')
 if o.get('active_renderer') and any(s in o['active_renderer'].lower() for s in SOFTWARE):gpu.append('ACTIVE_CONTEXT_IS_SOFTWARE')
 carla=o.get('carla') or {};calibration=o.get('calibration') or {}
 return dict(full_s=row(full),hardware_gpu=row(gpu),carla=row([key for valid,key in [(carla.get('endpoint_configured') is True,'DEDICATED_CARLA_ENDPOINT_REQUIRED'),(carla.get('client_installed') is True,'MATCHING_CARLA_CLIENT_REQUIRED'),(carla.get('dedicated_server') is True,'DEDICATED_SERVER_OWNERSHIP_REQUIRED')] if not valid]),physical_optics=row([key for valid,key in [(calibration.get('manifest_exists') is True,'OFFLINE_CALIBRATION_MANIFEST_REQUIRED'),(calibration.get('measured_provenance') is True,'MEASURED_CALIBRATION_DATASET_REQUIRED')] if not valid]))

def _command(argv):
 try:
  r=subprocess.run(argv,capture_output=True,text=True,timeout=8,check=False)
  return dict(argv=argv,returncode=r.returncode,stdout=r.stdout[:16384],stderr=r.stderr[:1024],truncated=len(r.stdout)>16384)
 except (OSError,subprocess.TimeoutExpired) as e:return dict(argv=argv,returncode=None,error=type(e).__name__,stdout='')

def effective_memory(total,available,limit,current):
 if type(limit) is int and type(current) is int and 0<limit<2**60 and current>=0:return min(total,limit),min(available,max(0,limit-current))
 return total,available

def _memory(system):
 if system=='Linux':
  values={k:int(v.split()[0])*1024 for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines()) if k in ('MemTotal','MemAvailable')};total,available=values.get('MemTotal'),values.get('MemAvailable')
  for maxpath,currentpath in [('/sys/fs/cgroup/memory.max','/sys/fs/cgroup/memory.current'),('/sys/fs/cgroup/memory/memory.limit_in_bytes','/sys/fs/cgroup/memory/memory.usage_in_bytes')]:
   try:
    text=Path(maxpath).read_text().strip();limit=None if text=='max' else int(text);current=int(Path(currentpath).read_text());return effective_memory(total,available,limit,current)
   except (OSError,ValueError):continue
  return total,available
 if system=='Windows':
  import ctypes
  class Status(ctypes.Structure):_fields_=[('length',ctypes.c_uint32),('load',ctypes.c_uint32)]+[(n,ctypes.c_uint64) for n in ('total_phys','available_phys','total_page','available_page','total_virtual','available_virtual','available_extended')]
  status=Status();status.length=ctypes.sizeof(status)
  if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):return status.total_phys,status.available_phys
 if system=='Darwin':
  r=_command(['sysctl','-n','hw.memsize'])
  if r.get('returncode')==0:return int(r['stdout'].strip()),None
 return None,None

def collect_resources(*,calibration=None,carla_host=None,carla_port=2000,dedicated_server=False):
 system=platform.system();total,available=_memory(system);devices=[];probes=[]
 for directory,pattern in [('/dev/dri','renderD*'),('/dev','nvidia[0-9]*'),('/dev','dxg')]:
  for path in Path(directory).glob(pattern):devices.append(dict(path=str(path),kind='device_node_only'))
 if shutil.which('nvidia-smi'):
  r=_command(['nvidia-smi','--query-gpu=name,driver_version,memory.total','--format=csv,noheader,nounits']);probes.append(r)
  if r.get('returncode')==0 and not r.get('truncated'):devices.extend(dict(name=line.strip(),kind='nvidia_inventory_only') for line in r['stdout'].splitlines() if line.strip())
 if system=='Windows':
  r=_command(['powershell','-NoProfile','-NonInteractive','-Command','Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion | ConvertTo-Json -Compress']);probes.append(r)
  if r.get('returncode')==0:
   try:
    data=json.loads(r['stdout']);devices.extend(dict(name=x.get('Name'),kind='windows_inventory_only') for x in (data if isinstance(data,list) else [data]) if x.get('Name') and not any(s in x['Name'].lower() for s in SOFTWARE))
   except (ValueError,TypeError,AttributeError):pass
 manifest=Path(calibration).expanduser().resolve() if calibration else None;cal=dict(manifest_exists=bool(manifest and manifest.is_file()),measured_provenance=False)
 if cal['manifest_exists']:
  cal['path']=str(manifest)
  try:
   if manifest.stat().st_size>128*1024:raise ValueError('manifest size')
   data=json.loads(manifest.read_text());cal['measured_provenance']=data.get('provenance')=='OFFLINE_MEASURED_CAMERA_CORRESPONDENCES';cal['provenance_declaration_only']=True
  except (OSError,ValueError):cal['manifest_error']='INVALID_OR_UNREADABLE_MANIFEST'
 remote=endpoint(carla_host,carla_port) if carla_host else None
 o=dict(protocol='four-validation-laptop-resources-v1',system=system,machine=platform.machine(),python_version=platform.python_version(),wsl=bool(os.environ.get('WSL_DISTRO_NAME')),memory_total_bytes=total,memory_available_bytes=available,disk_free_bytes=shutil.disk_usage(Path.cwd()).free,gpu_devices=devices,active_renderer=None,device_probes=probes,carla=dict(endpoint_configured=remote is not None,endpoint=remote,client_installed=importlib.util.find_spec('carla') is not None,dedicated_server=dedicated_server),calibration=cal,simulator_imported=False,model_loaded=False,network_connections_attempted=0)
 o['tracks']=resource_readiness(o);return o
