"""Offline dashboard smoke and XSS escaping tests."""
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

from bigbench.dashboard import render_diagnostic_dashboard,save_diagnostic_dashboard


def fixture(name):
    return dict(model_label=name,model_sha256='b'*64,status='DIAGNOSTIC_EXECUTED',
                scenario='s_curve_left_right',completed_steps=2,
                frames=[{'world_x_m':0,'world_y_m':0},
                        {'world_x_m':1,'world_y_m':.2}],
                lane_truth={'absolute_lateral_error_max_m':.14,
                            'intrusion_depth_max_m':.0,'intrusion_count':0})


class DashboardTests(unittest.TestCase):
    def test_renders_trajectory_and_meaningful_nonranking_warning(self):
        html=render_diagnostic_dashboard([fixture('MD-V3'),fixture('Light Speed 2')])
        self.assertIn('<svg',html)
        self.assertIn('MD-V3',html)
        self.assertIn('Light Speed 2',html)
        self.assertIn('모델 성능 순위 아님',html)
        self.assertNotIn('<script',html)

    def test_escapes_untrusted_model_name(self):
        h=render_diagnostic_dashboard([fixture('<script>alert(1)</script>')])
        self.assertNotIn('<script>',h)
        self.assertIn('&lt;script&gt;',h)

    def test_file_creation_and_invalid_receipts(self):
        with TemporaryDirectory() as d:
            p=save_diagnostic_dashboard(Path(d)/'report.html',[fixture('M')])
            self.assertTrue(p.exists())
        with self.assertRaises(ValueError):
            render_diagnostic_dashboard([])
        with self.assertRaises(ValueError):
            render_diagnostic_dashboard([{'status':'INVALID'}])


if __name__=='__main__':unittest.main()
