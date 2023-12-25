# Microservices concept

Conceptual implementation of the architecture for CAEN control

## List of microservices

### WebService
* `/set_ticket/{name}`
  * POST request to execute ticket
  * receives args related to the ticket
  * preliminary inspects the ticket (quality, necessary args and so on)
* `/params?time={timestamp}`
  * GET request to return monitor information after `timestamp` (UTC) value (in seconds)
* `/list_tickets`
  * GET request to return the list of available tickets
  * Returns JSON: List[Ticket]
  * Useful for `Frontend` part
* `/`
  * root path is `Frontend` page for ticket setting

#### How to attach react frontend into this project
1. Frontend page (CAEN Manager) can be found https://github.com/caenHV/frontend_webpage
    1. Clone this repo and go to the folder
    1. Execute `npm run build`
1. Copy `build` folder into `caen_tools/WebService` folder (replacing the one that exists already)
1. It's done. Now WebService will use built frontend

### ProxyService
Proxy Queue to forward tickets to `DeviceBackend`
* Manipulates with JSON ticket representations
* `WebService` / `MonitorService` / `ConsoleClient` → `ProxyService` → `DeviceBackend`
* Has `PUB` socket output for every proxying message

### DeviceBackend
* Recieves JSON tickets and executes them
* Uses `caen_setup` module

### MonitorService
Sends special `MonitorTicket` to the `DeviceBackend`, recieves parameters of the device and manipulates them.

### ConsoleClient
Alternative for WebService for setting tickets (from console)

> *Note*:
> in future, seems, we can add ssh tunneling (for zmq) and enable remote managing 

### connection
Python class wrappers for client and server

### utils
Set of utility functions, e.g.
* config reader can get information from some custom `.ini` config file
  * `config.ini` is the default config file

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
* Run `WebService` (in another bash) by `python WebService/ws.py` to execute a random number of SetVoltage tickets or 
```bash
uvicorn WebService.ws:app --reload
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