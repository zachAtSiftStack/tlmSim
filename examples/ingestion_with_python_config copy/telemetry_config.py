from pathlib import Path
from sift_py.ingestion.channel import (
    ChannelBitFieldElement,
    ChannelConfig,
    ChannelDataType,
    ChannelEnumType,
)
from sift_py.ingestion.config.telemetry import FlowConfig, TelemetryConfig
from sift_py.ingestion.config.yaml.load import load_named_expression_modules
from sift_py.ingestion.rule.config import (
    RuleActionCreateDataReviewAnnotation,
    RuleConfig,
)

EXPRESSION_MODULES_DIR = Path().joinpath("expression_modules")

def vehicle_telemetry_config() -> TelemetryConfig:

    def motor_encoder_channel(motor: str) -> ChannelConfig:
        return ChannelConfig(
            name=f"encoder",
            data_type=ChannelDataType.INT_32,
            description=f"Hall encoder value for motor {motor}",
            component=f"motor_{motor}",  # Individual motor component
        )
        
    def motor_current_channel(motor: str) -> ChannelConfig:
        return ChannelConfig(
            name=f"current",
            data_type=ChannelDataType.DOUBLE,
            description=f"Current value for motor {motor}",
            unit="mA",
            component=f"motor_{motor}",  # Individual motor component
        )
        
    def motor_temp_channel(motor: str) -> ChannelConfig:
        return ChannelConfig(
            name=f"temperature",
            data_type=ChannelDataType.DOUBLE,
            description=f"Temperature value for motor {motor}",
            unit="C",
            component=f"motor_{motor}",  # Individual motor component
        )

    named_expressions = load_named_expression_modules(
        [
            EXPRESSION_MODULES_DIR.joinpath("kinematics.yml"),
            EXPRESSION_MODULES_DIR.joinpath("string.yml"),
        ]
    )

    state_log_channel = ChannelConfig(
        name="state_log",
        data_type=ChannelDataType.STRING,
        description="State machine transitions log",
    )

    sys_log_channel = ChannelConfig(
        name="sys_log",
        data_type=ChannelDataType.STRING,
        description="Random system logs",
    )

    # Motor channels
    # This will contain all 4 vehicle motors
    # Hall encoder values, current values, and temperature values

    motor_a_encoder_channel = motor_encoder_channel("a")
    motor_b_encoder_channel = motor_encoder_channel("b")
    motor_c_encoder_channel = motor_encoder_channel("c")
    motor_d_encoder_channel = motor_encoder_channel("d")

    motor_a_current_channel = motor_current_channel("a")
    motor_b_current_channel = motor_current_channel("b")
    motor_c_current_channel = motor_current_channel("c")
    motor_d_current_channel = motor_current_channel("d")

    motor_a_temp_channel = motor_temp_channel("a")
    motor_b_temp_channel = motor_temp_channel("b")
    motor_c_temp_channel = motor_temp_channel("c")
    motor_d_temp_channel = motor_temp_channel("d")

    voltage_channel = ChannelConfig(
        name="voltage",
        data_type=ChannelDataType.INT_32,
        description="Voltage at source",
        unit="Volts",
    )
    vehicle_state_channel = ChannelConfig(
        name="vehicle_state",
        data_type=ChannelDataType.ENUM,
        description="Vehicle state",
        enum_types=[
            ChannelEnumType(name="Fault", key=0),
            ChannelEnumType(name="Idle", key=1),
            ChannelEnumType(name="Forward Drive", key=2),
            ChannelEnumType(name="Reverse Drive", key=3),
            ChannelEnumType(name="Left Turn", key=4),
            ChannelEnumType(name="Right Turn", key=5),
            ChannelEnumType(name="Charging", key=6),
            ChannelEnumType(name="Camera 1", key=7),
            ChannelEnumType(name="Camera 2", key=8),
        ],
    )

    """
    GPIO_12V = 0b00000001        # Bit 0
    GPIO_CHARGE = 0b00000010     # Bit 1
    GPIO_LED_1 = 0b00000100      # Bit 2
    GPIO_LED_2 = 0b00001000      # Bit 3
    GPIO_CAMERA_1 = 0b00010000   # Bit 4
    GPIO_CAMERA_2 = 0b00100000   # Bit 5
    GPIO_HEATER_1 = 0b01000000   # Bit 6
    GPIO_HEATER_2 = 0b10000000   # Bit 7
    """
    gpio_channel = ChannelConfig(
        name="gpio",
        data_type=ChannelDataType.BIT_FIELD,
        description="GPIO pin states",
        bit_field_elements=[
            ChannelBitFieldElement(name="12v", index=0, bit_count=1),         # Bit 0 for 12V
            ChannelBitFieldElement(name="charge", index=1, bit_count=1),      # Bit 1 for charge
            ChannelBitFieldElement(name="led_1", index=2, bit_count=1),       # Bit 2 for LED 1
            ChannelBitFieldElement(name="led_2", index=3, bit_count=1),       # Bit 3 for LED 2
            ChannelBitFieldElement(name="camera_1", index=4, bit_count=1),    # Bit 4 for Camera 1
            ChannelBitFieldElement(name="camera_2", index=5, bit_count=1),    # Bit 5 for Camera 2
            ChannelBitFieldElement(name="heater_1", index=6, bit_count=1),    # Bit 6 for Heater 1
            ChannelBitFieldElement(name="heater_2", index=7, bit_count=1),    # Bit 7 for Heater 2
        ],
    )

    # Define Rules (optional, based on your needs)
    overheating_rule = RuleConfig(
        name="overheating",
        description="Checks for vehicle overheating",
        expression='$1 == "Forward Drive" && $2 > 80',
        channel_references=[
            {"channel_reference": "$1", "channel_identifier": vehicle_state_channel.fqn()},
            {"channel_reference": "$2", "channel_config": voltage_channel},
        ],
        action=RuleActionCreateDataReviewAnnotation(),
    )

    kinetic_energy_rule = RuleConfig(
        name="kinetic_energy",
        description="Tracks high energy output while in motion",
        expression=named_expressions["kinetic_energy_gt"],
        channel_references=[
            {"channel_reference": "$1", "channel_config": voltage_channel},
        ],
        sub_expressions={"$mass": 10, "$threshold": 470},
        action=RuleActionCreateDataReviewAnnotation(tags=["vehicle"]),
    )

    failure_rule = RuleConfig(
        name="failure",
        description="Checks for failures reported by logs",
        expression=named_expressions["log_substring_contains"],
        channel_references=[
            {"channel_reference": "$1", "channel_config": sys_log_channel},
        ],
        sub_expressions={"$sub_string": "failure"},
        action=RuleActionCreateDataReviewAnnotation(tags=["vehicle", "failure"]),
    )

    # Define Flows
    return TelemetryConfig(
        asset_name="rover_1",
        ingestion_client_key="rover_1",
        rules=[overheating_rule, kinetic_energy_rule, failure_rule],
        flows=[
            FlowConfig(
                name="vehicle_10_hz",
                channels=[
                    vehicle_state_channel,
                    motor_a_encoder_channel,
                    motor_b_encoder_channel,
                    motor_c_encoder_channel,
                    motor_d_encoder_channel,
                    motor_a_current_channel,
                    motor_b_current_channel,
                    motor_c_current_channel,
                    motor_d_current_channel,
                    motor_a_temp_channel,
                    motor_b_temp_channel,
                    motor_c_temp_channel,
                    motor_d_temp_channel,
                ],
            ),
            FlowConfig(
                name="vehicle_50_hz",
                channels=[voltage_channel, gpio_channel],
            ),
            FlowConfig(
                name="readings",
                channels=[voltage_channel, vehicle_state_channel, gpio_channel],
            ),
            FlowConfig(name="voltage", channels=[voltage_channel]),
            FlowConfig(name="gpio_channel", channels=[gpio_channel]),
            FlowConfig(name="state_logs", channels=[state_log_channel]),
            FlowConfig(name="sys_logs", channels=[sys_log_channel]),
        ],
    )
