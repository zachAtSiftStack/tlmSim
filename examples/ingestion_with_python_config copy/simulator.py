import logging
import random
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from motor import Motor

from sift_py.ingestion.channel import (
    bit_field_value,
    double_value,
    enum_value,
    int32_value,
    string_value,
)
from sift_py.ingestion.service import IngestionService

READINGS_FREQUENCY_HZ = 10  # 10Hz for regular telemetry
CONTROL_LOOP_FREQUENCY_HZ = 50  # 50Hz for low-level control
PUB_TELEMETRY_FREQUENCY_HZ = 10  # 10Hz for telemetry publishing

GPIO_12V = 0b00000001        # Bit 0
GPIO_CHARGE = 0b00000010     # Bit 1
GPIO_LED_1 = 0b00000100      # Bit 2
GPIO_LED_2 = 0b00001000      # Bit 3
GPIO_CAMERA_1 = 0b00010000   # Bit 4
GPIO_CAMERA_2 = 0b00100000   # Bit 5
GPIO_HEATER_1 = 0b01000000   # Bit 6
GPIO_HEATER_2 = 0b10000000   # Bit 7


class VehicleState:
    FAULT = 0
    IDLE = 1
    FORWARD_DRIVE = 2
    REVERSE_DRIVE = 3
    LEFT_TURN = 4
    RIGHT_TURN = 5
    CHARGING = 6
    CAMERA_1 = 7
    CAMERA_2 = 8

class Simulator:
    def __init__(self, ingestion_service: IngestionService, environment_temperature=25.0, seed=1, faults=False):
        self.ingestion_service = ingestion_service

        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)

        self.state = VehicleState.IDLE
        self.previous_state = self.state  # Track the previous state
        self.environment_temperature = environment_temperature
        self.seed = seed
        self.faults = faults
        self.motors = {
            "motor_a": Motor("motor_a", environment_temperature=self.environment_temperature, seed=1*seed),
            "motor_b": Motor("motor_b", environment_temperature=self.environment_temperature, seed=2*seed),
            "motor_c": Motor("motor_c", environment_temperature=self.environment_temperature, seed=3*seed),
            "motor_d": Motor("motor_d", environment_temperature=self.environment_temperature, seed=4*seed),
        }
        if self.faults:
            self.motors['motor_b'].inject_fault()
        self._stop_event = threading.Event()

    def log_event(self, message: str):
        """Logs an event and sends it to the ingestion service."""
        timestamp = datetime.now(timezone.utc)
        log_channel_value = {"channel_name": "state_log", "value": string_value(message)}
        
        # Ingest the log message as telemetry data
        self.ingestion_service.try_ingest_flows(
            {
                "flow_name": "state_logs",  # Make sure this flow is defined in your TelemetryConfig
                "timestamp": timestamp,
                "channel_values": [log_channel_value],
            }
        )

        self.logger.info(f"{timestamp} - {message}")

    def update_gpio_state(self):
        """Update the GPIO state based on the vehicle's current state."""
        gpio_state = 0b00000000  # Start with all bits off

        if not self.state == VehicleState.IDLE:
            gpio_state |= GPIO_12V  # 12V power on during driving

        if self.state == VehicleState.CHARGING:
            gpio_state |= GPIO_CHARGE  # Charging bit on during charging
        if self.state == VehicleState.CAMERA_1:
            gpio_state |= GPIO_CAMERA_1 | GPIO_LED_1  # Camera 1 and LED 1 on
        if self.state == VehicleState.CAMERA_2:
            gpio_state |= GPIO_CAMERA_2 | GPIO_LED_2  # Camera 2 and LED 2 on

        # Convert the int gpio_state to a single byte
        return gpio_state.to_bytes(1, byteorder='big')

    def run(self, duration=60):
        start_time = time.time()
        end_time = start_time + duration

        last_reading_time = start_time
        last_control_loop_time = start_time
        last_publish_time = start_time

        readings_interval_s = 1 / READINGS_FREQUENCY_HZ
        control_loop_interval_s = 1 / CONTROL_LOOP_FREQUENCY_HZ

        while time.time() < end_time and not self._stop_event.is_set():
            current_time = time.time()

            if current_time - last_control_loop_time >= control_loop_interval_s:
                self.control_loop()
                last_control_loop_time = current_time

            # Publish telemetry at the rate specified by PUB_TELEMETRY_FREQUENCY_HZ
            if current_time - last_publish_time >= 1 / PUB_TELEMETRY_FREQUENCY_HZ:
                self.publish_telemetry()
                last_publish_time = current_time

        self.logger.info("Completed simulation.")

    def stop(self):
        """Sets the stop event to terminate the run loop."""
        self._stop_event.set()

    def control_loop(self):
        if self.state != self.previous_state:
            # Handle state transitions
            if self.state == VehicleState.FORWARD_DRIVE:
                for motor in self.motors.values():
                    motor.start(direction=1)
                self.log_event("Vehicle transitioned to FORWARD_DRIVE")
            elif self.state == VehicleState.REVERSE_DRIVE:
                for motor in self.motors.values():
                    motor.start(direction=-1)
                self.log_event("Vehicle transitioned to REVERSE_DRIVE")
            elif self.state == VehicleState.LEFT_TURN:
                # Assuming left turn would involve only certain motors or reduced power
                self.motors['motor_a'].start(direction=1)
                self.motors['motor_b'].start(direction=1)
                self.motors['motor_c'].start(direction=-1)
                self.motors['motor_d'].start(direction=-1)
                self.log_event("Vehicle transitioned to LEFT_TURN")
            elif self.state == VehicleState.RIGHT_TURN:
                # Assuming right turn would involve only certain motors or reduced power
                self.motors['motor_a'].start(direction=-1)
                self.motors['motor_b'].start(direction=-1)
                self.motors['motor_c'].start(direction=1)
                self.motors['motor_d'].start(direction=1)
                self.log_event("Vehicle transitioned to RIGHT_TURN")
            elif self.state == VehicleState.IDLE:
                for motor in self.motors.values():
                    motor.stop()
                self.log_event("Vehicle transitioned to IDLE")
            elif self.state == VehicleState.CHARGING:
                # Simulate charging, possibly stopping all motors
                for motor in self.motors.values():
                    motor.stop()
                self.log_event("Vehicle transitioned to CHARGING")
            elif self.state == VehicleState.CAMERA_1:
                # Simulate camera 1 activity, motors might be stationary
                for motor in self.motors.values():
                    motor.stop()
                self.log_event("Vehicle transitioned to CAMERA_1")
            elif self.state == VehicleState.CAMERA_2:
                # Simulate camera 2 activity, motors might be stationary
                for motor in self.motors.values():
                    motor.stop()
                self.log_event("Vehicle transitioned to CAMERA_2")
            elif self.state == VehicleState.FAULT:
                # Handle fault state, perhaps stopping all motors
                for motor in self.motors.values():
                    motor.stop()
                self.log_event("Vehicle transitioned to FAULT")
        
        # Update the GPIO state whenever the vehicle state changes
        self.update_gpio_state()
        
        # Update all motors with the current environment temperature
        for motor in self.motors.values():
            motor.update(environment_temperature=self.environment_temperature)

        # Update the previous state
        self.previous_state = self.state

    def log_state_transition(self, from_state, to_state):
        """Log state transition to state_log."""
        timestamp = datetime.now(timezone.utc)
        state_transition_message = f"State transition from {self.state_name(from_state)} to {self.state_name(to_state)}"
        self.ingestion_service.try_ingest_flows(
            {
                "flow_name": "state_logs",
                "timestamp": timestamp,
                "channel_values": [
                    {"channel_name": "state_log", "value": string_value(state_transition_message)},
                ],
            }
        )

    def publish_sys_log(self):
        """Generate and publish a random system log to sys_log."""
        timestamp = datetime.now(timezone.utc)
        sys_log_messages = [
            "kernel: [123456.789012] Initializing cgroup subsys cpuset",
            "kernel: [123456.789012] Initializing cgroup subsys cpu",
            "kernel: [123456.789012] Initializing cgroup subsys cpuacct",
            "sshd[12345]: Server listening on 0.0.0.0 port 22.",
            "sshd[12345]: Server listening on :: port 22.",
            "systemd[1]: Started ACPI event daemon.",
            "kernel: [123456.789012] EXT4-fs (sda1): re-mounted. Opts: (null)",
            "systemd-logind[6789]: New seat seat0.",
            "systemd-logind[6789]: Watching system buttons on /dev/input/event1 (Power Button)",
            "systemd-logind[6789]: Watching system buttons on /dev/input/event0 (Lid Switch)",
            "systemd[1]: Started Network Manager.",
            "NetworkManager[2345]: <info>  [1234567890.123] manager: NetworkManager state is now CONNECTED_GLOBAL",
            "kernel: [123456.789012] IPv6: ADDRCONF(NETDEV_UP): eth0: link is not ready",
            "kernel: [123456.789012] eth0: Link is Up - 100Mbps Full Duplex",
            "kernel: [123456.789012] IPv6: ADDRCONF(NETDEV_CHANGE): eth0: link becomes ready",
            "systemd[1]: Starting Authorization Manager...",
            "systemd[1]: Started Authorization Manager.",
            "systemd[1]: Starting Virtualization daemon...",
            "systemd[1]: Started Virtualization daemon.",
            "systemd[1]: Starting LSB: automatic crash report generation...",
            "apport[3456]:  * Starting automatic crash report generation: apport",
            "systemd[1]: Started LSB: automatic crash report generation.",
            "kernel: [123456.789012] Bluetooth: Core ver 2.22",
            "kernel: [123456.789012] Bluetooth: HCI device and connection manager initialized",
            "kernel: [123456.789012] Bluetooth: HCI socket layer initialized",
            "kernel: [123456.789012] Bluetooth: L2CAP socket layer initialized",
            "kernel: [123456.789012] Bluetooth: SCO socket layer initialized",
            "systemd[1]: Reached target Bluetooth.",
            "kernel: [123456.789012] random: crng init done",
            "systemd[1]: Starting Load Kernel Modules...",
            "systemd[1]: Starting Apply Kernel Variables...",
            "systemd[1]: Starting udev Coldplug all Devices...",
            "systemd[1]: Starting Create Static Device Nodes in /dev...",
            "systemd[1]: Started Load Kernel Modules.",
            "systemd[1]: Started Apply Kernel Variables.",
            "systemd[1]: Started Create Static Device Nodes in /dev.",
            "systemd[1]: Starting udev Kernel Device Manager...",
            "systemd[1]: Started udev Kernel Device Manager.",
            "systemd[1]: Started udev Coldplug all Devices.",
            "systemd[1]: Reached target Local File Systems (Pre).",
            "systemd[1]: Reached target Local File Systems.",
            "systemd[1]: Starting Create Volatile Files and Directories...",
            "systemd[1]: Starting Network Time Synchronization...",
            "systemd[1]: Started Network Time Synchronization.",
            "systemd[1]: Started Create Volatile Files and Directories.",
            "systemd[1]: Starting Update UTMP about System Boot/Shutdown...",
            "systemd[1]: Started Update UTMP about System Boot/Shutdown.",
            "systemd[1]: Reached target System Initialization.",
            "systemd[1]: Started Daily Cleanup of Temporary Directories.",
            "systemd[1]: Started Daily apt download activities.",
            "systemd[1]: Started Daily apt upgrade and clean activities.",
            "systemd[1]: Reached target Timers.",
            "systemd[1]: Listening on D-Bus System Message Bus Socket.",
            "systemd[1]: Reached target Sockets.",
            "systemd[1]: Reached target Basic System.",
            "systemd[1]: Starting Avahi mDNS/DNS-SD Stack...",
            "systemd[1]: Started Avahi mDNS/DNS-SD Stack.",
            "avahi-daemon[7890]: Joining mDNS multicast group on interface eth0.IPv6 with address fe80::1234:5678:9abc:def0.",
            "avahi-daemon[7890]: New relevant interface eth0.IPv6 for mDNS.",
            "avahi-daemon[7890]: Network interface enumeration completed.",
            "avahi-daemon[7890]: Server startup complete. Host name is rover.local. Local service cookie is 123456789.",
            "systemd[1]: Started OpenSSH Daemon.",
            "sshd[12345]: Server listening on 0.0.0.0 port 22.",
            "sshd[12345]: Server listening on :: port 22.",
            "systemd[1]: Started LSB: Apache2 web server.",
            "apache2[23456]: AH00163: Apache/2.4.29 (Ubuntu) configured -- resuming normal operations",
            "apache2[23456]: AH00094: Command line: '/usr/sbin/apache2'",
            "systemd[1]: Started Login Service.",
            "systemd[1]: Starting Hold until boot process finishes up...",
            "systemd[1]: Started Hold until boot process finishes up.",
            "systemd[1]: Starting Terminate Plymouth Boot Screen...",
            "systemd[1]: Started Terminate Plymouth Boot Screen.",
            "systemd[1]: Started Console Getty.",
            "systemd[1]: Reached target Login Prompts.",
            "systemd[1]: Starting Set console scheme...",
            "systemd[1]: Started Set console scheme.",
            "systemd[1]: Reached target Multi-User System.",
            "systemd[1]: Starting Update UTMP about System Runlevel Changes...",
            "systemd[1]: Started Update UTMP about System Runlevel Changes.",
            "systemd[1]: Reached target Graphical Interface.",
            "systemd[1]: Starting GNOME Display Manager...",
            "systemd[1]: Started GNOME Display Manager.",
            "systemd[1]: Starting Hostname Service...",
            "systemd[1]: Started Hostname Service.",
            "gdm3[34567]: Gdm: GdmDisplay: display lasted 0.1 seconds",
            "systemd[1]: Stopping User Manager for UID 1000...",
            "systemd[1]: Starting User Manager for UID 1000...",
            "systemd[1]: Started User Manager for UID 1000.",
            "systemd[1]: Started Session c1 of user root.",
            "systemd[1]: Starting Network Manager Script Dispatcher Service...",
            "systemd[1]: Started Network Manager Script Dispatcher Service.",
            "systemd[1]: Starting LSB: Record successful boot for GRUB...",
            "systemd[1]: Started LSB: Record successful boot for GRUB.",
            "systemd[1]: Starting Cleanup of Temporary Directories...",
            "systemd[1]: Started Cleanup of Temporary Directories.",
            "rsyslogd: [origin software=\"rsyslogd\" swVersion=\"8.32.0\" x-pid=\"11234\" x-info=\"http://www.rsyslog.com\"] rsyslogd was HUPed",
            "ntpd[2345]: ntpd 4.2.8p10@1.3728-o (1): Starting",
            "ntpd[2345]: Command line: ntpd -g -u ntp:ntp",
            "ntpd[2345]: proto: precision = 0.072 usec (-24)",
            "ntpd[2345]: Listen and drop on 0 v6wildcard [::]:123",
            "ntpd[2345]: Listen and drop on 1 v4wildcard 0.0.0.0:123",
            "ntpd[2345]: Listen normally on 2 lo 127.0.0.1:123",
            "ntpd[2345]: Listen normally on 3 eth0 192.168.1.100:123",
            "ntpd[2345]: Listen normally on 4 lo [::1]:123",
            "ntpd[2345]: Listen normally on 5 eth0 [fe80::1234:5678:9abc:def0%eth0]:123",
            "ntpd[2345]: Listening on routing socket on fd #22 for interface updates",
            "ntpd[2345]: Soliciting pool server 192.168.1.1",
            "ntpd[2345]: ntpd: time slew +0.001234 s",
        ]

        random_message = random.choice(sys_log_messages)
        self.ingestion_service.try_ingest_flows(
            {
                "flow_name": "sys_logs",
                "timestamp": timestamp,
                "channel_values": [
                    {"channel_name": "sys_log", "value": string_value(random_message)},
                ],
            }
        )

    def publish_telemetry(self):
        timestamp = datetime.now(timezone.utc)

        channel_values = []

        for motor_name, motor in self.motors.items():
            motor_telemetry = motor.get_telemetry()

            # Append telemetry data for each motor with correct component and channel name
            channel_values.extend([
                {"channel_name": "encoder", "component": f"{motor_name}", "value": int32_value(motor_telemetry[f"{motor_name}_encoder"])},
                {"channel_name": "current", "component": f"{motor_name}", "value": double_value(motor_telemetry[f"{motor_name}_current"])},
                {"channel_name": "temperature", "component": f"{motor_name}", "value": double_value(motor_telemetry[f"{motor_name}_temperature"])},
            ])

        # Additional telemetry (not related to individual motors)
        channel_values.append({"channel_name": "vehicle_state", "value": enum_value(self.state)})

        self.ingestion_service.try_ingest_flows(
            {
                "flow_name": "vehicle_10_hz",
                "timestamp": timestamp,
                "channel_values": channel_values,
            }
        )

        self.ingestion_service.try_ingest_flows(
            {
                "flow_name": "vehicle_50_hz",
                "timestamp": timestamp,
                "channel_values": [
                    {"channel_name": "voltage", "value": int32_value(12)},
                    {"channel_name": "gpio", "value": bit_field_value(self.update_gpio_state())},  # Include GPIO state
                ],
            }
        )

        # Publish a random system log at a reduced rate
        if random.random() < 0.1:  # 10% chance to publish a sys_log each time
            self.publish_sys_log()

    def command(self, command: str):

        if command == "forward":
            self.state = VehicleState.FORWARD_DRIVE
            self.logger.info("Command: FORWARD_DRIVE - Vehicle in Forward Drive")
            self.log_event("Command received: START")
        elif command == "idle":
            self.state = VehicleState.IDLE
            self.logger.info("Command: IDLE - Vehicle Idle")
            self.log_event("Command received: STOP")
        elif command == "reverse":
            self.state = VehicleState.REVERSE_DRIVE
            self.logger.info("Command: REVERSE_DRIVE - Vehicle in Reverse Drive")
            self.log_event("Command received: REVERSE")
        elif command == "left_turn":
            self.state = VehicleState.LEFT_TURN
            self.logger.info("Command: LEFT_TURN - Vehicle turning left")
            self.log_event("Command received: LEFT TURN")
        elif command == "right_turn":
            self.state = VehicleState.RIGHT_TURN
            self.logger.info("Command: RIGHT_TURN - Vehicle turning right")
            self.log_event("Command received: RIGHT TURN")
        elif command == "charge":
            self.state = VehicleState.CHARGING
            self.logger.info("Command: CHARGING - Vehicle is charging")
            self.log_event("Command received: CHARGING")
        elif command == "camera_1":
            self.state = VehicleState.CAMERA_1
            self.logger.info("Command: CAMERA_1 - Operating camera 1")
            self.log_event("Command received: CAMERA 1")
        elif command == "camera_2":
            self.state = VehicleState.CAMERA_2
            self.logger.info("Command: CAMERA_2 - Operating camera 2")
            self.log_event("Command received: CAMERA 2")
        elif command == "inject_fault":
            self.state = VehicleState.FAULT
            self.logger.info("Command: FAULT - Fault")
            self.log_event("Command received: INJECT FAULT")


    def execute_command_sequence(self, command_sequence: List[tuple]):
        time.sleep(1)
        for command, delay in command_sequence:
            self.command(command)
            time.sleep(delay)

    @staticmethod
    def state_name(state):
        """Return the string name of the vehicle state."""
        if state == VehicleState.IDLE:
            return "Idle"
        elif state == VehicleState.FORWARD_DRIVE:
            return "Forward Drive"
        elif state == VehicleState.REVERSE_DRIVE:
            return "Reverse Drive"
        elif state == VehicleState.FAULT:
            return "Fault"
        else:
            return "Unknown"

