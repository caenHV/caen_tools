import logging
from datetime import datetime
from pathlib import Path
from typing import TypeAlias

from .ODB import ODB_Handler

BackendStatusCode: TypeAlias = str


class Monitor:
    def __init__(self, dbpath: str, param_file_path: str, status_file_path: str):
        self.__odb = ODB_Handler(dbpath)
        self.__param_file_path = Path(param_file_path)
        self.__status_file_path = Path(status_file_path)

    @staticmethod
    def __imon_key(val_ImonRange: int) -> str:
        return "IMonH" if val_ImonRange == 0 else "IMonL"

    def __process_response(self, res_dict, measurement_time):
        ts = measurement_time

        res = res_dict["params"]

        res_list = []
        for chidx, val in res.items():
            status = int(bin(int(val["ChStatus"]))[2:])
            imon_key = self.__imon_key(int(val["ImonRange"]))
            res_list.append((chidx, val["VMon"], val[imon_key], ts, status))
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
        logging.debug("Start sending parameters to ODB")
        cooked_res_list = self.__process_response(params, measurement_time)
        is_ok = self.__odb.write_params(cooked_res_list, self.__param_file_path)
        response = {
            "timestamp": int(datetime.now().timestamp()),
            "is_ok": is_ok,
        }
        return response

    def send_status(self, is_ok: bool, description: str, timestamp: int) -> dict:
        """Sends the hardware status to the DB.

        Parameters
        ----------
        is_ok : bool
            True if yes False otherwise. Pretty obvious!
        description : str
            Explanation of the status. Meaningful only if is_ok == False
        timestamp : int
            time from the epoch of the status issue.

        Returns
        -------
        str
            json response:
            {
                "timestamp" : current_time,
                "is_ok" : True for ok and False if something is wrong.
            }
        """
        logging.debug("Start sending the hardware status to the ODB")
        logging.info(
            "The hardware status is is_ok = %s with the full description '%s' at %s",
            is_ok,
            description,
            datetime.fromtimestamp(timestamp),
        )
        is_ok = self.__odb.write_status(
            is_ok, description, timestamp, self.__status_file_path
        )
        response = {
            "timestamp": int(datetime.now().timestamp()),
            "is_ok": is_ok,
        }
        return response

    def get_params(self, start: int, end: int) -> dict:
        logging.debug("Start getting parameters from ODB")
        res = self.__odb.get_params(start, end)
        response = {
            "timestamp": int(datetime.now().timestamp()),
            "is_ok": res is not None,
            "params": res,
        }
        return response

    def get_status(self, start: int, end: int) -> dict:
        logging.debug("Start getting parameters from ODB")
        res = self.__odb.get_status(start, end)
        response = {
            "timestamp": int(datetime.now().timestamp()),
            "is_ok": res is not None,
            "status": res,
        }
        return response
