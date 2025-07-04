import config, preprocess_OF_tutorial, case_file_requirements, qa_modules, file_writer, run_of_case,file_corrector, set_config
import PyPDF2, pdfplumber, pdf_chunk_ask_question
import json
import torch
import os

import check_boundary_module

torch.classes.__path__ = [os.path.join(torch.__path__[0], torch.classes.__file__)]

test_solver = None

test_turbulence_model = None

test_case_name = None

test_case_description = None

def process_pdf_pdfplumber(file_path):
    text = ""
    tables = []

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            # 提取文本
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

            # 提取表格
            page_tables = page.extract_tables()
            if page_tables:
                for table in page_tables:
                    tables.append(table)

    return {
        "text": text,
        "tables": tables
    }

def process_pdf_PyPDF2(pdf_file):
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        return f"PDF processing error: {str(e)}"

def pdf_chunk_ask():
    extractor = pdf_chunk_ask_question.CFDCaseExtractor()
    extractor.process_pdf(config.pdf_path)

    initial_files = []
    for i in config.global_files:
        if "0/" in i:
            initial_files.append(i[2:])

    bc_prompt = f'''What are the boundary conditions (B.C.)? The boundary type in the paper might be spelling-incorrect. You must validate the boundary type against the OpenFOAM boundary name list and correct them. You must only correct the spelling and mustn't change boundary type. YOU MUST NOT CHANGE THE BOUNDARY TYPE EXCEPT FOR SPELLING CORRECTION. When boundary names include a slash (e.g., a/b), they must be divided into distinct boundaries ('a' and 'b') and listed separately. The OpenFOAM boundary name list [[[ {config.string_of_boundary_type_keywords} ]]]. You must clearly point out the B.C. for these boundaries [[[ {config.case_boundary_names}]]] and do not include other boundaries. You must consider fields [[[ {initial_files} ]]]. Validate your answer for two times before response. In your response, only show the final result in of the corrected boundary condition and do not show any correction or validation process. The final response must be a json-format string.'''

    bc_response = extractor.query_case_setup(bc_prompt, context = True)

    ic_bc_prompt = f'''I want to simulate the case with these descrpition [[[{test_case_description}]]] in the paper using OpenFOAM-v2406. What are the values of initial and boundary conditions? You must strictly follow this list of boundary conditions {bc_response}, and you must not change any boundary type in the list. The flow condition might be given as non-dimensional parameters such as Re, Ma, or other paramters. Convert these flow parameters to the field values. Validate your answer for two times before response. In your response, only show the final result of the initial and boundary conditions and do not show any correction or validation process. The final response must be a json-format string showing initial and boundary conditions.'''

    ic_bc_response = extractor.query_case_setup(ic_bc_prompt, context = True)

    config.case_ic_bc_from_paper = ic_bc_response

    OF_header = '''/*--------------------------------*- C++ -*----------------------------------*\\\\\\n| =========                 |                                                 |\\n| \\\\\\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |\\n|  \\\\\\\\    /   O peration     | Version:  v2406                                 |\\n|   \\\\\\\\  /    A nd           | Website:  www.openfoam.com                      |\\n|    \\\\\\\\/     M anipulation  |                                                 |\\n\\\\*---------------------------------------------------------------------------*/'''

    Foamfile_string = '''FoamFile
{
    version     2.0;
    format      ascii;
    class       <the_file_class_type>;
    object      <the_file_object_type>;
}
'''

    case_file_prompts = f'''I want to simulate the case with these descrpition [[[{test_case_description}]]] in the paper using OpenFOAM-v2406. I want to use the {config.case_solver} and {config.case_turbulece_model}. Please draft all the cases files [[[ {config.global_files} ]]] necessary to run the case for me. 
    - You must strictly follow these initial and boundary conditions [[[ {ic_bc_response} ]]]. Do not add or miss any boundaries.
    - I have already prepared the grid for this case and you don't need to prepare the blockMeshDict.
    - You must response in the json format with the keys as files name as 0/*, system/*, constant/*, and the value are file contents.
    - You must make sure the system/controlDict is correct especially the application entry is write as [[[ application   {config.case_solver};]]]
    - For each file, avoid generating the heading lines of the OpenFOAM file, such as [[[{OF_header}]]], but do not omit the FoamFile content such as [[[ {Foamfile_string} ]]]. 
    Validate your answer for two times before response.
    - If wavetransmissive boundary presents, you must set the derived parameter of this boundary type lInf = 1. such as [[[type            waveTransmissive; lInf            1;]]]

    In your response: Absolutely AVOID any non-JSON elements including but not limited to:
    - Markdown code block markers (```json or ```)
    - Extra comments or explanations
    - Unnecessary empty lines or indentation
    - Any text outside JSON structure
    - Make sure both key and value are string
    '''

    case_file = extractor.query_case_setup(case_file_prompts, context = True)
    

    # build_case_file_prompt = f'''I want to use the {test_solver} and {test_turbulence_model} model to simulate the case. The boundary conditions are: 
    # Please draft all the cases files [[[ {config.global_files} ]]] necessary to run the case for me. If the table in the paper describe the boundary or initial conditions, the case boundary or initial conditions must strictly follow the descriptions in the table. You tasks are:
    # '''

    return case_file
    

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

    if solver_ == "reactingFoam":
        if "GRI" in config.other_physical_model:
            config.global_files.append("constant/thermo.compressibleGasGRI")
            config.global_files.append("constant/reactionsGRI")

    compressible_solvers = ["acousticFoam", "overRhoPimpleDyMFoam", "overRhoSimpleFoam", "rhoCentralFoam", "rhoPimpleAdiabaticFoam", "rhoPimpleFoam", "rhoPorousSimpleFoam", "rhoSimpleFoam", "sonicDyMFoam", "sonicFoam", "sonicLiquidFoam"]

    if config.case_solver in compressible_solvers:
        if config.case_turbulece_model in ["SpalartAllmaras","kOmegaSST","LaunderSharmaKE","realizableKE","kOmegaSSTLM","kEpsilon","RNGkEpsilon", "SpalartAllmarasDDES", "SpalartAllmarasIDDES"]:
            config.global_files.append("0/alphat")


def load_OF_data_json():
    try:
        with open(config.OF_data_path, 'r', encoding='utf-8') as file:
            config.OF_case_data_dict = json.load(file)  # 直接转换为Python列表
            print("Success reading in the OF_tut_case_json file！")
    except json.JSONDecodeError:
        print("输入JSON格式错误，请检查数据完整性")
        exit()

def main(file_name):

    set_config.load_openfoam_environment()
    
    # print(config.pdf_path)
    config.paper_content, config.paper_table = process_pdf_pdfplumber(config.pdf_path)
    # config.paper_content = process_pdf(config.pdf_path)

    case_file_requirements.extract_boundary_names(config.case_grid)

    boundary_names = ", ".join(config.case_boundaries)

    config.case_boundary_names = boundary_names

    # prepare config
    config.case_name = file_name
    config.OUTPUT_PATH = f'{config.OUTPUT_CHATCFD_PATH}/{config.case_name}'
    config.ensure_directory_exists(config.OUTPUT_PATH)
    config.case_log_write = True

    # list the files required by the solver and turbulence model
    if 0:
        case_required_file(test_solver, test_turbulence_model)  # case的solver和turbulence model
    else: # 如果通用的文件结构不能满足case的需求
        file_corrector.case_required_file2(test_solver, test_turbulence_model)
    print("文件结构：", config.global_files)

    write_initial_files = False
    while not write_initial_files:
        pdf_chunk_response = pdf_chunk_ask()                    # 生成最初的文件
        # print("pdf_chunk_response", pdf_chunk_response)

        config.target_case_requirement_json = pdf_chunk_response

        preprocess_OF_tutorial.read_in_processed_merged_OF_cases()
        try:
            config.global_files = json.loads(config.target_case_requirement_json)
            write_initial_files = True
        except json.JSONDecodeError as e:
            print(f"JSON解码错误: {e}")
            print("重新生成初始文件")

    # write the case files
    for key, value in config.global_files.items():
        output_file = f"{config.OUTPUT_PATH}/{key}"

        try:
            file_writer.write_field_to_file(value,output_file)
            print(f"write the file {key}")

        except Exception as e:
            print(f"Errors occur during write_field_to_file: {e}")
            continue
        else: # 正确执行了场文件写入操作
            file_format_correct = True

    # return

    # revise controlDict to run 2 steps
    run_of_case.setup_cfl_control(config.OUTPUT_PATH)

    # run file test and correct
    run_of_case.convert_mesh(config.OUTPUT_PATH, config.case_grid)

    print("检查网格维度")
    file_corrector.fix_boundary_dimension()

    with open(f"{config.OUTPUT_PATH}/error_history.txt", "w") as f:
        f.write("****************error_history****************\n")

    # run the OpenFOAM case and ICOT debug
    for test_time in range(0, config.max_running_test_round):
        try:
            print(f"****************start running the case {config.case_name} , test_round = {test_time}****************")

            case_run_info = run_of_case.case_run(config.OUTPUT_PATH)
            
            if case_run_info != "case run success.":
                running_error = case_run_info
                config.error_history.append(running_error)

                # 报错错误历史记录
                with open(f"{config.OUTPUT_PATH}/error_history.txt", "a") as f:
                    f.write(f"=====Test round {test_time}=====\n运行错误:\n{running_error}\n")

                # OpenFOAM浮点数带来的错误(Floating point exception)
                float_error_keywords = [
                    "Foam::error::printStack(Foam::Ostream&) at ??:?",
                    "Foam::sigFpe::sigHandler(int)",
                    "Floating point exception"
                ]
                float_error = any(keyword if keyword in running_error else False for keyword in float_error_keywords)
                if float_error:
                    file_corrector.fix_floating_point_exception(running_error)
                    if running_error.startswith("[stack trace]\n=============\n#1  Foam::sigFpe::sigHandler(int)"):
                        print("仅发生浮点数异常错误")
                        with open(f"{config.OUTPUT_PATH}/error_history.txt", "a") as f:
                            f.write("纠错方案：\n进行浮点数异常错误修正\n")
                        continue
                    
                # OpenFOAM化学体积分数不为1
                if "Sum of mass fractions is zero for species" in running_error:
                    file_corrector.fix_mass_fraction_zero()
                    with open(f"{config.OUTPUT_PATH}/error_history.txt", "a") as f:
                        f.write("纠错方案：\n进行化学体积分数之和不为1的修正\n")
                    continue

                # OpenFOAM进行网格转换带来的问题
                # if "inconsistent" in running_error.lower() and test_time <= 2:
                #     print("检查网格维度")
                #     file_corrector.fix_boundary_dimension()
                #     continue
                # if "Foam::error::simpleExit(int, bool) in" in running_error or "Foam::sigFpe::sigHandler(int)" in running_error or file_corrector.detect_boundary_error(running_error) or "No \"neighbourPatch\" provided" in running_error:
                #     print("检查网格边界导致的问题")
                #     file_corrector.fix_boundary_type(running_error)
                #     continue

                boundary_error_keywords = [
                    "inconsistent", 
                    "Foam::error::simpleExit(int, bool) in", 
                    "Foam::sigFpe::sigHandler(int)",
                    "No \"neighbourPatch\" provided"
                    ]

                boundary_error = any(keyword if keyword in running_error else False for keyword in boundary_error_keywords)
                if boundary_error or file_corrector.detect_boundary_error(running_error):
                    print("检查网格边界导致的问题")
                    file_corrector.fix_boundary_error(running_error)
                    with open(f"{config.OUTPUT_PATH}/error_history.txt", "a") as f:
                        f.write("纠错方案：\n网格边界条件的修正\n")
                    # continue

                if file_corrector.detect_dimension_error(running_error):
                    # constant/pRef不正确

                    file_corrector.strongly_correct_all_dimension_with_reference_files()
                    with open(f"{config.OUTPUT_PATH}/error_history.txt", "a") as f:
                        f.write("纠错方案：\n场文件量纲的修正\n")
                else:
                    #判断是否需要添加新文件
                    answer_add_new_file = file_corrector.identify_error_to_add_new_file(running_error)

                    answer_add_new_file_strip = answer_add_new_file.strip()

                    if answer_add_new_file_strip.lower() == 'no':# 修改文件分支

                        file_for_revision, early_revision_advice = file_corrector.analyze_running_error_with_all_case_file_content(running_error)
                        reference_files = file_corrector.find_reference_files_by_solver(file_for_revision)  # 根据file_for_revision查找参考文件

                        try:
                            print(file_for_revision, "的参考文件：", reference_files)
                        except Exception as e:
                            print(f"打印参考文件时发生错误: {e}")
                            continue

                        # 检查错误是否出现了三次，如果出现了三次，则重写该文件。
                        if file_corrector.analyze_error_repetition(config.error_history):
                            print("重写文件")
                            file_corrector.rewrite_file(file_for_revision,reference_files)
                            config.error_history = []  # 重置错误历史记录
                            with open(f"{config.OUTPUT_PATH}/error_history.txt", "a") as f:
                                f.write("纠错方案：\n重写文件\n")
                        else:
                            # 检查网格边界（costant/polyMesh/boundary）
                            # if test_time == 0:
                            #     check_boundary_module.check_and_change_boundary(config.simulate_requirement, config.OUTPUT_PATH)

                            print("修改文件")
                            advices_for_revision = file_corrector.analyze_running_error_with_reference_files(running_error, file_for_revision,early_revision_advice,reference_files)
                            file_corrector.single_file_corrector2(file_for_revision, advices_for_revision, reference_files)

                            with open(f"{config.OUTPUT_PATH}/error_history.txt", "a") as f:
                                f.write(f"纠错方案：\n修改文件{file_for_revision}\n参考文件：\n{reference_files}\n修改建议：\n{advices_for_revision}\n")
                    else:#添加文件分支
                        print("添加缺失文件")
                        file_for_adding = answer_add_new_file_strip
                        file_corrector.add_new_file(file_for_adding)
                        with open(f"{config.OUTPUT_PATH}/error_history.txt", "a") as f:
                            f.write(f"纠错方案：\n添加文件{file_for_adding}\n")

                if not config.set_controlDict_time:
                    run_of_case.setup_cfl_control(config.OUTPUT_PATH)

                if not config.mesh_convert_success:
                    run_of_case.convert_mesh(config.OUTPUT_PATH, config.case_grid)

            else:
                with open(f"{config.OUTPUT_PATH}/cycle_index.txt", "w") as f:
                    f.write(f"Case {config.case_name} run successfully at test_round {test_time}+1.\n")
                break
                
        except Exception as e:
            # 捕获所有异常并处理
            running_error = str(e)
            print("running_error: ", running_error)

            # 有跨文件的量纲不匹配
            if file_corrector.detect_dimension_error(running_error):
                file_corrector.strongly_correct_all_dimension_with_reference_files()
            else:# 无跨文件的量纲不匹配

                #判断是否需要添加新文件
                answer_add_new_file = file_corrector.identify_error_to_add_new_file(running_error)

                answer_add_new_file_strip = answer_add_new_file.strip()

                if answer_add_new_file_strip.lower() == 'no':# 修改文件分支

                    file_for_revision, early_revision_advice = file_corrector.analyze_running_error_with_all_case_file_content(running_error)
                    reference_files = file_corrector.find_reference_files_by_solver(file_for_revision)
                    # 检查错误是否出现了三次，如果出现了三次，则重写该文件。
                    if file_corrector.analyze_error_repetition(config.error_history):
                        file_corrector.rewrite_file(file_for_revision,reference_files)
                    else:
                        advices_for_revision = file_corrector.analyze_running_error_with_reference_files(running_error, file_for_revision,early_revision_advice,reference_files)
                        file_corrector.single_file_corrector2(file_for_revision, advices_for_revision, reference_files)
                else:#添加文件分支
                    file_for_adding = answer_add_new_file_strip
                    file_corrector.add_new_file(file_for_adding)

                if not config.set_controlDict_time:
                    run_of_case.setup_cfl_control(config.OUTPUT_PATH)

                if not config.mesh_convert_success:
                    run_of_case.convert_mesh(config.OUTPUT_PATH, config.case_grid)
            
            continue  # 显式继续下一个循环


    a = 1

def run_case():
    load_OF_data_json()
    case_name_b = test_case_name

    # 运行10次
    for i in range(config.run_time):
        case_name = f"{case_name_b}_{i}"
        main(case_name)