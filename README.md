# Microservices concept

Conceptual implementation of the architecture for CAEN control

## List of microservices

### WebService
* `/set_ticket/{name}`
  * POST request to execute ticket
  * receives args related to the ticket
  * preliminary inspects the ticket (quality, necessary args and so on)
* `/list_tickets`
  * GET request to return the list of available tickets
  * Returns JSON: List[Ticket]
  * Useful for `Frontend` part
* `/ws`
  * WebSocket connection to receive news from the `ProxyService`
  * Useful for `Frontend` part
* `/`
  * root path is `Frontend` page for ticket setting

### ProxyService
Proxy Queue to forward tickets to `DeviceBackend`
* Manipulates with JSON ticket representations
* `WebService` / `MonitorService` → `ProxyService` → `DeviceBackend`
* Has `PUB` socket output for every proxying message

### DeviceBackend
Recieves JSON tickets and executes them


### MonitorService
Sends special `MonitorTicket` to the `DeviceBackend`, recieves parameters of the device and manipulates them.


### CAENLib
Python module containing:
* List of available tickets
* Implementation of the tickets

## Helpful links
* [ZMQ Guide](https://zguide.zeromq.org/)
* [ZMQ Socket API](https://zeromq.org/socket-api/)
* [PyZMQ API](https://pyzmq.readthedocs.io/en/latest/api/zmq.html)