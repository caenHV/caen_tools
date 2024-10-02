# System check

A simple service that verifies CAEN data from DeviceBackend in loop sends it in Monitor

## api


<details>
 <summary><code>GET</code> <code><b>status</b></code>
 <code>(gets a status of the microservice)</code></summary>

##### Parameters

> None

</details>


<details>
 <summary><code>GET</code> <code><b>status_autopilot</b></code>
 <code>(gets a status of the autopilot)</code></summary>

##### Parameters

> None

</details>


<details>
 <summary><code>POST</code> <code><b>set_autopilot</b></code>
 <code>(sets a status of the autopilot)</code></summary>

</details>

### Config

**[check]** section
* Geneal settings of SystemCheck service

| title | description | default value |
|------|-----|-----|
| `protocol:str` | conversation protocol of the SystemCheck | `tcp` |
| `host:str` | host name of the SystemCheck service | `localhost` |
| `port:int` | port of the SystemCheck | `5571` |
| `address:str` | SystemCheck address for binding | `${protocol}://*:${port}` |
| `device_backend:str` | DeviceBackend service address for connection | `${device:protocol}://${device:host}:${device:port}` |
| `monitor:str` | MonitorService address for connection | `${monitor:protocol}://${monitor:host}:${monitor:port}` |
| `interlock_db_uri:str` | interlock database credentials (postgres starts with `postgres://` or reading from text file starts with `fake://`)  | `fake://./interlockfile.txt` |
| `loglevel:str` | logging frequency (`debug`, `info`, `warining`, `error`) | `info` |
| `logfile:str` | logging file path |  |

**[check.loader]** section
* LoaderControl script settings (transfers data from DevBackend to Monitor) 

| title | description | default value |
|------|-----|-----|
| `enable:bool` | enable/disable running this script by default | `true` |
| `repeat_every:int` | script execution frequency (in seconds) | `1` |

**[check.health]** section
* HealthControl script settings (checks the current parameters of the device)

| title | description | default value |
|------|-----|-----|
| `enable:bool` | enable/disable running this script by default | `true` |
| `repeat_every:int` | script execution frequency (in seconds) | `1` |
| `max_currents_map_path:str` | config containing necessary information for parameter checks | `${root_configs}/max_currents_map.json` |

**[check.interlock]** section
* InterlockControl script settings (monitors the status of interlock and sets given state in MChSworker)

| title | description | default value |
|------|-----|-----|
| `enable:bool` | enable/disable running this script by default | `true` |
| `repeat_every:int` | script execution frequency (in seconds) | `1` |

**[check.autopilot]** section
* Autopilot general settings (automatic control of the target voltage without user)

| title | description | default value |
|------|-----|-----|
| `enable:bool` | enable/disable running this script by default | `true` |
| `target_voltage:float` | autopilot maintains target level of the voltage in normal situation | `1` |
| `voltage_modifier:float` | autopilot reduces voltage by this modifier during certain contitions | `0.4` |

**[check.autopilot.relax]** section
* RelaxControl (included in autopilot scripts group) settings (reduces target voltage during interlock)

| title | description | default value |
|------|-----|-----|
| `enable:bool` | enable/disable running this script by default | `${check.autopilot:enable}` |
| `repeat_every:int` | script execution frequency (in seconds) | `15` |
| `target_voltage:float` | RelaxControl maintains target level of the voltage in normal situation | `${check.autopilot:voltage_modifier}` |
| `voltage_modifier:float` | RelaxControl reduces voltage by this modifier during certain contitions | `${check.autopilot:target_voltage}` |

**[check.autopilot.reducer]** section
* ReducerControl (included in autopilot scripts group) settings (reduces target voltage periodically)

| title | description | default value |
|------|-----|-----|
| `enable:bool` | enable/disable running this script by default | `${check.autopilot:enable}` |
| `repeat_every:int` | script execution frequency (in seconds) | `1800` |
| `reducing_period:int` | voltage reducing duration (in seconds) | `60` |
| `target_voltage:float` | ReducerControl maintains target level of the voltage in normal situation | `${check.autopilot:voltage_modifier}` |
| `voltage_modifier:float` | ReducerControl reduces voltage by this modifier during certain contitions | `${check.autopilot:target_voltage}` |


**[check.mchs]** section
* MChS general settings

| title | description | default value |
|------|-----|-----|
| `host:str` |  | `127.0.0.1` |
| `port:int` |  | `22` |
| `client_id:int` |  | `10` |



## scripts

* *health.py*
  * Parameters health control. Checks the CAEN device parameters in loop
* *interlock.py*
  * Retrieves interlock value in loop. Fill up MChS status
* *loader.py*
  * Transfers parameters from DeviceBackend to MonitorService in loop
* *manager.py*
  * Watches to other script statuses in loop
* *mchswork.py*
  * (not the script) stores statuses of the systems need for mchs
* *metascript.py*
  * Abstract base class for all scripts
* *reducer.py*
  * Periodically reduces voltage level (if no interlock)
  * The part of the autopilot
* *relax.py*
  * Reduces voltage level during interlock
  * The part of the autopilot
* *structures.py*
  * a set of utility structures