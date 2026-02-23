import os
import sys

def parse_forces_dat(filepath):
    # force.dat または forceCoeffs.dat をパースして最終行の値を取得
    if not os.path.exists(filepath):
        return None
    
    last_line = ""
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            last_line = line
    
    if not last_line:
        return None
    
    # 最後の行の値をパース
    # フォーマット例 (time, (fx fy fz), (m_px m_py m_pz), ...) のように括弧がネストしている
    # 単純なスペース区切りで抜き出すための処理
    parts = last_line.replace('(', ' ').replace(')', ' ').split()
    try:
        data = [float(p) for p in parts]
        return data
    except ValueError:
        return None

def main():
    print("\n\n")
    print("==================================================")
    print("                 Aerodynamic Results")
    print("==================================================")

    # 1. 係数の抽出
    coeffs_file = "postProcessing/forceCoeffs_all/0/coefficient.dat"
    if os.path.exists(coeffs_file):
        data = parse_forces_dat(coeffs_file)
        if data and len(data) >= 3:
            # forceCoeffs.dat の典型的なフォーマット (OpenFOAM verによるが概ね Cd, Cs, Cl ...)
            # data[0]=time, data[1]=Cd, data[2]=Cs, data[3]=Cl が一般的
            print(f" Drag Coefficient (Cd) : {data[1]:.4f}")
            print(f" Lift Coefficient (Cl) : {data[3]:.4f}")
        else:
            print(" 係数データのパースに失敗しました。")
    else:
        print(" coefficient.dat が見つかりません。")

    print("--------------------------------------------------")

    # 2. 力の抽出
    forces_file = "postProcessing/forces_all/0/force.dat"
    if os.path.exists(forces_file):
        data = parse_forces_dat(forces_file)
        if data and len(data) >= 7:
            # force.dat フォーマット (time, px, py, pz, vx, vy, vz)  (p:pressure, v:viscous)
            p_drag = data[1]
            p_lift = data[3]
            v_drag = data[4]
            v_lift = data[6]
            
            total_drag = p_drag + v_drag
            total_lift = p_lift + v_lift
            
            print(f" Total Drag [N] : {total_drag:.2f}  (Pressure: {p_drag:.2f}, Viscous: {v_drag:.2f})")
            print(f" Total Lift [N] : {total_lift:.2f}  (Pressure: {p_lift:.2f}, Viscous: {v_lift:.2f})")
        else:
             print(" 力データのパースに失敗しました。")
    else:
        print(" force.dat が見つかりません。")

    print("==================================================")
    print("ParaViewを用いて VTK/ ディレクトリ内のデータで可視化が可能です。")

if __name__ == "__main__":
    main()
