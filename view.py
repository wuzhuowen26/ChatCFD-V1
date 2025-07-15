# THIS SCRIPT IS INTENDED TO BE RUN WITH pvpython, NOT REGULAR PYTHON.
# Example: pvpython visualize_openfoam_paraview.py /path/to/your/case /path/to/output_image.png latest

import sys
from pathlib import Path

# Import ParaView modules
from paraview.simple import *


def visualize_openfoam_velocity_paraview(case_path_str: str, output_image_path_str: str, time_step: str = "latest"):
    """
    使用 ParaView (pvpython) 自动可视化 OpenFOAM 案例的速度 U 场并保存为图片。

    Args:
        case_path_str (str): OpenFOAM 案例的路径字符串 (例如 "/path/to/your/case/myCylinderFlow").
        output_image_path_str (str): 输出图片文件的完整路径字符串 (例如 "./velocity_magnitude.png").
        time_step (str): 要可视化的时间步。可以是 "latest" (默认) 或具体的数字时间步字符串 (例如 "1000")。
                         ParaView 会自动处理时间步，通常无需显式指定。
    """
    case_path = Path(case_path_str)
    output_image_path = Path(output_image_path_str)

    if not case_path.is_dir():
        print(f"错误: 案例路径 '{case_path}' 不存在或不是一个目录。")
        sys.exit(1)

    print(f"正在处理案例: {case_path}")
    print(f"目标输出图片: {output_image_path}")

    # 1. 打开 OpenFOAM 案例
    # ParaView 可以直接读取 OpenFOAM 案例，不需要 foamToVTK
    # 根据 OpenFOAM 案例的路径创建一个阅读器。
    # 对于较新的 OpenFOAM 版本（>v1906），可以使用 OpenFOAMReader
    # 对于旧版本或特定设置，可能需要 OpenFOAMReaderV2。通常 OpenFOAMReader 即可。
    reader = OpenFOAMReader(FileName=str(case_path))

    # 获取所有时间步并选择最新或指定的时间步
    # 如果 time_step="latest"，ParaViewReader 会自动加载最新时间
    # 如果需要指定时间，可以在这里选择
    # reader.UpdatePipeline() # 确保读取器更新
    # available_times = reader.TimestepValues
    # if time_step != "latest" and time_step in [str(t) for t in available_times]:
    #     view.ViewTime = float(time_step)

    # 2. 创建渲染视图
    renderView1 = CreateRenderView()
    renderView1.ViewSize = [1280, 720]  # 设置图像分辨率
    renderView1.CameraPosition = [0, 0, 10]  # 初始相机位置，Z轴向前看
    renderView1.CameraFocalPoint = [0, 0, 0]  # 焦点
    renderView1.CameraViewUp = [0, 1, 0]  # 向上方向

    # 3. 显示数据
    # 将 reader 的数据关联到渲染视图
    display = Show(reader, renderView1)

    # 4. 计算速度大小 (如果需要)
    # 假设 'U' 是速度向量场 (Ux, Uy, Uz)
    # 使用 'Calculator' 过滤器计算速度大小
    # 如果 U 是标量，则不需要此步骤，直接显示 U

    # ParaView的Calculator过滤器中，'mag(U)' 直接计算向量 U 的大小
    calculator = Calculator(Input=reader)
    calculator.ResultArrayName = 'VelocityMagnitude'  # 新数组的名称
    calculator.Function = 'mag(U)'  # 计算 U 的大小

    # 移除原始显示，显示计算器结果
    Hide(reader, renderView1)  # 隐藏原始数据
    display_calc = Show(calculator, renderView1)  # 显示计算器输出

    # 5. 设置颜色映射和标量条
    # 设置标量映射的范围和颜色图
    # 根据实际数据调整范围，这里使用自动范围
    display_calc.ColorArrayName = ['POINTS', 'VelocityMagnitude']
    display_calc.LookupTable = Get
    display_calc.LookupTable = GetColorTransferFunction('VelocityMagnitude')
    display_calc.RescaleTransferFunctionToDataRange(True, False)  # 自动调整颜色映射范围

    # 确保标量条可见
    display_calc.SetScalarBarVisibility(renderView1, True)
    scalarBar = GetScalarBar(display_calc, renderView1)
    scalarBar.Title = 'Velocity Magnitude'
    scalarBar.ComponentTitle = ''  # 清空分量标题

    # 6. 设置相机视图 (2D 案例常见)
    # 对于 2D 案例，通常在 XY 平面。ParaView 默认视图可能需要调整
    renderView1.CameraViewUp = [0.0, 1.0, 0.0]
    renderView1.CameraPosition = [0.0, 0.0, 10.0]  # 从Z轴正方向看
    renderView1.CameraFocalPoint = [0.0, 0.0, 0.0]  # 焦点在原点
    renderView1.ResetCamera()  # 重置相机以适应数据

    # 7. 保存图片
    output_image_path.parent.mkdir(parents=True, exist_ok=True)  # 确保输出目录存在
    SaveScreenshot(str(output_image_path), renderView1, ImageResolution=[1280, 720])

    print(f"图片已成功保存到: {output_image_path}")

    # 清理 ParaView 状态，避免在连续脚本运行时出现问题
    Delete(renderView1)
    del renderView1
    Delete(reader)
    del reader
    Delete(calculator)
    del calculator


if __name__ == "__main__":
    # --- 示例用法 ---
    # 请根据你的实际情况修改以下路径！

    # OpenFOAM 案例的根路径
    openfoam_case_root = Path("/personal/naca0012_case")  # <--- 修改为你的案例路径

    # 输出图片的路径
    output_image_dir = Path("./visualization_output")
    output_image_dir.mkdir(exist_ok=True)
    output_image_file = output_image_dir / "velocity_magnitude_paraview.png"  # <--- 输出图片文件名

    # 直接调用可视化函数
    visualize_openfoam_velocity_paraview(str(openfoam_case_root), str(output_image_file), time_step="latest")

    print("\n可视化脚本运行完毕。")
    print(f"请检查 '{output_image_file}' 以查看结果。")