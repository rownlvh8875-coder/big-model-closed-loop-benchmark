"""Independent wire mutations and actual compiled CPU-fake interoperability."""
from dataclasses import replace
from pathlib import Path
import hashlib
import tempfile
import unittest
from tests.test_readback_return_core import compile_fixture,fixture_result,HEADER,FOOTER,NONCE
try:
    from scripts import readback_return_codec as codec
except ImportError:
    codec=None

def change_header(raw,index,value,offset=0):
    fields=list(HEADER.unpack_from(raw,offset));fields[index]=value
    return raw[:offset]+HEADER.pack(*fields)+raw[offset+160:]

def finalization_receipt(raw,stats):
    """Out-of-band producer return/stats plus the spooled stream identity."""
    return dict(schema='readback-return-producer-finalization-v1',nonce=NONCE.hex(),
                stream_sha256=hashlib.sha256(raw).hexdigest(),stream_nbytes=len(raw),
                finish_result=stats['finish'],error=stats['error'],forwards=stats['forwards'],
                attempts=stats['attempts'],captured=stats['captured'],data_wire_bytes=stats['wire_bytes'])

class ReturnCodecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=None;cls.samples={}
        if codec is not None:
            cls.temp=tempfile.TemporaryDirectory(prefix='rb-codec-test-');exe=Path(cls.temp.name)/'fixture'
            compile_fixture(exe)
            for mode in ('basic','rgb','rgba','bgra','packed','off','ambiguous','unknownproducer','limit','max','footerfail'):
                cls.samples[mode]=fixture_result(exe,mode)
    @classmethod
    def tearDownClass(cls):
        if cls.temp:cls.temp.cleanup()
    def setUp(self):self.assertIsNotNone(codec,'strict return-buffer codec required')
    def decode(self,mode='basic',raw=None,**kwargs):
        options=dict(expected_nonce=NONCE,expected_windows=12 if mode=='max' else 1,reads_per_window=2,enabled=mode!='off')
        sample,stats=self.samples[mode]
        options['producer_receipt']=finalization_receipt(sample if raw is None else raw,stats)
        options.update(kwargs)
        return codec.decode_stream(self.samples[mode][0] if raw is None else raw,**options)
    def test_c_stream_closes_cpu_window_without_native_or_gpu_authority(self):
        result=self.decode();self.assertEqual(len(result['records']),2)
        self.assertTrue(result['cpu_window_closed'])
        for flag in ('native_admitted','gpu_write_proven','physical_frame_proven'):
            self.assertIs(result[flag],False)
    def test_all_component_orders_and_padding_normalize_top_down_rgb(self):
        expected=bytes([v for r in (12,11,10) for col in (1,2,3,4,5) for v in (r,col,77)])
        for mode in ('basic','rgb','rgba','bgra','packed'):
            records=self.decode(mode)['records']
            with self.subTest(mode=mode):self.assertEqual(codec.normalize_rgb(records[0]),expected)
    def test_off_requires_complete_footer_and_has_no_data(self):
        result=self.decode('off');self.assertEqual(result['records'],())
        with self.assertRaises(ValueError):self.decode('off',enabled=True)
    def test_boundary_and_partial_truncation_never_close_window(self):
        raw=self.samples['basic'][0]
        for cut in (0,8,159,160,204,205,410,len(raw)-96,len(raw)-1):
            with self.subTest(cut=cut),self.assertRaises(ValueError):self.decode(raw=raw[:cut])
        with self.assertRaises(ValueError):self.decode(raw=raw+b'junk')
    def test_external_nonce_window_reads_and_mode_are_binding(self):
        for options in ({'expected_nonce':b'x'*32},{'expected_windows':2},{'reads_per_window':1},{'enabled':False},
                        {'expected_nonce':bytes(32)},{'expected_windows':0},{'reads_per_window':3},{'enabled':1}):
            with self.subTest(options=options),self.assertRaises(ValueError):self.decode(**options)
    def test_record_index_nonce_host_requester_and_context_cannot_drift(self):
        raw=self.samples['basic'][0]
        for index,value in ((0,b'BADMAGIC'),(1,2),(2,164),(3,2),(4,b'x'*32),(5,2),(6,2),(7,3),(9,0),(21,0)):
            with self.subTest(index=index),self.assertRaises(ValueError):self.decode(raw=change_header(raw,index,value))
        with self.assertRaises(ValueError):self.decode(raw=change_header(raw,3,1,205))
    def test_layout_pbo_capacity_and_wire_arithmetic_are_checked(self):
        raw=self.samples['basic'][0]
        for index,value in ((12,0),(12,965),(13,605),(14,0),(15,0),(16,3),(17,4097),(18,1),(19,4097),
                            (20,1),(22,44),(22,2**64-1),(23,16),(24,1),(25,44),(25,8*1024*1024+1)):
            with self.subTest(index=index,value=value),self.assertRaises(ValueError):self.decode(raw=change_header(raw,index,value))
    def test_every_terminal_counter_and_status_is_checked(self):
        raw=self.samples['basic'][0];fields=list(FOOTER.unpack(raw[-96:]))
        for i in range(len(fields)):
            changed=fields.copy()
            changed[i]=b'x'*len(changed[i]) if isinstance(changed[i],bytes) else changed[i]+1
            with self.subTest(index=i),self.assertRaises(ValueError):self.decode(raw=raw[:-96]+FOOTER.pack(*changed))
    def test_failed_capture_footer_is_rejected(self):
        with self.assertRaises(ValueError):self.decode('limit')
    def test_complete_footer_write_followed_by_emitter_failure_cannot_close_window(self):
        raw,stats=self.samples['footerfail'];self.assertEqual(raw,self.samples['basic'][0])
        self.assertNotEqual(stats['finish'],0);self.assertNotEqual(stats['error'],0)
        with self.assertRaises(ValueError):self.decode('footerfail')
    def test_successful_out_of_band_receipt_is_mandatory_and_bound_to_entire_stream(self):
        raw,stats=self.samples['basic'];receipt=finalization_receipt(raw,stats)
        for changed in (None,{},receipt|{'extra':1},receipt|{'nonce':'0'*64},receipt|{'stream_sha256':'0'*64},
                        receipt|{'stream_nbytes':len(raw)-1},receipt|{'finish_result':-1},receipt|{'error':1},
                        receipt|{'forwards':1},receipt|{'attempts':1},receipt|{'captured':1},
                        receipt|{'data_wire_bytes':409},receipt|{'finish_result':False}):
            with self.subTest(receipt=changed),self.assertRaises(ValueError):self.decode(producer_receipt=changed)
        # Successful status from another byte stream cannot be reused even for same nonce/counts.
        with self.assertRaises(ValueError):self.decode('rgb',producer_receipt=receipt)
    def test_unique_match_requires_all_labels_and_bytes(self):
        records=self.decode()['records'];rgb=codec.normalize_rgb(records[0])
        args=dict(nonce=NONCE,host_call=1,camera=1,context_tag=101,width=5,height=3,rgb=rgb)
        match=codec.match_cpu_candidate(records,**args)
        self.assertEqual((match['status'],match['record_indices']),('unique_cpu_byte_candidate',[1]))
        for flag in ('native_admitted','gpu_write_proven','physical_frame_proven'):self.assertIs(match[flag],False)
        for name,value in (('context_tag',102),('rgb',bytes(45)),('nonce',b'x'*32)):
            with self.subTest(name=name):self.assertEqual(codec.match_cpu_candidate(records,**(args|{name:value}))['status'],'no_cpu_byte_candidate')
    def test_equal_bytes_and_unknown_producers_cannot_be_unique(self):
        for mode,status in (('ambiguous','ambiguous_cpu_byte_candidates'),('unknownproducer','insufficient_producer_metadata')):
            records=self.decode(mode)['records'];rgb=codec.normalize_rgb(records[0])
            result=codec.match_cpu_candidate(records,nonce=NONCE,host_call=1,camera=1,context_tag=101,width=5,height=3,rgb=rgb)
            with self.subTest(mode=mode):self.assertEqual(result['status'],status)
    def test_normalization_revalidates_public_record_and_match_input(self):
        record=self.decode()['records'][0]
        for broken in (replace(record,payload=b''),replace(record,width=-1),replace(record,row_stride=999)):
            with self.assertRaises(ValueError):codec.normalize_rgb(broken)
        with self.assertRaises(ValueError):codec.match_cpu_candidate([record]*25,nonce=NONCE,host_call=1,camera=1,context_tag=101,width=5,height=3,rgb=bytes(45))
    def test_largest_declared_24_record_window_stays_bounded(self):
        result=self.decode('max');self.assertEqual(len(result['records']),24)
        self.assertEqual(len(self.samples['max'][0]),55900512)

if __name__=='__main__':unittest.main()
