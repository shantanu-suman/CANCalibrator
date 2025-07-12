#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random
import time
import json
import logging

logger = logging.getLogger(__name__)

class CANSimulator:
    """
    CAN Bus Simulator Engine that generates simulated CAN messages
    with both random noise and event-driven messages.
    """
    
    def __init__(self):
        """Initialize the CAN Simulator with default message patterns."""
        self.noise_patterns = [
            {"id": "0x100", "data": "0000000000000000"},
            {"id": "0x200", "data": "FFFFFFFFFFFFFFFF"},
            {"id": "0x300", "data": "A5A5A5A5A5A5A5A5"},
            {"id": "0x400", "data": "1234567890ABCDEF"},
            {"id": "0x500", "data": "FEDCBA0987654321"},
        ]
        
        # Events dict with ID, ON data, OFF data
        self.events = {
            "Horn": {"id": "0x1A2", "on_data": "AAFFBBCC00000000", "off_data": "00FFBBCC00000000"},
            "AC": {"id": "0x1F3", "on_data": "00AAFF1100000000", "off_data": "0000FF1100000000"},
            "Headlights": {"id": "0x2B4", "on_data": "FF00000000000000", "off_data": "0000000000000000"},
            "Turn Signal Left": {"id": "0x3C5", "on_data": "AA00000000000000", "off_data": "0000000000000000"},
            "Turn Signal Right": {"id": "0x3C6", "on_data": "BB00000000000000", "off_data": "0000000000000000"},
            "Brake": {"id": "0x4D7", "on_data": "FFAA000000000000", "off_data": "00AA000000000000"},
            "Door Lock": {"id": "0x5E8", "on_data": "11223344AABBCCDD", "off_data": "11223344AABB0000"},
            "Window Down": {"id": "0x6F9", "on_data": "ABCDEF0000000000", "off_data": "ABCDEF0000000000"},
        }
        
        # Active events tracking
        self.active_events = set()
        
        # Injected messages (from playback)
        self.injected_messages = []
        
        # Track last sent messages to avoid repetition
        self.last_messages = []
        self.max_last_messages = 10
        
        logger.info("CAN Simulator initialized with %d noise patterns and %d events", 
                   len(self.noise_patterns), len(self.events))
    
    def generate_message(self):
        """
        Generate a simulated CAN message. Could be:
        1. From injected messages queue
        2. From active events
        3. Random noise
        
        Returns:
            dict: CAN message with id, data, and timestamp
        """
        # First priority: injected messages (from playback)
        if self.injected_messages:
            message = self.injected_messages.pop(0)
            message["timestamp"] = time.time()
            logger.debug("Generated injected message: %s", message)
            return message
            
        # Second priority: active events
        if self.active_events and random.random() < 0.3:
            event = random.choice(list(self.active_events))
            message = {
                "id": self.events[event]["id"],
                "data": self.events[event]["on_data"],
                "timestamp": time.time(),
                "event": event
            }
            logger.debug("Generated active event message: %s", message)
            return message
        
        # Third priority: random events (with low probability)
        if random.random() < 0.05 and self.events:
            event_name = random.choice(list(self.events.keys()))
            # Randomly decide if it's ON or OFF state
            data_key = "on_data" if random.random() < 0.5 else "off_data"
            
            message = {
                "id": self.events[event_name]["id"],
                "data": self.events[event_name][data_key],
                "timestamp": time.time(),
                "event": event_name
            }
            
            # Add to active events if ON, remove if OFF
            if data_key == "on_data" and message["event"] not in self.active_events:
                self.active_events.add(message["event"])
            elif data_key == "off_data" and message["event"] in self.active_events:
                self.active_events.remove(message["event"])
                
            logger.debug("Generated random event message: %s", message)
            return message
        
        # Finally: generate noise message
        pattern = random.choice(self.noise_patterns)
        
        # Add some randomization to noise data
        if random.random() < 0.3:
            # Modify a random byte in the data
            data_list = list(pattern["data"])
            pos = random.randint(0, len(pattern["data"]) - 1)
            hex_chars = "0123456789ABCDEF"
            data_list[pos] = random.choice(hex_chars)
            data = "".join(data_list)
        else:
            data = pattern["data"]
        
        message = {
            "id": pattern["id"],
            "data": data,
            "timestamp": time.time()
        }
        
        # Check if this exact message was recently sent
        if any(m["id"] == message["id"] and m["data"] == message["data"] 
               for m in self.last_messages):
            # Try again to avoid repetition
            return self.generate_message()
        
        # Update last messages list
        self.last_messages.append(message)
        if len(self.last_messages) > self.max_last_messages:
            self.last_messages.pop(0)
            
        logger.debug("Generated noise message: %s", message)
        return message
    
    def inject_message(self, can_id, data):
        """
        Inject a message into the simulation queue (for playback)
        
        Args:
            can_id (str): The CAN ID (e.g., "0x1A2")
            data (str): The data payload (e.g., "AAFFBBCC00000000")
        """
        message = {
            "id": can_id,
            "data": data,
            "timestamp": time.time(),
            "injected": True
        }
        
        self.injected_messages.append(message)
        logger.info("Message injected: ID=%s, Data=%s", can_id, data)
        
    def activate_event(self, event_name):
        """
        Activate a specific event
        
        Args:
            event_name (str): Name of the event to activate
        
        Returns:
            bool: Success status
        """
        if event_name in self.events:
            self.active_events.add(event_name)
            # Inject an immediate message
            self.inject_message(
                self.events[event_name]["id"], 
                self.events[event_name]["on_data"]
            )
            logger.info("Event activated: %s", event_name)
            return True
        else:
            logger.warning("Unknown event: %s", event_name)
            return False
    
    def deactivate_event(self, event_name):
        """
        Deactivate a specific event
        
        Args:
            event_name (str): Name of the event to deactivate
        
        Returns:
            bool: Success status
        """
        if event_name in self.active_events:
            self.active_events.remove(event_name)
            # Inject an immediate OFF message
            self.inject_message(
                self.events[event_name]["id"], 
                self.events[event_name]["off_data"]
            )
            logger.info("Event deactivated: %s", event_name)
            return True
        else:
            logger.warning("Event not active or unknown: %s", event_name)
            return False
    
    def add_event(self, event_name, can_id, on_data, off_data=None):
        """
        Add a new event to the simulator
        
        Args:
            event_name (str): Name of the event
            can_id (str): CAN ID for this event
            on_data (str): Data payload for ON state
            off_data (str): Data payload for OFF state (optional)
        """
        if off_data is None:
            # Create an OFF state by zeroing out the first byte
            off_data = "00" + on_data[2:]
            
        self.events[event_name] = {
            "id": can_id,
            "on_data": on_data,
            "off_data": off_data
        }
        
        logger.info("New event added: %s (ID=%s)", event_name, can_id)

if __name__ == "__main__":
    # Simple test of the simulator
    simulator = CANSimulator()
    
    print("Generating 10 random messages:")
    for _ in range(10):
        message = simulator.generate_message()
        print(f"ID: {message['id']}, Data: {message['data']}")
        
    print("\nInjecting a message:")
    simulator.inject_message("0x1A2", "AAFFBBCC00000000")
    
    print("Next message should be the injected one:")
    message = simulator.generate_message()
    print(f"ID: {message['id']}, Data: {message['data']}")