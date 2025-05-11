from sentence_transformers import SentenceTransformer
import torch
import json

"""
Repo directory: /home/hk/bge-base-en-v1.5
"""

# # Check AMD GPU availability
# print(f"GPU Available: {torch.cuda.is_available()}")
# print(f"GPU Name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")

# Load model with AMD optimization
# model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2', 
#                           device='cuda' if torch.cuda.is_available() else 'cpu')
# model = SentenceTransformer("/home/hk/bge-base-en-v1.5")
# model = SentenceTransformer("/home/hk/all-mpnet-base-v2")

# Test embeddings
sentences = [
    "Turbulence model: SST k-omega with wall functions",
    "Finite volume discretization using second-order upwind scheme",
    "Mesh independence study with 1.2 million hexahedral cells"
]

# tutorials_name = []
# with open("database_OFv24/discrete_case_config_with_descriptions.json", "r") as f:
#     tutorials_content = json.load(f)
#     for name, value in tutorials_content.items():
#         tutorials_name.append(name) 

# print(tutorials_name)

def extract_top_level_keys(json_str):
    decoder = json.JSONDecoder()
    index = 0
    keys = []
    
    while index < len(json_str):
        # 跳过空白字符
        while index < len(json_str) and json_str[index].isspace():
            index += 1
        if index >= len(json_str):
            break
        
        try:
            obj, end_index = decoder.raw_decode(json_str, idx=index)
            if isinstance(obj, dict):
                keys.extend(obj.keys())
            index = end_index
        except json.JSONDecodeError as e:
            print(f"JSON解析错误：{e}")
            break
    
    return keys

def get_configuration_files(json_str, target_key):
    """
    从包含多个JSON对象的字符串中提取指定键的configuration_files值
    
    参数:
        json_str (str): 原始JSON字符串
        target_key (str): 要查找的顶级键名
        
    返回:
        dict: 找到的configuration_files字典，未找到返回None
    """
    decoder = json.JSONDecoder()
    index = 0
    
    while index < len(json_str):
        # 跳过前导空白字符
        while index < len(json_str) and json_str[index].isspace():
            index += 1
        if index >= len(json_str):
            break
            
        try:
            # 解析当前JSON对象
            obj, end_index = decoder.raw_decode(json_str, idx=index)
            
            # 检查是否匹配目标键
            if isinstance(obj, dict) and target_key in obj:
                config_data = obj[target_key]["configuration_files"]
                
                # 验证数据结构
                if config_data is not None and isinstance(config_data, dict):
                    return config_data
                else:
                    print(f"警告：'{target_key}' 中未找到有效的 configuration_files")
                    return None
                    
            index = end_index  # 移动到下一个对象
            
        except json.JSONDecodeError as e:
            print(f"JSON解析错误：{e}")
            break
    
    print(f"错误：未找到键 '{target_key}'")
    return None

def retrieve_file(case_name, num = 1):
    """
    Args:
        case_name (str): 案例名称
        num (int): 返回的相似案例数量
    """
    # 加载数据
    with open("database_OFv24/discrete_case_config_with_descriptions.json", "r") as f:
        content = f.read()
    tutorials_name = extract_top_level_keys(content)

    model = SentenceTransformer("/home/hk/all-mpnet-base-v2")
    case_name_embedding = model.encode(case_name)
    tutorials_name_embedding = model.encode(tutorials_name)

    # 计算相似度
    similarities = []
    for i, tutorial_name_embedding in enumerate(tutorials_name_embedding):
        similarity = case_name_embedding @ tutorial_name_embedding.T  # 点积计算相似度
        similarities.append((tutorials_name[i], similarity))

    # 按相似度排序，取前 n 个
    similarities = sorted(similarities, key=lambda x: x[1], reverse=True)
    top_n_tutorials = [item[0] for item in similarities[:num]]


    tutorials_content = []
    for target in top_n_tutorials:
        # print(f"相似案例: {target}")

        config_files = get_configuration_files(content, target)
        reference_file = {target: config_files}

        tutorials_content.append(reference_file)
    
    return tutorials_content


# 测试函数
if __name__ == "__main__":
    # 测试
    case_name = "cylinder"
    num = 1
    result = retrieve_file(case_name, num)
    print(result)

