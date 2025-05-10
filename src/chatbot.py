import streamlit as st
from openai import OpenAI
import PyPDF2
import io
import json
from PIL import Image
import base64
import re
import tiktoken
from datetime import datetime

import config, case_file_requirements, preprocess_OF_tutorial, set_config, main_run_chatcfd, qa_modules
import pathlib
import os
import torch

torch.classes.__path__ = [os.path.join(torch.__path__[0], torch.classes.__file__)] 

general_prompt = ''

# OF算例设置keywords，用于提取算例描述中的关键词，以匹配算例库中最相关的算例。OF-v2406

class ChatBot:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.environ.get("DEEPSEEK_R1_KEY"),
            base_url=os.environ.get("DEEPSEEK_R1_BASE_URL")
        )
        self.system_prompt = """You are an intelligent assistant capable of:
        1. Maintaining politeness and professionalism
        2. Remembering the context of the conversation
        3. Processing and analyzing content from documents uploaded by users
        4. Answering user questions while keeping the conversation coherent

        Please always respond in a clear, accurate, and helpful manner."""
        self.temperature = 0.9

        self.token_counter = {
            "total": 0,
            "qa_history": []
        }

    def process_pdf(self, pdf_file):
        try:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
        except Exception as e:
            return f"PDF processing error: {str(e)}"

    def get_response(self, messages):

        try:
            response = self.client.chat.completions.create(
                model=os.environ.get("DEEPSEEK_R1_MODEL_NAME"),
                messages=[{"role": "system", "content": self.system_prompt}] + messages,
                temperature=self.temperature
            )
            # 记录token使用
            usage = response.usage
            self.token_counter["total"] += usage.total_tokens
            qa_record = {
                "prompt": messages,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "timestamp": datetime.now().isoformat()
            }
            return response.choices[0].message.content
        except Exception as e:
            return f"Chat error: {str(e)}"

    def count_tokens(self, text: str, model: str = "gpt-4o") -> int:
        """使用tiktoken统计token数量"""
        try:
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(text))
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))

def initialize_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = ChatBot()
    if "file_content" not in st.session_state:
        st.session_state.file_content = None
    if "file_processed" not in st.session_state:
        st.session_state.file_processed = False
    if "ask_case_solver" not in st.session_state:
        st.session_state.ask_case_solver = False
    if "user_answered" not in st.session_state:
        st.session_state.user_answered = False
    if "user_answer_finished" not in st.session_state:
        st.session_state.user_answer_finished = False
    if "uploaded_grid" not in st.session_state:
        st.session_state.uploaded_grid = False
    if "show_start" not in st.session_state:
        st.session_state.show_start = False

def extract_pure_response(text):
    # 使用正则表达式匹配所有内容（包括换行符）
    pattern = r"Here is my response:(.*?)(?=$|\Z)"
    match = re.search(pattern, text, re.DOTALL)
    
    if match:
        # 去除首尾空白字符
        return match.group(1).strip()
    return ""

def test_function_call_by_QA():
    """测试函数调用"""
    print("the test_function_call_by_QA() is called")  # 控制台打印
    return "✅ 测试函数已成功调用！系统状态正常。"
    

def main():

    # test other functions

    # test_function_call_by_QA()

    # a = 1

    # streamlit functions

    st.title("ChatCFD: chat to run CFD cases.")

    st.divider()
    
    initialize_session_state()

    with st.sidebar:

        # 导出对话记录功能
        st.header("Export chat history")
        export_format = "JSON"
        
        if st.button("Export chat"):
            if not st.session_state.messages:
                st.warning("Empty chat history")
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"chatlog_{timestamp}"

                chat_data = {
                    "metadata": {
                        "export_time": datetime.now().isoformat(),
                        "total_messages": len(st.session_state.messages),
                        "total_tokens": st.session_state.chatbot.token_counter["total"]
                    },
                    "messages": st.session_state.messages
                }
                
                st.sidebar.download_button(
                    label="下载JSON文件",
                    data=json.dumps(chat_data, indent=2, ensure_ascii=False),
                    file_name=f"{filename}.json",
                    mime="application/json"
                )

    # Sidebar: File Upload
    with st.sidebar:
        st.header("Upload the document")
        uploaded_file = st.file_uploader(
            "Please upload PDF",
            type=['pdf']
        )
        
        if uploaded_file:
            if not st.session_state.file_processed:
                if uploaded_file.type == "application/pdf":

                    save_dir = pathlib.Path(config.TEMP_PATH)
                    
                    try:
                        # 构建保存路径
                        file_path = save_dir / uploaded_file.name.replace(" ", "_")
                        
                        # 保存上传文件
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())

                        config.pdf_path =  f"{config.TEMP_PATH}/{uploaded_file.name}"

                    except Exception as e:
                        st.error(f"Failed at processed the pdf file: {str(e)}") 

                    text_content = st.session_state.chatbot.process_pdf(uploaded_file)
                    config.paper_content = text_content
                    st.session_state.file_content = f"The  contents：\n{text_content}"
                    st.toast("PDF uploaded！", icon="💾")
                    
                    # Add 1st question
                    question_1 = f'''The attached PDF contain several CFD cases, and I would like to run one or several of the case by my self later. Please read the paper and list all distinct CFD cases with characteristic description. Give each case a tag as Case_X (such as Case_1, Case_2).

                    - Please count each unique combination of parameters that results in a separate simulation run as one CFD case. These parameters include but not limited to the geometry, boundary Conditions, flow Parameters (Re/Mach/AoA/velocity), physical Model, or Solver.
                    - If there are multiple runs of the same parameters for statistical analysis or convergence studies, count these as one case, unless the paper specifies them as distinct due to different goals or conditions.
                    - If any case is simulated using OpenFOAM, identify the solver or find a proper solver to run the case. Show the solver name when describing the case.
                    
                    The paper is as follows: \n{text_content}. 
                    '''

                    st.session_state.messages.append({
                        "role": "user",
                        "content": question_1, "timestamp": datetime.now().isoformat()
                    })
                    
                    # Get response for question A
                    with st.chat_message("assistant"):
                        response_1 = st.session_state.chatbot.get_response(st.session_state.messages)
                        st.write(response_1)
                        st.session_state.messages.append({"role": "assistant", "content": response_1, "timestamp": datetime.now().isoformat()})

                    st.session_state.file_processed = True

                    # Chatbot ask the user to choose case and solver
                    if not st.session_state.ask_case_solver:
                        ask_to_choose_case_and_solver = '''Please choose the case you want to simulate and the OpenFOAM solver you want to use. 
                            Your answer shall be like one of the followings:\n- I want to simulate Case_1 using rhoCentralFoam and the SpalartAllmaras model.\n- I want to simulate the Case with AOA = 10 degree and kOmegaSST model.\n
                            
                        \n You must choose only one case.
                        '''
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": ask_to_choose_case_and_solver,
                            "timestamp": datetime.now().isoformat()
                        })

                        st.session_state.ask_case_solver = True

    with st.sidebar:
        st.header("Upload the mesh file")
        uploaded_mesh_file = st.file_uploader(
            "Please upload mesh (only support the Fluent-format .msh)",
            type=['msh']
        )
        if uploaded_mesh_file:
            if not st.session_state.uploaded_grid:
                # 创建保存目录
                save_dir = pathlib.Path(config.TEMP_PATH)
                
                try:
                    # 构建保存路径
                    file_path = save_dir / uploaded_mesh_file.name.replace(" ", "_")
                    
                    # 保存上传文件
                    with open(file_path, "wb") as f:
                        f.write(uploaded_mesh_file.getbuffer())
                    
                    st.toast(f"The mesh file has been saved: {file_path}", icon="💾")

                    config.case_grid = f"{config.TEMP_PATH}/{uploaded_mesh_file.name}"

                    # check the grid using OpenFOAM, later
                    
                    case_file_requirements.extract_boundary_names(file_path)

                    st.toast(f"The mesh file has been processed! ")

                    boundary_names = ", ".join(config.case_boundaries)
                    # print(config.case_boundaries)

                    config.case_boundary_names = boundary_names

                    info_after_mesh_processed = f'''You have uploaded a mesh file with boundary names as: {boundary_names}.\nNow the case are prepared and running in the background. Running information will be shown in the console.'''
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": info_after_mesh_processed,
                        "timestamp": datetime.now().isoformat()
                    })

                    st.session_state.ask_case_solver = True

                    st.session_state.uploaded_grid = True

                except Exception as e:
                    st.error(f"Failed at processed the mesh file: {str(e)}")              

    # Display conversation history
    if len(st.session_state.messages) > 0:
        for message in st.session_state.messages[1:]:
            if message["role"] == "user":
                st.chat_message("user").write(message["content"])
            else:
                if message["content"].startswith("Understand the user's answer"):
                    continue
                else:
                    st.chat_message("assistant").write(message["content"])

    if st.session_state.show_start == False:
        st.header('**Please upload the paper to start!**')
        st.session_state.show_start = True

    # guide the user to choose cases
    if st.session_state.ask_case_solver == True and st.session_state.user_answered == True:
        a = 1
        try: 
            user_answer = st.chat_messages[-1]['content']
            paper_case_descriptions = st.chat_messages[-1]['content']

            json_reponse_sample = '''
            {
                "Case_1":{
                    "solver":"<solver_name>",
                    "turbulence_model":"<model_name>",
                    "other_physical_model":"<model_name>",
                    "case_specific_description":"<specific case discription that differenciate this case from the others in the paper."
                },
                "Case_2":{
                    "solver":"<solver_name>",
                    "turbulence_model":"<model_name>",
                    "other_physical_model":"<model_name>",
                    "case_specific_description":"<specific case discription that differenciate this case from the others in the paper."
                },
                "Case_X":{
                    "solver":"<solver_name>",
                    "turbulence_model":"<model_name>",
                    "other_physical_model":"<model_name>",
                    "case_specific_description":"<specific case discription that differenciate this case from the others in the paper."
                }
            }
            '''

            guide_case_choose_prompt = f'''Understand the user's answer and describe the case details of the user's requirement.

                        The user's answer is:{user_answer}

                        Please generate JSON content according to these requirements:

                        1. Strictly follow this example format containing ONLY JSON content:{json_reponse_sample}. For the case_specific_description sections, propose characteristics that can differenciate this case from the other similar cases in the paper. The differentiating characteristics must exclude conventional attributes such as geometry, shape, numerical parameters, physical models, or other standard descriptors. 

                        2. Absolutely AVOID any non-JSON elements including but not limited to:
                        - Markdown code block markers (```json or ```)
                        - Extra comments or explanations
                        - Unnecessary empty lines or indentation
                        - Any text outside JSON structure

                        3. Critical syntax requirements:
                        - Maintain strict JSON syntax compliance
                        - Enclose all keys in double quotes
                        - Use double quotes for string values
                        - Ensure no trailing comma after last property
            '''

            st.chat_message("assistant").write(guide_case_choose_prompt)
            st.session_state.messages.append({"role": "assistant", "content": guide_case_choose_prompt, "timestamp": datetime.now().isoformat()})

            with st.chat_message("assistant"):
                response = st.session_state.chatbot.get_response(st.session_state.messages)
                st.write(response)
                st.session_state.messages.append({"role": "assistant", "content": response, "timestamp": datetime.now().isoformat()})

            prompt_2 = f'''Task: The user want to simulate a CFD case with the following characteristicis,
            identify the CFD case from the following case descriptions from a PDF.
            - Characteristics: {user_answer}.
            - Case descriptions: {paper_case_descriptions}.
            Your response shall only include the answer without any thinking content.
            '''

        except Exception as e:
            return f"Chat error: {str(e)}"

    # User input
    if prompt := st.chat_input("Enter your requirement or reply."):
        
        st.chat_message("user").write(prompt)  # Display the user's original prompt in the UI

        if st.session_state.ask_case_solver and not st.session_state.user_answer_finished: # ask the user for Case_X, solver and turbulence
            json_reponse_sample = '''
            {
                "Case_1":{
                    "case_name" = <some_case_name>,
                    "solver":"<solver_name>",
                    "turbulence_model":"<model_name>",
                    "other_physical_model":"<model_name>",
                    "case_specific_description":"<a sentence that describes the case setup with detailed parameters that differenciate this case from the other cases in the paper>"
                }
            }
            '''

            guide_case_choose_prompt = f'''Understand the user's answer and describe the case details of the user's requirement.

                        The user's answer is:{prompt}

                        Please generate JSON content according to these requirements:

                        1. Strictly follow this example format containing ONLY JSON content:{json_reponse_sample}

                        2. Absolutely AVOID any non-JSON elements including but not limited to:
                        - Markdown code block markers (```json or ```)
                        - Extra comments or explanations
                        - Unnecessary empty lines or indentation
                        - Any text outside JSON structure

                        3. Critical syntax requirements:
                        - Maintain strict JSON syntax compliance
                        - Enclose all keys in double quotes
                        - Use double quotes for string values
                        - Ensure no trailing comma after last property

                        4. Case_name must adhere to the following format:
                         [a-zA-Z0-9_]+ - only containing lowercase letters, uppercase letters, numbers, or underscores. Special characters (e.g. -, @, #, spaces) are not permitted.

                        5. The solver must be one of the followings: {config.string_of_solver_keywords}. 
                        The turbulence _model must be one of the followings: {config.string_of_turbulence_model}.
            '''

            st.session_state.messages.append({"role": "user", "content": guide_case_choose_prompt, "timestamp": datetime.now().isoformat()})

            # Get assistant's response
            with st.chat_message("assistant"):
                response = st.session_state.chatbot.get_response(st.session_state.messages)
                config.all_case_dict = json.loads(response)

                qa = qa_modules.QA_NoContext_deepseek_R1()

                convert_json_to_md = f'''Convert the provided JSON string into a Markdown format where:
                    1. Each top-level JSON key becomes a main heading (#)
                    2. Its corresponding key-value pairs are rendered as unordered list items
                    3. Maintain the original key-value hierarchy in list format

                    The provided json string is as follow:{response}.
                '''

                md_form = qa.ask(convert_json_to_md)

                decorated_response = f'''You choose to simulate the cases with the following setups:\n{md_form}'''
                st.write(decorated_response)
                st.session_state.messages.append({"role": "assistant", "content": decorated_response, "timestamp": datetime.now().isoformat()})
                # later, fnae
                st.session_state.user_answer_finished = True

                

        else:   # normal case
            st.session_state.messages.append({"role": "user", "content": prompt, "timestamp": datetime.now().isoformat()})
            # Get assistant's response
            with st.chat_message("assistant"):
                response = st.session_state.chatbot.get_response(st.session_state.messages)
                st.write(response)
                st.session_state.messages.append({"role": "assistant", "content": response, "timestamp": datetime.now().isoformat()})

    if st.session_state.file_processed and st.session_state.user_answer_finished and not st.session_state.uploaded_grid:
        st.write("If you don't have further requirement on the case setup. \n**Please upload the mesh of the Fluent .msh format.**")

    if st.session_state.uploaded_grid and st.session_state.file_processed and st.session_state.user_answer_finished:
        # read in preprocess OF tutorials
        print(f"**************** Preprocessing OF tutorials at {config.of_tutorial_dir} ****************")
        # if not config.flag_OF_tutorial_processed:
        #     preprocess_OF_tutorial.main()
        #     config.flag_OF_tutorial_processed = True
        preprocess_OF_tutorial.read_in_processed_merged_OF_cases()
        for key, value in config.all_case_dict.items():
            case_name = value["case_name"]
            print(f"***** start processing {key}: {case_name} *****")
            solver = value["solver"]
            turbulence_model = value["turbulence_model"]

            case_specific_description = value["case_specific_description"]

            main_run_chatcfd.test_solver = solver

            main_run_chatcfd.test_turbulence_model = turbulence_model

            main_run_chatcfd.test_case_name = case_name

            main_run_chatcfd.test_case_description = case_specific_description

            main_run_chatcfd.run_case()

            # single_case_builder_runner.single_case_details_from_PDF(case_name, solver, turbulence_model, 
            #     transient, simulation_duration, case_specific_description)

if __name__ == "__main__":
    set_config.read_in_config()
    main()