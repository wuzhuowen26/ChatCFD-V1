import os
import subprocess
from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile
from PyFoam.Applications.Decomposer import Decomposer
from PyFoam.Applications.Runner import Runner
from PyFoam.Applications.PlotRunner import PlotRunner
from PyFoam.Applications.PrepareCase import PrepareCase

import config

def convert_mesh(case_path, grid_path):
    """将Fluent网格转换为OpenFOAM格式"""
    try:
        command = [
            "fluentMeshToFoam",
            "-case",
            case_path,
            grid_path
        ]
        subprocess.run(command, check=True)
        print("网格转换成功完成")
        config.mesh_convert_success = True
        # 保存最初的boundary文件
        boundary_path = f"{config.OUTPUT_PATH}/constant/polyMesh/boundary"
        with open(boundary_path, "r", encoding="utf-8") as file:
            boundary_content = file.read()
        config.boundary_init = boundary_content

        return True
    except subprocess.CalledProcessError as e:
        print(f"网格转换失败: {e}")
        return False
    except FileNotFoundError:
        print("未找到fluentMeshToFoam命令，请确保OpenFOAM环境已正确加载")
        return False

def setup_cfl_control(case_path, max_co=0.6):
    """设置CFL控制参数"""
    try:
        # 修改controlDict文件
        control_dict_path = f'{case_path}/system/controlDict'
        control_dict = ParsedParameterFile(control_dict_path)

        demo_compressible_solver = ["rhoCentralFoam", "sonicFoam"]

        solver = control_dict["application"]
        if solver in config.steady_solvers:
            control_dict["adjustTimeStep"] = "yes"
            control_dict["maxCo"] = max_co
            control_dict["startTime"] = 0
            control_dict["endTime"] = 10
            control_dict["stopAt"] = "endTime"
            control_dict["writeInterval"] = 5
            control_dict["deltaT"] = 1
        else:
            control_dict["adjustTimeStep"] = "yes"
            control_dict["maxCo"] = max_co
            control_dict["startTime"] = 0
            dt = 1e-8
            if solver in demo_compressible_solver:
                dt = 1e-8
            else:
                dt = 1e-5
            control_dict["deltaT"] = dt
            control_dict["endTime"] = dt*10
            control_dict["stopAt"] = "endTime"
            control_dict["writeInterval"] = 2
            if solver in demo_compressible_solver:
                control_dict["deltaT"] = 1e-8
            else:
                control_dict["deltaT"] = 1e-5
            control_dict["purgeWrite"] = 20    # 只保留最新的10个时间步
            control_dict["minDeltaT"] = 1e-7   # 设置最小时间步长
        
        # 保存修改
        control_dict.writeFile()
        config.set_controlDict_time = True
        print("成功配置CFL控制参数")
        return True
    except Exception as e:
        print(f"修改controlDict失败: {e}")
        return False
    
def setup_cfl_control_2(case_path, max_co=0.6):
    """设置CFL控制参数"""
    try:
        # 修改controlDict文件
        control_dict_path = f'{case_path}/system/controlDict'
        control_dict = ParsedParameterFile(control_dict_path)
        control_dict["adjustTimeStep"] = "yes"
        control_dict["maxCo"] = max_co
        control_dict["startTime"] = 0
        control_dict["endTime"] = 2
        control_dict["stopAt"] = "endTime"
        control_dict["writeInterval"] = 1
        control_dict["deltaT"] = 1
        
        # 保存修改
        control_dict.writeFile()
        print("成功配置CFL控制参数")
        return True
    except Exception as e:
        print(f"修改controlDict失败: {e}")
        return False

def case_run(case_path):
    solver = ""
    try:
        control_dict_path = f'{case_path}/system/controlDict'
        # control_dict = ParsedParameterFile(control_dict_path)
        # solver = control_dict["application"]
        # 打开文件并读取内容
        with open(control_dict_path, 'r') as file:
            content = file.read()

        # 查找 "application" 后的内容
        start_index = content.find('application') + len('application')
        end_index = content.find(';', start_index)

        # 提取字符串并去除空格
        solver = content[start_index:end_index].strip()
    except Exception as e:
        print(f"Fail acquiring the solver: {e}")
        return False

    running_log = f'{case_path}/case_run.log'

    command = f'{solver} -case {case_path} > {running_log}'
    # command = f'ls'
    output = subprocess.run(
        command,
        shell=True,
        executable="/usr/bin/bash",
        text=True,
        capture_output=True  # get stdout and stderr
        )
    
    run_case_error = output.stderr
    run_case_output = output.stdout
    
    if output.returncode != 0: # 判断命令运行是否出错
        print("程序出错了！错误信息:", output.stderr)
        return output.stderr
    else:
        print("程序运行成功，输出:", output.stdout)
        config.flag_case_success_run = True
        return "case run success."

    a = 1

    # output_dir = Path(opts.output_dir.get_path())
