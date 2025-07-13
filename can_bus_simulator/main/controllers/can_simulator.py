import random
import time
import logging
import cantools  # DBC parsing library

logger = logging.getLogger(__name__)

class CANSimulator:
    def __init__(self, dbc_path='can_bus_simulator/db/FORD_CADS.dbc'):
        # List of generic noise CAN messages fallback (empty or filled later)
        self.noise_patterns = []

        # Example events: event_name -> dict with 'id' and 'on_data'
        # You can extend these or load dynamically from DBC if you want
        self.events = {
            "horn": {"id": "0x1A2", "on_data": "FF00000000000000"},
            "brake": {"id": "0x224", "on_data": "FF000000FFFF0000"},
            "turn_signal_left": {"id": "0x1B4", "on_data": "0100000000000000"},
            "turn_signal_right": {"id": "0x1B4", "on_data": "0200000000000000"},
        }

        self.active_events = set()
        self.injected_messages = []
        self.last_messages = []
        self.max_last_messages = 10

        # Load DBC database
        try:
            self.db = cantools.database.load_file(dbc_path)
            self.dbc_messages = self.db.messages
            logger.info(f"Loaded {len(self.dbc_messages)} messages from DBC")

            # Prepare noise patterns from DBC messages with random signal values
            self.noise_patterns = []
            for msg in self.dbc_messages:
                # Generate random signal values within signal ranges
                signals = {}
                for sig in msg.signals:
                    if sig.minimum is not None and sig.maximum is not None:
                        val = random.uniform(sig.minimum, sig.maximum)
                    else:
                        val = random.uniform(0, 100)
                    signals[sig.name] = round(val, 2)
                try:
                    encoded = msg.encode(signals)
                    hex_data = encoded.hex().upper().ljust(16, '0')  # 8 bytes hex string
                    self.noise_patterns.append({
                        "id": hex(msg.frame_id),
                        "data": hex_data
                    })
                except Exception as e:
                    logger.warning(f"Failed to encode noise message {msg.name}: {e}")

            logger.info(f"Prepared {len(self.noise_patterns)} noise patterns")

        except Exception as e:
            logger.error(f"Failed to load DBC file {dbc_path}: {e}")
            self.db = None
            self.dbc_messages = []
            self.noise_patterns = []

    def generate_dbc_message(self):
        """Generate a realistic CAN message with random signals based on DBC."""
        if not self.db:
            logger.warning("DBC not loaded, cannot generate DBC message")
            return None

        message = random.choice(self.dbc_messages)
        signal_values = {}

        for sig in message.signals:
            if sig.minimum is not None and sig.maximum is not None:
                value = random.uniform(sig.minimum, sig.maximum)
            else:
                value = random.uniform(0, 100)
            signal_values[sig.name] = round(value, 2)

        try:
            encoded_data = message.encode(signal_values)
            hex_data = encoded_data.hex().upper().ljust(16, '0')  # 8 bytes hex string
            return {
                "id": hex(message.frame_id),
                "data": hex_data,
                "timestamp": time.time(),
                "signals": signal_values
            }
        except Exception as e:
            logger.error(f"Encoding failed for message {message.name}: {e}")
            return None

    def generate_message(self):
        """Generate CAN message with priority:
        1) injected messages queue,
        2) active events (e.g., horn on),
        3) random DBC message,
        4) noise pattern fallback.
        """
        # 1) Use any injected message if available
        if self.injected_messages:
            msg = self.injected_messages.pop(0)
            msg["timestamp"] = time.time()
            return msg

        # 2) Randomly generate active event messages
        if self.active_events and random.random() < 0.3:
            event = random.choice(list(self.active_events))
            event_info = self.events.get(event)
            if event_info:
                return {
                    "id": event_info["id"],
                    "data": event_info["on_data"],
                    "timestamp": time.time()
                }

        # 3) Random DBC message
        if self.dbc_messages and random.random() < 0.5:
            dbc_msg = self.generate_dbc_message()
            if dbc_msg:
                return dbc_msg

        # 4) Noise fallback message
        if self.noise_patterns:
            noise_msg = random.choice(self.noise_patterns)
            return {**noise_msg, "timestamp": time.time()}

        # If all else fails, generate dummy message
        return {
            "id": "0x000",
            "data": "0000000000000000",
            "timestamp": time.time()
        }

    def inject_message(self, can_id, data):
        """Inject a CAN message that will be sent before others."""
        msg = {
            "id": can_id,
            "data": data,
            "timestamp": time.time()
        }
        self.injected_messages.append(msg)

    def activate_event(self, event_name):
        """Activate an event to generate event messages during simulation."""
        if event_name in self.events:
            self.active_events.add(event_name)
            logger.info(f"Activated event: {event_name}")
        else:
            logger.warning(f"Trying to activate unknown event: {event_name}")

    def deactivate_event(self, event_name):
        """Deactivate an active event."""
        if event_name in self.active_events:
            self.active_events.remove(event_name)
            logger.info(f"Deactivated event: {event_name}")

