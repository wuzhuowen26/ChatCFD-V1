import config, json, os, subprocess

def read_in_config():
    config_data = []
    with open(f'{config.Base_PATH}/inputs/chatcfd_config.json', 'r', encoding='utf-8') as file:
        config_data = json.load(file)

    os.environ["DEEPSEEK_V3_KEY"] = config_data["DEEPSEEK_V3_KEY"]
    os.environ["DEEPSEEK_V3_BASE_URL"] = config_data["DEEPSEEK_V3_BASE_URL"]
    os.environ["DEEPSEEK_V3_MODEL_NAME"] = config_data["DEEPSEEK_V3_MODEL_NAME"]
    config.V3_temperature = config_data["V3_temperature"]

    os.environ["DEEPSEEK_R1_KEY"] = config_data["DEEPSEEK_R1_KEY"]
    os.environ["DEEPSEEK_R1_BASE_URL"] = config_data["DEEPSEEK_R1_BASE_URL"]
    os.environ["DEEPSEEK_R1_MODEL_NAME"] = config_data["DEEPSEEK_R1_MODEL_NAME"]
    config.R1_temperature = config_data["R1_temperature"]

    config.run_time = config_data["run_time"]
    config.OpenFOAM_path = config_data["OpenFOAM_path"]
    config.OpenFOAM_tutorial_path = config_data["OpenFOAM_tutorial_path"]
    config.max_running_test_round = config_data["max_running_test_round"]
    config.pdf_chunk_d = config_data["pdf_chunk_d"]

    config.sentence_transformer_path = config_data["sentence_transformer_path"]

def load_openfoam_environment():
    """一次性加载OpenFOAM环境变量到当前Python进程"""
    try:
        # 通过bash获取source后的环境变量
        command =  f'source {config.OpenFOAM_path}/etc/bashrc && env'
        output = subprocess.run(
            command,
            shell=True,
            executable="/usr/bin/bash",  # 确保使用Bash
            check=True,  # 检查命令是否成功
            text=True,
            capture_output=True,
        )
        # 注入环境变量
        for line in output.stdout.splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value
    except subprocess.CalledProcessError as e:
        print(f"加载OpenFOAM环境失败: {e.stderr}")
        raise