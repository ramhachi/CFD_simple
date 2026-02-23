import os
import glob
import numpy as np
try:
    import pyvista as pv
    import vtk
    
    # VTKの不要なC++エラーログ出力を無効化（破損VTKファイル用）
    vtk.vtkObject.GlobalWarningDisplayOff()
    # 空のメッシュでの描画警告を抑制
    pv.global_theme.allow_empty_mesh = True
except ImportError:
    print("Error: pyvista not found. Please install it with: pip3 install pyvista imageio vtk")
    exit(1)

def get_vtk_steps():
    """
    Returns a sorted list of tuples: (step_number, internal_vtu_path)
    """
    files = glob.glob("VTK/data_*/internal.vtu")
    steps = []
    for f in files:
        # "VTK/data_X/internal.vtu" からステップ数を抽出
        dir_name = os.path.basename(os.path.dirname(f))
        try:
            step = int(dir_name.replace("data_", ""))
            steps.append((step, f))
        except ValueError:
            pass
    steps.sort(key=lambda x: x[0])
    return steps

def get_global_clim(mesh, fields=['p', 'U']):
    """
    Get the (min, max) scalar range for the specified fields from a given mesh.
    This ensures color scales remain consistent across different frames.
    """
    clim_dict = {}
    for field in fields:
        if field in mesh.array_names:
            arr = mesh[field]
            if len(arr.shape) > 1 and arr.shape[1] > 1:
                # ベクトルの場合は大きさ(magnitude)で最小最大を取得
                mag = np.linalg.norm(arr, axis=1)
                clim_dict[field] = (float(np.nanmin(mag)), float(np.nanmax(mag)))
            else:
                clim_dict[field] = (float(np.nanmin(arr)), float(np.nanmax(arr)))
    return clim_dict

def generate_static_slices(mesh, step, out_dir, clim=None):
    """
    Generates X, Y, Z normal slices at origin (0,0,0) for fields 'p' and 'U'.
    """
    names = ['X', 'Y', 'Z']
    normals = ['x', 'y', 'z']
    fields = ['p', 'U']
    
    for name, normal in zip(names, normals):
        try:
            slice_mesh = mesh.slice(normal=normal, origin=(0, 0, 0))
            if slice_mesh.n_points == 0:
                continue
                
            for field in fields:
                if field not in slice_mesh.array_names:
                    continue
                    
                p = pv.Plotter(off_screen=True)
                field_clim = clim.get(field) if clim else None
                p.add_mesh(slice_mesh, scalars=field, cmap='jet', clim=field_clim)
                
                # カメラ位置の調整
                if normal == 'x': p.view_yz()
                elif normal == 'y': p.view_xz()
                else: p.view_xy()
                
                p.add_axes()
                p.add_title(f"{field} Distribution on {name}=0 Plane (Step {step})", font_size=12)
                
                out_path = os.path.join(out_dir, f"{field}_slice_{name}_step{step}.png")
                p.screenshot(out_path)
                p.close()
                print(f"Saved: {out_path}")
        except Exception:
            pass

def create_animation(steps, out_dir, clim=None):
    """
    Creates GIF animations for 'p' and 'U' on X=0, Y=0, Z=0 planes across all steps.
    """
    names = ['X', 'Y', 'Z']
    normals = ['x', 'y', 'z']
    fields = ['p', 'U']
    
    for name, normal in zip(names, normals):
        for field in fields:
            gif_path = os.path.join(out_dir, f"{field}_animation_{name}.gif")
            print(f"Generating animation: {gif_path} ...")
            
            p = pv.Plotter(off_screen=True)
            p.open_gif(gif_path)
            
            for step, filepath in steps:
                try:
                    mesh = pv.read(filepath)
                    slice_mesh = mesh.slice(normal=normal, origin=(0, 0, 0))
                    
                    if slice_mesh.n_points == 0 or field not in slice_mesh.array_names:
                        continue
                    
                    p.clear()
                    field_clim = clim.get(field) if clim else None
                    p.add_mesh(slice_mesh, scalars=field, cmap='jet', clim=field_clim)
                    
                    if normal == 'x': p.view_yz()
                    elif normal == 'y': p.view_xz()
                    else: p.view_xy()
                    
                    p.add_axes()
                    p.add_title(f"{field} Distribution on {name}=0 Plane (Step {step})", font_size=12)
                    p.write_frame()
                except Exception:
                    pass
            
            p.close()
            print(f"Saved animation: {gif_path}")

def create_sweeping_animation(mesh, step, out_dir, num_frames=30, clim=None):
    """
    Creates sweeping animations along X, Y, Z axes for 'p' and 'U' at a specific step.
    """
    names = ['X', 'Y', 'Z']
    normals = ['x', 'y', 'z']
    fields = ['p', 'U']
    
    bounds = mesh.bounds # (xmin, xmax, ymin, ymax, zmin, zmax)
    x_range = np.linspace(bounds[0], bounds[1], num_frames)
    y_range = np.linspace(bounds[2], bounds[3], num_frames)
    z_range = np.linspace(bounds[4], bounds[5], num_frames)
    ranges = [x_range, y_range, z_range]
    
    for name, normal, sweep_range in zip(names, normals, ranges):
        for field in fields:
            gif_path = os.path.join(out_dir, f"{field}_sweep_{name}_step{step}.gif")
            print(f"Generating sweep animation: {gif_path} ...")
            
            p = pv.Plotter(off_screen=True)
            p.open_gif(gif_path)
            
            for val in sweep_range:
                try:
                    origin = [0, 0, 0]
                    if normal == 'x': origin[0] = val
                    elif normal == 'y': origin[1] = val
                    else: origin[2] = val
                    
                    slice_mesh = mesh.slice(normal=normal, origin=origin)
                    
                    if slice_mesh.n_points == 0 or field not in slice_mesh.array_names:
                        continue
                    
                    p.clear()
                    field_clim = clim.get(field) if clim else None
                    p.add_mesh(slice_mesh, scalars=field, cmap='jet', clim=field_clim)
                    
                    if normal == 'x': p.view_yz()
                    elif normal == 'y': p.view_xz()
                    else: p.view_xy()
                    
                    p.add_axes()
                    p.add_title(f"{field} Sweep along {name}-axis (Step {step})", font_size=12)
                    p.write_frame()
                except Exception as e:
                    pass
            
            p.close()
            print(f"Saved sweeping animation: {gif_path}")

def main():
    try:
        pv.start_xvfb()
    except Exception:
        pass
        
    steps = get_vtk_steps()
    if not steps:
        print("No VTK files found. Ensure CFD analysis completed and 'VTK' folder exists.")
        return
        
    out_dir = "visualization_output"
    os.makedirs(out_dir, exist_ok=True)
    
    max_step, max_filepath = steps[-1]
    target_half = max_step // 2
    
    # 色のスケールを最終ステップに固定するための範囲を取得
    print("Calculating global color scales from the final step...")
    try:
        mesh_max = pv.read(max_filepath)
        global_clim = get_global_clim(mesh_max)
        print(f"Color scales fixed: {global_clim}")
    except Exception as e:
        print(f"Warning: could not compute global color bounds: {e}")
        global_clim = None
    
    # 計算の半分のステップに最も近いデータを探す
    closest = min(steps, key=lambda x: abs(x[0] - target_half))
    half_step, half_filepath = closest
    
    print(f"--- 1. Generating Static Images and Sweeps for Half-way Step ({half_step}) ---")
    try:
        mesh_half = pv.read(half_filepath)
        generate_static_slices(mesh_half, half_step, out_dir, clim=global_clim)
        create_sweeping_animation(mesh_half, half_step, out_dir, clim=global_clim)
    except Exception as e:
        print(f"Failed to read or process half-way step VTK: {e}")
        
    print(f"\n--- 2. Generating Time-series Animations (up to Step {max_step}) ---")
    create_animation(steps, out_dir, clim=global_clim)
    
    print(f"\nAll visualizations have been successfully generated in the '{out_dir}' directory!")

if __name__ == "__main__":
    main()
