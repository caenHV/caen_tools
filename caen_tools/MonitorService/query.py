import json

# from dataclasses import dataclass


class QueryMaster:
    NAME = "MonitorQuery"

    @staticmethod
    def serialize(timestamp: int) -> str:
        query = dict()
        query["name"] = QueryMaster.NAME
        query["starttime"] = timestamp
        json_str = json.dumps(query)
        return json_str

    @staticmethod
    def deserialize(json_str: str) -> dict:
        data = json.loads(json_str)

        if data["name"] != QueryMaster.NAME:
            raise ValueError(f"Wrong name {data['name']}")
        return data
