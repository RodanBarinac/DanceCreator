class Dancer:
    def __init__(self, name, gender=None):
        self.name = name
        self.gender = gender

    def to_dict(self):
        return {"name": self.name, "gender": self.gender}

    def __repr__(self):
        return f"Dancer({self.name},{self.gender})"