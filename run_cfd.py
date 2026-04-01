import argparse
import math
import os
import re
import shlex
import shutil
import struct
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_MODEL_DIRS = ("model", "models")
AIR_KINEMATIC_VISCOSITY = 1.5e-5
MESH_LEVEL_LABELS = {
    '1': '粗い',
    '2': '普通',
    '3': '細かい',
}
MESH_LEVEL_SETTINGS = {
    '1': {'body_cells': 6, 'surface_level': '2 3', 'feature_level': '2', 'layers': 2},
    '2': {'body_cells': 8, 'surface_level': '3 4', 'feature_level': '3', 'layers': 3},
    '3': {'body_cells': 10, 'surface_level': '4 5', 'feature_level': '4', 'layers': 5},
}


@dataclass
class StlPart:
    source_path: Path
    relative_path: Path
    safe_base: str
    role: str
    raw_bounds: Tuple[float, float, float, float, float, float]
    unit_scale: float
    unit_label: str

    @property
    def scaled_bounds(self) -> Tuple[float, float, float, float, float, float]:
        return tuple(value * self.unit_scale for value in self.raw_bounds)


@dataclass
class PreparedPart:
    part: StlPart
    translation_m: Tuple[float, float, float]


@dataclass
class CaseConfiguration:
    prepared_parts: List[PreparedPart]
    surface_names: List[str]
    frame_names: List[str]
    tire_names: List[str]
    offsets_mm: Dict[str, Tuple[float, float, float]]
    clearance_mm: float
    auto_ground_shift_mm: float
    velocity: float
    mesh_level: str
    overall_bounds: Tuple[float, float, float, float, float, float]
    domain: Dict[str, float]


class ConfigurationError(RuntimeError):
    pass


def to_display_path(path: Path) -> Path:
    try:
        return path.relative_to(ROOT_DIR)
    except ValueError:
        return path


def sanitize_name(stl_filename: str) -> str:
    name = Path(stl_filename).stem
    name = unicodedata.normalize('NFKD', name)
    name = name.encode('ascii', 'ignore').decode('ascii')
    name = re.sub(r'[^A-Za-z0-9]+', '_', name)
    name = name.strip('_')
    if not name:
        return 'body'
    if name[0].isdigit():
        name = f'body_{name}'
    return name


def make_safe_names(stl_paths: Sequence[Path]) -> Dict[Path, str]:
    used = set()
    result: Dict[Path, str] = {}
    for path in stl_paths:
        base = sanitize_name(path.name)
        candidate = base
        suffix = 2
        while candidate in used:
            candidate = f"{base}_{suffix}"
            suffix += 1
        used.add(candidate)
        result[path] = candidate
    return result


def read_stl_bounds(filepath: Path) -> Tuple[float, float, float, float, float, float]:
    file_size = filepath.stat().st_size
    if file_size >= 84:
        with filepath.open('rb') as handle:
            handle.read(80)
            triangle_count = struct.unpack('<I', handle.read(4))[0]
            if file_size == 84 + triangle_count * 50 and triangle_count > 0:
                return _read_stl_binary(filepath, triangle_count)
    return _read_stl_ascii(filepath)


def _read_stl_binary(filepath: Path, triangle_count: int) -> Tuple[float, float, float, float, float, float]:
    xmin = ymin = zmin = float('inf')
    xmax = ymax = zmax = float('-inf')
    with filepath.open('rb') as handle:
        handle.read(84)
        for _ in range(triangle_count):
            data = handle.read(50)
            if len(data) < 50:
                break
            values = struct.unpack('<12f', data[:48])
            for index in range(3):
                x, y, z = values[3 + index * 3], values[4 + index * 3], values[5 + index * 3]
                xmin = min(xmin, x)
                xmax = max(xmax, x)
                ymin = min(ymin, y)
                ymax = max(ymax, y)
                zmin = min(zmin, z)
                zmax = max(zmax, z)
    if xmin == float('inf'):
        raise ConfigurationError(f"STL の頂点を読み取れませんでした: {filepath}")
    return xmin, xmax, ymin, ymax, zmin, zmax


def _read_stl_ascii(filepath: Path) -> Tuple[float, float, float, float, float, float]:
    xmin = ymin = zmin = float('inf')
    xmax = ymax = zmax = float('-inf')
    found = False
    with filepath.open('r', errors='ignore') as handle:
        for line in handle:
            parts = line.strip().split()
            if len(parts) == 4 and parts[0].lower() == 'vertex':
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                xmin = min(xmin, x)
                xmax = max(xmax, x)
                ymin = min(ymin, y)
                ymax = max(ymax, y)
                zmin = min(zmin, z)
                zmax = max(zmax, z)
                found = True
    if not found:
        raise ConfigurationError(f"ASCII STL の頂点を読み取れませんでした: {filepath}")
    return xmin, xmax, ymin, ymax, zmin, zmax


def infer_unit_scale(bounds: Tuple[float, float, float, float, float, float], unit_mode: str) -> Tuple[float, str]:
    lx = abs(bounds[1] - bounds[0])
    ly = abs(bounds[3] - bounds[2])
    lz = abs(bounds[5] - bounds[4])
    characteristic = max(lx, ly, lz)

    if unit_mode == 'm':
        return 1.0, 'm'
    if unit_mode == 'mm':
        return 0.001, 'mm'
    if characteristic > 10.0:
        return 0.001, 'mm'
    return 1.0, 'm'


def classify_role(path: Path) -> str:
    stem = path.stem.lower()
    if stem == 'frame':
        return 'frame'
    if stem == 'tires':
        return 'tires'
    return 'surface'


def resolve_stl_directories(stl_dir: str = None) -> List[Path]:
    if stl_dir:
        candidate = Path(stl_dir)
        if not candidate.is_absolute():
            candidate = ROOT_DIR / candidate
        candidate = candidate.resolve()
        if not candidate.exists() or not candidate.is_dir():
            raise ConfigurationError(f"STL ディレクトリが見つかりません: {candidate}")
        return [candidate]

    directories = [(ROOT_DIR / name).resolve() for name in DEFAULT_MODEL_DIRS if (ROOT_DIR / name).is_dir()]
    non_empty = [
        directory for directory in directories
        if any(entry.is_file() and entry.suffix.lower() == '.stl' for entry in directory.iterdir())
    ]

    if non_empty:
        return [non_empty[0]]

    if not directories:
        (ROOT_DIR / 'models').mkdir(exist_ok=True)
        directories.append((ROOT_DIR / 'models').resolve())

    return [directories[0]]


def discover_stl_files(stl_dir: str = None, unit_mode: str = 'auto') -> List[StlPart]:
    directories = resolve_stl_directories(stl_dir)
    paths: List[Path] = []
    for directory in directories:
        for entry in sorted(directory.iterdir(), key=lambda path: path.name.casefold()):
            if entry.is_file() and entry.suffix.lower() == '.stl':
                paths.append(entry.resolve())

    if not paths:
        searched = ', '.join(str(to_display_path(path)) for path in directories)
        raise ConfigurationError(
            "STL ファイルが見つかりません。\n"
            f"次のディレクトリを確認しました: {searched or ', '.join(str(path) for path in directories)}\n"
            "解析したい STL を model/ または models/ に入れて再実行してください。"
        )

    safe_names = make_safe_names(paths)
    parts: List[StlPart] = []
    for path in paths:
        raw_bounds = read_stl_bounds(path)
        unit_scale, unit_label = infer_unit_scale(raw_bounds, unit_mode)
        parts.append(
            StlPart(
                source_path=path,
                relative_path=to_display_path(path),
                safe_base=safe_names[path],
                role=classify_role(path),
                raw_bounds=raw_bounds,
                unit_scale=unit_scale,
                unit_label=unit_label,
            )
        )
    return parts


def get_float_input(prompt: str, default: float = None) -> float:
    while True:
        try:
            value = input(prompt).strip()
            if not value and default is not None:
                return float(default)
            return float(value)
        except ValueError:
            print("有効な数値を入力してください。")


def get_mesh_level(default: str = '2') -> str:
    value = input(f"メッシュの細かさを選択してください (1:粗い 2:普通 3:細かい) [デフォルト: {default}]: ").strip()
    if value not in MESH_LEVEL_SETTINGS:
        return default
    return value


def get_xyz_input(part_label: str) -> Tuple[float, float, float]:
    print(f"\n--- {part_label} の配置設定 ---")
    x = get_float_input(f"{part_label} の X方向移動量 (mm) [デフォルト: 0]: ", 0.0)
    y = get_float_input(f"{part_label} の Y方向移動量 (mm) [デフォルト: 0]: ", 0.0)
    z = get_float_input(f"{part_label} の 追加 Z方向移動量 (mm) [デフォルト: 0]: ", 0.0)
    return x, y, z


def clamp_int(value: float, min_value: int, max_value: int) -> int:
    return max(min_value, min(max_value, int(math.ceil(value))))


def clamp_float(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def compute_domain(
    xmin: float,
    xmax: float,
    ymin: float,
    ymax: float,
    zmin: float,
    zmax: float,
    velocity: float,
    mesh_level: str,
) -> Dict[str, float]:
    lx = max(xmax - xmin, 1e-6)
    ly = max(ymax - ymin, 1e-6)
    lz = max(zmax - zmin, 1e-6)
    characteristic = max(lx, ly, lz)

    upstream = 3.0 * characteristic
    downstream = 7.0 * characteristic
    lateral_half_span = max(3.0 * ly, 1.5 * characteristic)
    top_margin = max(4.0 * lz, 1.5 * characteristic)

    dom_xmin = xmin - upstream
    dom_xmax = xmax + downstream
    y_center = (ymin + ymax) / 2.0
    dom_ymin = y_center - lateral_half_span
    dom_ymax = y_center + lateral_half_span
    dom_zmin = 0.0
    dom_zmax = zmax + top_margin

    base_cell_size = characteristic / MESH_LEVEL_SETTINGS[mesh_level]['body_cells']
    dom_lx = dom_xmax - dom_xmin
    dom_ly = dom_ymax - dom_ymin
    dom_lz = dom_zmax - dom_zmin

    nx = clamp_int(dom_lx / base_cell_size, 48, 140)
    ny = clamp_int(dom_ly / base_cell_size, 24, 120)
    nz = clamp_int(dom_lz / base_cell_size, 24, 96)

    dx = dom_lx / nx
    dy = dom_ly / ny
    dz = dom_lz / nz

    loc_x = dom_xmin + 2.37 * dx
    loc_y = clamp_float(ymax + 1.37 * dy, dom_ymin + 1.5 * dy, dom_ymax - 1.5 * dy)
    loc_z = clamp_float(zmax + 1.37 * dz, dom_zmin + 1.5 * dz, dom_zmax - 1.5 * dz)

    a_ref = max(ly * lz, 1e-6)
    l_ref = characteristic
    cofr_x = (xmin + xmax) / 2.0
    cofr_y = (ymin + ymax) / 2.0
    cofr_z = (zmin + zmax) / 2.0

    turbulence_intensity = 0.01
    turbulence_length_scale = max(0.07 * characteristic, 0.005)
    turbulence_k = 1.5 * (velocity * turbulence_intensity) ** 2
    turbulence_omega = math.sqrt(max(turbulence_k, 1e-12)) / ((0.09 ** 0.25) * turbulence_length_scale)
    reynolds_number = velocity * l_ref / AIR_KINEMATIC_VISCOSITY

    return {
        'model_lx': round(lx, 6),
        'model_ly': round(ly, 6),
        'model_lz': round(lz, 6),
        'dom_xmin': round(dom_xmin, 6),
        'dom_xmax': round(dom_xmax, 6),
        'dom_ymin': round(dom_ymin, 6),
        'dom_ymax': round(dom_ymax, 6),
        'dom_zmin': round(dom_zmin, 6),
        'dom_zmax': round(dom_zmax, 6),
        'nx': nx,
        'ny': ny,
        'nz': nz,
        'base_cell_size': round(base_cell_size, 6),
        'loc_x': round(loc_x, 6),
        'loc_y': round(loc_y, 6),
        'loc_z': round(loc_z, 6),
        'l_ref': round(l_ref, 6),
        'a_ref': round(a_ref, 6),
        'cofr_x': round(cofr_x, 6),
        'cofr_y': round(cofr_y, 6),
        'cofr_z': round(cofr_z, 6),
        'turbulence_intensity': turbulence_intensity,
        'turbulence_length_scale': round(turbulence_length_scale, 6),
        'turbulence_k': round(turbulence_k, 6),
        'turbulence_omega': round(turbulence_omega, 6),
        'reynolds_number': round(reynolds_number, 0),
    }


def build_case_configuration(
    parts: Sequence[StlPart],
    offsets_mm: Dict[str, Tuple[float, float, float]],
    clearance_mm: float,
    velocity: float,
    mesh_level: str,
) -> CaseConfiguration:
    min_prealigned_z = float('inf')
    for part in parts:
        _, _, _, _, zmin, _ = part.scaled_bounds
        _, _, z_shift_mm = offsets_mm[part.safe_base]
        min_prealigned_z = min(min_prealigned_z, zmin + z_shift_mm / 1000.0)

    clearance_m = clearance_mm / 1000.0
    auto_ground_shift_m = clearance_m - min_prealigned_z

    prepared_parts: List[PreparedPart] = []
    ov_xmin = ov_ymin = ov_zmin = float('inf')
    ov_xmax = ov_ymax = ov_zmax = float('-inf')

    for part in parts:
        x_shift_mm, y_shift_mm, z_shift_mm = offsets_mm[part.safe_base]
        translation_m = (
            x_shift_mm / 1000.0,
            y_shift_mm / 1000.0,
            z_shift_mm / 1000.0 + auto_ground_shift_m,
        )
        xmin, xmax, ymin, ymax, zmin, zmax = part.scaled_bounds
        ov_xmin = min(ov_xmin, xmin + translation_m[0])
        ov_xmax = max(ov_xmax, xmax + translation_m[0])
        ov_ymin = min(ov_ymin, ymin + translation_m[1])
        ov_ymax = max(ov_ymax, ymax + translation_m[1])
        ov_zmin = min(ov_zmin, zmin + translation_m[2])
        ov_zmax = max(ov_zmax, zmax + translation_m[2])
        prepared_parts.append(PreparedPart(part=part, translation_m=translation_m))

    overall_bounds = (ov_xmin, ov_xmax, ov_ymin, ov_ymax, ov_zmin, ov_zmax)
    domain = compute_domain(*overall_bounds, velocity=velocity, mesh_level=mesh_level)
    surface_names = [prepared.part.safe_base for prepared in prepared_parts]
    frame_names = [prepared.part.safe_base for prepared in prepared_parts if prepared.part.role == 'frame']
    tire_names = [prepared.part.safe_base for prepared in prepared_parts if prepared.part.role == 'tires']

    return CaseConfiguration(
        prepared_parts=prepared_parts,
        surface_names=surface_names,
        frame_names=frame_names,
        tire_names=tire_names,
        offsets_mm=offsets_mm,
        clearance_mm=clearance_mm,
        auto_ground_shift_mm=auto_ground_shift_m * 1000.0,
        velocity=velocity,
        mesh_level=mesh_level,
        overall_bounds=overall_bounds,
        domain=domain,
    )


def clear_generated_case() -> None:
    removable_dirs = [
        ROOT_DIR / '0',
        ROOT_DIR / 'constant',
        ROOT_DIR / 'system',
        ROOT_DIR / 'VTK',
        ROOT_DIR / 'postProcessing',
        ROOT_DIR / 'visualization_output',
        ROOT_DIR / 'logs',
    ]
    for directory in removable_dirs:
        if directory.exists():
            shutil.rmtree(directory)

    for entry in ROOT_DIR.iterdir():
        if entry.is_dir() and entry.name.isdigit():
            shutil.rmtree(entry)
        elif entry.is_dir() and re.fullmatch(r'processor\d+', entry.name):
            shutil.rmtree(entry)
        elif entry.is_file() and entry.name.startswith('log.'):
            entry.unlink()

    for generated_file in (ROOT_DIR / 'cfd_params.txt', ROOT_DIR / 'setup_stl.sh'):
        if generated_file.exists():
            generated_file.unlink()


def prepare_runtime_templates() -> None:
    for name in ('0', 'system', 'constant'):
        shutil.copytree(ROOT_DIR / 'template' / name, ROOT_DIR / name)


def write_setup_stl_script(configuration: CaseConfiguration) -> None:
    lines = [
        '#!/bin/sh',
        '# This file is auto-generated by run_cfd.py',
        'set -eu',
        '',
        'mkdir -p constant/triSurface',
        '',
    ]

    for prepared in configuration.prepared_parts:
        source_rel = prepared.part.relative_path.as_posix()
        translation = ' '.join(format(value, '.6f') for value in prepared.translation_m)
        read_scale = format(prepared.part.unit_scale, '.6f').rstrip('0').rstrip('.') or '1'
        safe_file = f"{prepared.part.safe_base}.stl"
        lines.append(f"echo 'Processing {safe_file} from {source_rel} ({prepared.part.unit_label}) ...'")
        lines.append(
            'surfaceTransformPoints '
            f"-read-scale {read_scale} "
            f"-translate '({translation})' "
            f"{shlex.quote('./' + source_rel)} "
            f"{shlex.quote('constant/triSurface/' + safe_file)}"
        )
        lines.append('')

    script_path = ROOT_DIR / 'setup_stl.sh'
    script_path.write_text('\n'.join(lines), encoding='utf-8')
    script_path.chmod(0o755)


def write_params_file(configuration: CaseConfiguration) -> None:
    params = {
        'VELOCITY': configuration.velocity,
        'MESH_LEVEL': configuration.mesh_level,
        'MESH_LEVEL_LABEL': MESH_LEVEL_LABELS[configuration.mesh_level],
        'SURFACE_STLS': ','.join(configuration.surface_names),
        'AERO_STLS': ','.join(
            prepared.part.safe_base
            for prepared in configuration.prepared_parts
            if prepared.part.role == 'surface'
        ),
        'FRAME_STLS': ','.join(configuration.frame_names),
        'TIRE_STLS': ','.join(configuration.tire_names),
        'USE_FRAME': 1 if configuration.frame_names else 0,
        'USE_TIRES': 1 if configuration.tire_names else 0,
        'CLEARANCE_MM': round(configuration.clearance_mm, 3),
        'AUTO_GROUND_SHIFT_MM': round(configuration.auto_ground_shift_mm, 3),
    }
    params.update({key.upper(): value for key, value in configuration.domain.items()})

    output_lines = [f"{key}={value}" for key, value in params.items()]
    (ROOT_DIR / 'cfd_params.txt').write_text('\n'.join(output_lines) + '\n', encoding='utf-8')


def generate_openfoam_case() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT_DIR / 'template' / 'configure_templates.py')],
        cwd=ROOT_DIR,
        check=False,
    )
    if result.returncode != 0:
        raise ConfigurationError('OpenFOAM 設定ファイルの生成に失敗しました。')


def docker_image_exists(image_name: str) -> bool:
    result = subprocess.run(
        ['docker', 'image', 'inspect', image_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def ensure_runtime_image(env: Dict[str, str], image_name: str = 'fsae-cfd') -> None:
    if docker_image_exists(image_name):
        return

    print(f"Docker イメージ '{image_name}' が見つからないため、自動ビルドします。")
    build = subprocess.run(
        ['docker', 'build', '-t', image_name, '.'],
        cwd=ROOT_DIR,
        env=env,
        check=False,
    )
    if build.returncode != 0:
        raise ConfigurationError("Docker イメージのビルドに失敗しました。Docker Desktop の起動状態を確認してください。")


def move_logs_to_directory() -> None:
    logs_dir = ROOT_DIR / 'logs'
    logs_dir.mkdir(exist_ok=True)
    for log_file in ROOT_DIR.glob('log.*'):
        destination = logs_dir / log_file.name
        if destination.exists():
            destination.unlink()
        shutil.move(str(log_file), str(destination))


def run_post_processing_on_host() -> None:
    extract = subprocess.run([sys.executable, str(ROOT_DIR / 'extract_results.py')], cwd=ROOT_DIR, check=False)
    if extract.returncode != 0:
        print('警告: extract_results.py の実行に失敗しました。')

    render = subprocess.run([sys.executable, str(ROOT_DIR / 'make_video.py')], cwd=ROOT_DIR, check=False)
    if render.returncode != 0:
        print('警告: make_video.py の実行に失敗しました。Docker 版ランチャーの利用を推奨します。')


def try_generate_visualizations() -> None:
    print('\n[可視化画像・動画生成中...]')
    try:
        render = subprocess.run(
            [sys.executable, str(ROOT_DIR / 'make_video.py')],
            cwd=ROOT_DIR,
            check=False,
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        print('警告: 可視化生成が時間内に完了しませんでした。CFD 結果自体は保存されています。')
        return

    if render.returncode != 0:
        print('警告: 可視化生成に失敗しました。CFD 結果自体は保存されています。必要に応じて ParaView で VTK/ を直接開いてください。')
    else:
        print('可視化ファイルの生成が完了しました。')


def run_analysis(args: argparse.Namespace) -> int:
    env = os.environ.copy()
    env['PATH'] = env.get('PATH', '') + ':/usr/local/bin:/opt/homebrew/bin:/Applications/Docker.app/Contents/Resources/bin'

    if args.no_docker:
        print('[TEST MODE] Docker execution skipped.')
        return 0

    if os.environ.get('IN_DOCKER') == '1':
        print('\n==================================================')
        print('    Starting CFD Analysis inside Docker')
        print('==================================================')
        proc = subprocess.run(['bash', '-lc', './template/Allrun'], cwd=ROOT_DIR, check=False)
        if proc.returncode != 0:
            print('解析中にエラーが発生しました。')
            return proc.returncode
        move_logs_to_directory()
        subprocess.run([sys.executable, str(ROOT_DIR / 'extract_results.py')], cwd=ROOT_DIR, check=False)
        try_generate_visualizations()
        return 0

    try:
        ensure_runtime_image(env)
    except ConfigurationError as error:
        print(f'エラー: {error}')
        return 1

    command = 'cd /data && ./template/Allrun && python3 extract_results.py'
    proc = subprocess.run(
        ['docker', 'run', '--rm', '-v', f'{ROOT_DIR}:/data', 'fsae-cfd', 'bash', '-lc', command],
        env=env,
        check=False,
    )
    if proc.returncode != 0:
        print('Docker 実行中にエラーが発生しました。')
        return proc.returncode

    move_logs_to_directory()
    try_generate_visualizations()
    return 0


def print_detected_parts(parts: Sequence[StlPart]) -> None:
    print('\n検出された STL:')
    for part in parts:
        xmin, xmax, ymin, ymax, zmin, zmax = part.scaled_bounds
        print(f"  - {part.relative_path.as_posix()}")
        print(f"      OpenFOAM名 : {part.safe_base}.stl")
        print(f"      単位推定   : {part.unit_label} (scale={part.unit_scale})")
        print(f"      寸法[m]    : X={xmax - xmin:.4f} Y={ymax - ymin:.4f} Z={zmax - zmin:.4f}")


def print_case_summary(configuration: CaseConfiguration) -> None:
    xmin, xmax, ymin, ymax, zmin, zmax = configuration.overall_bounds
    domain = configuration.domain
    print('\n[自動調整結果]')
    print(f"  全体境界         : X[{xmin:.4f}, {xmax:.4f}] Y[{ymin:.4f}, {ymax:.4f}] Z[{zmin:.4f}, {zmax:.4f}]")
    print(f"  追加自動Zシフト  : {configuration.auto_ground_shift_mm:.2f} mm")
    print(
        '  風洞ドメイン     : '
        f"X[{domain['dom_xmin']:.3f}, {domain['dom_xmax']:.3f}] "
        f"Y[{domain['dom_ymin']:.3f}, {domain['dom_ymax']:.3f}] "
        f"Z[{domain['dom_zmin']:.3f}, {domain['dom_zmax']:.3f}]"
    )
    print(f"  背景メッシュ     : ({domain['nx']}, {domain['ny']}, {domain['nz']})")
    print(f"  背景セル寸法     : 約 {domain['base_cell_size']:.4f} m")
    print(f"  代表長さ / 面積  : Lref={domain['l_ref']:.4f} m, Aref={domain['a_ref']:.4f} m^2")
    print(f"  推定Re数         : {int(domain['reynolds_number']):,}")
    print(f"  メッシュ段階     : {configuration.mesh_level} ({MESH_LEVEL_LABELS[configuration.mesh_level]})")


def ensure_directory_is_mountable(parts: Sequence[StlPart], no_docker: bool) -> None:
    if no_docker:
        return
    for part in parts:
        if not part.source_path.is_relative_to(ROOT_DIR):
            raise ConfigurationError(
                f"Docker 実行時はリポジトリ配下の STL のみ使用できます: {part.source_path}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description='FSAE CFD Setup Wizard')
    parser.add_argument('--no-docker', action='store_true', help='Do not run docker, just prepare files')
    parser.add_argument('--stl-dir', help='Directory containing STL files (default: auto-detect model/ and models/)')
    parser.add_argument('--stl-unit', choices=('auto', 'm', 'mm'), default='auto', help='Interpret STL coordinates as meters or millimeters')
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(line_buffering=True)
    except AttributeError:
        pass

    os.chdir(ROOT_DIR)

    print('==================================================')
    print('      FSAE 簡易CFDシステム Setup Wizard')
    print('==================================================')

    try:
        parts = discover_stl_files(args.stl_dir, args.stl_unit)
        ensure_directory_is_mountable(parts, args.no_docker)
    except ConfigurationError as error:
        print(f'エラー: {error}')
        sys.exit(1)

    print_detected_parts(parts)

    velocity = get_float_input('\n解析する風速を入力してください (m/s) [デフォルト: 20]: ', 20.0)
    mesh_level = get_mesh_level('2')
    clearance = get_float_input(
        '\n最低地上高 (最も低い点と地面の距離, mm) を入力してください [デフォルト: 0]: ',
        0.0,
    )

    offsets_mm: Dict[str, Tuple[float, float, float]] = {}
    for part in parts:
        offsets_mm[part.safe_base] = get_xyz_input(part.relative_path.as_posix())

    configuration = build_case_configuration(parts, offsets_mm, clearance, velocity, mesh_level)
    print_case_summary(configuration)

    print('\n[システム構築中...]')
    clear_generated_case()
    prepare_runtime_templates()
    write_setup_stl_script(configuration)
    write_params_file(configuration)

    try:
        generate_openfoam_case()
    except ConfigurationError as error:
        print(f'エラー: {error}')
        sys.exit(1)

    print('\n設定が完了しました。解析を開始します。')
    print('--------------------------------------------------')
    exit_code = run_analysis(args)
    if exit_code != 0:
        sys.exit(exit_code)


if __name__ == '__main__':
    main()
