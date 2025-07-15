import os
import subprocess
import sys
import re
from pathlib import Path

# 确保在脚本开始时就导入这些库，因为它们是核心
try:
    import pyvista as pv
    import numpy as np
except ImportError:
    print("错误: 缺少必要的Python库。请运行 'pip install pyvista numpy'")
    sys.exit(1)

def visualize_openfoam_velocity(case_path: Path, output_image_path: Path, time_step: str = "latest"):
    """
    自动调用 OpenFOAM 的 foamToVTK 工具，并将指定 OpenFOAM 案例的速度 U 场可视化为图片。

    Args:
        case_path (Path): OpenFOAM 案例的路径 (例如 Path("/path/to/your/case/myCylinderFlow")).
        output_image_path (Path): 输出图片文件的完整路径 (例如 Path("./velocity_magnitude.png")).
        time_step (str): 要可视化的时间步。可以是 "latest" (默认) 或具体的数字时间步字符串 (例如 "1000")。
                         如果指定 "latest"，脚本会尝试找到最新的时间步。
    """
    if not case_path.is_dir():
        print(f"错误: 案例路径 '{case_path}' 不存在或不是一个目录。")
        sys.exit(1)

    print(f"正在处理案例: {case_path}")
    print(f"目标输出图片: {output_image_path}")

    # 1. 运行 foamToVTK 将 OpenFOAM 结果转换为 VTK 格式
    print("正在运行 foamToVTK...")
    try:
        # 构建 foamToVTK 命令
        command = ["foamToVTK"]
        if time_step == "latest":
            command.append("-latestTime")
        else:
            command.extend(["-time", time_step])
        
        # 捕获输出和错误，以便调试
        result = subprocess.run(command, cwd=case_path, capture_output=True, text=True, check=True)
        print("foamToVTK 输出:")
        print(result.stdout)
        if result.stderr:
            print("foamToVTK 错误输出:")
            print(result.stderr)

    except subprocess.CalledProcessError as e:
        print(f"错误: foamToVTK 运行失败。请确保 OpenFOAM 环境已正确配置且案例路径正确。")
        print(f"命令: {' '.join(e.cmd)}")
        print(f"返回码: {e.returncode}")
        print(f"标准输出:\n{e.stdout}")
        print(f"标准错误:\n{e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print("错误: 'foamToVTK' 命令未找到。请确保 OpenFOAM 环境已正确源化 (sourced)。")
        sys.exit(1)

    # 2. 确定 VTK 文件的路径
    vtk_output_dir = case_path / "VTK"
    case_name = case_path.name

    target_vtk_file = None
    if time_step == "latest":
        # 寻找所有可能的 .vtm 文件，按时间步排序
        vtm_files_found = []
        for f in vtk_output_dir.iterdir():
            if f.is_file() and f.suffix == '.vtm':
                match_case_time_vtm = re.match(rf"^{re.escape(case_name)}_(\d+\.?\d*)\.vtm$", f.name)
                if match_case_time_vtm:
                    vtm_files_found.append((float(match_case_time_vtm.group(1)), f))
        
        if vtm_files_found:
            vtm_files_found.sort(key=lambda x: x[0], reverse=True) # 找到最新时间的 .vtm
            target_vtk_file = vtm_files_found[0][1]
            print(f"已找到最新的 VTK 文件: {target_vtk_file.name}")
        else:
            # 如果没有找到 <case_name>_<time_value>.vtm，尝试 <case_name>.vtm.series
            series_file = vtk_output_dir / f"{case_name}.vtm.series"
            if series_file.is_file():
                target_vtk_file = series_file
                print(f"已找到 VTK 系列文件: {target_vtk_file.name}")
            else:
                print(f"错误: 在 '{vtk_output_dir}' 中未找到任何 VTK 文件 (.vtm 或 .vtm.series)。")
                sys.exit(1)
    else:
        # 如果指定了具体时间步，直接构建文件名 <case_name>_<time_step>.vtm
        target_vtk_file = vtk_output_dir / f"{case_name}_{time_step}.vtm"
        if not target_vtk_file.is_file():
            print(f"错误: 指定时间步 '{time_step}' 的 VTK 文件 '{target_vtk_file}' 不存在。")
            sys.exit(1)

    print(f"正在加载 VTK 文件: {target_vtk_file}")

    # 3. 使用 PyVista 加载数据
    try:
        full_data_set = pv.read(target_vtk_file)
    except Exception as e:
        print(f"错误: 使用 PyVista 读取 VTK 文件失败: {e}")
        print("请确保 PyVista 版本兼容，并且 VTK 文件未损坏。")
        sys.exit(1)

    # 从 MultiBlock 数据集中获取实际的网格数据
    mesh = None
    if isinstance(full_data_set, pv.MultiBlock):
        for block in full_data_set:
            if 'internal' in str(block).lower() or block.n_points > 0:
                mesh = block
                break
        if mesh is None:
            print("错误: 在 MultiBlock 数据集中未找到有效的内部网格数据。")
            sys.exit(1)
    elif isinstance(full_data_set, pv.DataSet):
        mesh = full_data_set
    else:
        print(f"错误: PyVista 加载了未知类型的数据集: {type(full_data_set)}")
        sys.exit(1)

    # 4. 提取速度 U 场并计算速度大小
    if "U" not in mesh.point_data:
        print(f"错误: 在 VTK 数据中未找到 'U' 场。请确保 foamToVTK 导出了速度 U。")
        print(f"可用数据场: {list(mesh.point_data.keys())}")
        sys.exit(1)

    velocity_u = mesh.point_data["U"]
    velocity_magnitude = np.linalg.norm(velocity_u, axis=1)
    mesh["VelocityMagnitude"] = velocity_magnitude

    print("已计算速度大小。")

    # 5. 可视化并保存图片
    print("正在生成可视化图片...")
    
    # 确保 off_screen=True 在服务器环境
    plotter = pv.Plotter(off_screen=True)
    
    # 标量条参数，去掉了 font_size，因为它可能在某些 PyVista 版本不支持
    plotter.add_mesh(mesh, scalars="VelocityMagnitude", cmap="viridis", show_scalar_bar=True,
                     scalar_bar_args={'title': 'Velocity Magnitude'})
    
    plotter.view_xy() # 适用于2D或对称轴在XY平面的3D案例
    plotter.camera.zoom(1.2) # 稍微放大视图

    output_image_path.parent.mkdir(parents=True, exist_ok=True) # 确保输出目录存在
    plotter.screenshot(output_image_path, transparent_background=False, scale=2) # scale=2 可提高图片质量
    print(f"图片已成功保存到: {output_image_path}")

    plotter.close()

if __name__ == "__main__":
    # --- 示例用法 ---
    # 建议将 OpenFOAM 案例路径和输出图片路径作为命令行参数传递
    # 示例运行: python3 visualize_foam.py /personal/naca0012_case ./output_images/velocity_plot.png latest

    if len(sys.argv) < 3:
        print("用法: python3 visualize_foam.py <OpenFOAM案例路径> <输出图片路径> [时间步(latest/数字)]")
        print("例如: python3 visualize_foam.py /personal/naca0012_case ./output_images/velocity_plot.png latest")
        sys.exit(1)

    openfoam_case_root = Path(sys.argv[1])
    output_image_file = Path(sys.argv[2])
    time_step = sys.argv[3] if len(sys.argv) > 3 else "latest"

    visualize_openfoam_velocity(openfoam_case_root, output_image_file, time_step)

    print("\n可视化脚本运行完毕。")
    print(f"请检查 '{output_image_file}' 以查看结果。")
