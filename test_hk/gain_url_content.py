import re
import requests
from bs4 import BeautifulSoup

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
        
        # 示例：提取所有段落文本
        paragraphs = [p.get_text(strip=True) for p in soup.find_all('p')]
        
        # 示例：提取标题
        title = soup.title.string if soup.title else 'No Title'
        
        # 方法一：提取所有可见文本，并去除其中的 HTML 标签和一些通常不可见的内容
        def get_all_visible_text(soup):
            [s.decompose() for s in soup(['style', 'script', 'head', 'meta', '[document]'])]
            return soup.get_text(separator='\n', strip=True)

        full_text = get_all_visible_text(soup)

        # # 方法二：智能段落检测
        # content_blocks = soup.find_all(['div', 'section', 'article'], class_=re.compile(r'content|body|main', re.I))
        # paragraphs = [block.get_text('\n', strip=True) for block in content_blocks]

        return {
            'title': title,
            'content': '\n'.join(paragraphs),
            'status': response.status_code,
            'full_text': full_text
        }
    except Exception as e:
        return {'error': str(e)}

# 使用示例
result = scrape_website("https://www.cfd-online.com/Forums/openfoam/260000-help-oversetmesh-2d-floating-object-simulation-openfoam-v2206.html")
print(result)



