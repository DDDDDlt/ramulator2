import pickle
import pprint

# 修改成你自己的文件路径
file_path = "./model_shape_config/opt_1_point_3.pickle"

with open(file_path, "rb") as f:
    model_config, layer_config = pickle.load(f)

print("===== Model Config =====")
pprint.pprint(model_config)   # 打印整体模型配置

print("\n===== Layer Config (Linear layers) =====")
for name, shape in layer_config.items():
    print(f"{name:60s} {shape}")

