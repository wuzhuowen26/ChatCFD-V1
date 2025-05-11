import os
import json
import requests
import re
from datetime import datetime

import config
from openai import OpenAI            
import tiktoken

# LLM 设置
API_KEY = "d28ed432-bb2d-4efe-971d-7041a7f924f6"
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
LLM_client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# 估计token
def estimate_tokens(text: str, model_name: str="deepseek-v3") -> int:
    """使用tiktoken估算token数量"""
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        # 如果模型未识别，默认使用cl100k_base（GPT-4的编码）
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

TOKEN_SEARCH = 0

# 获得LLM API的响应
def get_LLM_response(messages, model="deepseek-v3-250324", functions=None, function_call=None):
    try:
        response = LLM_client.chat.completions.create(
            model=model,
            messages=messages,
            functions=functions,
            function_call=function_call
        )
        answer = response.choices[0].message.content

        # 计算token数量
        global TOKEN_SEARCH
        TOKEN_SEARCH += estimate_tokens(json.dumps(messages, ensure_ascii=False))
        TOKEN_SEARCH += estimate_tokens(answer, model)
        return answer
    
    except Exception as e:
        print(f"调用LLM API时出错: {str(e)}")
        return None

# 判断是否为二维算例，并检查边界条件设置
def check_and_change_boundary(simulate_requirement = config.simulate_requirement, file_dir = config.OUTPUT_PATH):
    """
    Args:
        simulate_requirement (str): 模拟要求
        file_dir (str): 算例文件的根目录
    """

    file_path = file_dir + "/constant/polyMesh/boundary"   # boundary文件路径

    with open(file_path, "r") as f:
        boundary_content = f.read()

    # 判断是否为二维算例
    judge_prompt = f"""
        有一个计算流体力学算例的仿真需求为[[{simulate_requirement}]]，请你判断是否要进行二维算例的仿真？如果不是要进行二维算例的仿真，请你直接返回"No"，不用进入下面的判断。
        如果要进行二维算例，请你检查OpenFOAM的boundary文件内容[[{boundary_content}]]，其中是否有边界条件的type为"empty"，如果没有请你返回"Yes"，其余任何情况都返回“No”。

        注意：你只需要返回"Yes"或"No"，不需要解释，也不需要返回任何代码格式，比如:```。
    """
    judge_result = get_LLM_response([{"role": "user", "content": judge_prompt}], model="deepseek-r1-250120")

    # print(judge_result)

    # 检查是否需要修改边界条件
    if judge_result.strip() == "Yes":
        print("需要修改边界条件")
        change_prompt = f"""
            这是OpenFOAM的boundary文件内容[[{boundary_content}]]。这是一个二维算例，所以所有边界条件中必定有一个边界条件的type为"empty"。
            这是该算例的仿真需求[[{simulate_requirement}]]，请你根据该算例的仿真需求，判断哪一个边界条件的type应该为"empty"。
            请你修改错误的边界条件的type为"empty"，并返回修改后的boundary文件内容。
            注意：你只需要返回修改后的boundary文件内容，不需要解释，也不需要返回任何代码格式，比如:```。
        """
        boundary_content = get_LLM_response([{"role": "user", "content": change_prompt}])
        with open(file_path, "w") as f:
            f.write(boundary_content)

    extract_prompt = f"""
        这是OpenFOAM的boundary文件内容[[{boundary_content}]]，请你从中提取出所有的边界条件名称和他的type，并返回以下格式的字典：
        {{
            "boundary_conditions": [
                {{
                    "name": "边界条件名称",
                    "type": "边界条件类型"
                }},
                ...
            ]
        }}
        注意：你只需要返回字典，不需要解释，也不需要返回任何代码格式，比如:```。
    """

    config.boundary_name_and_type = get_LLM_response([{"role": "user", "content": extract_prompt}])

    # print(config.boundary_name_and_type)

    timestamp = datetime.now().isoformat()
    with open("spend_token/check_boundary_token.txt", "a", encoding="utf-8") as f:
        f.write(f"{timestamp} : {TOKEN_SEARCH}\n")

    return None


if __name__ == "__main__":
    # search_solution(error_info="#0 [2] Foam::error:: printStack(Foam::Ostream&)Foam::error:: printStack(Foam::Ostream&")

    dir = "CFD/cylinder"

    simlate_requirement = """
        case_name: CircularCylinder_Re3_6e6_URANS
        solver: pimpleFoam
        turbulence_model: kEpsilon
        other_physical_model: None
        case_specific_description: 2D_transient_simulation_of_flow_past_smooth_circular_cylinder_at_Re_3.6e6_using_URANS_approach_with_high-Re_k-epsilon_model_mesh_refined_around_cylinder_Courant_number_controlled_below_1_free-stream_velocity_3.6m/s_turbulence_intensity_3.22%
    """
    check_and_change_boundary(simlate_requirement, dir)
    print(config.boundary_name_and_type)
