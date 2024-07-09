import json
from datetime import datetime

from caen_tools.connection.client import SyncClient
from caen_tools.ODB_handler.ODB_Handler import ODB_Handler


class SystemCheck:
    def __init__(self, dbpath: str):
        self.__interlock = True
        self.__last_interlock_check = int(datetime.now().timestamp())
        self.__max_interlock_check_delta_time = 100
        self.__are_params_ok = True
        self.__last_params_check = int(datetime.now().timestamp())

        self.__is_ok = True
        
        self.__odb = ODB_Handler(dbpath)
    
    def update_state(self):
        delta_time = int(datetime.now().timestamp()) - self.__last_interlock_check
        if delta_time > self.__max_interlock_check_delta_time:
            self.check_interlock()
            
    def check_interlock(self)->str:
        interlock = self.__odb.get_interlock()
        self.__interlock = interlock[-1]['state'] if interlock is not None else 1
        self.__last_interlock_check = interlock[-1]['time'] if interlock is not None else self.__last_interlock_check
        self.__is_ok = interlock is not None
            
        response = {
            "name" : "SystemCheck",
            "timestamp" : int(datetime.now().timestamp()),
            "is_ok" : self.__is_ok,
            "params_ok" : self.__are_params_ok,
            "interlock" : self.__interlock,
            "interlock check timestamp" : self.__last_interlock_check,
            "params check timestamp" : self.__last_params_check
        }
        return json.dumps(response)
    
    def check_params(self, params: str) -> str:
        """Check params.

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

        # Checks that all channels are okay.
        ch_status_list = [int(bin(int(val['ChStatus']))[2:]) > 111 for _, val in res_dict["body"]["params"].items()]
        self.__are_params_ok = not any(ch_status_list)
        self.__last_params_check = int(datetime.now().timestamp())
        
        self.update_state()
        response = {
            "name" : "SystemCheck",
            "timestamp" : int(datetime.now().timestamp()),
            "is_ok" : self.__is_ok,
            "params_ok" : self.__are_params_ok,
            "interlock" : self.__interlock,
            "interlock check timestamp" : self.__last_interlock_check,
            "params check timestamp" : self.__last_params_check
        }
        return json.dumps(response)
    
    def is_ok(self)->str:
        self.update_state()
        response = {
            "name" : "SystemCheck",
            "timestamp" : int(datetime.now().timestamp()),
            "is_ok" : self.__is_ok,
            "params_ok" : self.__are_params_ok,
            "interlock" : self.__interlock,
            "interlock check timestamp" : self.__last_interlock_check,
            "params check timestamp" : self.__last_params_check
        }
        return json.dumps(response)
        