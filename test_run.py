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

    def run_case(
        self,
        folder_name: str,
        filename: str,
        size_x: float,
        size_y: float,
        size_z: float,
        expected_scale: str,
        clearance_mm: float = 15.0,
    ):
        case_dir = TEMP_ROOT / folder_name
        case_dir.mkdir()
        self.write_box(case_dir / filename, size_x, size_y, size_z)

        user_input = f'20\n2\n{clearance_mm}\n0\n0\n0\n'
        result = subprocess.run(
            [sys.executable, 'run_cfd.py', '--no-docker', '--stl-dir', str(case_dir)],
            cwd=ROOT_DIR,
            input=user_input,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + '\n' + result.stderr)

        params_text = (ROOT_DIR / 'cfd_params.txt').read_text(encoding='utf-8')
        setup_script = (ROOT_DIR / 'setup_stl.sh').read_text(encoding='utf-8')
        params = dict(
            line.split('=', 1)
            for line in params_text.splitlines()
            if '=' in line
        )
        self.assertIn('SURFACE_STLS', params)
        self.assertIn('NX', params)
        self.assertIn('A_REF', params)
        self.assertIn(expected_scale, result.stdout)
        return result.stdout, params, setup_script

    def test_meter_scale_model_directory(self):
        self.run_case('meter_case', 'car_body.stl', 1.2, 0.5, 0.35, '単位推定   : m')

    def test_millimeter_scale_model_directory(self):
        self.run_case('millimeter_case', 'mini4wd_box.stl', 160.0, 85.0, 45.0, '単位推定   : mm')

    def test_space_in_filename_uses_staged_stl_input(self):
        _, _, setup_script = self.run_case(
            'space_case',
            'Part Studio 1 - Part 1.stl',
            0.372,
            0.372,
            0.854,
            '単位推定   : m',
        )
        command_line = next(
            line for line in setup_script.splitlines()
            if line.startswith('surfaceTransformPoints ')
        )
        self.assertIn('constant/triSurfaceInput/Part_Studio_1_Part_1_input.stl', command_line)
        self.assertNotIn('Part Studio 1 - Part 1.stl', command_line)

    def test_zero_clearance_enables_ground_gap_guard(self):
        stdout, params, _ = self.run_case(
            'zero_clearance_case',
            'ground_touching.stl',
            1.2,
            0.5,
            0.35,
            '単位推定   : m',
            clearance_mm=0.0,
        )
        self.assertEqual(params['CLEARANCE_MM'], '0.0')
        self.assertGreater(float(params['GROUND_GAP_GUARD_MM']), 0.0)
        self.assertEqual(params['EFFECTIVE_CLEARANCE_MM'], params['GROUND_GAP_GUARD_MM'])
        self.assertIn('0mm安全浮上量', stdout)


if __name__ == '__main__':
    unittest.main()
