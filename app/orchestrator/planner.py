import json

class Planner:
    def __init__(self):
        with open("prompts.json") as f:
            self.strategies = json.load(f)

    def create_plan(self, query: str):
        # For now, always use default strategy
        return self.strategies["default_strategy"]["steps"]

