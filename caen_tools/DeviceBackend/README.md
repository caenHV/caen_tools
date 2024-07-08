# DeviceBackend
The microservice for execution of the tickets on the CAEN device.

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
 <summary><code>GET</code> <code><b>/get_params</b></code> 
 <code>(gets parameters of the CAEN device)</code></summary>


##### Parameters

> None

##### Responses

> | status code | response | response example |
> |------|-----|-----|
> | `1` | `application/json` | `{'timestamp': 1720361379, 'parameters': [{'board': 10001, 'channel': 0, 'voltage': 500}]}` |
> | `0` | `text/plain;charset=UTF-8` | `"Voltage is not set on the device"` |

</details>

<details>
 <summary><code>POST</code> <code><b>/set_voltage</b></code> 
 <code>(sets a voltage on the CAEN device)</code></summary>


##### Parameters

> | name |  type   | data type  | description |
> |------|-----|---------|-----------------|
> | target_voltage |  required | float   | Voltage as a relative float value for setting on the device |

##### Responses

> | status code | response/body | response/body example |
> |------|-----|-----|
> | `1` | `application/json` | `{'voltage': 1.01}` |
> | `0` | `text/plain;charset=UTF-8` | `"Voltage is not set on the device"` |

</details>

## Config

**[device]** section

| title | description | default value |
|------|-----|-----|
| `map_config` | DC Layer map config | `./test_config.json` |
| `host` | host name of the DeviceBackend service | `localhost` |
| `protocol` | conversation protocol of the DeviceBackend | `tcp` |
| `port` | port of the DeviceBackend | `5570` |
| `address` | device backend address for binding | `${protocol}://*:${port}` |