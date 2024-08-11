# tlmSim
Telemetry Sim for demo purposes

## Setup

1. Configure .env file
2. Setup venv

```bash
python3 -m venv tlmSim
source tlmSim/bin/activate
```

3. Install Required Modules

```bash
pip3 install -r requirements.txt
```


## Prompt

I need to create a vehicle simulation for streaming data into sift.

This veichle simulation must have data that seems atleast relativly realistic.
* Need to make sense to an engineer and non-technical individuals. To achive this use an easy naming structure for channels and make the data do something relevant. 
* Example of relevant data:
    * State machine going from idle -> forward drive causes current to be applied to all 4 wheels, as well the motor feedback is showing the expected increments.
    * A fault can be injected into the system such that when the vehicle is commanded forward from idle -> forward drive a wheel is stuck. The stuck wheel is in a state that it should drive but no upticks on the encoder are seen and the current is at the stall current.

The simulator needs to be able to run from pre-programed sequences. The sequences must be able to:
* Command the vehicle
* Effect the environment the vehcile is in
* Inject an error into the vehicle.

I want most vehicle telemetry to be published at 10Hz. One process on the vehicle should be running at 50Hz. That process should be the one controlling low level operation of the vehicle. It takes commands from the main state machine. 
