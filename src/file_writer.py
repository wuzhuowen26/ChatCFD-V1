import config
import shutil
import os

from qa_modules import QA_NoContext_deepseek_V3,QA_NoContext_deepseek_R1
from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile

import json
import re

def extract_content_in_brackets(text, indicator_string):
    # double brackets
    pattern = fr'{indicator_string} \[\[(.*?)\]\]'
    matches = re.findall(pattern, text, re.DOTALL)
    return [m.strip() for m in matches]

def extract_foamfile_content(input_string, indicator_string):
    start_tag = r"\\Start_" + indicator_string
    end_tag = r"\\End_" + indicator_string
    
    # 使用正则表达式来找到所有的匹配项
    pattern = re.compile(f"{start_tag}(.*?){end_tag}", re.DOTALL)
    matches = pattern.findall(input_string)
    
    # 过滤出包含 "FoamFile" 的内容
    foamfile_matches = [match for match in matches if 'FoamFile' in match]
    
    if len(foamfile_matches) == 0:
        return "没有找到包含 'FoamFile' 的内容"
    elif len(foamfile_matches) > 1:
        return "错误：找到多个包含 'FoamFile' 的内容"
    else:
        return foamfile_matches[0]
    
def extract_pure_response(text):
    # 使用正则表达式匹配所有内容（包括换行符）
    pattern = r"Here is my response:(.*?)(?=$|\Z)"
    match = re.search(pattern, text, re.DOTALL)
    
    if match:
        # 去除首尾空白字符
        return match.group(1).strip()
    return ""

def remove_functions_blocks(text):
    pattern = r'functions\s*\{.*?\}'
    return re.sub(pattern, '', text, flags=re.DOTALL)

def write_field_to_file(field_file_content, output_file_name):
    # 转义处理（处理\n和特殊符号）
    processed_content = field_file_content.encode('latin-1').decode('unicode_escape')

    directory = os.path.dirname(output_file_name)

    if directory and not os.path.exists(directory):
        os.makedirs(directory)

    # 写入文件（推荐使用与object字段对应的文件名）
    with open(output_file_name, 'w', encoding='utf-8') as f:  # 文件名根据object字段建议使用"U"
        f.write(processed_content)

# 1. 从物理模型、求解器，判断需要写哪些constant文件；
# 2. 参考相应的constant文件，写文件
def copy_folder(source_folder, destination_folder):
    """
    Copy a folder and its contents from source_folder to destination_folder with specific exclusions.

    :param source_folder: Path to the source folder.
    :param destination_folder: Path to where the folder should be copied.
    :return: None
    """
    # 如果目标文件夹不存在，则创建它
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    destination_path = os.path.join(destination_folder, os.path.basename(source_folder))

    try:
        for root, dirs, files in os.walk(source_folder):
            # 相对路径，用于在目标文件夹中构建相同的结构
            rel_path = os.path.relpath(root, source_folder)
            for dir in dirs:
                if os.path.join(rel_path, dir).startswith('constant/polyMesh'):
                    dirs.remove(dir)  # 不拷贝 constant/polyMesh 下的文件夹
            new_root = os.path.join(destination_path, rel_path)
            os.makedirs(new_root, exist_ok=True)
            
            for file in files:
                source_file = os.path.join(root, file)
                dest_file = os.path.join(new_root, file)
                
                # 检查文件大小是否超过 25k (25 * 1024 字节)
                if os.path.getsize(source_file) > 25 * 1024:
                    print(f"跳过文件 {source_file} 因为其大小超过 25k")
                    continue
                
                # 不拷贝 .msh 文件
                if file.endswith('.msh'):
                    print(f"跳过文件 {source_file} 因为其是 .msh 文件")
                    continue

                shutil.copy2(source_file, dest_file)
                print(f"成功拷贝文件 {source_file} 到 {dest_file}")

        print(f"成功将 {source_folder} 拷贝到 {destination_folder}")
    except shutil.Error as e:
        print(f"拷贝文件夹时出错: {e}")
    except OSError as e:
        print(f"创建目录或拷贝文件时出错: {e.strerror}")

def analyze_running_error(running_error):

    str_global_files = ", ".join(config.global_files)

    analyze_running_error_prompt = f'''{config.general_prompts}
    Examine the following error encountered while running an OpenFOAM case, and determine which file needs revision to correct the error. The candidate files are {str_global_files}.
    - Indicate the file requiring revision with File_for_revision [[file_name]], where file_name within the double brackets is the exact file needing changes.
    - Provide your recommendations for correcting the file with Advice_for_revision [[actual_advices]], where actual_advices within the double brackets are specific suggestions to fix the error
    
    The error is {running_error}.
    '''
    
    async_qa = QA_NoContext_deepseek_V3()

    answer = async_qa.ask(analyze_running_error_prompt)

    pure_response = extract_pure_response(answer)

    file_for_revision = extract_content_in_brackets(pure_response, "File_for_revision")[0]

    advices_for_revision = extract_content_in_brackets(pure_response, "Advice_for_revision")[0]

    config.global_file_requirement[file_for_revision]['correction_advice'] = advices_for_revision

    return file_for_revision

def draft_case_file_2(file_name, file_setup=""):
    # file_name: name of the target file, including 0/*, constant/*, system/*
    # file_setup: setup of this file
    # running error

    print(f"preparing {file_name}")

    # field_dimension = ""

    # 1. assemble reference contents for this file
    reference_contents = ""
    for case in config.best_reference_cases:
        case_path = f"{config.of_tutorial_dir}/{case['name']}"

        # 0/* files
        if file_name.split('/')[0] == "0":
            case_content = find_best_reference_cases_2.find_reference_files(file_name,case['name'])
            # if field_dimension == "":
            #     pattern = r"dimensions\s+(\[[^\]]*\])\s*;"
            #     match = re.search(pattern, case_content)
            #     field_dimension = match.group(1)
            if case_content is not None:
                reference_contents += "{"+ case_content + "}, \n"

        # turbulence setups, 需要turbulence_type和turbulence_model都被该算例match到
        elif file_name == "constant/turbulenceProperties":
            for matched_keywords in case['finding_matches']:
                if matched_keywords in config.global_OF_keywords['turbulence_type']:
                    for matched_keywords2 in case['finding_matches']:
                        if matched_keywords2 in config.global_OF_keywords['turbulence_model']:
                            case['turbulence_setup_file'] = case[matched_keywords]
                            case_content = find_best_reference_cases_2.find_reference_files(file_name,case['name'])
                            if case_content is not None:
                                reference_contents += "{"+ case_content + "}, \n"

        # transportProperties
        elif file_name == "constant/transportProperties":
            case_content = find_best_reference_cases_2.find_reference_files(file_name,case['name'])
            if case_content is not None:
                reference_contents += "{"+ case_content + "}, \n"

        # controlDict, 需要solver被该算例match
        elif file_name == "system/controlDict":
            for matched_keywords in case['finding_matches']:
                if matched_keywords in config.global_OF_keywords['solver']:
                    case_content = find_best_reference_cases_2.find_reference_files(file_name,case['name'])

                    # 删除functions{}结构，即算例特定的后处理方法
                    no_function_block_content = remove_functions_blocks(case_content)
                    reference_contents += "{"+ no_function_block_content + "}, \n"

        # fvSchemes，先尝试提供全部参考算例的fvSchemes(later)
        elif file_name == "system/fvSchemes":
            case_content = find_best_reference_cases_2.find_reference_files(file_name,case['name'])
            if case_content is not None:
                reference_contents += "{"+ case_content + "}, \n"

        # fvSolution，先尝试提供全部参考算例的fvSolution
        elif file_name == "system/fvSolution":
            case_content = find_best_reference_cases_2.find_reference_files(file_name,case['name'])
            if case_content is not None:
                reference_contents += "{"+ case_content + "}, \n"

        # decomposeParDict
        elif file_name == "system/decomposeParDict":
            case_content = find_best_reference_cases_2.find_reference_files(file_name,case['name'])
            if case_content is not None:
                reference_contents += "{"+ case_content + "}, \n"

        else:
            case_content = find_best_reference_cases_2.find_reference_files(file_name,case['name'])
            if case_content is not None:
                reference_contents += "{"+ case_content + "}, \n"
            # print(f"the file_name {file_name} is not supported by draft_case_file_2.")

    file_format_correct = False

    write_file_prompt = ""

    # for the 0/* field files
    if file_name.split('/')[0] == "0":

        write_file_prompt = f'''{config.general_prompts}
        Please draft the {file_name} file for OpenFOAM to strictly adhere to the following CFD setup conditions and running errors.
        If the CFD setup is empty, draft the file by referring to the referenced files.
        
        - Enclose the contents of the field file within `\Start_file contents_of_the_file \End_file`, where contents_of_the_file endclosed by the \Start_file and \End_file represents the actural contrents in the file you have drafted.
       
        - After drafting, **review the file at least three times** to:
            1. Ensure the contents of the files is given as `\Start_file contents_of_the_file \End_file`
            2. Ensure the dimension is set as the same with the reference files.
            3. Ensure no boundary conditions or other setup parameters are missed or incorrectly specified.
            4. Confirm no additional, unintended boundary conditions or parameters are added to the field file.
            5. Verify the accuracy and completeness of all included conditions.
        
        The CFD setup conditions are as follows: {file_setup}.

        The reference contents are as follows: {reference_contents}
        '''

    # for other setups
    else:

        write_file_prompt = f'''{config.general_prompts}
        Please draft the {file_name} file for OpenFOAM to strictly adhere to the following CFD setup conditions and running errors.
        If the CFD setup is empty, draft the file by referring to the referenced files.
        
        - Enclose the contents of the field file within `\Start_file contents_of_the_file \End_file`, where contents_of_the_file endclosed by the \Start_file and \End_file represents the actural contrents in the file you have drafted.
   
        - After drafting, **review the file at least three times** to:
            1. Ensure the contents of the files is given as `\Start_file contents_of_the_file \End_file`
            2. Ensure the dimension is set as the same with the reference files.
            3. Verify the accuracy and completeness of all included conditions.
        
        The CFD setup conditions are as follows: {file_setup}.

        The reference contents are as follows: {reference_contents}
        '''

    async_qa = QA_NoContext_deepseek_V3()

    check_correctness = False

    # ensure the file_format is correct
    while not file_format_correct or not check_correctness:

        answer = async_qa.ask(write_file_prompt)
        
        pure_response = extract_pure_response(answer)

        # 从这里就开始try
        # file_content = extract_content_in_brackets(pure_response, 'Draft_file')

        file_content = extract_foamfile_content(pure_response, 'file')

        file_content_dimensions_corrected = file_content
        
        # if file_name.split('/')[0] == "0":
        #     # forced correction of field dimensions
        #     try:
        #         pattern = r"(dimensions\s+)(\[[^\]]*\])\s*;"
        #         replacement = rf"\g<1>{field_dimension};"
        #         file_content_dimensions_corrected = re.sub(pattern, replacement, file_content)
        #     except Exception as e:
        #         print(f"Errors occur in forced dimension correction: {e}")
        #         continue

        if file_name.split('/')[0] == "0":
            async_qa_check_correctness = QA_NoContext_deepseek_V3()
        
            check_field_prompt = f'''
                Your task is to verify whether the OpenFOAM field file matches the specified field setups, including boundary names and boundary types.

                ### Input:
                1. **OpenFOAM Field File**:
                {file_content_dimensions_corrected}

                2. **Field Setups**:
                {file_setup}

                ### Output:
                - If the field file fully agrees with the setups, answer `yes`.
                - If there are any discrepancies (e.g., unmatched boundary names or types), answer `no`.

                ### Notes:
                - You must only respond with `yes` or `no`. Do not provide additional explanations.
            '''

            check_correctness_anwser = async_qa_check_correctness.ask(check_field_prompt)

            if check_correctness_anwser == "yes":
                check_correctness = True
            else:
                continue

        else:
            check_correctness = True


        output_file = f"{config.OUTPUT_PATH}/{file_name}"

        try:
            write_field_to_file(file_content_dimensions_corrected,output_file)
            print(f"write the file {file_name}")

        except Exception as e:
            print(f"Errors occur during write_field_to_file: {e}")
            continue
        else: # 正确执行了场文件写入操作
            file_format_correct = True

def correct_case_file(file_name, file_setup="", correction_advice=""):
    # file_name: name of the target file, including 0/*, constant/*, system/*
    # file_setup: setup of this file
    # running error

    print(f"correcting {file_name}")

    file_content = None
    file_path = f'{config.OUTPUT_PATH}/{file_name}'

    with open(file_path, "r", encoding="utf-8") as file:
        file_content = file.read()

    # field_dimension = ""

    # 1. assemble reference contents for this file
    reference_contents = ""
    for case in config.best_reference_cases:
        case_path = f"{config.of_tutorial_dir}/{case['name']}"

        # 0/* files
        if file_name.split('/')[0] == "0":
            case_content = find_best_reference_cases_2.find_reference_files(file_name,case['name'])
            # if field_dimension == "":
            #     pattern = r"dimensions\s+(\[[^\]]*\])\s*;"
            #     match = re.search(pattern, case_content)
            #     field_dimension = match.group(1)
            if case_content is not None:
                reference_contents += "{"+ case_content + "}, \n"

        # turbulence setups, 需要turbulence_type和turbulence_model都被该算例match到
        elif file_name == "constant/turbulenceProperties":
            for matched_keywords in case['finding_matches']:
                if matched_keywords in config.global_OF_keywords['turbulence_type']:
                    for matched_keywords2 in case['finding_matches']:
                        if matched_keywords2 in config.global_OF_keywords['turbulence_model']:
                            case['turbulence_setup_file'] = case[matched_keywords]
                            case_content = find_best_reference_cases_2.find_reference_files(file_name,case['name'])
                            if case_content is not None:
                                reference_contents += "{"+ case_content + "}, \n"

        # transportProperties
        elif file_name == "constant/transportProperties":
            case_content = find_best_reference_cases_2.find_reference_files(file_name,case['name'])
            if case_content is not None:
                reference_contents += "{"+ case_content + "}, \n"

        # controlDict, 需要solver被该算例match
        elif file_name == "system/controlDict":
            for matched_keywords in case['finding_matches']:
                if matched_keywords in config.global_OF_keywords['solver']:
                    case_content = find_best_reference_cases_2.find_reference_files(file_name,case['name'])

                    # 删除functions{}结构，即算例特定的后处理方法
                    no_function_block_content = remove_functions_blocks(case_content)
                    reference_contents += "{"+ no_function_block_content + "}, \n"

        # fvSchemes，先尝试提供全部参考算例的fvSchemes(later)
        elif file_name == "system/fvSchemes":
            case_content = find_best_reference_cases_2.find_reference_files(file_name,case['name'])
            if case_content is not None:
                reference_contents += "{"+ case_content + "}, \n"

        # fvSolution，先尝试提供全部参考算例的fvSolution
        elif file_name == "system/fvSolution":
            case_content = find_best_reference_cases_2.find_reference_files(file_name,case['name'])
            if case_content is not None:
                reference_contents += "{"+ case_content + "}, \n"

        else:
            print(f"the file_name {file_name} is not supported by draft_case_file_2.")

    file_format_correct = False

    write_file_prompt = ""

    # for the 0/* field files
    if file_name.split('/')[0] == "0":

        write_file_prompt = f'''{config.general_prompts}
        Please correct the {file_name} file for OpenFOAM to strictly adhere to the following CFD setup conditions and the correction advice.
        The incorrect file content is: {file_content}.
        The correction advice is as follows: {correction_advice}.
        The CFD setup conditions are as follows: {file_setup}.
        The reference files are as follows: {reference_contents}
        
        - Enclose the contents of the field file within `\Start_file contents_of_the_file \End_file`, where contents_of_the_file endclosed by the \Start_file and \End_file represents the actural contrents in the file you have drafted.
       
        - After drafting, **review the file at least three times** to:
            1. Ensure the contents of the files is given as `\Start_file contents_of_the_file \End_file`
            2. Ensure the dimension is set as the same with the reference files.
            3. Ensure no boundary conditions or other setup parameters are missed or incorrectly specified.
            4. Confirm no additional, unintended boundary conditions or parameters are added to the field file.
            5. Verify the accuracy and completeness of all included conditions.
        '''

    # for other setups
    else:

        write_file_prompt = f'''{config.general_prompts}
        Please correct the {file_name} file for OpenFOAM to strictly adhere to the following CFD setup conditions and the correction advice.
        The incorrect file content is: {file_content}.
        The correction advice is as follows: {correction_advice}.
        The CFD setup conditions are as follows: {file_setup}.
        The reference files are as follows: {reference_contents}

        If the CFD setup is empty, draft the file by referring to the referenced files.
        
        - Enclose the contents of the field file within `\Start_file contents_of_the_file \End_file`, where contents_of_the_file endclosed by the \Start_file and \End_file represents the actural contrents in the file you have drafted.
   
        - After drafting, **review the file at least three times** to:
            1. Ensure the contents of the files is given as `\Start_file contents_of_the_file \End_file`
            2. Ensure the dimension is set as the same with the reference files.
            3. Verify the accuracy and completeness of all included conditions.
        '''

    async_qa = QA_NoContext_deepseek_V3()

    check_correctness = False

    # ensure the file_format is correct
    # while not file_format_correct or not check_correctness:
    while not file_format_correct:

        answer = async_qa.ask(write_file_prompt)
        
        pure_response = extract_pure_response(answer)

        # 从这里就开始try
        # file_content = extract_content_in_brackets(pure_response, 'Draft_file')

        file_content = extract_foamfile_content(pure_response, 'file')

        file_content_dimensions_corrected = file_content

        # if file_name.split('/')[0] == "0":
        #     async_qa_check_correctness = QA_NoContext_deepseek_V3()
        
        #     check_field_prompt = f'''
        #         Your task is to verify whether the OpenFOAM field file matches the specified field setups including boundary names and boundary types.

        #         ### Input:
        #         1. **OpenFOAM Field File**:
        #         {file_content_dimensions_corrected}

        #         2. **Field Setups**:
        #         {file_setup}

        #         ### Output:
        #         - If the field file fully agrees with the setups, answer `yes`.
        #         - If there are any discrepancies (e.g., unmatched boundary names or types), answer `no`.

        #         ### Notes:
        #         - You must only respond with `yes` or `no`. Do not provide additional explanations.
        #     '''

        #     check_correctness_anwser = async_qa_check_correctness.ask(check_field_prompt)

        #     if check_correctness_anwser == "yes":
        #         check_correctness = True
        #     else:
        #         continue

        # else:
        #     async_qa_check_correctness = QA_NoContext_deepseek_V3()
            
        #     check_file_prompt = f'''
        #         Your task is to verify whether the OpenFOAM case file have been corrected to solve the reported error.
        #         - Before correction, the file content is: {file_content}.
        #         - After correction, the file content is: {file_content_dimensions_corrected}.
        #         - The reported error is: {running_error}.
        #         - The case

        #         ### Input:
        #         1. **OpenFOAM Field File**:
        #         {file_content_dimensions_corrected}

        #         2. **Field Setups**:
        #         {file_setup}

        #         ### Output:
        #         - If the field file fully agrees with the setups, answer `yes`.
        #         - If there are any discrepancies (e.g., unmatched boundary names or types), answer `no`.

        #         ### Notes:
        #         - You must only respond with `yes` or `no`. Do not provide additional explanations.
        #     '''

        #     check_correctness = True

        output_file = f"{config.OUTPUT_PATH}/{file_name}"

        try:
            write_field_to_file(file_content_dimensions_corrected,output_file)
            print(f"write the file {file_name}")

        except Exception as e:
            print(f"Errors occur during write_field_to_file: {e}")
            continue
        else: # 正确执行了场文件写入操作
            file_format_correct = True

def revise_R1_config_file_to_reference_case_files(file_name, original_file=""):
    # file_name: name of the target file, including 0/*, constant/*, system/*
    # file_setup: setup of this file
    # running error

    print(f"revising early R1 result {file_name} according to reference files")

    # field_dimension = ""

    # 1. assemble reference contents for this file
    reference_contents = ""
    for case in config.best_reference_cases:
        case_path = f"{config.of_tutorial_dir}/{case['name']}"

        # 0/* files
        if file_name.split('/')[0] == "0":
            case_content = find_best_reference_cases_2.find_reference_files(file_name,case['name'])
            if case_content is not None:
                reference_contents += "{"+ case_content + "}, \n"

        # turbulence setups, 需要turbulence_type和turbulence_model都被该算例match到
        elif file_name == "constant/turbulenceProperties":
            for matched_keywords in case['finding_matches']:
                if matched_keywords in config.global_OF_keywords['turbulence_type']:
                    for matched_keywords2 in case['finding_matches']:
                        if matched_keywords2 in config.global_OF_keywords['turbulence_model']:
                            case['turbulence_setup_file'] = case[matched_keywords]
                            case_content = find_best_reference_cases_2.find_reference_files(file_name,case['name'])
                            if case_content is not None:
                                reference_contents += "{"+ case_content + "}, \n"

        # transportProperties
        elif file_name == "constant/transportProperties":
            case_content = find_best_reference_cases_2.find_reference_files(file_name,case['name'])
            if case_content is not None:
                reference_contents += "{"+ case_content + "}, \n"

        # controlDict, 需要solver被该算例match
        elif file_name == "system/controlDict":
            for matched_keywords in case['finding_matches']:
                if matched_keywords in config.global_OF_keywords['solver']:
                    case_content = find_best_reference_cases_2.find_reference_files(file_name,case['name'])

                    # 删除functions{}结构，即算例特定的后处理方法
                    no_function_block_content = remove_functions_blocks(case_content)
                    reference_contents += "{"+ no_function_block_content + "}, \n"

        # fvSchemes，先尝试提供全部参考算例的fvSchemes(later)
        else:
            case_content = find_best_reference_cases_2.find_reference_files(file_name,case['name'])
            if case_content is not None:
                reference_contents += "{"+ case_content + "}, \n"

    file_format_correct = False

    write_file_prompt = ""

    turbulence_model = "laminar"
    if config.case_turbulece_model is not None:
        turbulence_model = config.case_turbulece_model

    # for the 0/* field files

    write_file_prompt = f'''{config.general_prompts}
    You are an OpenFOAM expert assistant. Adjust the following case file to optimize simulation stability. 
    - You MUST NOT change any name of the the initial conditions, boundary conditions, or physical properties. 
    - You MUST NOT change any value of the the initial conditions, boundary conditions, or physical properties. 
    - If the {file_name} is 0/* format, you must ensure the dimension show in the file correctly, and the dimension agrees with the reference file.
    - If a boundary type in the refernce file is the same with the original file, revise the boundary of the original file to have all entries of the boundary type description in the reference file.
    - If the fluid is not specified, assume the fluid is air.

    **The orginal file contents requires adjustment**: [[[ {original_file} ]]]

    **The reference file** are some files found in OpenFOAM tutorial cases with same or similar solvers.  The reference file contents are: [[[ {reference_contents} ]]]


    - Enclose the contents of the file within `\Start_file contents_of_the_file \End_file`, where contents_of_the_file endclosed by the \Start_file and \End_file represents the actural contrents in the file you have drafted.

    - After drafting, **review the file at least three times** to:
        1. Ensure the contents of the files is given as `\Start_file contents_of_the_file \End_file`
        2. Ensure the dimension is set as the same with the reference files.
        3. Verify the accuracy and completeness of all included conditions.
    '''

    async_qa = QA_NoContext_deepseek_V3()

    # ensure the file_format is correct
    while not file_format_correct:

        answer = async_qa.ask(write_file_prompt)
        
        pure_response = extract_pure_response(answer)

        # 从这里就开始try
        # file_content = extract_content_in_brackets(pure_response, 'Draft_file')

        file_content = extract_foamfile_content(pure_response, 'file')

        output_file = f"{config.OUTPUT_PATH}/{file_name}"

        config.global_files[file_name] = file_content

        try:
            write_field_to_file(file_content,output_file)
            print(f"write the file {file_name}")

        except Exception as e:
            print(f"Errors occur during write_field_to_file: {e}")
            continue
        else: # 正确执行了场文件写入操作
            file_format_correct = True