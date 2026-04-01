from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent


def read_params():
    params_path = ROOT_DIR / 'cfd_params.txt'
    params = {}
    if not params_path.exists():
        return params
    with params_path.open('r', encoding='utf-8') as handle:
        for line in handle:
            if '=' in line:
                key, value = line.strip().split('=', 1)
                params[key] = value
    return params


def parse_table(filepath: Path):
    if not filepath.exists():
        return None, None

    header = None
    last_values = None
    with filepath.open('r', encoding='utf-8', errors='ignore') as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith('#'):
                if 'Time' in line:
                    header = line.lstrip('#').strip().replace('\t', ' ').split()
                continue
            values = [float(item) for item in line.replace('(', ' ').replace(')', ' ').split()]
            if header and len(values) == len(header):
                last_values = dict(zip(header, values))
            else:
                last_values = values
    return header, last_values


def print_float(label: str, value: float, unit: str = '') -> None:
    suffix = f' {unit}' if unit else ''
    print(f' {label:<22}: {value:.4f}{suffix}')


def main():
    params = read_params()
    forces_header, forces = parse_table(ROOT_DIR / 'postProcessing' / 'forces_all' / '0' / 'force.dat')
    coeff_header, coeffs = parse_table(ROOT_DIR / 'postProcessing' / 'forceCoeffs_all' / '0' / 'coefficient.dat')

    print('\n==================================================')
    print('                 Aerodynamic Results')
    print('==================================================')

    if params:
        if 'MODEL_LX' in params and 'MODEL_LY' in params and 'MODEL_LZ' in params:
            print(
                ' Bounding Box [m]        : '
                f"X={float(params['MODEL_LX']):.4f} "
                f"Y={float(params['MODEL_LY']):.4f} "
                f"Z={float(params['MODEL_LZ']):.4f}"
            )
        if 'L_REF' in params and 'A_REF' in params:
            print(f" Reference Length [m]   : {float(params['L_REF']):.4f}")
            print(f" Reference Area [m^2]   : {float(params['A_REF']):.4f}")
        if 'REYNOLDS_NUMBER' in params:
            print(f" Estimated Reynolds No. : {int(float(params['REYNOLDS_NUMBER'])):,}")
        print('--------------------------------------------------')

    if isinstance(coeffs, dict):
        print_float('Drag Coefficient (Cd)', coeffs.get('Cd', 0.0))
        print_float('Lift Coefficient (Cl)', coeffs.get('Cl', 0.0))
        if 'Cs' in coeffs:
            print_float('Side Coefficient (Cs)', coeffs.get('Cs', 0.0))
    else:
        print(' coefficient.dat を読み取れませんでした。')

    print('--------------------------------------------------')

    if isinstance(forces, dict):
        total_drag = forces.get('total_x', 0.0)
        total_side = forces.get('total_y', 0.0)
        total_lift = forces.get('total_z', 0.0)
        pressure_drag = forces.get('pressure_x', 0.0)
        pressure_lift = forces.get('pressure_z', 0.0)
        viscous_drag = forces.get('viscous_x', 0.0)
        viscous_lift = forces.get('viscous_z', 0.0)

        print_float('Total Drag', total_drag, 'N')
        print_float('Total Lift', total_lift, 'N')
        print_float('Total Side Force', total_side, 'N')
        print_float('Pressure Drag', pressure_drag, 'N')
        print_float('Viscous Drag', viscous_drag, 'N')
        print_float('Pressure Lift', pressure_lift, 'N')
        print_float('Viscous Lift', viscous_lift, 'N')
    else:
        print(' force.dat を読み取れませんでした。')

    print('==================================================')
    print('ParaView では VTK/ ディレクトリ内のデータを開いて可視化できます。')


if __name__ == '__main__':
    main()
