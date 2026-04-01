import shutil
import subprocess
import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
TEMP_ROOT = ROOT_DIR / 'test_artifacts'


class RunCfdSmokeTests(unittest.TestCase):
    def setUp(self):
        if TEMP_ROOT.exists():
            shutil.rmtree(TEMP_ROOT)
        TEMP_ROOT.mkdir()

    def tearDown(self):
        if TEMP_ROOT.exists():
            shutil.rmtree(TEMP_ROOT)

    def write_box(self, path: Path, size_x: float, size_y: float, size_z: float):
        from dummy import create_box
        create_box(path, size_x, size_y, size_z, offset=(size_x / 2.0, 0.0, size_z / 2.0))

    def run_case(self, folder_name: str, filename: str, size_x: float, size_y: float, size_z: float, expected_scale: str):
        case_dir = TEMP_ROOT / folder_name
        case_dir.mkdir()
        self.write_box(case_dir / filename, size_x, size_y, size_z)

        user_input = '20\n2\n15\n0\n0\n0\n'
        result = subprocess.run(
            [sys.executable, 'run_cfd.py', '--no-docker', '--stl-dir', str(case_dir)],
            cwd=ROOT_DIR,
            input=user_input,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + '\n' + result.stderr)

        params = (ROOT_DIR / 'cfd_params.txt').read_text(encoding='utf-8')
        self.assertIn('SURFACE_STLS=', params)
        self.assertIn('NX=', params)
        self.assertIn('A_REF=', params)
        self.assertIn(expected_scale, result.stdout)

    def test_meter_scale_model_directory(self):
        self.run_case('meter_case', 'car_body.stl', 1.2, 0.5, 0.35, '単位推定   : m')

    def test_millimeter_scale_model_directory(self):
        self.run_case('millimeter_case', 'mini4wd_box.stl', 160.0, 85.0, 45.0, '単位推定   : mm')


if __name__ == '__main__':
    unittest.main()
