import json

def calculate_loop_num(qa_logs: dict) -> int:
    loop_num = 0

    p_1 = "请你分析这个报错是否是由于constant/polyMesh/boundary文件中的边界条件设置错误、不合理或boundary文件格式有问题导致的"
    p_2 = "OpenFOAM中由fluentMeshToFoam命令转换得到的最初的constant/polyMesh/boundary文件的内容为"
    p_3 = "1. some values may be too large or too small, or set to negative or unreasonable values, leading to floating point exceptions in calculations"

    for i, log in enumerate(qa_logs):
        if p_1 in log["user_prompt"]:
            loop_num += 1

    for i, log in enumerate(qa_logs):
        if p_2 in log["user_prompt"]:
            if p_1 in qa_logs[i-1]["user_prompt"]:
                continue
            else:
                loop_num += 1

    return loop_num
    

# file_dir = "run_chatcfd/"
# case_name = ""
# case_name = case_name+"/"
# file_path = file_dir + case_name + "all_qa_logs.json"
file_path = "/home/data/SquareBendLiq_Compressible_kEpsilon_0" + "/all_qa_logs.json"

with open(file_path, "r") as f:
    all_qa_logs = json.load(f)    # 所有处理

loop_num = calculate_loop_num(all_qa_logs)
print("循环次数:", loop_num)

"""damBreak"""
# dam_break_2d_laminar_0    23
# dam_break_2d_laminar_1    37-23=14
# dam_break_2d_laminar_2    52-37=15
# DamBreak_2D_WaterAir_0    14
# DamBreak_2D_WaterAir_1    35-14=21

"""planarPoiseuille_Maxwell"""
# PlanarPoiseuille_Maxwell_0    20
# PlanarPoiseuille_Maxwell_1    44-20=24
# PlanarPoiseuille_Maxwell_2D_0 19
# PlanarPoiseuille_Maxwell_2D_1 30-19=11
# PlanarPoiseuille_Maxwell_2D_2 45-30=15

"""squreBendLiq"""
# square_bend_liq_3d_compressible_kepsilon_0    5
# square_bend_liq_3d_compressible_kepsilon_1    13-5=8
# square_bend_liq_3d_compressible_kepsilon_2    37-13=29
# SquareBendLiq_3D_kEpsilon_HeatTransfer_0      5
# SquareBendLiq_3D_kEpsilon_HeatTransfer_1      12-5=7
# # SquareBendLiq_3D_kEpsilon_HeatTransfer_2      17-12=5
# SquareBendLiq_Compressible_kEpsilon_0         30

"""Counterflow_Flame_2D"""
# 2D_Laminar_Counterflow_Flame_0    30
# 2D_Laminar_Counterflow_Flame_1    60-30=30
# 2D_Laminar_Counterflow_Flame_2    82-60=22
# Counterflow_Flame_2D_Laminar_0    26
# Counterflow_Flame_2D_Laminar_1    56-26=30

"""box"""
# DNS_Forced_HIT_0  6
# DNS_Forced_HIT_1  5
# DNS_Forced_HIT_2  6

"""Cavity"""




