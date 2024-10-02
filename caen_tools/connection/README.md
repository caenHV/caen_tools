# connection
A simple implementation of the server and client (based on zmq) that is used by all microservices.

### [client.py](./client.py)
* asynchronous client implementation
* sends and recieves **Receipts** from `zmq.DEALER` socket

### [server.py](./server.py)
* asynchronous server implementation
* recieves and sends **Receipts** from `zmq.ROUTER` socket

-----------

[**Receipt**](../utils/) is the messaging protocol between all microservices