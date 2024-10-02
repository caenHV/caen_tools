# WebService

## Config

**[ws]** section

| title | description | example value |
|------|-----|-----|
| `receive_time` | Waiting time for response from other microservices [in seconds] (default is 10) | `10` |
| `device_backend` | DeviceBackend microservice address | `tcp://localhost:5555` |
| `monitor` | MonitorService microservice address | `tcp://localhost:5556` |
| `system_check` | SystemCheck microservice address | `tcp://localhost:5571` |
| `host` | WebService host | `0.0.0.0` |
| `port` | WebService port | `8000` |
| `loglevel` | logging level, can be {debug, info, warning, error} | `info` |
| `logfile` | logging file path (only console logs by default) | `./ws.log` |
| `subscribers` | subscribers emails list to get message on crash of webservice (by default nobody). addresses must be written one per line (not working inside docker now) | `Petrov@example.com`<br>`Ivanov@example.com` |
