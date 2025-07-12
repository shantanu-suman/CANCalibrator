#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import logging
import json
import os
import threading
from collections import deque

logger = logging.getLogger(__name__)

class PlaybackEngine:
    """
    Engine for playing back recorded CAN messages, supporting:
    - Playback of individual messages
    - Sequence playback with original timing
    - Loop playback
    - Import/export of playback sequences
    """
    
    def __init__(self, can_simulator):
        """
        Initialize the Playback Engine
        
        Args:
            can_simulator: CAN simulator instance to inject messages
        """
        self.can_simulator = can_simulator
        self.current_playback = None
        self.playback_thread = None
        self.is_playing = False
        self.loop_playback = False
        self.sequences = {}  # Stored sequences by name
        
        logger.info("Playback Engine initialized")
    
    def send_message(self, can_id, data):
        """
        Send a single CAN message through the simulator
        
        Args:
            can_id (str): CAN ID (e.g., "0x1A2")
            data (str): Data payload (e.g., "AAFFBBCC00000000")
            
        Returns:
            bool: Success status
        """
        try:
            self.can_simulator.inject_message(can_id, data)
            logger.info("Sent message: ID=%s, Data=%s", can_id, data)
            return True
        except Exception as e:
            logger.error("Error sending message: %s", str(e))
            return False
    
    def create_sequence(self, name, messages):
        """
        Create a new playback sequence
        
        Args:
            name (str): Sequence name
            messages (list): List of message dicts, each with id, data, and delay
            
        Returns:
            bool: Success status
        """
        if not name or not messages:
            logger.error("Invalid sequence parameters")
            return False
            
        self.sequences[name] = messages
        logger.info("Created sequence '%s' with %d messages", name, len(messages))
        return True
    
    def play_sequence(self, name, loop=False):
        """
        Play a sequence of CAN messages
        
        Args:
            name (str): Name of the sequence to play
            loop (bool): Whether to loop playback
            
        Returns:
            bool: Success status
        """
        if name not in self.sequences:
            logger.error("Sequence '%s' not found", name)
            return False
            
        if self.is_playing:
            self.stop_playback()
            
        self.current_playback = name
        self.loop_playback = loop
        self.is_playing = True
        
        # Start playback in a separate thread
        self.playback_thread = threading.Thread(
            target=self._playback_worker,
            args=(self.sequences[name], loop)
        )
        self.playback_thread.daemon = True
        self.playback_thread.start()
        
        logger.info("Started playback of sequence '%s'", name)
        return True
    
    def stop_playback(self):
        """
        Stop the current playback
        
        Returns:
            bool: Success status
        """
        if not self.is_playing:
            logger.info("No active playback to stop")
            return False
            
        self.is_playing = False
        
        # Wait for thread to terminate (with timeout)
        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join(1.0)
        
        self.current_playback = None
        logger.info("Stopped playback")
        return True
    
    def _playback_worker(self, messages, loop=False):
        """
        Worker thread for sequence playback
        
        Args:
            messages (list): List of message dicts
            loop (bool): Whether to loop playback
        """
        while self.is_playing:
            for message in messages:
                if not self.is_playing:
                    break
                    
                # Send the message
                self.can_simulator.inject_message(
                    message["id"], 
                    message["data"]
                )
                
                # Wait for specified delay
                delay = message.get("delay", 0.1)
                time.sleep(delay)
            
            # If not looping, stop after one pass
            if not loop:
                self.is_playing = False
                self.current_playback = None
                break
    
    def import_sequence(self, sequence_data):
        """
        Import a sequence from JSON data
        
        Args:
            sequence_data (str or dict): JSON string or data object
            
        Returns:
            bool: Success status
        """
        try:
            # Parse JSON if string
            if isinstance(sequence_data, str):
                data = json.loads(sequence_data)
            else:
                data = sequence_data
                
            name = data.get("name")
            messages = data.get("messages")
            
            if not name or not messages:
                logger.error("Invalid sequence data format")
                return False
                
            return self.create_sequence(name, messages)
            
        except Exception as e:
            logger.error("Error importing sequence: %s", str(e))
            return False
    
    def export_sequence(self, name, export_path=None):
        """
        Export a sequence to JSON format
        
        Args:
            name (str): Sequence name to export
            export_path (str, optional): File path for export
            
        Returns:
            str: Path to export file or JSON string if no path provided
        """
        if name not in self.sequences:
            logger.error("Sequence '%s' not found", name)
            return None
            
        try:
            # Create export data
            export_data = {
                "name": name,
                "messages": self.sequences[name],
                "export_date": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Convert to JSON
            json_data = json.dumps(export_data, indent=2)
            
            if export_path:
                # Make sure directory exists
                os.makedirs(os.path.dirname(export_path), exist_ok=True)
                
                # Write to file
                with open(export_path, 'w') as f:
                    f.write(json_data)
                    
                logger.info("Exported sequence '%s' to %s", name, export_path)
                return export_path
            else:
                # Return JSON string
                return json_data
                
        except Exception as e:
            logger.error("Error exporting sequence '%s': %s", name, str(e))
            return None
    
    def get_sequence_info(self, name):
        """
        Get information about a specific sequence
        
        Args:
            name (str): Sequence name
            
        Returns:
            dict: Sequence information or None if not found
        """
        if name not in self.sequences:
            return None
            
        messages = self.sequences[name]
        total_duration = sum(m.get("delay", 0.1) for m in messages)
        
        return {
            "name": name,
            "message_count": len(messages),
            "total_duration": total_duration,
            "is_playing": self.is_playing and self.current_playback == name
        }
    
    def get_all_sequences(self):
        """
        Get information about all available sequences
        
        Returns:
            list: List of sequence info dictionaries
        """
        result = []
        for name in self.sequences:
            info = self.get_sequence_info(name)
            if info:
                result.append(info)
                
        return result

if __name__ == "__main__":
    # Simple test
    from can_simulator import CANSimulator
    
    simulator = CANSimulator()
    playback = PlaybackEngine(simulator)
    
    # Create a test sequence
    test_sequence = [
        {"id": "0x1A2", "data": "AAFFBBCC00000000", "delay": 0.2},
        {"id": "0x1F3", "data": "00AAFF1100000000", "delay": 0.3},
        {"id": "0x2B4", "data": "FF00000000000000", "delay": 0.1}
    ]
    
    playback.create_sequence("Test Sequence", test_sequence)
    
    # Play the sequence
    print("Playing sequence...")
    playback.play_sequence("Test Sequence")
    
    # Wait for sequence to finish
    time.sleep(1.0)
    
    # Export the sequence
    json_data = playback.export_sequence("Test Sequence")
    print("Exported sequence:", json_data)