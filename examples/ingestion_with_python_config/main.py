import os
from datetime import datetime, timezone

import threading
from dotenv import load_dotenv
from sift_py.grpc.transport import SiftChannelConfig, use_sift_channel
from sift_py.ingestion.service import IngestionService
from simulator import Simulator
from telemetry_config import vehicle_telemetry_config
import time

if __name__ == "__main__":
    """
    Example of telemetering data for the asset of name 'NostromoLV426' with various channels
    and rules. The simulator will be sending data for various flows at various frequencies.
    """

    load_dotenv()

    apikey = os.getenv("SIFT_API_KEY")

    if apikey is None:
        raise Exception("Missing 'SIFT_API_KEY' environment variable.")

    base_uri = os.getenv("BASE_URI")

    if base_uri is None:
        raise Exception("Missing 'BASE_URI' environment variable.")

    # Load your telemetry config
    telemetry_config = vehicle_telemetry_config()

    # Create a gRPC transport channel configured specifically for the Sift API
    sift_channel_config = SiftChannelConfig(uri=base_uri, apikey=apikey)

    with use_sift_channel(sift_channel_config) as channel:
        # Create ingestion service using the telemetry config we loaded in
        ingestion_service = IngestionService(
            channel,
            telemetry_config,
            overwrite_rules=True,  # Overwrite any rules created in the Sift UI that isn't in the config
            end_stream_on_error=True,  # End stream if errors occur API-side.
        )

        # Create an optional run as part of this ingestion
        current_ts = datetime.now(timezone.utc)
        run_name = f"{telemetry_config.asset_name} functional dry run at {current_ts}"
        ingestion_service.attach_run(channel, run_name, f"Rover functional checkout started at {current_ts}")

        simulator = Simulator(ingestion_service, seed=42)

        command_sequence = [
            ("idle", 10),
            ("forward", 5),         # Start the vehicle after 2 seconds
            ("idle", 1),          # Stop the vehicle after 5 seconds
            ("left_turn", 5),     # Turn left after 5 seconds
            ("idle", 1),
            ("right_turn", 5),    # Turn right after 5 seconds
            ("idle", 1),
            ("reverse", 5),       # Reverse after 5 seconds
            ("idle", 1),
            ("forward", 5),       # Forward after 5 seconds
            ("idle", 1),
            ("camera_1", 5),      # Operate Camera 1 after 5 seconds
            ("camera_2", 5),      # Operate Camera 2 after 5 seconds
            ("charge", 20),        # Charge the vehicle after 5 seconds
            ("idle", 5),          # Stop the vehicle after 5 seconds
            #("inject_fault", 5),  # Inject a fault after 5 seconds
        ]

        # Start the simulator in a separate thread
        simulator_thread = threading.Thread(target=simulator.run, args=(80,))
        simulator_thread.start()

        # Execute the command sequence in the main thread
        simulator.execute_command_sequence(command_sequence)

        # Wait for the simulator to finish
        simulator_thread.join()
    
    time.sleep(20)

    with use_sift_channel(sift_channel_config) as channel:
        # Create ingestion service using the telemetry config we loaded in
        ingestion_service = IngestionService(
            channel,
            telemetry_config,
            overwrite_rules=True,  # Overwrite any rules created in the Sift UI that isn't in the config
            end_stream_on_error=True,  # End stream if errors occur API-side.
        )

        # Create an optional run as part of this ingestion
        current_ts = datetime.now(timezone.utc)
        run_name = f"{telemetry_config.asset_name} functional pre vibe {current_ts}"
        ingestion_service.attach_run(channel, run_name, f"Rover functional checkout started at {current_ts}")

        simulator = Simulator(ingestion_service, seed=442)

        command_sequence = [
            ("idle", 1),
            ("forward", 5),         # Start the vehicle after 2 seconds
            ("idle", 1),          # Stop the vehicle after 5 seconds
            ("left_turn", 5),     # Turn left after 5 seconds
            ("idle", 1),
            ("right_turn", 5),    # Turn right after 5 seconds
            ("idle", 1),
            ("reverse", 5),       # Reverse after 5 seconds
            ("idle", 1),
            ("forward", 5),       # Forward after 5 seconds
            ("idle", 1),
            ("camera_1", 5),      # Operate Camera 1 after 5 seconds
            ("camera_2", 5),      # Operate Camera 2 after 5 seconds
            ("charge", 20),        # Charge the vehicle after 5 seconds
            ("idle", 5),          # Stop the vehicle after 5 seconds
            #("inject_fault", 5),  # Inject a fault after 5 seconds
        ]

        # Start the simulator in a separate thread
        simulator_thread = threading.Thread(target=simulator.run, args=(80,))
        simulator_thread.start()

        # Execute the command sequence in the main thread
        simulator.execute_command_sequence(command_sequence)

        # Wait for the simulator to finish
        simulator_thread.join()

    time.sleep(20)


    with use_sift_channel(sift_channel_config) as channel:
        # Create ingestion service using the telemetry config we loaded in
        ingestion_service = IngestionService(
            channel,
            telemetry_config,
            overwrite_rules=True,  # Overwrite any rules created in the Sift UI that isn't in the config
            end_stream_on_error=True,  # End stream if errors occur API-side.
        )

        # Create an optional run as part of this ingestion
        current_ts = datetime.now(timezone.utc)
        run_name = f"{telemetry_config.asset_name} functional post vibe {current_ts}"
        ingestion_service.attach_run(channel, run_name, f"Rover functional checkout started at {current_ts}")

        simulator = Simulator(ingestion_service, seed=2442, faults=True)

        command_sequence = [
            ("idle", 6),
            ("forward", 5),         # Start the vehicle after 2 seconds
            ("idle", 1),          # Stop the vehicle after 5 seconds
            ("left_turn", 5),     # Turn left after 5 seconds
            ("idle", 1),
            ("right_turn", 5),    # Turn right after 5 seconds
            ("idle", 1),
            ("reverse", 5),       # Reverse after 5 seconds
            ("idle", 1),
            ("forward", 5),       # Forward after 5 seconds
            ("idle", 1),
            ("camera_1", 5),      # Operate Camera 1 after 5 seconds
            ("camera_2", 5),      # Operate Camera 2 after 5 seconds
            ("charge", 20),        # Charge the vehicle after 5 seconds
            ("idle", 5),          # Stop the vehicle after 5 seconds
            #("inject_fault", 5),  # Inject a fault after 5 seconds
        ]

        # Start the simulator in a separate thread
        simulator_thread = threading.Thread(target=simulator.run, args=(80,))
        simulator_thread.start()

        # Execute the command sequence in the main thread
        simulator.execute_command_sequence(command_sequence)

        # Wait for the simulator to finish
        simulator_thread.join()