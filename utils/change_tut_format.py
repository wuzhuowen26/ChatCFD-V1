import json
from pathlib import Path


tutorials_path = "mix.txt"

with open(tutorials_path, "r") as file:
    data = file.read()

file_basename = tutorials_path.split("/")[-1]
print(data)


with open(f"{file_basename}_changed.json", "w") as json_file:
    json.dump(data, json_file)


