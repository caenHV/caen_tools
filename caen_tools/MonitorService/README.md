# Monitor

The microservice for reading, writing and checking CAEN channel parameters.

## API

<details>
 <summary><code>GET</code> <code><b>/status</b></code>
 <code>(gets a status of the microservice)</code></summary>

##### Parameters

> None

##### Responses

> | status code | response/body | response/body example |
> |------|-----|-----|
> | `1` | `application/json` | `{}` |
> | `0` | `text/plain;charset=UTF-8` | `"No response from the device"` |

</details>

<details>
 <summary><code>Post</code> <code><b>/send_params</b></code> 
 <code>(Write parameters of the CAEN device to the DB)</code></summary>

##### Parameters

> | name |  type   | data type  | description |
> |------|-----|---------|-----------------|
> | channel_id |  required | str   | Channel id in the following format: "board_conet_link_channel" |
> | channel_parameters |  required | dict   | Channel parameters from CAEN board |

##### Responses

> | status code | response | response example | comment |
> |------|-----|-----|-----|
> | `1` | `application/json` | `{'timestamp': 1720361379,'body': {'params_ok' : True, 'interlock' : False,  'interlock check timestamp' : 1720361369, 'params check timestamp' : 1720361379}}` | `Parameters were written` |
> | `0` | `application/json` | `{'timestamp': 1720361379, 'body': {'params_ok' : True, 'interlock' : False, 'interlock check timestamp' : 1720361369, 'params check timestamp' : 1720361379}}` | `There  the DB. Parameters were not written.`|

</details>

<details>
 <summary><code>GET</code> <code><b>/get_params</b></code>
 <code>(Get cahnnel params from the DB )</code></summary>

##### Parameters

> | name |  type   | data type  | description |
> |------|-----|---------|-----------------|
> | start_time |  required | int   | Start timestamp of requested info (in seconds from the Epoch) |
> | end_time |  required | int   | End timestamp of requested info (in seconds from the Epoch)  |

##### Responses

> | status code | response/body | response/body example |
> |------|-----|-----|
> | `1` | `application/json` | `{'timestamp': 1720361379,'body': {'params_ok' : True, 'interlock' : False,  'interlock check timestamp' : 1720361369, 'params check timestamp' : 1720361379}}` |
> | `0` | `text/plain;charset=UTF-8` | `"Something is wrong in the DB. No rows selected."` |

</details>

<details>
 <summary><code>GET</code> <code><b>/get_interlock</b></code>
 <code>(Get cahnnel params from the DB )</code></summary>

##### Parameters

> | name |  type   | data type  | description |
> |------|-----|---------|-----------------|

##### Responses

> | status code | response/body | response/body example |
> |------|-----|-----|-----|
> | `1` | `application/json` | `'body': {'params_ok' : True, 'interlock' : False,  'interlock check timestamp' : 1720361369, 'params check timestamp' : 1720361379}}` |
> | `0` | `text/plain;charset=UTF-8` | `"Something is wrong in the DB. No rows selected."` |

</details>

## Config

**[device]** section

| title | description | default value |
|------|-----|-----|
| `dbpath` | Path to DB. | `./monitor.db` |
| `channel_map_path` | Map between CAEN channels and DC layers. | `./channel_map.json` |
| `max_interlock_check_delta_time` | Time before interlock info expires. | `100` |
| `host` | host name of the DeviceBackend service | `localhost` |
| `protocol` | conversation protocol of the DeviceBackend | `tcp` |
| `port` | port of the DeviceBackend | `5561` |
| `address` | device backend address for binding | `${protocol}://*:${port}` |
