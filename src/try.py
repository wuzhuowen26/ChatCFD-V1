import json
import ast

import config
from qa_modules import QA_NoContext_deepseek_R1,QA_NoContext_deepseek_V3

import sys
sys.path.append('..') # 添加上级目录到系统路径
from utils.use_api import use_api # 导入上级目录中的模块

def load_OF_data_json():
    try:
        with open(config.OF_data_path, 'r', encoding='utf-8') as file:
            config.OF_case_data_dict = json.load(file)  # 直接转换为Python列表
            print("Success reading in the OF_tut_case_json file！")
    except json.JSONDecodeError:
        print("输入JSON格式错误，请检查数据完整性")
        exit()

def case_required_file(solver_, turbulence_model_):
    # 加载OpenFOAM的求解器、湍流模型等
    config.case_solver = solver_
    config.case_turbulece_model = turbulence_model_
    other_physical_model = config.other_physical_model
    other_model_list = [
        "GRI", "TDAC", "LTS","common","Maxwell","Stokes"
    ]
    if other_physical_model not in other_model_list:
        other_physical_model = None

    if config.case_turbulece_model in ["SpalartAllmarasDDES", "SpalartAllmarasIDDES"]:
        config.case_turbulence_type = "LES"
    elif config.case_turbulece_model in ["SpalartAllmaras","kOmegaSST","LaunderSharmaKE","realizableKE","kOmegaSSTLM","kEpsilon","RNGkEpsilon"]:
        config.case_turbulence_type = "RAS"
    else:
        config.case_turbulence_type = "laminar"

    # the case files required by solver and turbulence models
    OF_solver_requirements = []
    try:
        file_requirements = f"{config.Database_OFv24_PATH}/final_OF_solver_required_files.json"
        with open(file_requirements, 'r', encoding='utf-8') as file:
            OF_solver_requirements = json.load(file)  # 直接转换为Python列表
    except json.JSONDecodeError:
        print(f"Fail reading {file_requirements}")
        exit()
    
    solver_file_requirement = OF_solver_requirements[solver_]

    turbulence_model_file_requirement = []

    if config.case_turbulence_type != "laminar":
        OF_turbulence_requirements = None

        try:
            file_requirements = f"{config.Database_OFv24_PATH}/final_OF_turbulence_required_files.json"
            with open(file_requirements, 'r', encoding='utf-8') as file:
                OF_turbulence_requirements = json.load(file)  # 直接转换为Python列表
        except json.JSONDecodeError:
            print(f"Fail reading {file_requirements}")
            exit()

        turbulence_model_file_requirement = OF_turbulence_requirements[turbulence_model_]

    result_set = set(solver_file_requirement).union(turbulence_model_file_requirement)

    # config.global_files = list(result_set)

    if solver_ == "reactingFoam" and config.other_physical_model:
        if "GRI" in config.other_physical_model:
            # config.global_files.append("constant/thermo.compressibleGasGRI")
            # config.global_files.append("constant/reactionsGRI")
            result_set.add("constant/thermo.compressibleGasGRI")
            result_set.add("constant/reactionsGRI")

    compressible_solvers = ["acousticFoam", "overRhoPimpleDyMFoam", "overRhoSimpleFoam", "rhoCentralFoam", "rhoPimpleAdiabaticFoam", "rhoPimpleFoam", "rhoPorousSimpleFoam", "rhoSimpleFoam", "sonicDyMFoam", "sonicFoam", "sonicLiquidFoam"]

    if config.case_solver in compressible_solvers:
        if config.case_turbulece_model in ["SpalartAllmaras","kOmegaSST","LaunderSharmaKE","realizableKE","kOmegaSSTLM","kEpsilon","RNGkEpsilon", "SpalartAllmarasDDES", "SpalartAllmarasIDDES"]:
            # config.global_files.append("0/alphat")
            result_set.add("0/alphat")
    
    # config.global_files = list(result_set)

    # 根据solver寻找参考文件，并且根据仿真需求，添加case所需要的文件
    file_alternative = {}
    # file_unnecessary = ["system/decomposeParDict", "system/topoSetDict", "system/surfaceFeatureExtractDict", "system/setSetDict", "system/postProcessDict", "system/sample", "system/sampleDict", "system/singleGraph", "system/snappyHexMeshDict", "system/mapFieldsDict", "system/foamDataToFluentDict"]
    file_necessary = ["system/fvSolution","system/controlDict","system/fvSchemes","system/FOBilgerMixtureFraction"]
    for key,value in config.OF_case_data_dict.items():
        if config.case_solver == value["solver"] and config.case_turbulece_model == value["turbulence_model"]:
            
            if "other_physical_model" in value.keys():
                print(1)
                if not other_physical_model == value["other_physical_model"]:
                    print(2)
                    continue

            file_filtered = []
            for file in value["configuration_files"].keys():
                if file != "":
                    if file.startswith("system/"):
                        if file in file_necessary:
                            file_filtered.append(file)
                    else:
                        file_filtered.append(file)

            # filtered_fields = [field for field in value["configuration_files"].keys() if field and field not in file_unnecessary]
            case_name = key.split("/")[-1]
            file_alternative[case_name] = file_filtered

    if len(file_alternative) == 0:
        for key, value in config.OF_case_data_dict.items():
            if config.case_solver == value["solver"]:
                # filtered_fields = [field for field in value["configuration_files"].keys() if field and field not in file_unnecessary]
                file_filtered = []
                for file in value["configuration_files"].keys():
                    if file != "":
                    if file.startswith("system/"):
                        if file in file_necessary:
                            file_filtered.append(file)
                    else:
                        file_filtered.append(file)
                case_name = key.split("/")[-1]
                file_alternative[case_name] = file_filtered

    simulation_example = """
do a 2-dimensional laminar simulation of incompressible planar Poiseuille flow of a non-Newtonian fluid using pimpleFoam, modelled using the Maxwell viscoelastic laminar stress model, initially at rest, constant pressure gradient applied from time zero. Therefore, the other_physcial_model is set to Maxwell here

The relative pressure internal field at the initial moment is 0.
The velocity of wall at the initial moment is 0.
The stefan-boltzman constant(sigma) is 0

Apply a constant speed of 5m/s in the x-direction of the source term in fvOptions
    """

    add_file_prompt = f"""
    你是一个OpenFOAM专家，以下是仿真需求：{simulation_example}

    可选的参考算例和对应的文件列表如下：
    {file_alternative}

    1. 请你根据仿真需求，分析最符合仿真需求的文件列表，并返回对应参考算例名称。重点关注明确的参数设置要求，例如：如果仿真需求中明确要求了速度的初始条件设置，那么文件列表中必须包含0/U文件
    2. 如果没有合适的文件列表，给出一个最接近的参考算例名称。
    3. 如果每一个文件列表都极其不合适，请你返回“[]”
    4. 请你以仅返回算例名称，不要返回解释、代表块标识等其他内容。
    """
    try:
        # qa = QA_NoContext_deepseek_V3()
        # answer = qa.ask(add_file_prompt)
        answer = use_api(add_file_prompt, "deepseek-v3-250324")
        # answer = ast.literal_eval(answer)
        print(answer)
        print(type(answer))
        # try: 
        #     answer = list

        # prompt_2 = f"""
        #     下面这段话描述了一个openfoam算例所需要的文件结构，请你将其中的文件名提取出来，返回一个python列表。
        #     f{answer}
        #     """
    except Exception as e:
        print(f"Error: {e}")
        answer = result_set

    config.global_files = file_alternative[answer]
    return config.global_files, file_alternative



if __name__ == "__main__":
    load_OF_data_json()
    # print(len(config.OF_case_data_dict))

    solver = "pimpleFoam"
    turbulence_model = None
    config.other_physical_model = "Maxwell"  # 可选值：GRI, TDAC, LTS, Maxwell, Stokes, common
    file_tree,file_alternative = case_required_file(solver, turbulence_model)

    print("file_tree:\n",file_tree)
    print("file_alternative:\n",file_alternative)