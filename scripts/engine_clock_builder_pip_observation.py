"""Bounded pip call/hook/log coordinates. Never retain messages, arguments or environment."""
import builtins
import contextlib
import hashlib
import logging
from pathlib import Path
import re
import sys
import zipfile

PIP_NAMES=frozenset('PipError DiagnosticPipError ConfigurationError InstallationError FailedToPrepareCandidate MissingPyProjectBuildRequires InvalidPyProjectBuildRequires NoneMetadataError UserInstallationInvalid InvalidSchemeCombination DistributionNotFound RequirementsFileParseError BestVersionAlreadyInstalled BadCommand CommandError PreviousBuildDirError NetworkConnectionError ConnectionFailedError ConnectionTimeoutError SSLMissingError SSLVerificationError ProxyConnectionError InvalidWheelFilename UnsupportedWheel InvalidWheel MetadataInconsistent SidecarMetadataInconsistent MetadataInvalid InstallationSubprocessError MetadataGenerationFailed HashErrors HashError VcsHashUnsupported DirectoryUrlHashUnsupported HashMissing HashUnpinned HashMismatch UnsupportedPythonVersion ConfigurationFileCouldNotBeLoaded ExternallyManagedEnvironment UninstallMissingRecord LegacyDistutilsInstall InvalidInstalledPackage IncompleteDownloadError ResolutionTooDeepError InstallWheelBuildError InvalidEggFragment BuildDependencyInstallError VenvImportError VenvCreationError'.split())
BUILTIN_NAMES=('ValueError','TypeError','OSError','FileNotFoundError','PermissionError','NotADirectoryError','IsADirectoryError','BlockingIOError','RuntimeError','MemoryError','ImportError','ModuleNotFoundError','AttributeError','KeyError','AssertionError','SystemExit','KeyboardInterrupt')
CODES={'OTHER',*('pip.'+n for n in PIP_NAMES),*('builtin.'+n for n in BUILTIN_NAMES)}
OWNED_CODES=frozenset('UNSUPPORTED_OWNED_DRIVER SOURCE_LOCATION_MISMATCH SOURCE_LOCATION_NOT_EMPTY MULTIPLE_SOURCE_UNPACKS SOURCE_PAYLOAD_MISMATCH MISSING_SOURCE_UNPACK SOURCE_LOCATION_CHANGED PIP_WHEEL_FAILED BUILD_LOG_LIMIT SOURCE_MANIFEST_LIMIT INVALID_SOURCE_SNAPSHOTS'.split())


def _need(ok):
    if not ok:raise ValueError('INVALID_PIP_OBSERVATION')


def empty_location():return {'kind':'NONE','length':None,'relative_to_tmp':None,'matches_owned_pattern':None,'sha256':None}

def empty():
    return {'schema':'pip-boundary-observation-v1','pip_invocations':0,'pip_returncode':None,'pip_raised':False,'pip_exception_code':None,
            'unpack_calls':0,'hook_returns':0,'hook_error_code':None,'hook_exception_code':None,'hook_errno':None,
            'location':empty_location(),'error_sites':[],'logs':None,'observer_errors':0}


def _code(exc,types):return None if exc is None else types.get(type(exc),'OTHER')

def _digest(v):return type(v) is str and re.fullmatch('[0-9a-f]{64}',v) is not None


def validate(f,*,members):
    try:
        _need(type(f) is dict and set(f)==set(empty()) and f['schema']=='pip-boundary-observation-v1')
        for k,maxv in (('pip_invocations',1),('unpack_calls',16),('hook_returns',16),('observer_errors',16)):_need(type(f[k]) is int and 0<=f[k]<=maxv)
        _need(f['pip_returncode'] is None or type(f['pip_returncode']) is int and -2**31<=f['pip_returncode']<2**31)
        _need(type(f['pip_raised']) is bool and all(f[k] is None or type(f[k]) is str and f[k] in CODES for k in ('pip_exception_code','hook_exception_code')))
        _need(f['hook_error_code'] is None or type(f['hook_error_code']) is str and f['hook_error_code'] in OWNED_CODES)
        _need(f['hook_errno'] is None or type(f['hook_errno']) is int and 0<=f['hook_errno']<=4095)
        loc=f['location'];_need(type(loc) is dict and set(loc)==set(empty_location()) and loc['kind'] in ('NONE','STR','PATH','OTHER'))
        _need(loc['length'] is None or type(loc['length']) is int and 0<=loc['length']<=4096)
        _need(all(loc[k] is None or type(loc[k]) is bool for k in ('relative_to_tmp','matches_owned_pattern')) and (loc['sha256'] is None or _digest(loc['sha256'])))
        _need(type(f['error_sites']) is list and len(f['error_sites'])<=16)
        for r in f['error_sites']:
            _need(type(r) is dict and set(r)=={'member','line','level','exception_code'})
            _need(r['member'] is None or type(r['member']) is str and r['member'] in members)
            _need(r['line'] is None or type(r['line']) is int and 1<=r['line']<=1000000)
            _need(type(r['level']) is int and r['level'] in (40,50) and (r['exception_code'] is None or type(r['exception_code']) is str and r['exception_code'] in CODES))
        logs=f['logs']
        if logs is not None:
            _need(type(logs) is dict and set(logs)=={'stdout_bytes','stderr_bytes','stdout_sha256','stderr_sha256'})
            _need(all(type(logs[k]) is int and 0<=logs[k]<=1048576 for k in ('stdout_bytes','stderr_bytes')) and all(_digest(logs[k]) for k in ('stdout_sha256','stderr_sha256')))
        return f
    except (TypeError,ValueError,KeyError):raise ValueError('INVALID_PIP_OBSERVATION') from None


def pip_context():
    import pip
    from pip._internal import exceptions
    with zipfile.ZipFile('/inputs/pip-26.2.2-py3-none-any.whl') as archive:
        names=archive.namelist();_need(len(names)<=20000)
        members={n for n in names if re.fullmatch(r'pip/[A-Za-z0-9_/]+\.py',n)}
    _need(bool(members) and pip.__version__=='26.2.2')
    types={getattr(builtins,n):'builtin.'+n for n in BUILTIN_NAMES}
    for name in PIP_NAMES:
        cls=getattr(exceptions,name,None)
        if isinstance(cls,type) and cls.__module__==exceptions.__name__:types[cls]='pip.'+name
    return Path(pip.__file__).parent.parent,members,types


class PrepareProxy:
    def __init__(self,real,facts,*,types):
        self.real,self.facts,self.types=real,facts,types;self.original=real.unpack_url
    @property
    def unpack_url(self):return self.real.unpack_url
    @unpack_url.setter
    def unpack_url(self,hook):
        if hook is self.original:self.real.unpack_url=hook;return
        def observed(*args,**kwargs):
            f=self.facts;f['unpack_calls']=min(16,f['unpack_calls']+1)
            location=args[1] if len(args)>1 else kwargs.get('location')
            try:
                loc=empty_location();loc['kind']='STR' if type(location) is str else 'PATH' if type(location) is type(Path('/')) else 'NONE' if location is None else 'OTHER'
                if loc['kind'] in ('STR','PATH'):
                    raw=location if type(location) is str else str(location)
                    if len(raw)<=4096:
                        loc.update(length=len(raw),sha256=hashlib.sha256(raw.encode()).hexdigest())
                        try:relative=Path(raw).relative_to('/build/tmp').as_posix();loc['relative_to_tmp']=True
                        except ValueError:relative='';loc['relative_to_tmp']=False
                        loc['matches_owned_pattern']=re.fullmatch(r'pip-wheel-[a-z0-9_-]{1,64}/progressbar_[0-9a-f]{32}',relative) is not None
                f['location']=loc
            except Exception:f['observer_errors']=min(16,f['observer_errors']+1)
            try:result=hook(*args,**kwargs)
            except BaseException as exc:
                f['hook_exception_code']=_code(exc,self.types)
                if type(exc) is ValueError and len(exc.args)==1 and type(exc.args[0]) is str and exc.args[0] in OWNED_CODES:f['hook_error_code']=exc.args[0]
                number=exc.errno if isinstance(exc,OSError) else None
                if type(number) is int and 0<=number<=4095:f['hook_errno']=number
                raise
            f['hook_returns']=min(16,f['hook_returns']+1);return result
        self.real.unpack_url=observed


def observe_pip(pip_main,args,facts,*,context_info):
    site,members,types=context_info;old=logging.getLogRecordFactory();facts['pip_invocations']+=1
    def factory(*args,**kwargs):
        record=old(*args,**kwargs)
        try:
            if type(record.levelno) is int and record.levelno>=40 and len(facts['error_sites'])<16:
                try:member=Path(record.pathname).relative_to(site).as_posix()
                except (TypeError,ValueError):member=None
                if member not in members:member=None
                line=record.lineno if type(record.lineno) is int and 1<=record.lineno<=1000000 else None
                info=record.exc_info if type(record.exc_info) is tuple and len(record.exc_info)==3 else sys.exc_info()
                facts['error_sites'].append({'member':member,'line':line,'level':50 if record.levelno>=50 else 40,'exception_code':_code(info[1],types)})
        except Exception:facts['observer_errors']=min(16,facts['observer_errors']+1)
        return record
    logging.setLogRecordFactory(factory)
    try:
        code=pip_main(args)
        facts['pip_returncode']=code if type(code) is int and -2**31<=code<2**31 else None
        return code
    except BaseException as exc:
        facts['pip_raised']=True;facts['pip_exception_code']=_code(exc,types);raise
    finally:
        logging.setLogRecordFactory(old)
        try:
            logs={}
            for name,stream in (('stdout',sys.stdout),('stderr',sys.stderr)):
                logs[name+'_bytes']=stream.nbytes;logs[name+'_sha256']=stream.digest.hexdigest()
            facts['logs']=logs
        except Exception:facts['observer_errors']=min(16,facts['observer_errors']+1)
