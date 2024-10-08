# Monitor

The microservice for writing CAEN channel parameters
and retrieveing historical information.

## API

<details>
 <summary><code>GET</code> <code><b>status</b></code>
 <code>(gets a status of the microservice)</code></summary>

##### Parameters

> None

</details>

<details>
 <summary><code>Post</code> <code><b>send_params</b></code> 
 <code>(writes parameters of the CAEN device to the own DB and online database)</code></summary>

##### Parameters

> | name |  type   | data type  | description |
> |------|-----|---------|-----------------|
> | channel_id |  required | str   | Channel id |
> | channel_parameters |  required | dict   | Channel parameters from CAEN board |

</details>

<details>
 <summary><code>GET</code> <code><b>get_params</b></code>
 <code>(retrieves historical channel parameters from the own DB)</code></summary>

##### Parameters

> | name |  type   | data type  | description |
> |------|-----|---------|-----------------|
> | start_time |  required | int   | Start timestamp of requested info (in seconds from the Epoch) |
> | end_time |  optional | int   | End timestamp of requested info (in seconds from the Epoch), default is current timestamp  |

</details>

## Config

**[monitor]** section

| title | description | default value |
|------|-----|-----|
| `protocol` | conversation protocol of the DeviceBackend | `tcp` |
| `host` | host name of the DeviceBackend service | `localhost` |
| `port` | port of the DeviceBackend | `5561` |
| `address` | device backend address for binding | `${protocol}://*:${port}` |
| `dbpath` | Path to DB | `./monitor.db` |
| `param_file_path` | Online database parses this file | `/home/cmd3daq/caendc/data/last_measurement.json` |
| `max_interlock_check_delta_time` | Time before interlock info expires. | `100` |
| `loglevel:str` | logging frequency (`debug`, `info`, `warining`, `error`) | `info` |
| `logfile:str` | logging file path |  |
