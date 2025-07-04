import pdfplumber
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from openai import OpenAI
from pdfplumber.utils import within_bbox
import re
import tiktoken
from datetime import datetime
import qa_modules, config, os

import config

class CFDCaseExtractor:
    # def __init__(self, model_name='sentence-transformers/all-mpnet-base-v2'):
    def __init__(self, model_name=config.sentence_transformer_path):
        self.embedder = SentenceTransformer(model_name)
        self.client = OpenAI(
            api_key=os.environ.get("DEEPSEEK_R1_KEY"), 
            base_url=os.environ.get("DEEPSEEK_R1_BASE_URL")
        )
        self.gpt_model = os.environ.get("DEEPSEEK_R1_MODEL_NAME")
        self.index = None
        self.chunks = []
        self.token_usage = []  # 新增Token统计存储
        self.encoder = tiktoken.encoding_for_model("gpt-4")

    def process_pdf(self, file_path):
        """优化后的PDF处理流程（修复bbox错误）"""
        with pdfplumber.open(file_path) as pdf:
            text_blocks = []
            for i, page in enumerate(pdf.pages):
                # 定义有效的文本区域（单位：点）
                bbox = (
                    50,  # left margin
                    50,  # top margin (跳过页眉)
                    page.width - 50,  # right margin
                    page.height - 50  # bottom margin (跳过页脚)
                )
                
                # 创建过滤函数（关键修复）
                crop_filter = lambda obj: (
                    obj["x0"] >= bbox[0] and
                    obj["top"] >= bbox[1] and
                    obj["x1"] <= bbox[2] and
                    obj["bottom"] <= bbox[3]
                )
                
                # 应用区域过滤
                cropped_page = page.filter(crop_filter)
                
                # 优化文本提取参数
                text = cropped_page.extract_text(
                    layout=True,
                    x_tolerance=3,
                    y_tolerance=2,
                    keep_blank_chars=False,
                    extra_attrs=["size", "fontname"]
                )
                
                # 文本清洗
                cleaned_text = self.clean_text(text, page_number=i+1)
                if cleaned_text:
                    text_blocks.append(cleaned_text)
        
        # 4. 智能分块策略
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=600,
            chunk_overlap=100,
            separators=[
                r"\n\s*[A-Z][A-Z\s]+\s*:\s*\n",  # 匹配标题如 "METHODOLOGY:"
                r"\n\s*\d+\.\s*[A-Z]",          # 匹配章节号如 "3. RESULTS"
                "\n\n"
            ]
        )
        self.chunks = splitter.split_text("\n".join(text_blocks))
        
        # 过滤空块和短文本
        self.chunks = [chunk for chunk in self.chunks 
                    if len(chunk.strip()) > 50]
        
        # Create FAISS index
        embeddings = self.embedder.encode(self.chunks, 
                                        convert_to_numpy=True,
                                        show_progress_bar=False)
        embeddings = np.array(embeddings).astype('float32')
        
        self.index = faiss.IndexFlatL2(embeddings.shape[1])
        self.index.add(embeddings)
        

    def clean_text(self, text, page_number):
        """多阶段文本清洗"""
        # 阶段1：合并断词
        text = re.sub(r'(?<=\w)-\n(?=\w)', '', text)  # 连接被换行分割的单词
        
        # 阶段2：处理数字和单位
        text = re.sub(r'\n(?=\d+\s*[A-Za-z]{1,3}\b)', ' ', text)  # 单位换行修复
        
        # 阶段3：移除孤立页码
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
        
        # 阶段4：压缩空白
        text = re.sub(r'\n{3,}', '\n\n', text)  # 多个换行压缩为两个
        text = re.sub(r'[ \t]{2,}', ' ', text)   # 多个空格压缩为一个
        
        # 阶段5：过滤小段文本（可能为图表标注）
        lines = [line.strip() for line in text.split('\n') if len(line.strip()) > 3]
        
        # 添加页面元数据
        return f"Page {page_number}:\n" + "\n".join(lines) if lines else ""

    def _count_tokens(self, text):
        """使用Tiktoken精确计算Token"""
        return len(self.encoder.encode(text))

    def query_case_setup(self, question, top_k=3, context = False):
        """带Token统计的增强版查询方法"""
        try:
            # 初始化请求记录
            request_entry = {
                "timestamp": datetime.now().isoformat(),
                "question": question,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "status": "success",
                "error": None
            }

            if not self.index:
                raise ValueError("请先使用process_pdf处理PDF文档")

            # 语义检索阶段
            query_embed = self.embedder.encode([question])
            distances, indices = self.index.search(query_embed, top_k)
            relevant_chunks = [self.chunks[i] for i, d in zip(indices[0], distances[0]) if d < config.pdf_chunk_d]

            # 记录上下文Token消耗
            context_tokens = sum(self._count_tokens(chunk) for chunk in relevant_chunks)
            request_entry["context_tokens"] = context_tokens  # 新增上下文Token统计

            if not relevant_chunks:
                request_entry["status"] = "empty"
                self.token_usage.append(request_entry)
                return "未找到相关CFD配置信息"
            
            prompt = f'''You are a CFD expert assistant. Extract technical parameters from research papers and structure answers in markdown tables.
            Analyze these CFD paper excerpts:
            [[[ {relevant_chunks} ]]]
            Extract specific details about: [[[ {question} ]]] 
            '''

            qa = None

            if context == True:
                qa = qa_modules.QA_Context_deepseek_R1()
            else:
                qa = qa_modules.QA_NoContext_deepseek_R1()

            R1_response = qa.ask(prompt)

            return R1_response

        except Exception as e:
            request_entry.update({
                "status": "failed",
                "error": str(e)
            })
            self.token_usage.append(request_entry)
            return f"处理异常: {str(e)}"
    
    
    # def _validate_response(self, response):
    #     """Ensure response contains key CFD parameters"""
    #     required_terms = [
    #         'mesh', 'boundary', 'turbulence', 
    #         'solver', 'discretization'
    #     ]
    #     if not any(term in response.lower() for term in required_terms):
    #         return "Incomplete CFD details found. Consider refining your query with:\n" \
    #                "- Specific parameters of interest\n" \
    #                "- Section references from the paper\n" \
    #                "- Comparison requests between multiple setups"
    #     return response

def main():
    # Usage Example
    Case_PDF = "/home/fane/MetaOpenFOAM_path/CFD_LLM_Bots/pdf/Yu_2023_nozzle.pdf"

    extractor = CFDCaseExtractor()
    extractor.process_pdf(Case_PDF)
    for chunk_content in extractor.chunks:
        print(chunk_content)

# main()