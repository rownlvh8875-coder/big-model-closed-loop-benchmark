"""Owned clock and successful/failed API snapshots only; no external calls or sleeps."""
import unittest
try:from scripts import engine_clock_image_preparation_v4 as p
except ImportError:p=None
class VisibilityTests(unittest.TestCase):
 def client(self,rows):
  class Client:
   deadline=100
   def __init__(self):self.rows=iter(rows);self.names=[]
   def get_json(self,endpoint,name):
    self.names.append(name);value=next(self.rows)
    if isinstance(value,Exception):raise value
    return value
  return Client()
 def clock(self):
  now=[0.]
  return lambda:now[0],lambda seconds:now.__setitem__(0,now[0]+seconds)
 def test_empty_successful_snapshot_can_wait_for_actual_nonempty_proof(self):
  self.assertIsNotNone(p);client=self.client([{'total_count':0,'workflow_runs':[]},{'total_count':1,'workflow_runs':[{'id':11}]}]);clock,sleep=self.clock()
  result,record=p.observe_unique(client,'registered/endpoint',clock=clock,sleep=sleep)
  self.assertEqual(1,result['total_count']);self.assertEqual(2,record['snapshots']);self.assertEqual(['live-unique-00.json','live-unique-01.json'],client.names);self.assertEqual(100,client.deadline)
 def test_always_empty_is_finite_and_restores_shared_deadline(self):
  self.assertIsNotNone(p);client=self.client([{'total_count':0,'workflow_runs':[]}]*6);clock,sleep=self.clock()
  with self.assertRaisesRegex(ValueError,'^IMAGE_WORKFLOW_VISIBILITY_REJECTED$'):p.observe_unique(client,'registered/endpoint',clock=clock,sleep=sleep)
  self.assertEqual(6,len(client.names));self.assertEqual(100,client.deadline)
 def test_nonempty_duplicate_is_not_repolled_or_replaced(self):
  self.assertIsNotNone(p);value={'total_count':2,'workflow_runs':[{'id':11},{'id':12}]};client=self.client([value]);clock,sleep=self.clock();result,record=p.observe_unique(client,'registered/endpoint',clock=clock,sleep=sleep)
  self.assertEqual(value,result);self.assertEqual(1,record['snapshots']);self.assertEqual(1,len(client.names))
 def test_http_error_has_no_retry_or_wait(self):
  self.assertIsNotNone(p);client=self.client([ValueError('owned error')]);clock,sleep=self.clock()
  with self.assertRaises(ValueError):p.observe_unique(client,'registered/endpoint',clock=clock,sleep=sleep)
  self.assertEqual(1,len(client.names));self.assertEqual(100,client.deadline)
if __name__=='__main__':unittest.main()
