# Interlock service
Proxy between caen_tools ecosystem and outer interlock storage

## API routes

### `get_value`
returns interlock value

**Returns**

* `statuscode: int = 200` (Success)
* `body: dict = {value: bool, timestamp: int}`

### `report`
returns report of the microservice work
(not implemented yet)

**Returns**

* `statuscode: int = 200` (Success)
* `body: dict = {}`

### `set_mode`
sets mode of the microservice

manual mode: uses custom defined interlock value
socket mode: uses interlock value provided by socket

**Parameters**
* `mode: int`
  - interlock microserice mode
    (0: manual mode, 1: socket mode)
  
**Returns**

* `statuscode: int = 200` (Success)
* `body: dict = {..., mode: int}`

### `set_value`
sets interlock value
(only for manual mode)

**Parameters**
* `value: bool`
  - interlock value
    (False: OFF, True: ON)
  
**Returns**

* `statuscode: int = 200` (Success)
* `body: dict = {}`

### `status`
returns microservice status
  
**Returns**

* `statuscode: int = 200` (Success)
* `body: dict = {bind_address: str, socket: str, mode: int}`


### Errors

#### ForbiddenMethod
API request with wrong parameters case

* `statuscode: int = 403`
* `body: str = "Wrong arguments passed"`

#### GatewayTimeout
No connection case

* `statuscode: int = 503`
* `body: str = "Broken pipe to outer source"`

#### NotImplemented
Called method is not implemented

* `statuscode: int = 405`
* `body: str`
