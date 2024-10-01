# configs
A set of default config files needed for running microservices

* [config.ini](./config.ini)
  * main config file that contain metadata for all microservices
  * detailed description of the fields can be seen in the following microservices README's

* [map_config.json](./test_config.json)
  * defines the default settings for the CAEN device
  * it is used by [`caen_setup`](https://github.com/caenHV/Setup) module, so that file must match the structure defined there

* [max_currents_map.json](./max_currents_map.json)
  * defines the current limits used by HealthControl in SystemCheck microservice
