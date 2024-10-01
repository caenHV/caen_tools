# System check

A simple service that verifies CAEN data from DeviceBackend in loop sends it in Monitor

### api


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


### scripts

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