# WebService

## Config

**[ws]** section

| title | description | example value |
|------|-----|-----|
| `receive_time` | Waiting time for response from other microservices [in seconds] (default is 10) | `10` |
| `device_backend` | DeviceBackend microservice address | `tcp://localhost:5555` |
| `monitor` | Monitor microservice address | `tcp://localhost:5556` |
| `host` | WebService host | `0.0.0.0` |
| `port` | WebService port | `8000` |
| `loglevel` | logging level, can be {debug, info, warning, error} | `info` |
| `logfile` | logging file path (only console logs by default) | `./ws.log` |
| `subscribers` | subscribers emails list to get device statuses (by default nobody). addresses must be written one per line | `Petrov@example.com`<br>`Ivanov@example.com` |
