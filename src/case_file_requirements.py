import json
import config
import re

def extract_boundary_names(filename):
    """
    从fluent.msh网格文件中提取边界条件名称
    参数：
        filename (str): 要处理的文本文件路径
    返回：
        list: 过滤后的结果列表
    """
    # 读取文件内容
    with open(filename, 'r') as f:
        content = f.read().splitlines()

    # 寻找起始点
    start_index = -1
    for i in range(len(content)-1, -1, -1):  # 从后往前找起始行
        if content[i].strip() == '(0 "Zone Sections")':
            start_index = i
            break

        if content[i].strip().startswith('4 4 4 4 4 4 4 4 4'):
            start_index = i
            break
    
    if start_index == -1:
        return []

    # 提取相关行
    pattern = re.compile(r'\(\d+\s+\(\d+\s+\S+\s+(\S+)\)\(\)\)')
    results = []
    
    # 处理每行数据
    for line in content[start_index+1:]:
        line = line.strip()
        if not line.startswith('(39'):
            continue
            
        match = pattern.match(line)
        if match:
            value = match.group(1)
            # 过滤*_FLUID和*_SOLID
            if not re.search(r'^(FLUID|\w+?_FLUID|\w+?_SOLID)$', value):
                results.append(value)
    
    config.case_boundaries = results
