"""Only handwritten CPU components are loaded; real Panda SDK is DATA ONLY."""
from pathlib import Path
import json,subprocess,tempfile,unittest
from scripts import panda_cache_adapter_cpu as cpu
try:
    from scripts import build_panda_adapter_sdk as sdk
except ImportError:sdk=None
ROOT=Path(__file__).resolve().parents[1]
OFF_SOURCE=r'''#include "panda_cache_adapter.h"
#include <cstdio>
struct cpu_call {int32_t x,y,w,h;uint32_t f,t;void *p;uintptr_t tex,gsg,capacity,image;int32_t z,view;};
extern "C" int pca_fixture_call(const cpu_call*);
static unsigned calls,ok=1;static unsigned char pixels[128];
static void original(int32_t x,int32_t y,int32_t w,int32_t h,uint32_t f,uint32_t t,void*p){++calls;if(x!=-7||y!=11||w!=5||h!=3||f!=0x1907||t!=0x1401||p!=pixels||errno!=ERANGE)ok=0;errno=EDOM;}
int main(){psd_counts s={};if(psd_get_stats(&s)||s.configured||psd_bind_read(original))return 1;cpu_call a={-7,11,5,3,0x1907,0x1401,pixels,0x1111,0x333,128,(uintptr_t)pixels,-1,0};errno=ERANGE;int regs=pca_fixture_call(&a);if(psd_get_stats(&s)||s.events||s.configured||calls!=1||!ok||!regs||errno!=EDOM||psd_source_idle(nullptr,nullptr)==0)return 2;std::printf("CPU_DEFAULT_OFF_ORIGINAL_ONLY\n");}
'''

def compile_cpu_sdk(out,sanitize=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=False);commands=[]
    flags=['-O1' if sanitize else '-O2','-Wall','-Wextra','-Werror','-pthread','-I',str(ROOT/'native')]
    san=['-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer'] if sanitize else []
    caller=out/'caller.S';caller.write_bytes((ROOT/'tests/fixtures/panda_readback_caller.S').read_bytes().replace(b'pb_entry',b'psd_read_pixels'))
    common=['-Dpb_fixture_call=pca_fixture_call','-Dpb_fixture_return=pca_fixture_return']
    def run(command,name):
        r=cpu.run_command(command,ROOT,cpu.cpu_environment(),out/name,30);commands.append(r)
        if r['returncode'] or r['stderr']:raise AssertionError(r['stderr'])
    objects=[]
    for name,compiler,standard,source,visibility in (
        ('cache','/usr/bin/gcc','c11',ROOT/'native/readback_command_state.c',[]),
        ('activity','/usr/bin/g++','c++11',ROOT/'native/panda_source_activity.cxx',['-fvisibility=hidden']),
        ('adapter','/usr/bin/g++','c++11',ROOT/'native/panda_cache_adapter.cxx',[]),
        ('caller','/usr/bin/gcc',None,caller,[])):
        obj=out/(name+'.o');run([compiler,*(['-std='+standard] if standard else []),*flags,*san,*common,*visibility,'-fPIC','-c',str(source),'-o',str(obj)],'compile-'+name);objects.append(str(obj))
    library=out/'libpca_sdk_cpu.so';run(['/usr/bin/g++','-shared',*flags,*san,*objects,'-Wl,-z,defs','-Wl,-soname,libpca_sdk_cpu.so','-o',str(library)],'link-sdk')
    exe=out/'fixture';off=out/'off';off_cpp=out/'off.cxx';off_cpp.write_text(OFF_SOURCE)
    for source,binary,name in ((ROOT/'tests/fixtures/panda_cache_adapter_fixture.cxx',exe,'link-fixture'),(off_cpp,off,'link-off')):
        run(['/usr/bin/g++','-std=c++11',*flags,*san,*(['-no-pie'] if sanitize else []),str(source),'-L'+str(out),'-lpca_sdk_cpu','-Wl,-rpath,$ORIGIN','-o',str(binary)],name)
    return dict(library=str(library),fixture=str(exe),off=str(off),commands=commands)

class AdapterSdkCpuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=None;cls.profile=None
        if sdk is not None:
            cls.temp=tempfile.TemporaryDirectory(prefix='as-cpu-');cls.out=Path(cls.temp.name);cls.profile=compile_cpu_sdk(cls.out/'normal')
    @classmethod
    def tearDownClass(cls):
        if cls.temp:cls.temp.cleanup()
    def setUp(self):self.assertIsNotNone(self.profile,'single-image SDK CPU/link inspector required')
    def test_default_off_shared_source_preserves_original_tail(self):
        p=subprocess.run([self.profile['off']],capture_output=True,text=True,timeout=10,env=cpu.cpu_environment())
        self.assertEqual((p.returncode,p.stdout,p.stderr),(0,'CPU_DEFAULT_OFF_ORIGINAL_ONLY\n',''))
    def test_all_fifty_shared_image_cases_preserve_expected_acceptance(self):
        for mode in cpu.GOOD+cpu.BAD:
            p=subprocess.run([self.profile['fixture'],mode],capture_output=True,text=True,timeout=10,env=cpu.cpu_environment());self.assertEqual((p.returncode,p.stderr),(0,''));r=json.loads(p.stdout)
            with self.subTest(mode=mode):
                self.assertEqual((r['args_ok'],r['errno_ok'],r['reads'],r['regs_ok'],r['stale_output']),(1,1,1,1,0));self.assertEqual(r['finish']==0,mode in cpu.GOOD);self.assertFalse(r['native_admitted'])
                if mode=='bootstrap':self.assertEqual((r['originals'],r['replayed'],r['pack_buffer']),(8,5,0))
    def test_shared_sdk_exports_controls_and_mutated_activity_symbol_rejects(self):
        dest=self.out/'inspect';dest.mkdir();r=sdk.inspect_exports(Path(self.profile['library']),dest)
        self.assertEqual(len(r['required_exports']),33);self.assertTrue(r['same_image_interfaces_verified']);self.assertEqual(r['source_state_instances'],1)
        bad=self.out/'bad.so';bad.write_bytes(Path(self.profile['library']).read_bytes().replace(b'psd_source_idle\0',b'psd_source_fail\0'))
        dest=self.out/'bad-inspect';dest.mkdir()
        with self.assertRaises(ValueError):sdk.inspect_exports(bad,dest)
    def test_old_runtime_without_activity_fails_actual_strict_link(self):
        command=['/usr/bin/g++','-std=c++11','-shared','-fPIC','-pthread','-I',str(ROOT/'native'),str(ROOT/'native/panda_source_dispatch.cxx'),str(ROOT/'native/panda_cache_adapter.cxx'),str(self.out/'normal/cache.o'),'-Wl,-z,defs','-o',str(self.out/'old-runtime.so')]
        p=subprocess.run(command,capture_output=True,text=True,timeout=30,env=cpu.cpu_environment());self.assertNotEqual(p.returncode,0);self.assertIn('psd_source_idle',p.stderr)
    def test_sanitized_shared_sdk_pending_lookup_and_deletion(self):
        profile=compile_cpu_sdk(self.out/'sanitized',True)
        for mode in ('bootstrap','delete_mutate','pending_known','pending_unknown','adapter_thread'):
            p=subprocess.run([profile['fixture'],mode],capture_output=True,text=True,timeout=10,env=cpu.cpu_environment());self.assertEqual((p.returncode,p.stderr),(0,''));r=json.loads(p.stdout);self.assertEqual((r['args_ok'],r['errno_ok'],r['stale_output']),(1,1,0))
if __name__=='__main__':unittest.main()
