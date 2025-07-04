import json
from datetime import datetime

def calculate_token_length(qa_logs: dict) -> int:
    token_num_r1 = 0
    token_num_v3 = 0
    token_input_r1 = 0
    token_output_r1 = 0
    token_input_v3 = 0
    token_output_v3 = 0

    for log in qa_logs:
        if log["model_type"] == "deepseek-r1":
            token_num_r1 += log["prompt_tokens"]+log["response_tokens"]+log["reasoning_tokens"]
            token_input_r1 += log["prompt_tokens"]
            token_output_r1 += log["response_tokens"]+log["reasoning_tokens"]

        if log["model_type"] == "deepseek-v3":
            token_num_v3 += log["prompt_tokens"]+log["response_tokens"]
            token_input_v3 += log["prompt_tokens"]
            token_output_v3 += log["response_tokens"]
    
    token = {
        "token_num_r1": token_num_r1,
        "token_num_v3": token_num_v3,
        "token_input_r1": token_input_r1,
        "token_output_r1": token_output_r1,
        "token_input_v3": token_input_v3,
        "token_output_v3": token_output_v3
    }

    return token

def calculate_time(qa_logs: dict) -> float:

    flag = 0
    for i,log in enumerate(all_qa_logs):
        if log["user_prompt"].startswith("You are a CFD expert assistant. Extract technical parameters"):
            flag += 1
            break
    dt1 = datetime.fromisoformat(all_qa_logs[i]["timestamp"])
    seconds1 = dt1.timestamp()
    dt2 = datetime.fromisoformat(all_qa_logs[-1]["timestamp"])
    seconds2 = dt2.timestamp()

    time_diff = seconds2 - seconds1
    return time_diff


def spend_money(token_num: dict) -> float:

    r1_input  = 0.0040 / 1000
    r1_output = 0.0160 / 1000
    v3_input  = 0.0020 / 1000
    v3_output = 0.0080 / 1000

    r1_cost = token_num["token_input_r1"] * r1_input + token_num["token_output_r1"] * r1_output
    v3_cost = token_num["token_input_v3"] * v3_input + token_num["token_output_v3"] * v3_output

    total_cost = r1_cost + v3_cost

    money = {
        "r1_cost": r1_cost,
        "v3_cost": v3_cost,
        "total_cost": total_cost
    }
    return money


if __name__ == "__main__":
    
    # file_dir = "run_chatcfd/"
    # case_name = ['Transient_Cylinder_Re3.6e6_1', 'Transient_Flow_Past_Cylinder_Re3.6e6_0', 'TransientFlow_CircularCylinder_Re3p6e6_1']
    # case_name = case_name[2]+"/"
    # file_path = file_dir + case_name
    file_path = "/home/data/SquareBendLiq_file_new/SquareBendLiq_Compressible_kEpsilon_1"
    

    with open(file_path + "/all_qa_logs.json", "r") as f:
        all_qa_logs = json.load(f)    # 所有处理


    if 0:
        token_num = calculate_token_length(all_qa_logs)
        print("Token Number:\n", token_num)
        money = spend_money(token_num)
        print("Money Spent:\n", money)

        with open(file_path + "/token_num.json", "w") as f:
            json.dump(token_num, f, indent=4)
        with open(file_path + "/money_spent.json", "w") as f:
            json.dump(money, f, indent=4)

    else:   # 计算时间
        time_diff = calculate_time(all_qa_logs)
        print("Time Spent (seconds):", time_diff)

        with open(file_path + "/time_spent.json", "w") as f:
            json.dump({"time_spent(no parse_pdf)": time_diff}, f, indent=4)
