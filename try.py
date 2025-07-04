import json
from src import config


def case_required_file(solver_, turbulence_model_):
    # 1. solver name and turbulence model
    config.case_solver = solver_
    config.case_turbulece_model = turbulence_model_

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

    config.global_files = list(result_set)

    if solver_ == "reactingFoam" and config.other_physical_model:
        if "GRI" in config.other_physical_model:
            config.global_files.append("constant/thermo.compressibleGasGRI")
            config.global_files.append("constant/reactionsGRI")

    compressible_solvers = ["acousticFoam", "overRhoPimpleDyMFoam", "overRhoSimpleFoam", "rhoCentralFoam", "rhoPimpleAdiabaticFoam", "rhoPimpleFoam", "rhoPorousSimpleFoam", "rhoSimpleFoam", "sonicDyMFoam", "sonicFoam", "sonicLiquidFoam"]

    if config.case_solver in compressible_solvers:
        if config.case_turbulece_model in ["SpalartAllmaras","kOmegaSST","LaunderSharmaKE","realizableKE","kOmegaSSTLM","kEpsilon","RNGkEpsilon", "SpalartAllmarasDDES", "SpalartAllmarasIDDES"]:
            config.global_files.append("0/alphat")

    # 根据solver寻找参考文件，并且根据仿真需求，添加case所需要的文件
    prompt = """
    
    """
    return config.global_files



if __name__ == "__main__":

    solver = "reactingFoam"
    turbulence_model = ""
    file_tree = case_required_file(solver, turbulence_model)

    print(file_tree)