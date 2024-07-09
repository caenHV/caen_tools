import json
from datetime import datetime

from caen_tools.ODB_handler.ODB_Handler import ODB_Handler

class Monitor:
    def __init__(self, dbpath: str):
        self.__odb = ODB_Handler(dbpath)

    @staticmethod
    def __process_response(res_dict):
        ts = int(datetime.now().timestamp())
        res = res_dict["body"]["params"]
        res_list = []
        for key, val in res.items():
            k0 = json.loads(key.replace("\\", ""))
            board_address = list(k0["board_info"].keys())[0]
            conet = k0["board_info"][board_address]["conet"]
            link = k0["board_info"][board_address]["link"]
            chidx = f'{board_address}_{conet}_{link}_{k0["channel_num"]}'
            status = int(bin(int(val['ChStatus']))[2:])
            res_list.append((chidx, val["VMon"], val["IMonH"], ts, status))
        return res_list

    def send_params(self, params: str)->str:
        """Sends params to DB.

        Parameters
        ----------
        params : str
            json string with key "body" where all parameters are stored (the GetParameters ticket response).

        Returns
        -------
        str
            json response:
            {
                "name" : "Monitor",
                "timestamp" : current_time,
                "is_ok" : True for ok and False if something is wrong.
            }
        """
        res_dict = json.loads(params)
        res_list = Monitor.__process_response(res_dict)
        
        self.__odb.write_params(res_list)
        response = {
            "name" : "Monitor",
            "timestamp" : int(datetime.now().timestamp()),
            "is_ok" : True
        }
        return json.dumps(response)
    
    def is_ok(self)->str:
        response = {
            "name" : "Monitor",
            "timestamp" : int(datetime.now().timestamp()),
            "is_ok" : True
        }
        return json.dumps(response)
        