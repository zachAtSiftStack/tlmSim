import time
import math
import random

class Motor:
    def __init__(self, name, environment_temperature=25.0, seed=None):
        self.name = name
        self.current = 0.0  # in mA
        self.encoder_ticks = 0
        self.direction = 1  # 1 for forward, -1 for reverse
        
        # Initialize the random generator with the motor-specific seed
        self.random_gen = random.Random(seed)
        
        # Motor-specific variations
        self.steady_state_current = self.apply_variation(333.0, 10)  # in mA, with 10% variation
        self.max_current = self.apply_variation(800.0, 10)  # in mA, with 10% variation
        self.stall_current = self.apply_variation(1500.0, 10)  # in mA, with 10% variation
        self.startup_duration = self.apply_variation(0.5, 10)  # startup duration with 10% variation
        
        # Temperature management (kept for compatibility)
        self.environment_temperature = environment_temperature
        self.temperature = environment_temperature
        self.max_temperature_rise = self.apply_variation(40.0, 10)

        self.start_time = None
        self.is_stalled = False
        self.fault = False  # New attribute to indicate a fault

    def apply_variation(self, value, percentage):
        """Apply a random variation to a value within the given percentage."""
        variation_range = value * (percentage / 100)
        return value + self.random_gen.uniform(-variation_range, variation_range)

    def start(self, direction=1):
        """Start the motor in the given direction (1 for forward, -1 for reverse)."""
        self.direction = direction
        self.start_time = time.time()
        self.is_stalled = False
        if self.fault and self.direction == 1:
            # Briefly hit stall current when starting in the forward direction with a fault
            self.current = self.stall_current
        else:
            self.current = self.max_current  # Start with max current

    def stop(self):
        """Stop the motor."""
        self.current = 0.0
        self.direction = 1
        self.start_time = None
        self.is_stalled = False

    def update(self, environment_temperature=25):
        """Update the motor's current, encoder, and temperature based on time elapsed since start."""
        self.environment_temperature = environment_temperature

        temp_on_rate = 0.01 

        if self.is_stalled:
            self.current = 1500.0  # Stall current in mA
        elif self.start_time is not None:
            elapsed_time = time.time() - self.start_time
            progress = elapsed_time / self.startup_duration

            # Normal encoder rate
            max_tick_increment = int(abs(self.steady_state_current) / 10)
            # Normal operation
            sigmoid = 1 / (1 + math.exp(-10 * (progress - 0.5)))  # Adjust the factor -10 for steepness, 0.5 for midpoint
            encoder_rate = max_tick_increment * sigmoid * 10  # Encoder rate transitions from 0 to steady state

            if self.fault and self.direction == 1:
                # Faulty forward driving behavior
                if elapsed_time < 4:  # Simulate stall for 4 seconds
                    self.current = self.apply_variation(self.stall_current, 10)  # Stall current with variation
                    encoder_rate = 0  # No encoder movement during stall
                    temp_on_rate = 0.07  # Faster temperature rise during stall
                else:
                    self.current = self.apply_variation(950.0, 10)  # Steady state at 80 mA with variation
                    encoder_rate = encoder_rate * 0.3
                    temp_on_rate = 0.025  # Faster temperature rise during stall
            else:
                target_current = self.steady_state_current + (self.max_current - self.steady_state_current) * (1 - sigmoid)

                # Approach the target current smoothly
                current_diff = target_current - self.current
                self.current += current_diff * 0.5  # Update factor to control approach speed

                # Apply random variation to the current
                self.current = self.apply_variation(self.current, 10)

            # Update encoder ticks based on direction and encoder rate
            if not self.is_stalled:
                self.encoder_ticks += int(self.direction * encoder_rate)

        # Temperature simulation
        if self.start_time is not None:
            target_temperature = self.environment_temperature + self.max_temperature_rise
            self.temperature += self.apply_variation((target_temperature - self.temperature) * temp_on_rate, 4)
        else:
            self.temperature += self.apply_variation((self.environment_temperature - self.temperature) * 0.005, 4)

    def get_telemetry(self):
        """Return the current telemetry for this motor."""
        return {
            f"{self.name}_current": self.current * self.direction,  # Current is positive or negative based on direction
            f"{self.name}_encoder": self.encoder_ticks,
            f"{self.name}_temperature": self.temperature,
        }

    def stall(self):
        """Set the motor to a stalled state."""
        self.is_stalled = True

    def unstall(self):
        """Remove the motor from the stalled state."""
        self.is_stalled = False
        self.start_time = time.time()  # Reset start time to simulate a fresh start

    def inject_fault(self):
        """Inject a fault into the motor."""
        self.fault = True
    
    def clear_fault(self):
        """Clear the fault from the motor."""
        self.fault = False
