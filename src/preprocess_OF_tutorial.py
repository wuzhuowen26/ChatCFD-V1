import os
import json
import requests
import config
import re

# sub-folders in the OpenFOAM tutorial
solver_features = ['basic', 'compressible', 'heatTransfer', 'lagrangian',
                  'multiphase', 'DNS', 'combustion', 'incompressible', 'combustion']

# 指定要收集的子目录
target_subdirs = {'0', '0.orig', 'system', 'constant'}

# 用于存储结果的字典
cases_dict_collection = {}

# LLM调用

# 删除配置文件过长的算例
def describe_cases(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as infile:
        data = json.load(infile)
        
    # 定义一个递归函数来遍历嵌套的字典结构
    def recursive_process(data):
        if isinstance(data, dict):
            for key, value in data.items():
                # 检查是否存在 'case_path' 和 'configuration_files'
                if 'case_path' in value and 'configuration_files' in value:
                    case_path = value['case_path']
                    # 将 'configuration_files' 字典转换为字符串
                    config_str = json.dumps(value['configuration_files'], ensure_ascii=False)

                    # print("Processing case = ",case_path)
                    
                    # 不处理过长的算例
                    if(len(config_str) > 2e5):
                        # print(f"Removing {case_path} since its too long. len(config_str) = {len(config_str)}")
                        continue
                    
                    # 将处理后的数据追加写入输出文件
                    with open(output_file, 'a', encoding='utf-8') as outfile:
                        json.dump({key: value}, outfile, ensure_ascii=False, indent=4)
                        outfile.write('\n')
                else:
                    # 递归处理嵌套的部分
                    recursive_process(value)
        elif isinstance(data, list):
            for item in data:
                recursive_process(item)

    recursive_process(data)


# 从openfoam/tutorial目录下收集算例描述文件
def case_config_collector():
    for feature in solver_features:
        feature_dir = os.path.join(config.of_tutorial_dir, feature)
        if not os.path.isdir(feature_dir):
            continue  # 如果特性目录不存在，跳过
        for solver in os.listdir(feature_dir):
            solver_dir = os.path.join(feature_dir, solver)
            if os.path.isdir(solver_dir) and solver.endswith('Foam'):
                for root_path, dirs, files in os.walk(solver_dir):
                    if 'system' in dirs:
                        system_dir = os.path.join(root_path, 'system')
                        required_files = {'controlDict', 'fvSchemes', 'fvSolution'}
                        if os.path.isdir(system_dir):
                            system_files = set(os.listdir(system_dir))
                            if required_files.issubset(system_files):
                                # 获取算例的相对路径
                                case_relative_path = os.path.relpath(root_path, config.of_tutorial_dir)
                                # 初始化存储结构
                                cases_dict_collection.setdefault(feature, {}).setdefault(solver, {})[case_relative_path] = {
                                    'case_path': case_relative_path,
                                    'configuration_files': {}
                                }
                                # 收集指定子目录中的配置文件及其内容
                                config_files = {}
                                for subdir in target_subdirs:
                                    subdir_path = os.path.join(root_path, subdir)
                                    if os.path.isdir(subdir_path):
                                        for dirpath, dirnames, filenames in os.walk(subdir_path):
                                            # 如果当前目录是constant，则需要跳过polyMesh子目录
                                            if os.path.basename(subdir_path) == 'constant':
                                                if 'polyMesh' in dirnames:
                                                    dirnames.remove('polyMesh')  # 从dirnames中移除'constant/polyMesh'，使os.walk不遍历它
                                            if os.path.basename(subdir_path) == '0':
                                                if 'include' in dirnames:
                                                    dirnames.remove('include')  # 从dirnames中移除'0/include'，使os.walk不遍历它 
                                            for filename in filenames:
                                                if "blockMeshDict" in filename:
                                                    continue
                                                if "changeDictionaryDict" in filename:
                                                    continue
                                                file_full_path = os.path.join(dirpath, filename)
                                                # 获取文件相对于算例目录的路径
                                                file_relative_path = os.path.relpath(file_full_path, root_path)
                                                # 读取文件内容
                                                try:
                                                    with open(file_full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                                        # 读取文件并去除开头的无用信息
                                                        lines = f.readlines()
                                                        content_started = False
                                                        processed_lines = []
                                                        for line in lines:
                                                            if not content_started and 'FoamFile' in line:
                                                                content_started = True
                                                            if content_started:
                                                                processed_lines.append(line)
                                                        # 将处理后的内容合并为字符串
                                                        file_content = ''.join(processed_lines)
                                                except Exception as e:
                                                    print(f"无法读取文件 {file_full_path}，错误：{e}")
                                                    file_content = ""
                                                # 将文件路径和内容添加到配置文件字典
                                                config_files[file_relative_path] = file_content
                                # 更新配置文件列表
                                cases_dict_collection[feature][solver][case_relative_path]['configuration_files'] = config_files

def merge_json_objects(file_path, output_path):
    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # 分割多个JSON对象
    json_strings = content.split('}\n{')
    
    # 创建合并后的字典
    merged_dict = {}
    
    for i, json_str in enumerate(json_strings):
        # 为分割的部分补充缺失的括号
        if i > 0:
            json_str = '{' + json_str
        if i < len(json_strings) - 1:
            json_str = json_str + '}'
            
        try:
            # 解析JSON
            data = json.loads(json_str)
            # 合并到主字典中
            merged_dict.update(data)
        except json.JSONDecodeError as e:
            print(f"解析第 {i+1} 个JSON对象时出错: {str(e)}")
    
    # 将合并后的数据写入新文件
    with open(output_path, 'w', encoding='utf-8') as file:
        json.dump(merged_dict, file, indent=4)
    
    return merged_dict

multiphase_flow_solvers = [
    "cavitatingFoam","compressibleInterFoam","compressibleMultiphaseInterFoam",
    "driftFluxFoam","icoReactingMultiphaseInterFoam","interCondensatingEvaporatingFoam",
    "interFoam","interIsoFoam","interPhaseChangeFoam","multiphaseEulerFoam",
    "multiphaseInterFoam","potentialFreeSurfaceFoam","twoLiquidMixingFoam",
    "chtMultiRegionFoam","reactingMultiphaseEulerFoam","reactingTwoPhaseEulerFoam","twoPhaseEulerFoam"
]

particle_flow_solvers = [
    "denseParticleFoam","particleFoam","reactingParcelFoam",
    "DPMFoam","MPPICFoam","icoUncoupledKinematicParcelDyMFoam",
    "kinematicParcelFoam","sprayFoam","MPPICDyMFoam",
    "coalChemistryFoam","icoUncoupledKinematicParcelFoam",
    "reactingHeterogenousParcelFoam","simpleReactingParcelFoam",
    "uncoupledKinematicParcelDyMFoam"
]

reacting_flow_solvers = [
    "buoyantReactingFoam","chemFoam","coldEngineFoam",
    "reactingFoam","fireFoam","PDRFoam","XiFoam",
    "XiEngineFoam", "rhoReactingFoam"
]

solver_set = set()
turbulence_type_set = set()
turbulence_model_set = set()
boundary_type_set = set()

def extract_turbulence_model(file_content):
    content = file_content.split('\n')
    model = None
    for line in content:
        if 'model' in line.lower():
            model = line.split()[-1].strip(';')
            break  # Exit loop once we've found the model
    return model

def add_case_path_keys(data):
    for case_data in data.values():
        config_files = case_data["configuration_files"]

        # print(f"updating case: {case_data['case_path']}")

        # Step 1: Process 0.orig/* keys and rename to 0/*
        keys_to_modify = []
        for key in list(config_files.keys()):
            if key.startswith("0.orig/"):
                new_key = key.replace("0.orig/", "0/", 1)
                # Remove .orig suffix in filename if present
                parts = new_key.split('/')
                if len(parts) > 1 and parts[-1].endswith('.orig'):
                    parts[-1] = parts[-1][:-5]  # Remove .orig extension
                    new_key = '/'.join(parts)
                keys_to_modify.append((key, new_key))
        
        # Perform key replacement
        for old_key, new_key in keys_to_modify:
            if old_key in config_files:
                config_files[new_key] = config_files.pop(old_key)
        
        # Step 2: Collect all 0/* keys for required_field
        required_fields = [k for k in config_files if k.startswith("0/")]
        case_data["required_field"] = required_fields
        
        # 提取solver（application）
        control_dict = config_files.get("system/controlDict", "")
        solver_match = re.search(r"application\s+(\w+);", control_dict)
        solver = solver_match.group(1) if solver_match else None
        case_data["solver"] = solver

        solver_set.add(solver)
        
        # 判别singlePhase
        case_data["singlePhase"] = True
        if solver in multiphase_flow_solvers:
            case_data["singlePhase"] = False
        
        # 判别particle flow
        case_data["particle_flow"] = False
        if case_data["particle_flow"] == False:
            if solver in particle_flow_solvers:
                case_data["particle_flow"] = True
            if any('Cloud' in s for s in list(config_files.keys())):
                case_data["particle_flow"] = True

        # 判别reacting flow
        case_data["reacting_flow"] = False
        if case_data["reacting_flow"] == False:
            if solver in reacting_flow_solvers:
                case_data["reacting_flow"] = True
            if "constant/combustionProperties" in list(config_files.keys()):
                case_data["reacting_flow"] = True
            if "constant/reactions" in list(config_files.keys()):
                case_data["reacting_flow"] = True

        # 提取 turbulence_type (RAS, LES, laminar ...)
        # 提取 turbulence_model (kEpsilon ...)

        turbulence_type = None
        turbulence_model = None
        for file_path in config_files:
            parts = file_path.split("/")
            if len(parts) > 1 and parts[0] == "constant" and parts[-1] == "turbulenceProperties":
                content = config_files[file_path]
                type_match = re.search(r"simulationType\s+(\w+);", content)
                if type_match:
                    turbulence_type = type_match.group(1)
                    if turbulence_type == "LES":
                        type_match = re.search(r"LESModel\s+(\w+);", content)
                        if type_match:
                            turbulence_model = type_match.group(1)
                    elif turbulence_type == "RAS":
                        type_match = re.search(r"RASModel\s+(\w+);", content)
                        if type_match:
                            turbulence_model = type_match.group(1)
                    elif turbulence_type == "laminar":
                        turbulence_model = None
                    break

        case_data["turbulence_type"] = turbulence_type
        case_data["turbulence_model"] = turbulence_model
        


        turbulence_type_set.add(turbulence_type)
        turbulence_model_set.add(turbulence_model)

        # 提取算例中的边条类型
        case_boundary_type_set = set()
        for file_path in config_files:
            parts = file_path.split("/")
            if len(parts) > 1 and (parts[0] == "0" or parts[0] == "0.org"):
                content = config_files[file_path]

                # 第一步：匹配 boundaryField 后的 {} 块内容
                boundary_field_pattern = re.compile(
                    r'boundaryField\s*{((?:[^{}]*{[^{}]*}[^{}]*)*)}', 
                    re.DOTALL
                )
                boundary_match = boundary_field_pattern.search(content)
                if boundary_match:
                    boundary_content = boundary_match.group(1)
                    
                    # 第二步：匹配所有 type 后的值
                    type_pattern = re.compile(r'type\s+([^;]+);', re.DOTALL)
                    type_matches = type_pattern.findall(boundary_content)

                    if type_matches:
                        # 去除前后空格并输出结果
                        type_values = [m.strip() for m in type_matches]
                        case_boundary_type_set.update(type_values)

        case_data["boundary_type"] = list(case_boundary_type_set)
        boundary_type_set.update(case_boundary_type_set)

    return data


def main():

    # 收集所有tutorial下的算例文件到一个json文件中
    case_config_collector()
    all_case_collector = f'{config.Database_OFv24_PATH}/openfoam_cases.json'
    with open(all_case_collector, 'w', encoding='utf-8') as f:
        json.dump(cases_dict_collection, f, indent=4, ensure_ascii=False)

    discrete_tmp_json = f'{config.Database_OFv24_PATH}/discrete_case_config_with_descriptions.json'

    describe_cases(all_case_collector, output_file=discrete_tmp_json)

    output_file = f'{config.Database_OFv24_PATH}/merged_OF_cases.json'

    merge_json_objects(discrete_tmp_json, output_file)

    # os.remove(all_case_collector)
    # os.remove(discrete_tmp_json)

    # 读取输入JSON
    with open(output_file, "r") as f:
        data = json.load(f)
        print("Total case number = ", len(data))

    # 处理数据
    updated_data = add_case_path_keys(data)

    new_solver_set = {item for item in solver_set if item is not None}
    new_turbulence_type_set = {item for item in turbulence_type_set if item is not None}
    new_turbulence_model_set = {item for item in turbulence_model_set if item is not None}
    new_boundary_type_set = {item for item in boundary_type_set if item is not None}

    config.global_OF_keywords = {
        "solver": list(new_solver_set),
        "turbulence_type": list(new_turbulence_type_set),
        "turbulence_model": list(new_turbulence_model_set),
        "boundary_type": list(new_boundary_type_set)
    }

    ofv24_keywords_file = f'{config.Database_OFv24_PATH}/ofv24_keywords.json'

    with open(ofv24_keywords_file, 'w', encoding='utf-8') as file:
        json.dump(config.global_OF_keywords, file, indent=4)

    processed_merged_OF_cases = f'{config.Database_OFv24_PATH}/processed_merged_OF_cases.json'

    # 输出结果
    with open(processed_merged_OF_cases, "w") as f:
        json.dump(updated_data, f, indent=4)

    config.global_OF_cases = updated_data
    config.flag_tutorial_preprocessed = True

def read_in_processed_merged_OF_cases():
    # 若不运行preprocess，则从之前运行的processed_merged_OF_cases.json中读取算例数据到config.global_OF_cases
    proprocess_case_json_file = f"{config.Database_OFv24_PATH}/processed_merged_OF_cases.json"
    with open(proprocess_case_json_file, 'r', encoding='utf-8') as file:
        # 将JSON文件内容读取到一个字典中
        config.global_OF_cases = json.load(file)
    # 更新config.global_OF_keywords
    solver_set = set()
    turbulence_type_set = set()
    turbulence_model_set = set()
    boundary_type_set = set()

    for key,value in config.global_OF_cases.items():
        solver_set.add(value["solver"])
        turbulence_type_set.add(value["turbulence_type"])
        turbulence_model_set.add(value["turbulence_model"])
        boundary_type_set.update(value["boundary_type"])

    new_solver_set = {item for item in solver_set if item is not None}
    new_turbulence_type_set = {item for item in turbulence_type_set if item is not None}
    new_turbulence_model_set = {item for item in turbulence_model_set if item is not None}
    new_boundary_type_set = {item for item in boundary_type_set if item is not None}

    config.global_OF_keywords = {
        "solver": list(new_solver_set),
        "turbulence_type": list(new_turbulence_type_set),
        "turbulence_model": list(new_turbulence_model_set),
        "boundary_type": list(new_boundary_type_set)
    }

    a = 1