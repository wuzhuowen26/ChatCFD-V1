import os
import json
import requests
import re
from bs4 import BeautifulSoup

from openai import OpenAI           
from duckduckgo_search import DDGS  # 利用duckduckgo进行网页搜索
from tavily import TavilyClient     # 为AI提供的网页搜索功能 (1000次/月) 
import tiktoken

# 代理设置（（使程序可以用VPN翻墙）
"""
ip -a 
127.0.0.1
export http_proxy=http://127.0.0.1:7897
export https_proxy=http://127.0.0.1:7897
echo $http_proxy
echo $https_proxy
curl -L www.duckduckgo.com
"""

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

# 网页连接测试
def test_connection(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print(f"成功连接到 {url}")
            return 1
        else:
            print(f"无法连接到 {url}, 状态码: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {str(e)}")

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

# 使用DuckDuckGo搜索
def search_duckduckgo(keywords, num_results=5):

    # # 测试连接
    # test_connection("https://duckduckgo.com/")

    if isinstance(keywords, list):
        search_term = " ".join(keywords)
    else:
        search_term = keywords

    with DDGS() as ddgs:
        results = list(ddgs.text(keywords=search_term, region="wt-wt", safesearch="on", max_results=num_results))

    # # 展示搜索结果
    # def print_search_results(results):
    #     for result in results:
    #         print(
    #             f"标题: {result['title']}\n链接: {result['href']}\n摘要: {result['body']}\n---")

    # print_search_results(results)

    return results  

# 使用Tavily搜索
def search_tavily(question):

    Tavily_client = TavilyClient("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")
    response = Tavily_client.search(query=question, max_results=5)

    # 获得网页链接
    urls = [result['url'] for result in response['results']]

    # 提取网页内容
    response = Tavily_client.extract(urls=urls[0])

    return response

# 抓取网页链接中的内容
def scrape_website(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        # 发送请求
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = response.apparent_encoding  # 自动检测编码
        response.raise_for_status()  # 检查HTTP错误

        # 解析内容
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 提取标题
        title = soup.title.string if soup.title else 'No Title'

        # # 方法一：提取所有段落文本
        # paragraphs = [p.get_text(strip=True) for p in soup.find_all('p')]
        # # 方法二：智能段落检测
        # content_blocks = soup.find_all(['div', 'section', 'article'], class_=re.compile(r'content|body|main', re.I))
        # paragraphs = [block.get_text('\n', strip=True) for block in content_blocks]

        # 提取所有可见文本，并去除其中的 HTML 标签和一些通常不可见的内容
        def get_all_visible_text(soup):
            [s.decompose() for s in soup(['style', 'script', 'head', 'meta', '[document]'])]
            return soup.get_text(separator='\n', strip=True)

        full_text = get_all_visible_text(soup)

        return {
            'title': title,
            # 'content': '\n'.join(paragraphs),
            'status': response.status_code,
            'full_text': full_text
        }
    except Exception as e:
        return {'error': str(e)}

# 收集网页内容
def search_web(refine_question, search_engine="duckduckgo"):
    """搜索引擎搜索
    Args:
        refine_question: 精炼后的问题
        search_engine: 搜索引擎类型
    Returns:
        raw_web_content: 搜索结果
    """

    if isinstance(refine_question, list):
        search_term = " ".join(refine_question)
    else:
        search_term = refine_question

    # 1. 搜索与问题相关的网页
    if search_engine == "duckduckgo":
        results = search_duckduckgo(search_term, 3)

        # 2. 获得网页链接
        urls = [result['href'] for result in results]

        # 3. 提取网页内容
        # print("url:",urls[0])
        raw_web_content = {}
        for url in urls:
            raw_web_content[url] = scrape_website(url)

    elif search_engine == "tavily":
        raw_web_content = search_tavily(search_term)

    else:
        raise ValueError("Only support the search engines: duckduckgo and tavily")

    return raw_web_content

# 获得算例文件的结构
def file_constructure(file_dir):
    """获得算例文件的结构，包含文件夹、文件及最多三层子目录内容
    Args:
        file_dir (str): 算例文件的根目录
    Returns:
        list: 文件结构树，格式为包含文件和目录嵌套结构的列表
    """
    def build_tree(current_dir, depth):
        """递归构建目录结构树"""
        structure = []
        # 添加当前目录下的所有文件
        for entry in os.scandir(current_dir):
            if entry.is_file():
                structure.append(entry.name)
        
        # 添加当前目录下的所有子目录（过滤以_开头的目录）
        for entry in os.scandir(current_dir):
            if entry.is_dir():
                dir_name = entry.name
                # 跳过以_开头的目录
                if dir_name.startswith("_"):        # 跳过dynamicCode中的“_xxsasxadassxa”目录
                    continue
                # 如果当前深度小于3，递归构建子目录结构
                if depth < 3:
                    subtree = build_tree(entry.path, depth + 1)
                else:
                    subtree = []  # 超过深度3的子目录不展开
                structure.append({dir_name: subtree})
        return structure

    # 从根目录开始构建，初始深度为0（根目录为第0层）
    return build_tree(file_dir, 0)

# 去除多余空格
def remove_whitespace_with_regex(text):
    # 替换多个空白字符（空格、换行、制表符等）为单个空格
    return re.sub(r'\s+', ' ', text).strip()

# 搜索，并由LLM整理网页内容
def organize_web_content(error_info: str):
    """整理网页内容
    Args:
        raw_web_content: 网页内容
    Returns:
        organized_content: 整理后的网页内容
    """
    # 1. 缩短要搜索的问题

    # messages = [
    #     {"role": "user", "content": "cfd online" + error_info[:20]}
    # ]
    # refine_question = get_LLM_response(messages)  

    refine_question = remove_whitespace_with_regex("cfd online" + error_info)[:200]
    # print("refine_question:", refine_question)

    # 2. 联网搜索相关内容
    print("正在搜索网页内容...")
    raw_web_content = search_web(refine_question, search_engine="duckduckgo")

    # 3. 清洗网页内容
    print("正在清洗网页内容...")
    clear_web_prompt = f"""
            Process the provided webpage content to extract error-resolution information related to '{error_info}'. Follow these steps:
            1. Remove ads, navigation menus, and irrelevant content.
            2. If multiple pages exist, prioritize the one with: 
            - Direct correlation to the error message
            - Actionable solutions (code examples/commands)
            3. Extract strictly these fields (skip missing ones):
            {{
                "url": "Original webpage URL",
                "title": "Page title reflecting error context",
                "error_msg": "Exact error message text matching '{error_info}'",
                "error_file": "Filename causing error (e.g., controlDict)",
                "file_content": "Relevant code/config snippets from the case",
                "user_description": "User's problem summary (1 sentence)",
                "solution": "Step-by-step fix (numbered list)",
                "advice": "Preventive measures (bullet points)",
                "other_information": "Any other information you think may be helpful in solving the error"
            }}
            Web content to process:
            {raw_web_content}
        """
    
    messages = [
        {"role": "user", "content": clear_web_prompt}
    ]

    organized_content = get_LLM_response(messages)
    # print(organized_content)
    
    return organized_content

# 根据网页内容生成建议
def search_solution(error_info: str, file_dir):
    """寻找报错解决办法
    Args:
        error: 报错信息，可以是问题描述、报错信息、代码片段等
        file_dir: 算例文件的根目录 
    Returns:
        advice: 解决建议
    """
    web_content = organize_web_content(error_info)

    # 4. 根据算例文件结构生成建议
    print("正在生成建议...")

    file_tree = file_constructure(file_dir)

    advice_prompt = f"""
        下面的网页内容是关于'{error_info}'报错问题的讨论、教学等。
        请你参考网页中的内容，以及文件结构'{file_tree}'，给出解决这个问题的建议，比如修改算例文件的哪些部分、添加哪些文件、修改哪些参数等。
        同时你要考虑网页中的内容是否足够可信，你可以结合自己的分析为大语言模型（没有视觉、不能调用ParaView等软件工具）提出建议，帮助大语言模型解决这个错误。
        仅返回改进建议，不要返回思考分析步骤、可信性分析等内容。
        网页内容：
        {web_content}
    """ 
    messages = [
        {"role": "user", "content": advice_prompt}
    ]

    # messages.append({"role": "user", "content": advice_prompt})

    advice = get_LLM_response(messages)
    return advice


if __name__ == "__main__":
    # search_solution(error_info="#0 [2] Foam::error:: printStack(Foam::Ostream&)Foam::error:: printStack(Foam::Ostream&")

    dir = "../CFD/cylinder"
    error_info = """
        --> FOAM FATAL ERROR: 
        Inconsistent number of faces between block pair 2 and 12

            From function void Foam::blockMesh::calcMergeInfo()
            in file blockMesh/blockMeshMerge.C at line 222.
        """

    advice = search_solution(error_info, dir)
    print("建议：", advice)
    print("消耗token数量：", TOKEN_SEARCH)

    # question = remove_whitespace_with_regex("cfd online" + error_info)
    # print(question[:200])
    # results = search_duckduckgo(question)
    # print(results)