import json
from datetime import datetime

from caen_tools.MonitorService.SystemCheck import SystemCheck
from caen_tools.ODB_handler.ODB_Handler import ODB_Handler

class Monitor:
    def __init__(self, dbpath: str, system_check: SystemCheck, channel_map: dict):
        self.__odb = ODB_Handler(dbpath)
        self.__system_check = system_check
        self.__channel_map: dict = channel_map

    @staticmethod
    def __process_response(res_dict, measurement_time):
        ts = measurement_time
        
        res = res_dict["params"]
        
        res_list = []
        for chidx, val in res.items():
            # k0 = json.loads(key.replace("\\", ""))
            # board_address = list(k0["board_info"].keys())[0]
            # conet = k0["board_info"][board_address]["conet"]
            # link = k0["board_info"][board_address]["link"]
            # chidx = f'{board_address}_{conet}_{link}_{k0["channel_num"]}'
            status = int(bin(int(val['ChStatus']))[2:])
            res_list.append((chidx, val["VMon"], val["IMonH"], ts, status))
        return res_list

    def send_params(self, params: dict, measurement_time: int)->dict:
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
        res_list = Monitor.__process_response(params, measurement_time)
        cooked_res_list = [(str(self.__channel_map[chidx]), VMon, IMonH, ts, status) 
                           for (chidx, VMon, IMonH, ts, status) in res_list 
                           if chidx in self.__channel_map.keys()]
        health_report = self.__system_check.check_params(params["params"])
        is_ok = self.__odb.write_params(cooked_res_list)
        response = {
            "timestamp" : int(datetime.now().timestamp()),
            "is_ok" : is_ok,
            "system_health_report" : health_report
        }
        return response
    
    def get_params(self, start: int, end: int)->dict:
        res = self.__odb.get_params(start, end)
        response = {
            "timestamp" : int(datetime.now().timestamp()),
            "is_ok" : res is not None,
            "params" : res
        }
        return response
    
    def get_interlock(self)->dict:
        res = self.__system_check.check_interlock()
        response = {
            "timestamp" : int(datetime.now().timestamp()),
            "is_ok" : res is not None,
            "system_health_report" : res
        }
        return response
    
    def is_ok(self)->dict:
        response = {
            "timestamp" : int(datetime.now().timestamp()),
            "is_ok" : True
        }
        return response
        