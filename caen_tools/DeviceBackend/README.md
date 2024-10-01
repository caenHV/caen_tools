# DeviceBackend
The microservice for execution of the tickets on the CAEN device.

## API

<details>
 <summary><code>GET</code> <code><b>status</b></code> 
 <code>(gets a status of the microservice)</code></summary>

##### Parameters

> None

##### Responses

> | statuscode | response/body | response/body example |
> |------|-----|-----|
> | `1` | `application/json` | `{}` |

</details>

<details>
    <summary><code>GET</code> <code><b>params</b></code> 
    <code>(gets parameters of the CAEN device)</code></summary>
</details>

<details>
    <summary><code>GET</code> <code><b>get_voltage</b></code> 
    <code>(gets set voltage multiplier from the CAEN device)</code></summary>
</details>

<details>
<summary><code>POST</code> <code><b>set_voltage</b></code> 
<code>(sets a voltage on the CAEN device)</code></summary>


##### Parameters

> | name |  type   | data type  | description |
> |------|-----|---------|-----------------|
> | target_voltage |  required | float   | Voltage as a relative float value for setting on the device |


</details>

<details>
    <summary><code>POST</code> <code><b>down</b></code> 
    <code>(turns off power from CAEN device channels)</code></summary>
</details>

## Config

**[device]** section

| title:type | description | default value |
|------|-----|-----|
| `protocol:str` | conversation protocol of the DeviceBackend | `tcp` |
| `host:str` | host name of the DeviceBackend service | `localhost` |
| `port:int` | port of the DeviceBackend | `5570` |
| `address:str` | device backend address for binding | `${protocol}://*:${port}` |
| `map_config:str` | DC Layer map config | `${root_configs}/map_config.json` |
| `refresh_time:int` | number of seconds to update data on board | `1` |
| `fake_board:bool` | use fake (`true`) or real (`false`) board interface | `true` |
| `ramp_up_speed:int` | base speed of voltage ramping up, V/s | `10` |
| `ramp_down_speed:int` | base speed of voltage ramping down, V/s | `100` |
| `is_high_Imon_range:bool` | use IMonH (`true`) of IMonL (`false`), details in V6533 technical information | `true` |
| `loglevel:str` | logging frequency (`debug`, `info`, `warining`, `error`) | `info` |
| `logfile:str` | logging file path |  |
