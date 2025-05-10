from openai import OpenAI
import os
import config
from datetime import datetime
import tiktoken
import json

def estimate_tokens(text: str, model_name: str) -> int:
    """使用tiktoken估算token数量"""
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        # 如果模型未识别，默认使用cl100k_base（GPT-4的编码）
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

class GlobalLogManager:
    _instance = None
    logs = []
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def _save_case_log(cls):
        if config.case_log_write:
            config.ensure_directory_exists(config.OUTPUT_PATH)
            log_file_path = f'{config.OUTPUT_PATH}/all_qa_logs.json'
            with open(log_file_path, 'w', encoding='utf-8') as f:
                json.dump(cls.logs, f, ensure_ascii=False, indent=2)

    @classmethod
    def add_log(cls, log_entry):
        cls.logs.append(log_entry)
        cls._save_case_log()
    
    @classmethod
    def _generate_statistics(cls):
        stats = {
            "deepseek-v3": {
                "total_calls": 0,
                "total_prompt_tokens": 0,
                "total_response_tokens": 0
            },
            "deepseek-r1": {
                "total_calls": 0,
                "total_prompt_tokens": 0,
                "total_response_tokens": 0,
                "total_reasoning_tokens": 0
            }
        }
        
        for log in cls.logs:
            model_type = log["model_type"]
            if model_type == "deepseek-v3":
                stats[model_type]["total_calls"] += 1
                stats[model_type]["total_prompt_tokens"] += log["prompt_tokens"]
                stats[model_type]["total_response_tokens"] += log["response_tokens"]
            elif model_type == "deepseek-r1":
                stats[model_type]["total_calls"] += 1
                stats[model_type]["total_prompt_tokens"] += log["prompt_tokens"]
                stats[model_type]["total_response_tokens"] += log["response_tokens"]
                stats[model_type]["total_reasoning_tokens"] += log["reasoning_tokens"]
        
        return stats
    
    @classmethod
    def save_logs(cls, log_file="all_qa_logs.json", stats_file=None):
        # 保存原始日志
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(cls.logs, f, ensure_ascii=False, indent=2)
        
        # 生成并保存统计结果
        stats = cls._generate_statistics()
        if not stats_file:
            stats_file = log_file.replace(".json", "_stats.json")
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        return log_file, stats_file

class BaseQA_deepseek_V3:
    def __init__(self):
        self.qa_interface = self._setup_qa_interface()
        self._initialized = True

    def _setup_qa_interface(self):
        def get_deepseekV3_response(messages):
            client = OpenAI(
                api_key=os.environ.get("DEEPSEEK_V3_KEY"), 
                base_url=os.environ.get("DEEPSEEK_V3_BASE_URL")
            )

            chat_completion = client.chat.completions.create(
                messages=messages,
                model=os.environ.get("DEEPSEEK_V3_MODEL_NAME"),
                temperature=config.V3_temperature,
                stream=False
            )
            
            return {
                "content": chat_completion.choices[0].message.content,
                "prompt_tokens": chat_completion.usage.prompt_tokens,
                "completion_tokens": chat_completion.usage.completion_tokens
            }

        return get_deepseekV3_response

    def ask(self, question: str):
        raise NotImplementedError

    def close(self):
        pass

class QA_Context_deepseek_V3(BaseQA_deepseek_V3):
    def __init__(self):
        super().__init__()
        self.conversation_history: list[dict[str, str]] = []

    def ask(self, question: str):
        self.conversation_history.append({"role": "user", "content": question})
        result = self.qa_interface(self.conversation_history.copy())
        
        self.conversation_history.append({"role": "assistant", "content": result["content"]})
        
        GlobalLogManager.add_log({
            "model_type": "deepseek-v3",
            "user_prompt": question,
            "assistant_response": result["content"],
            "prompt_tokens": result["prompt_tokens"],
            "response_tokens": result["completion_tokens"],
            "timestamp": datetime.now().isoformat()
        })
        
        return result["content"]

class QA_NoContext_deepseek_V3(BaseQA_deepseek_V3):
    def ask(self, question: str):
        messages = [{"role": "user", "content": question}]
        result = self.qa_interface(messages)
        
        GlobalLogManager.add_log({
            "model_type": "deepseek-v3",
            "user_prompt": question,
            "assistant_response": result["content"],
            "prompt_tokens": result["prompt_tokens"],
            "response_tokens": result["completion_tokens"],
            "timestamp": datetime.now().isoformat()
        })
        
        return result["content"]

class BaseQA_deepseek_R1:
    def __init__(self):
        self.qa_interface = self._setup_qa_interface()
        self._initialized = True
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def _setup_qa_interface(self):
        # def get_response(messages):
        #     client = OpenAI(
        #         api_key=os.environ.get("DEEPSEEK_V3_KEY"), 
        #         base_url=os.environ.get("DEEPSEEK_V3_BASE_URL")
        #     )

        #     chat_completion = client.chat.completions.create(
        #         messages=messages,
        #         model=os.environ.get("DEEPSEEK_R1_MODEL_NAME"),
        #         temperature=config.R1_temperature,
        #         stream=False
        #     )
            
        #     return {
        #         "reasoning_content": chat_completion.choices[0].message.model_extra['reasoning_content'],
        #         "answer": chat_completion.choices[0].message.content,
        #         "prompt_tokens": chat_completion.usage.prompt_tokens,
        #         "completion_tokens": chat_completion.usage.completion_tokens
        #     }

        def get_response(messages):
            client = OpenAI(
                api_key=os.environ.get("DEEPSEEK_V3_KEY"),
                base_url=os.environ.get("DEEPSEEK_V3_BASE_URL")
            )

            # 获取模型名称用于token估算
            model_name = os.environ.get("DEEPSEEK_R1_MODEL_NAME")
            
            # ===== 流式请求获取内容 =====
            stream = client.chat.completions.create(
                messages=messages,
                model=model_name,
                temperature=config.R1_temperature,
                stream=True
            )

            full_content = []
            reasoning_contents = []
            
            for chunk in stream:
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        full_content.append(delta.content)
                    if hasattr(delta, 'model_extra') and 'reasoning_content' in delta.model_extra:
                        reasoning_contents.append(str(delta.model_extra['reasoning_content']))

            # ===== 估算token用量 =====
            # 估算prompt tokens（将messages序列化为字符串）
            prompt_str = json.dumps(messages, ensure_ascii=False)
            prompt_tokens = estimate_tokens(prompt_str, model_name)
            
            # 估算completion tokens（实际返回内容）
            completion_str = "".join(full_content)
            completion_tokens = estimate_tokens(completion_str, model_name)

            return {
                "reasoning_content": "".join(reasoning_contents),
                "answer": completion_str,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens
            }


        return get_response

    def ask(self, question: str):
        raise NotImplementedError

    def close(self):
        pass

class QA_Context_deepseek_R1(BaseQA_deepseek_R1):
    def __init__(self):
        super().__init__()
        self.conversation_history: list[dict[str, str]] = []

    def ask(self, question: str):
        self.conversation_history.append({"role": "user", "content": question})
        result = self.qa_interface(self.conversation_history.copy())
        
        self.conversation_history.append({"role": "assistant", "content": result["answer"]})
        
        reasoning_tokens = len(self.encoding.encode(result["reasoning_content"]))
        
        GlobalLogManager.add_log({
            "model_type": "deepseek-r1",
            "user_prompt": question,
            "assistant_response": result["answer"],
            "reasoning_content": result["reasoning_content"],
            "prompt_tokens": result["prompt_tokens"],
            "response_tokens": result["completion_tokens"],
            "reasoning_tokens": reasoning_tokens,
            "timestamp": datetime.now().isoformat()
        })
        
        return result["answer"]

class QA_NoContext_deepseek_R1(BaseQA_deepseek_R1):
    def ask(self, question: str):
        messages = [{"role": "user", "content": question}]
        result = self.qa_interface(messages)
        
        reasoning_tokens = len(self.encoding.encode(result["reasoning_content"]))
        
        GlobalLogManager.add_log({
            "model_type": "deepseek-r1",
            "user_prompt": question,
            "assistant_response": result["answer"],
            "reasoning_content": result["reasoning_content"],
            "prompt_tokens": result["prompt_tokens"],
            "response_tokens": result["completion_tokens"],
            "reasoning_tokens": reasoning_tokens,
            "timestamp": datetime.now().isoformat()
        })
        
        return result["answer"]
    

