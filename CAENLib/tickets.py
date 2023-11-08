from enum import Enum
import abc


class Ticket(abc.ABC):
    description: dict = NotImplemented

    @abc.abstractmethod
    def execute(self, handler):
        pass

    def serialize(self):
        rep = {"name": self.description["name"]}
        rep_args = {key: getattr(self, key) for key in self.description["args"]}
        rep.update({"args": rep_args})
        return rep


class SetVoltage(Ticket):
    description = {
        "name": "SetVoltage",
        "args": {
            "voltage": "int",
        },
    }

    def __init__(self, voltage):
        self.voltage = voltage

    def execute(self, handler):
        return {"status": "success", "setV": self.voltage}


class Monitor(Ticket):
    description = {
        "name": "Monitor",
        "args": {
            "params": "list",
        },
    }

    def __init__(self, params: list):
        self.params = params

    def execute(self, handler):
        return [{p: idx} for idx, p in enumerate(self.params)]


class Ping(Ticket):
    """Empty ticket to ping the device"""

    description = {"name": "Ping", "args": {}}

    def __init__(self):
        pass

    def execute(self, handler):
        return {"status": "success"}


class Tickets(Enum):
    SET_VOLTAGE = SetVoltage
    MONITOR = Monitor
    PING = Ping

    @staticmethod
    def serialize(ticket_obj):
        if not (isinstance(ticket_obj, Ticket)):
            raise ValueError("Not found ticket")
        return ticket_obj.serialize()

    @staticmethod
    def deserialize(ticket_json):
        for t in Tickets:
            T = t.value
            if T.description["name"] == ticket_json["name"]:
                ticket_obj = T(**ticket_json["args"])
                return ticket_obj
        raise ValueError("Not found ticket")
