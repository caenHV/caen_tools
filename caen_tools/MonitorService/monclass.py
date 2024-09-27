import json
from datetime import datetime
from pathlib import Path

from caen_tools.ODB_handler.ODB_Handler import ODB_Handler


class Monitor:
    def __init__(self, dbpath: str, param_file_path: str, current_key: str = "IMnoH"):
        self.__odb = ODB_Handler(dbpath)
        self.__param_file_path = Path(param_file_path)
        self.__imon_key: str = current_key

    def __process_response(self, res_dict, measurement_time):
        ts = measurement_time

        res = res_dict["params"]

        res_list = []
        for chidx, val in res.items():
            status = int(bin(int(val["ChStatus"]))[2:])
            res_list.append((chidx, val["VMon"], val[self.__imon_key], ts, status))
        return res_list

    def send_params(self, params: dict, measurement_time: int) -> dict:
        """Sends params to DB.

        Parameters
        ----------
        params : dict
            json dict with key "body" where all parameters are stored (the GetParameters ticket response).

        Returns
        -------
        str
            json response:
            {
                "timestamp" : current_time,
                "is_ok" : True for ok and False if something is wrong.
            }
        """
        cooked_res_list = self.__process_response(params, measurement_time)
        is_ok = self.__odb.write_params(cooked_res_list, self.__param_file_path)
        response = {
            "timestamp": int(datetime.now().timestamp()),
            "is_ok": is_ok,
        }
        return response

    def get_params(self, start: int, end: int) -> dict:
        res = self.__odb.get_params(start, end)
        response = {
            "timestamp": int(datetime.now().timestamp()),
            "is_ok": res is not None,
            "params": res,
        }
        return response

    def is_ok(self) -> dict:
        response = {"timestamp": int(datetime.now().timestamp()), "is_ok": True}
        return response
