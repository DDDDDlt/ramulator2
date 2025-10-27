import pickle
import pprint

# Change to your own file path
file_path = "./model_shape_config/opt_1_point_3.pickle"

with open(file_path, "rb") as f:
    model_config, layer_config = pickle.load(f)

print("===== Model Config =====")
pprint.pprint(model_config)   # print model config

print("\n===== Layer Config (Linear layers) =====")
for name, shape in layer_config.items():
    print(f"{name:60s} {shape}")

