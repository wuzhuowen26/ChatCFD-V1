import config
import shutil
import os
import file_writer

from qa_modules import QA_NoContext_deepseek_V3,QA_NoContext_deepseek_R1
import json
import re
import random
from pathlib import Path

def select_random_items(a, number):
    # 过滤掉值转换为字符串后长度超过10000的键值对
    filtered_a = {k: v for k, v in a.items() if len(str(v)) <= 10000}
    
    # 判断处理后的字典键的数量是否大于5
    if len(filtered_a) > number:
        # 随机选取5个键
        selected_keys = random.sample(list(filtered_a.keys()), number)
        # 构建新字典
        return {key: filtered_a[key] for key in selected_keys}
    else:
        return filtered_a
        
    
def dict_to_json_string(data):
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    return json_str

def create_OF_case_json(source_dir):
    """
    将OpenFOAM案例目录（0/, constant/, system/）的文件内容保存到JSON文档
    
    参数：
    source_dir - 案例根目录路径（包含0/ constant/ system/的文件夹）
    output_json - 输出JSON文件的路径
    
    返回：
    None，结果将写入指定JSON文件
    """
    file_data = {}
    
    # 需要处理的三个目标目录
    target_dirs = ["0", "constant", "system"]
    
    for dir_name in target_dirs:
        dir_path = os.path.join(source_dir, dir_name)
        
        # 如果目录不存在则跳过
        if not os.path.isdir(dir_path):
            continue
            
        # 遍历目录中的条目
        for entry in os.listdir(dir_path):
            entry_path = os.path.join(dir_path, entry)
            
            # 只处理文件（忽略子目录）
            if os.path.isfile(entry_path):
                # 构建相对于源目录的路径（使用POSIX风格路径）
                relative_path = os.path.join(dir_name, entry).replace("\\", "/")
                
                try:
                    # 读取文件内容
                    with open(entry_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        file_data[relative_path] = content
                except Exception as e:
                    print(f"无法读取文件 {entry_path}: {str(e)}")
                    continue

    return dict_to_json_string(file_data)


def list_case_file(case_path):
    target_folders = ['0', 'system', 'constant']
    file_list = []
    for folder in target_folders:
        folder_path = os.path.join(case_path, folder)
        if not os.path.isdir(folder_path):
            continue
        for entry in os.listdir(folder_path):
            entry_path = os.path.join(folder_path, entry)
            if os.path.isfile(entry_path):
                # 构建相对路径并统一为Linux风格路径分隔符
                rel_path = f"{folder}/{entry}"
                file_list.append(rel_path)
    return file_list

def identify_error_to_add_new_file(running_error):

    analyze_error_to_add_new_file = f'''{config.general_prompts}. OpenFOAM File Requirement Analyzer
        Analyze the runtime error {running_error} to:

        1. Check if it contains the exact phrase "cannot find file"
        2. If present:
        a) Identify the missing file path from the error message
        b) Format the response as 0/..., system/..., or constant/...
        3. If absent/irrelevant: Respond with no

1. Respond ONLY with a filename (format: 0/xx, system/xx, or constant/xx) if required
2. Respond ONLY with 'no' if no file needed
3. Strict formatting requirements:
- No special characters: (), '', ", `
- No markdown/formatting symbols
- No whitespace, line breaks, or indentation
- No explanations or extra text
Your response must be exactly one of:
a) A directory-path formatted string from allowed locations
b) The lowercase string 'no'
Examples of valid responses:
system/fvSchemes
constant/g
no
'''

    qa = QA_NoContext_deepseek_V3()

    answer = qa.ask(analyze_error_to_add_new_file)

    pure_response = file_writer.extract_pure_response(answer)

    return pure_response

def read_files_to_dict(base_dir):
    file_dict = {}
    # 需要遍历的目录列表
    target_dirs = ['0', 'system', 'constant']
    
    for dir_name in target_dirs:
        dir_path = os.path.join(base_dir, dir_name)
        # 如果目录不存在则跳过
        if not os.path.isdir(dir_path):
            continue
        # 遍历目录下的所有条目
        for entry in os.listdir(dir_path):
            full_path = os.path.join(dir_path, entry)
            # 只处理文件，忽略子目录
            if os.path.isfile(full_path):
                # 构建相对路径作为key（相对于base_dir）
                rel_path = os.path.join(dir_name, entry)
                # 读取文件内容
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        file_dict[rel_path] = f.read()
                except Exception as e:
                    file_dict[rel_path] = f"<Error reading file: {str(e)}>"
    
    return file_dict

def add_new_file(file_name):

    print(f"adding new file: {file_name}")

    file_path = f'{config.OUTPUT_PATH}/{file_name}'

    other_case_file_content = read_files_to_dict(config.OUTPUT_PATH)

    add_new_file_prompt = f'''
    A new case file {file_name} must be add to the OpenFOAM case dir. The file contents of other case files are: {other_case_file_content}. Please respond the file contents for the new file which can make this case run correctly with other case files. Ensure the dimension is correct if the dimension shows in the file content.

    In your response: Absolutely AVOID any elements including but not limited to:
    - Markdown code block markers (``` or  ```)
    - Extra comments or explanations
    - Unnecessary empty lines or indentation
    '''

    qa = QA_NoContext_deepseek_R1()

    answer = qa.ask(add_new_file_prompt)

    try:
        file_writer.write_field_to_file(answer,file_path)
        print(f"write the file {file_name}")
    except Exception as e:
        print(f"Errors occur during write_field_to_file: {e}")
    else: # 正确执行了场文件写入操作
        file_write_successful = True

def identify_file_name_from_error(running_error):

    case_files = list_case_file(config.OUTPUT_PATH)

    analyze_running_error_prompt = f'''
    Analyze the provided OpenFOAM runtime error { {running_error} } to identify the file requires revision. The result must be one of the following files: { {case_files} }. You response must only include the case name.

    In your response: Absolutely AVOID any elements including but not limited to:
    - Markdown code block markers (``` or ```)
    - Extra comments or explanations
    - Unnecessary empty lines or indentation
    '''
    
    qa = QA_NoContext_deepseek_R1()

    answer = qa.ask(analyze_running_error_prompt)

    answer = answer.strip()

    # file_for_revision = file_writer.extract_pure_response(answer)

    return answer

# 参数target_file是从running_error中识别出来的、需要修改的文件名
# 根据solver找
def find_reference_files_by_solver(target_file):
    case_solver = config.case_solver
    turbulence_model = config.case_turbulece_model
    turbulence_model_list = [
        "SpalartAllmarasIDDES",
        "SpalartAllmarasDDES",
        "SpalartAllmaras",
        "kEpsilon",
        "WALE",
        "kEqn",
        "LaunderSharmaKE",
        "realizableKE",
        "kOmegaSSTLM",
        "RNGkEpsilon",
        "buoyantKEpsilon",
        "kkLOmega",
        "PDRkEpsilon",
        "kOmegaSST",
        "dynamicKEqn"
    ]
    if turbulence_model not in turbulence_model_list:
        turbulence_model = None

    other_physical_model = config.other_physical_model
    other_model_list = [
        "GRI", "TDAC", "LTS","common","Maxwell","Stokes"
    ]
    if other_physical_model not in other_model_list:
        other_physical_model = None

    # 返回内容
    target_file_reference = {}

    solver_type = None

    file_number = 0

    for key, value in config.OF_case_data_dict.items():
        if case_solver in key and turbulence_model == value["turbulence_model"]:
            
            # 如果有other_physical_model,则需要判断是否相同
            if "other_physical_model" in value.keys():
                if not other_physical_model == value["other_physical_model"]:
                    continue

            config_files = value['configuration_files']
            if target_file in config_files.keys():
                # print(config_files.keys())
                new_file_key = f'sample_file_{file_number}'
                file_number += 1
                target_file_reference[new_file_key] = config_files[target_file]
    
    # 如果没找到,则不考虑湍流模型相同
    if file_number == 0:
        for key, value in config.OF_case_data_dict.items():
            if case_solver in key:
                config_files = value['configuration_files']

                if target_file in config_files.keys():
                    # print(config_files.keys())
                    new_file_key = f'sample_file_{file_number}'
                    file_number += 1
                    target_file_reference[new_file_key] = config_files[target_file]

    # 如果上述结果为0，则在更高一级找，先找到求解器类型，如compressible
    if file_number == 0:
        for key, value in config.OF_case_data_dict.items():
            if case_solver in key:
                path_split = key.split('/')
                solver_type = path_split[0]
                break

    # 在求解器类型下找target_file
    if solver_type is not None:
        for key, value in config.OF_case_data_dict.items():
                path_split = key.split('/')
                if solver_type == path_split[0]:
                    config_files = value['configuration_files']
                    if target_file in config_files.keys():
                        # print(config_files.keys())
                        new_file_key = f'sample_file_{file_number}'
                        file_number += 1
                        target_file_reference[key] = config_files[target_file]

    # print(target_file_reference.keys())
    target_file_reference = {k: v for k, v in target_file_reference.items() if v != ""} # 去除空的value

    several_target_file_reference = select_random_items(target_file_reference, 3)

    return dict_to_json_string(several_target_file_reference)

def analyze_running_error_with_all_case_file_content(running_error):

    all_case_file_content = create_OF_case_json(config.OUTPUT_PATH)

    file_content = None

    case_files = list_case_file(config.OUTPUT_PATH)

    case_files = dict_to_json_string(case_files)    # json.dumps()

    analyze_running_error_prompt = f'''
    Analyze the provided OpenFOAM runtime error { {running_error} } to identify the root cause and which case file needs to be revised to fix the runtime error. The OpenFOAM case files are given as json-format string as { {all_case_file_content} }. 
    Your response must be a json format string with following keys and values:
    - a 'wrong_file' key, and its value the file name which will be revised to fix the error. This file name must be one of the case files { {case_files} }.
    - a 'advices_for_revision' key, and its value provide a step-by-step fix of the 'wrong_file' to fix the error. Ensure the advice addresses the error’s technical cause (e.g., CFL violation, invalid discretization scheme, missing required keyword). The advice must be a string.

    In your JSON response: Absolutely AVOID any elements including but not limited to:
    - Markdown code block markers (``` or ```)
    - Extra comments or explanations
    - Unnecessary empty lines or indentation
    '''
    
    qa = QA_NoContext_deepseek_R1()

    answer = qa.ask(analyze_running_error_prompt)

    dict_answer = json.loads(answer)

    advices_for_revision = dict_answer['advices_for_revision']
    wrong_file = dict_answer['wrong_file']

    return [wrong_file,advices_for_revision]

def analyze_running_error_2(running_error, file_name):

    file_content = None

    file_path = f'{config.OUTPUT_PATH}/{file_name}'

    with open(file_path, "r", encoding="utf-8") as file:
        file_content = file.read()

    case_files = list_case_file(config.OUTPUT_PATH)

    analyze_running_error_prompt = f'''
    Analyze the provided OpenFOAM runtime error {running_error} to identify the root cause. Give advice on correcting the file {file_name} with the file contents as {file_content}.

    In your response: Provide a step-by-step fix (e.g., adjust endTime, modify tolerance in solver settings, correct boundary type in U). Ensure the advice addresses the error’s technical cause (e.g., CFL violation, invalid discretization scheme, missing required keyword). The advice must be a string.

    In your response: Absolutely AVOID any elements including but not limited to:
    - Markdown code block markers (``` or ```)
    - Extra comments or explanations
    - Unnecessary empty lines or indentation
    '''
    
    qa = QA_NoContext_deepseek_R1()

    answer = qa.ask(analyze_running_error_prompt)

    advices_for_revision = answer

    return advices_for_revision

def analyze_error_repetition(error_history):
    answer = 'no'
    if(len(error_history)>=3):
        error_minus_1 = error_history[-1]
        error_minus_2 = error_history[-2]
        error_minus_3 = error_history[-3]

        analyze_running_error_repetition_prompt = f'''
        Analyze the following three error histories to identify whether the error have repetitively shown three time. Error 1: {error_minus_1}. Error 2: {error_minus_2}. Error 3: {error_minus_3}. If the error have repetitively shown three times, respond 'yes'; otherwise, respond 'no'. You must only respond 'yes' or 'no'.
        '''

        qa = QA_NoContext_deepseek_R1()

        answer = qa.ask(analyze_running_error_repetition_prompt)

    answer = answer.strip()

    if answer.lower() == 'yes':
        return True
    else:
        return False

def rewrite_file(file_name, reference_files):
    print(f"rewriting {file_name}")

    file_content = None

    file_path = f'{config.OUTPUT_PATH}/{file_name}'

    with open(file_path, "r", encoding="utf-8") as file:
        file_content = file.read()

    correct_file_prompt = f'''{config.general_prompts}
    Please rewrite the {file_name} file for the OpenFOAM case. The original file content is: {file_content}. You can reference these files from OpenFOAM tutorial {reference_files} for formating and key values. Ensure the dimension is correct if the dimension shows in the file content.

    In your response: Absolutely AVOID any elements including but not limited to:
    - Markdown code block markers (``` or  ```)
    - Extra comments or explanations
    '''

    qa = QA_NoContext_deepseek_V3()

    answer = qa.ask(correct_file_prompt)

    answer = file_writer.extract_pure_response(answer)

    try:
        file_writer.write_field_to_file(answer,file_path)
        print(f"write the file {file_name}")

    except Exception as e:
        print(f"Errors occur during write_field_to_file: {e}")
    else: # 正确执行了场文件写入操作
        file_write_successful = True

def detect_dimension_error(running_error):
    
    detect_dimension_error = f'''{config.general_prompts}\nAnalyze the OpenFOAM runtime error {running_error} to determine if it explicitly indicates a dimensional inequality. Look for patterns such as:

    - Imbalanced dimension comparisons (e.g., [dim1] != [dim2], a != b where a and b - are dimensions).
    - Keywords like dimensions, incompatible dimensions, or dimension mismatch.
    - Explicit dimension lists (e.g., [0 0 0 -1 0 0 0] != [0 0 0 -2 0 0 0])
    If the error directly references dimensional inequality (as defined above), respond 'yes'. If not, or if the error is unrelated (e.g., syntax, segmentation faults, solver crashes), respond 'no'. Only reply with 'yes' or 'no'.'''

    qa = QA_NoContext_deepseek_V3()

    answer = qa.ask(detect_dimension_error)

    answer = file_writer.extract_pure_response(answer)

    if answer.strip().lower() == 'yes':
        return True
    else:
        return False

def strongly_correct_all_dimension_with_reference_files():

    print(f"strongly correcting all field file dimension")

    case_0_folder = f'{config.OUTPUT_PATH}/0'

    folder_path = Path(case_0_folder)

    for file_path in folder_path.iterdir():
        file_content = None
        file_name = f'0/{file_path.name}'

        reference_files = find_reference_files_by_solver(file_name)

        if file_path.is_file():
            field_file = f'{case_0_folder}/{file_path.name}'

        with open(file_path, "r", encoding="utf-8") as file:
            file_content = file.read()
            a = 1

        correct_dimension_prompt =   f'''{config.general_prompts}
        Please check the dimension of the OpenFOAM field file {file_path.name} and correct it according to the dimensions of the reference file contents. The original file content is: {file_content}. The reference file contents are: {reference_files}. You must not revise any other contents of the original file except for the dimension.

        In your response: Absolutely AVOID any elements including but not limited to:
        - Markdown code block markers (``` or  ```)
        - Extra comments or explanations
        - Unnecessary empty lines or indentation
        '''

        qa = QA_NoContext_deepseek_V3()

        answer = qa.ask(correct_dimension_prompt)

        answer = file_writer.extract_pure_response(answer)

        try:
            file_writer.write_field_to_file(answer,file_path)
            print(f"write the file 0/{file_path.name}")

        except Exception as e:
            print(f"Errors occur during write_field_to_file: {e}")
        else: # 正确执行了场文件写入操作
            file_write_successful = True

def fix_floating_point_exception(running_error):
    # print(f"fix the problem: 'Floating point exception (core dumped)' ")
    print("修复浮点异常错误")

    case_0_folder = f'{config.OUTPUT_PATH}/0'
    folder_path = Path(case_0_folder)

    for file_path in folder_path.iterdir():
        file_content = ""
        file_name = f'0/{file_path.name}'

        reference_files = find_reference_files_by_solver(file_name)

        # if file_path.is_file():
        #     field_file = f'{case_0_folder}/{file_path.name}'

        with open(file_path, "r", encoding="utf-8") as file:
            file_content = file.read()

        fix_floating_point_exception_prompt =   f'''{config.general_prompts}
        The "Floating point exception (core dumped)" error encountered during OpenFOAM operation is most likely due to one of the following reasons:
        1. some values may be too large or too small, or set to negative or unreasonable values, leading to floating point exceptions in calculations
        2. there is a misunderstanding when setting a certain value, for example, for an incompressible fluid, p can be set to 0 to indicate that the relative pressure is 0, but for a compressible fluid, p cannot be set to 0 because p is the absolute pressure, which must include atmospheric pressure (e.g. 1e5)
        3. sometimes it is caused by unreasonable setting of boundary conditions or setting parameters for non-existent boundary conditions in the field file (with a relatively low probability).

        Please check the value setting of the OpenFOAM field file {file_path.name} and correct it according to the value of the reference file content. The original file content is {file_content}. The boundary conditions in the polyMesh/boundary file is {config.boundary_name_and_type}.The reference file content is {reference_files}. The contents of the original file must not be modified in any way other than the value of the parameter.(If there is no problem with the file, please return the content in the original file)
        But you have to follow the parameter settings mentioned in the user description: [{config.case_description}]
        
        In your response: Absolutely AVOID any elements including but not limited to:
        - Markdown code block markers (``` or  ```)
        - Extra comments or explanations
        - Unnecessary empty lines or indentation
        '''

        qa = QA_NoContext_deepseek_V3()
        answer = qa.ask(fix_floating_point_exception_prompt)
        answer = file_writer.extract_pure_response(answer)

        try:
            file_writer.write_field_to_file(answer,file_path)
            print(f"write the file 0/{file_path.name}")

        except Exception as e:
            print(f"Errors occur during write_field_to_file: {e}")
        else: # 正确执行了场文件写入操作
            file_write_successful = True

    file_t = f"{config.OUTPUT_PATH}/constant/thermophysicalProperties"
    if os.path.exists(file_t):
        reference_files = find_reference_files_by_solver("constant/thermophysicalProperties")
        with open(file_t, "r", encoding="utf-8") as file:
            file_content = file.read()

        fix_floating_point_exception_prompt =   f'''{config.general_prompts}
        The "Floating point exception (core dumped)" error encountered during OpenFOAM operation is most likely due to one of the following reasons:
        1. some values may be too large or too small, or set to negative or unreasonable values, leading to floating point exceptions in calculations
        2. sometimes it is caused by the unreasonable setting of thermoType and mixture

        Please check the value setting of the OpenFOAM file [thermophysicalProperties] and correct it according to the value of the reference file content. The original file content is {file_content}. The reference file content is {reference_files}. If there is no problem with the file, please return the content in the original file
        But you have to follow the parameter settings mentioned in the user description: [{config.case_description}]
        
        In your response: Absolutely AVOID any elements including but not limited to:
        - Markdown code block markers (``` or  ```)
        - Extra comments or explanations
        - Unnecessary empty lines or indentation
        '''

        qa = QA_NoContext_deepseek_V3()
        answer = qa.ask(fix_floating_point_exception_prompt)
        answer = file_writer.extract_pure_response(answer)

        try:
            file_writer.write_field_to_file(answer,file_t)
            print(f"write the file constant/thermophysicalProperties")
        except Exception as e:
            print(f"Errors occur during write_thermophysicalProperties_to_file: {e}")
        else: # 正确执行了场文件写入操作
            file_write_successful = True

    file_s = f"{config.OUTPUT_PATH}/system/fvSolution"
    reference_files = find_reference_files_by_solver("system/fvSolution")
    with open(file_s, "r", encoding="utf-8") as file:
        file_content = file.read()

    fix_floating_point_exception_prompt =   f'''{config.general_prompts}
    The [Floating Point Exception] occurred in openfoam. The specific error message is: {running_error}. 

    This error might be caused by the system/fvSolution file.
    Please check the value setting of the OpenFOAM file [system/fvSolution] and correct it according to the value of the reference file content. Finally, return the complete content of the modified fvSolution file. The original file content is [{file_content}]. The reference file content is [{reference_files}]. If there is no problem with the file, please return the content in the original file.
    But you have to follow the parameter settings mentioned in the user description: [{config.case_description}]
    
    In your response: Absolutely AVOID any elements including but not limited to:
    - Markdown code block markers (``` or  ```)
    - Extra comments or explanations
    - Unnecessary empty lines or indentation
    '''

    qa = QA_NoContext_deepseek_V3()
    answer = qa.ask(fix_floating_point_exception_prompt)
    answer = file_writer.extract_pure_response(answer)

    try:
        file_writer.write_field_to_file(answer,file_s)
        print(f"write the file system/fvSolution")
    except Exception as e:
        print(f"Errors occur during write_fvSolution_to_file: {e}")
    else: # 正确执行了场文件写入操作
        file_write_successful = True


def fix_mass_fraction_zero():
    print("修复化学分子质量")

    field_file_content = {}
    simulation_requirements = config.simulate_requirement

    case_0_folder = f'{config.OUTPUT_PATH}/0'
    folder_path = Path(case_0_folder)

    for file_path in folder_path.iterdir():
        file_name = file_path.name
        with open(file_path, "r", encoding="utf-8") as file:
            file_content = file.read()
        
        field_file_content[file_name] = file_content

    prompt = f"""
    OpenFOAM发生报错"Sum of mass fractions is zero for species...", 该报错由化学分子体积分数之和不为1导致的
    下面是场文件:
    {field_file_content}
    下面是仿真需求:
    {simulation_requirements}

    请你根据以上信息修改有问题的描述化学分子的场文件(不是所有场文件都与化学分子相关),确保各部分(如空气中,燃料中)化学分子体积分数之和为1。
    最终按照以下格式返回修改后的完整场文件内容,不要返回思考过程和代码块标识```等其他内容:
    {{
        "file_name": "N2",
        "file_content": "FoamFile ..."
    }}

    注意: 
    1. 即使有多个场文件错误,你也只能先修改并返回其中一个场文件内容,使这个场文件符合仿真需求,并且这个场文件不能是Ydefault,只能是描述化学分子的场文件。
    2. 请你仅对描述化学分子的场文件内容中有关质量分数的部分进行修改,不要修改其他内容(比如边界条件的数量,类型等)。
    3. 请你确保修改后的体积分数之和为1。
    4. 请你确保修改后的场文件内容符合OpenFOAM的格式要求, 不要忘记OpenFOAM文件头等。
    5. 请你按上述返回格式进行返回的场文件内容，不要返回其他内容。
    """

    qa = QA_NoContext_deepseek_R1()
    rsp = qa.ask(prompt)

    try:
        rsp = json.loads(rsp)
        file_name = rsp["file_name"]
        file_content = rsp["file_content"].strip('"').replace("\\n", "\n")
    except json.JSONDecodeError:
        print("处理质量分数错误时出现json解析错误")
        prompt = f"""
            这是一段错误的json格式内容:
            {rsp}
            请你返回"file_name"对应的内容,注意不要返回其他内容,也不要返回```或""等其他符号。
        """
        file_name = use_api.use_api(question=prompt, model_name="deepseek-v3-250324")
        prompt = f"""
            这是一段错误的json格式内容:
            {rsp}
            请你返回"file_content"对应的内容,注意不要返回其他内容,也不要返回```或""等其他符号。
        """
        file_content = use_api.use_api(question=prompt, model_name="deepseek-v3-250324")
        file_content = file_content.strip('"').replace("\\n", "\n")

    with open(f"{case_0_folder}/{file_name}", "w", encoding="utf-8") as f:
        f.write(file_content)
    print(f"修改了 {file_name} 质量分数")

def fix_boundary_dimension():
    print("修复边界条件维度错误")

    boundary_path = f"{config.OUTPUT_PATH}/constant/polyMesh/boundary"

    with open(boundary_path, "r", encoding="utf-8") as file:
        boundary_content = file.read()

    # 判断是否为二维算例
    judge_prompt = f"""
        有一个计算流体力学算例的仿真需求为[[{config.simulate_requirement}]]，请你判断是否要进行二维算例的仿真？如果不是要进行二维算例的仿真，请你直接返回"No"，不用进入下面的判断。
        如果要进行二维算例，请你检查OpenFOAM的boundary文件内容[[{boundary_content}]]，其中是否有边界条件的type为"empty"，如果没有请你返回"Yes"，其余任何情况都返回“No”。

        注意：你只需要返回"Yes"或"No"，不需要解释，也不需要返回任何代码格式，比如:```。
    """
    qa = QA_NoContext_deepseek_R1()
    judge_result = qa.ask(judge_prompt)
    # print(judge_result)

    # 检查是否需要修改边界条件
    if judge_result.strip() == "Yes":
        print("需要修改边界条件")
        change_prompt = f'''
            This is the content of the boundary file of OpenFOAM [[{boundary_content}]]. This is a two-dimensional example, so among all the boundary conditions, there must be one whose type is "empty".
            This is the simulation requirement of this example [[{config.simulate_requirement}]]. Please determine which boundary condition type should be "empty" based on the simulation requirement of this example.
            Please modify the type of the incorrect boundary condition to "empty" and return the content of the modified boundary file(Usually, the boundary type with the boundary name frontAndBack or defaultFaces is empty).
            Note: You only need to return the content of the modified boundary file. There is no need for interpretation or return any code format, such as: ```.
        '''
        qa = QA_NoContext_deepseek_R1()
        boundary_content = qa.ask(change_prompt)
        with open(boundary_path, "w") as f:
            f.write(boundary_content)

    extract_prompt = f'''
        This is the content of the boundary file of OpenFOAM [[{boundary_content}]]. Please extract all the names of the boundary conditions and their types from it, and return a dictionary in the following format:
        {{
            "boundary_conditions": [
                {{
                    "name": "Name of boundary condition"
                    "type": "Boundary condition type"
                }},
                ...
            ]
        }}
        Note: You only need to return the dictionary. There is no need for explanations or to return any code format, such as:```.
        '''
    qa = QA_NoContext_deepseek_V3()
    config.boundary_name_and_type = qa.ask(extract_prompt)

def detect_boundary_error(running_error):
    detect_boundary_error_prompt = f'''
    OpenFOAM发生了以下的报错:
    {running_error}
    请你分析这个报错是否是由于constant/polyMesh/boundary文件中的边界条件设置错误、不合理或boundary文件格式有问题导致的
    请你注意,如果报错由场文件自身的边界条件设置与boundary文件不符或由场文件缺少某个边界条件的设置,那么这个错误不是由boundary文件引起的
    
    你只需要回答yes或no。
    '''

    qa = QA_NoContext_deepseek_R1()

    answer = qa.ask(detect_boundary_error_prompt)
    print("judge: ", answer)
    
    if 'yes' in answer.lower():
        return True
    else:
        return False

def fix_boundary_type(running_error):

    # 读取boundary文件内容
    boundary_path = f"{config.OUTPUT_PATH}/constant/polyMesh/boundary"
    with open(boundary_path, "r", encoding="utf-8") as file:
        boundary_content = file.read()

    # 读取报错信息中的场文件内容，帮助进行边界条件的设置
    pattern = r'(?<=0/)(.*?)(?=/boundary)'    # 0/p/boundary -> p
    match = re.search(pattern, running_error)
    file_to_read = match.group(0) if match else 0  # group(0)返回完整匹配内容

    # 读取参考场文件中的内容
    if file_to_read:
        with open(f"{config.OUTPUT_PATH}/0/{file_to_read}", "r", encoding="utf-8") as file:
            file_content = file.read()

        # openfoam发生了如下报错，请你根据报错信息和场文件内容，修复边界条件错误
        prompt = f'''{config.general_prompts}
        The following error occurred in openfoam. Please fix the boundary condition Settings in the boundary file based on the error message and the content of the field file, and return the complete modified boundary file. Please note that you can only change the boundary condition type or add missing parameters to the boundary based on the error message. At the same time, do not forget to write the OpenFOAM file header.
        Error message: {running_error}
        The content of field file {file_to_read}: {file_content}
        The content of boundary file: {boundary_content}
        
        In your response: Absolutely AVOID any elements including but not limited to:
        - Markdown code block markers (``` or  ```)
        - Extra comments or explanations
        '''
    else:
        # openfoam发生了如下报错，请你根据报错信息，修复边界条件错误
        prompt = f'''{config.general_prompts}
        The following error occurred in openfoam. Please fix the boundary condition Settings in the boundary file based on the error message and the content of the field file, and return the complete modified boundary file. Please note that you can only change the boundary condition type or add missing parameters to the boundary based on the error message. At the same time, do not forget to write the OpenFOAM file header.
        Error message: {running_error}
        boundary file: {boundary_content}
        
        In your response: Absolutely AVOID any elements including but not limited to:
        - Markdown code block markers (``` or  ```)
        - Extra comments or explanations
        '''

    # 提取v3的响应
    qa = QA_NoContext_deepseek_V3()
    answer = qa.ask(prompt)
    boundary_content = file_writer.extract_pure_response(answer)

    try:
        file_writer.write_field_to_file(boundary_content, boundary_path)
        print(f"修改了边界条件文件: {boundary_path}")
        extract_prompt = f'''
            This is the content of the boundary file of OpenFOAM [[{boundary_content}]]. Please extract all the names of the boundary conditions and their types from it, and return a dictionary in the following format:
            {{
                "boundary_conditions": [
                    {{
                        "name": "Name of boundary condition"
                        "type": "Boundary condition type"
                    }},
                    ...
                ]
            }}
            Note: You only need to return the dictionary. There is no need for explanations or to return any code format, such as:```.
            '''
        qa = QA_NoContext_deepseek_V3()
        config.boundary_name_and_type = qa.ask(extract_prompt)
    except Exception as e:
        print(f"修改边界条件文件出现错误: {e}")
    else: 
        file_write_successful = True

def fix_boundary_error(running_error):
    
    boundary_path = f"{config.OUTPUT_PATH}/constant/polyMesh/boundary"
    with open(boundary_path, "r", encoding="utf-8") as file:
        boundary_content = file.read()

    prompt = f"""
    OpenFOAM中由fluentMeshToFoam命令转换得到的最初的constant/polyMesh/boundary文件的内容为：
    {config.boundary_init},
    最初的boundary文件可能发生以下的错误,但其余部分均是正确的:
    1. 仿真需求中要进行二维仿真,但是openfoam未能正确识别网格为二维网格,所以有一个边界名称(一般为frontAndBack, defaultFaces等)的类型应该为"empty"才对
    2. 边界条件的类型设置有问题,例如可能对某些边界条件的patch类型修改为合适的类型
    3. 在边界条件的设置中缺少了一些参数,比如cylic类型的边界条件可能需要设置neighbourPatch参数

    现在的网格文件为:
    {boundary_content}
    OpenFOAM发生了如下报错:
    {running_error}
    报错信息中包含"inconsistent"可能由于未能正确识别网格为二维网格导致,包含"Foam::error::simpleExit(int, bool)"或"Foam::sigFpe::sigHandler(int)"可能是由于边界条件的类型设置有问题,"No 'neighbourPatch'  provided"可能是由于cyclic类型的边界条件缺少neighbourPatch参数导致。
    用户的仿真需求:
    {config.simulate_requirement}

    请你根据上述信息,修复constant/polyMesh/boundary文件的错误,并返回修复后的boundary文件内容。请注意,你只能根据报错信息修改边界条件类型或添加缺失的参数,而边界条件的名称和数量,nFaces和startFace的大小应与最初的网格文件保持一致。
    不要返回除了修复后的boundary文件内容之外的任何内容,包括但不限于代码块标记(如```或```)、额外的注释或解释、不必要的空行或缩进等。需要注意修复后的boundary文件内容需要包含OpenFOAM的文件头信息:
    FoamFile
    {{
        version     2.0;
        format      ascii;
        class       polyBoundaryMesh;
        object      boundary;
    }}
    """

    qa = QA_NoContext_deepseek_R1()
    boundary_content_new = qa.ask(prompt)
    with open(boundary_path, "w") as f:
        f.write(boundary_content_new)

    extract_prompt = f'''
        This is the content of the boundary file of OpenFOAM [[{boundary_content_new}]]. Please extract all the names of the boundary conditions and their types from it, and return a dictionary in the following format:
        {{
            "boundary_conditions": [
                {{
                    "name": "Name of boundary condition"
                    "type": "Boundary condition type"
                }},
                ...
            ]
        }}
        Note: You only need to return the dictionary. There is no need for explanations or to return any code format, such as:```.
        '''
    qa = QA_NoContext_deepseek_V3()
    config.boundary_name_and_type = qa.ask(extract_prompt)

def analyze_running_error_with_reference_files(running_error, file_name,early_revision_advice, reference_files):

    file_content = None

    file_path = f'{config.OUTPUT_PATH}/{file_name}'

    with open(file_path, "r", encoding="utf-8") as file:
        file_content = file.read()

    case_files = list_case_file(config.OUTPUT_PATH)


    if 0:       # 是否开启联网搜索
        from search_module import organize_web_content
        web_content = organize_web_content(running_error)
        analyze_running_error_prompt = f'''
        Analyze the provided OpenFOAM runtime error [[[ {running_error} ]]] to identify the root cause. Give advice on correcting the file { {file_name} } with the file contents as [[[ {file_content} ]]]. The revision must not alter the file to voilate these initial and boundary conditions in the paper [[[ {config.case_ic_bc_from_paper} ]]]. You can refer to these files from OpenFOAM tutorial [[[ {reference_files} ]]] to improve the correction advice.
        Here are some web pages content [[[ {web_content} ]]] about this error that may help you.
        
        In your response: Provide a step-by-step fix. Ensure the advice addresses the error's technical cause. The advice must be a string.

        In your response: Absolutely AVOID any elements including but not limited to:
        - Markdown code block markers (``` or ```)
        - Extra comments or explanations
        - Unnecessary empty lines or indentation
        '''
    else:
        analyze_running_error_prompt = f'''
        Analyze the provided OpenFOAM runtime error [[[ {running_error} ]]] to identify the root cause. Give advice on correcting the file { {file_name} } with the file contents as [[[ {file_content} ]]]. The revision must not alter the file to voilate these initial and boundary conditions in the paper [[[ {config.case_ic_bc_from_paper} ]]]. You can refer to these files from OpenFOAM tutorial [[[ {reference_files} ]]] to improve the correction advice.
        
        In your response: Provide a step-by-step fix. Ensure the advice addresses the error's technical cause. The advice must be a string.
        Additionally, if an error occurs due to keyword settings, you need to analyze whether the content corresponding to that keyword should be set in { {file_name} }. If it is determined that such content should not appear in { {file_name} }, you should explicitly point it out and recommend its removal(common in files within the constant folder).For example, if the {{specie}} keyword in the {{thermo.compressibleGas}} file is incorrect, analysis shows that {{specie}} belongs to the {{mixture}} section of the file. However, {{mixture}} should be set in {{thermophysicalProperties}}, not in {{thermo.compressibleGas}}. So, it is recommended to delete the settings related to mixture.

        In your response: Absolutely AVOID any elements including but not limited to:
        - Markdown code block markers (``` or ```)
        - Extra comments or explanations
        - Unnecessary empty lines or indentation
        '''
    
    qa = QA_NoContext_deepseek_R1()

    answer = qa.ask(analyze_running_error_prompt)

    advices_for_revision = answer

    return advices_for_revision

def single_file_corrector2(file_name, advices_for_revision, reference_files):
    print(f"correcting {file_name}")

    file_content = None

    file_path = f'{config.OUTPUT_PATH}/{file_name}'

    with open(file_path, "r", encoding="utf-8") as file:
        file_content = file.read()

    if 1:       # 是否开启根据参考文件纠错 and 边界条件检查
        correct_file_prompt = f'''{config.general_prompts} Correct the OpenFOAM case file.
        Please correct the { {file_name} } file with file contents as { {file_content} } to strictly adhere to the following correction advice { {advices_for_revision} }. Ensure the dimension in [] is correct if the dimension shows in the file content. You must not change any other contents of the file except for the correction advice or dimension in [].
        You can reference these files from OpenFOAM tutorial { {reference_files} } for formatting.
        This is the name of the boundary condition and the corresponding type [[{config.boundary_name_and_type}]] for this example. Please ensure that the boundary condition settings in the file comply with it.
        
        In your final response after "Here is my response:", absolutely AVOID any elements including but not limited to:
        - Markdown code block markers (``` or  ```)
        - Extra comments or explanations
        '''
    else:
        correct_file_prompt = f'''{config.general_prompts} Correct the OpenFOAM case file.
        Please correct the { {file_name} } file with file contents as { {file_content} } to strictly adhere to the following correction advice { {advices_for_revision} }. Ensure the dimension in [] is correct if the dimension shows in the file content. You must not change any other contents of the file except for the correction advice or dimension in [].
        
        In your final response after "Here is my response:", absolutely AVOID any elements including but not limited to:
        - Markdown code block markers (``` or  ```)
        - Extra comments or explanations
        '''

    #     # You can reference these files from OpenFOAM tutorial { {reference_files} } for formatting.
    # 这是根据求解器类型和湍流模型来选择的参考文件{{}}，这是根据算例名称来选择的参考文件{{}}，这两个参考文件是来源不同。你可以根据这两个参考文件来选择一个最合适的参考文件。


    qa = QA_NoContext_deepseek_V3()

    answer = qa.ask(correct_file_prompt)

    answer = file_writer.extract_pure_response(answer)

    try:
        file_writer.write_field_to_file(answer,file_path)
        print(f"write the file {file_name}")

    except Exception as e:
        print(f"Errors occur during write_field_to_file: {e}")
    else: # 正确执行了场文件写入操作
        file_write_successful = True

def ensure_all_field_file_dimensions():

    print(f"ensuring all field file dimension")

    case_0_folder = f'{config.OUTPUT_PATH}/0'

    folder_path = Path(case_0_folder)

    for file_path in folder_path.iterdir():
        file_content = None
        if file_path.is_file():
            field_file = f'{case_0_folder}/{file_path.name}'

        with open(file_path, "r", encoding="utf-8") as file:
            file_content = file.read()
            a = 1

        # reference_files = find_reference_files_by_solver(field_file)

        correct_dimension_prompt =   f'''{config.general_prompts}
        Please check the dimension of the OpenFOAM field file {file_path.name} and correct it if the dimension is incorrect. The file content is: {file_content}.

        In your response: Absolutely AVOID any elements including but not limited to:
        - Markdown code block markers (``` or  ```)
        - Extra comments or explanations
        - Unnecessary empty lines or indentation
        '''

        qa = QA_NoContext_deepseek_V3()

        answer = qa.ask(correct_dimension_prompt)

        answer = file_writer.extract_pure_response(answer)

        try:
            file_writer.write_field_to_file(answer,file_path)
            print(f"write the file 0/{file_path.name}")

        except Exception as e:
            print(f"Errors occur during write_field_to_file: {e}")
        else: # 正确执行了场文件写入操作
            file_write_successful = True

def case_required_file2(solver_, turbulence_model_):
    config.case_solver = solver_
    config.case_turbulece_model = turbulence_model_
    other_physical_model = config.other_physical_model
    other_model_list = [
        "GRI", "TDAC", "LTS","common","Maxwell","Stokes"
    ]
    if other_physical_model not in other_model_list:
        other_physical_model = None

    # 寻找参考文件，并且根据仿真需求，选择case所需要的文件
    file_alternative = {}
    system_necessary = ["system/fvSolution","system/controlDict","system/fvSchemes","system/FOBilgerMixtureFraction"]
    for key,value in config.OF_case_data_dict.items():
        if config.case_solver == value["solver"] and config.case_turbulece_model == value["turbulence_model"]:
            
            if "other_physical_model" in value.keys():
                if not other_physical_model == value["other_physical_model"]:
                    continue

            file_filtered = []
            for file in value["configuration_files"].keys():
                if file != "":
                    if file.startswith("system/"): 
                        if file in system_necessary:
                            file_filtered.append(file)
                    else:
                        file_filtered.append(file)

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
                            if file in system_necessary:
                                file_filtered.append(file)
                        else:
                            file_filtered.append(file)

                case_name = key.split("/")[-1]
                file_alternative[case_name] = file_filtered

    add_file_prompt = f"""
    你是一个OpenFOAM专家，以下是仿真需求：{config.simulate_requirement}

    可选的参考算例和对应的文件列表如下：
    {file_alternative}

    1. 请你根据仿真需求，分析最符合仿真需求的文件列表，并返回对应参考算例名称。重点关注明确的参数设置要求，例如：如果仿真需求中明确要求了速度的初始条件设置，那么文件列表中必须包含0/U文件
    2. 如果没有合适的文件列表，给出一个最接近的参考算例名称。
    3. 如果每一个文件列表都极其不合适，请你返回“none”
    4. 请你以仅返回算例名称，不要返回解释、代表块标识等其他内容。
    """

    qa = QA_NoContext_deepseek_V3()
    answer = qa.ask(add_file_prompt).strip()
    if answer.lower() != "none":
        try:
            config.global_files = file_alternative[answer]

        except KeyError:
            print(f"参考算例名称错误: {answer}")
            answer = "none"
            
    if answer.lower() == "none":
        print("没有找到合适的参考算例，使用默认的文件列表")
        
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

