# CAEN Microservices

Implementation of the architecture for CAEN control

## List of microservices

### WebService
* `/device_backend/status`
  * GET request to check status of the deviceBackend
* `/device_backend/params`
  * GET request to recieve parmeters of the device
* `/device_backend/set_voltage`
  * POST request to set voltage on the device
* `/device_backend/down`
  * POST request to turn off voltage on the device
* `/`
  * root path is `Frontend` page for ticket setting
* `/docs`
  * a full list of the available API methods can be found 
  at this way

#### How to attach react frontend into this project
1. Frontend page (CAEN Manager) can be found https://github.com/caenHV/frontend_webpage
    1. Clone this repo and go to the folder
    1. Execute `npm run build`
1. Copy `build` folder into `caen_tools/WebService` folder (replacing the one that exists already)
1. It's done. Now WebService will use built frontend

### DeviceBackend
* Recieves **Receipts** from `WebService` and executes them:
  * *Set_Voltage* sets voltage on the Device
  * *Down* turns off voltage on the Device
  * *Get_Params* gets parameters from the Device
* Uses `caen_setup` module for the Device interaction

### MonitorService
* Recieves **Receipts** from `WebService` and executes them:
  * *Send_Params* sends parameters into database (and check them on system check)
  * *Get_Params* gets parameters from database

__________

### connection
Python class wrappers for client and server

### utils
Set of utility functions, e.g.
* config reader can get information from some custom `.ini` config file
  * `config.ini` is the default config file
* Receipt and ReceiptResponse structure

### [caen_setup](https://github.com/caenHV/Setup)
Python module containing:
* List of available tickets
* Implementation of the tickets
* Setup interaction

## Requirements
Tested on `python==3.11.2` with extra modules described in `requirements.txt`

## Running

* Build module via pip
```bash
pip install -e .
```
* Run `WebService` (in another bash) through 
```bash
uvicorn caen_tools.WebService.ws:app --reload
```
to deploy webserver

## Final view
Finally this project must be installed easily via pip like

```pip install caen-tools[webservice]```

## Helpful links
* [ZMQ Guide](https://zguide.zeromq.org/)
* [ZMQ Socket API](https://zeromq.org/socket-api/)
* [PyZMQ API](https://pyzmq.readthedocs.io/en/latest/api/zmq.html)
* [Install package from git](https://github.com/pypa/pip/issues/6548)
* [Git submodules](https://git-scm.com/book/ru/v2/%D0%98%D0%BD%D1%81%D1%82%D1%80%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D1%8B-Git-%D0%9F%D0%BE%D0%B4%D0%BC%D0%BE%D0%B4%D1%83%D0%BB%D0%B8)
* [PIP extra dependencies](https://setuptools.pypa.io/en/latest/userguide/dependency_management.html)