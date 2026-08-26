from abc import ABC, abstractmethod

class Figure(ABC):
    def __init__(self, name=None, version=None, desc=None, bars=0, addons=None):
        self.Name = name
        self.Version = version
        self.Desc = desc
        self.Bars = bars
        self.Addons = addons or {}

    @abstractmethod
    def DanceMove(self, oldDF):
        raise NotImplementedError

    @abstractmethod
    def getCrips(self, oldDF):
        raise NotImplementedError

    @classmethod
    def from_json(cls, data):
        # factory implemented in Dance.py
        raise NotImplementedError
