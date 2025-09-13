import json

class Configuration:
    flow_rate: float = 1
    tool_lead_time: float = 0.1
    tool_lag_time: float = 0.05
    retraction_distance: int = 50
    retraction_speed: int = 1000

    def __init__(self):
        with open("config.json", "r") as f:
            obj = json.load(f)
        self.flow_rate = obj.get("flow_rate", 1.0)
        self.tool_lead_time = obj.get("tool_lead_time", 0.1)
        self.tool_lag_time = obj.get("tool_lag_time", 0.05)
        self.retraction_distance = obj.get("retraction_distance", 50)
        self.retraction_speed = obj.get("retraction_speed", 1000)

    def save(self):
        obj = {
            "flow_rate": self.flow_rate,
            "tool_lead_time": self.tool_lead_time,
            "tool_lag_time": self.tool_lag_time,
            "retraction_distance": self.retraction_distance,
            "retraction_speed": self.retraction_speed
        }
        with open("config.json", "w") as f:
            json.dump(obj, f)
