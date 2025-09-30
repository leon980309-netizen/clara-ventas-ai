import json

class Security:
    def __init__(self, config_path="config.json"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

    def login(self, username, password):
        user = self.config["users"].get(username)
        if user and user["password"] == password:
            return {
                "username": username,
                "role": user["role"],
                "base": user.get("base")
            }
        return None