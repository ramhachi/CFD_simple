import shutil
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
TEMP_DIR = ROOT_DIR / 'files_for_smoke_test'


def write_box_stl(path: Path, size_x: float, size_y: float, size_z: float):
    from dummy import create_box
    create_box(path, size_x, size_y, size_z, offset=(size_x / 2.0, 0.0, size_z / 2.0))


def main():
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    TEMP_DIR.mkdir()
    write_box_stl(TEMP_DIR / 'Part Studio 1 - Part 1.stl', 160.0, 85.0, 45.0)

    user_input = '20\n2\n0\n0\n0\n0\n'
    process = subprocess.run(
        [sys.executable, 'run_cfd.py', '--no-docker', '--stl-dir', str(TEMP_DIR)],
        cwd=ROOT_DIR,
        input=user_input,
        text=True,
        check=False,
        capture_output=True,
    )

    print('--- STDOUT ---')
    print(process.stdout)
    print('--- STDERR ---')
    print(process.stderr)
    print(f'Exit code: {process.returncode}')

    params_path = ROOT_DIR / 'cfd_params.txt'
    if params_path.exists():
        print('\n--- cfd_params.txt ---')
        print(params_path.read_text(encoding='utf-8'))

    if process.returncode != 0:
        sys.exit(process.returncode)


if __name__ == '__main__':
    main()
