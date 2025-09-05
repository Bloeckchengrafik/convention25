import json

class Configuration:
    flow_rate: float = 1

    def __init__(self):
        with open("config.json", "r") as f:
            obj = json.load(f)
        self.flow_rate = obj["flow_rate"]

    def save(self):
        obj = {
            "flow_rate": self.flow_rate
        }
        with open("config.json", "w") as f:
            json.dump(obj, f)
