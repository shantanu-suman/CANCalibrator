#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import logging
import re
from collections import deque

logger = logging.getLogger(__name__)

class CANSniffer:
    """
    CAN Bus Sniffer that monitors and filters CAN messages.
    
    Features:
    - Filtering by ID
    - Filtering by data patterns
    - Change detection for identifying event patterns
    - Message history with frequency analysis
    """
    
    def __init__(self, can_source):
        """
        Initialize the CAN Sniffer
        
        Args:
            can_source: Source of CAN messages (e.g., CANSimulator instance)
        """
        self.can_source = can_source
        self.id_filters = []  # List of IDs to filter (include or exclude)
        self.data_filters = []  # List of regex patterns to match data
        self.include_mode = True  # True = whitelist, False = blacklist
        self.message_history = {}  # Dict of ID -> list of recent messages
        self.max_history_per_id = 100
        self.recent_messages = deque(maxlen=200)  # For overall analysis
        
        logger.info("CAN Sniffer initialized")
    
    def add_id_filter(self, can_id, include=True):
        """
        Add a filter for a specific CAN ID
        
        Args:
            can_id (str): The CAN ID to filter (e.g., "0x123")
            include (bool): Whether to include (True) or exclude (False) this ID
        """
        filter_item = {"id": can_id, "include": include}
        self.id_filters.append(filter_item)
        logger.info("Added ID filter: %s (%s)", 
                   can_id, "include" if include else "exclude")
    
    def add_data_filter(self, pattern, include=True):
        """
        Add a filter for a specific data pattern (regex)
        
        Args:
            pattern (str): Regex pattern to match in data field
            include (bool): Whether to include (True) or exclude (False) matching messages
        """
        try:
            compiled = re.compile(pattern)
            filter_item = {"pattern": compiled, "include": include}
            self.data_filters.append(filter_item)
            logger.info("Added data filter: %s (%s)", 
                       pattern, "include" if include else "exclude")
        except re.error:
            logger.error("Invalid regex pattern: %s", pattern)
    
    def set_filter_mode(self, include_mode):
        """
        Set the filter mode
        
        Args:
            include_mode (bool): True for whitelist mode, False for blacklist mode
        """
        self.include_mode = include_mode
        logger.info("Filter mode set to: %s", 
                   "include (whitelist)" if include_mode else "exclude (blacklist)")
    
    def clear_filters(self):
        """Clear all filters"""
        self.id_filters = []
        self.data_filters = []
        logger.info("All filters cleared")
    
    def process_message(self, message):
        """
        Process a CAN message through filters and add to history
        
        Args:
            message (dict): CAN message with id, data, timestamp
        
        Returns:
            dict: The processed message (possibly with additional metadata)
                  or None if filtered out
        """
        # Apply ID filters
        if self.id_filters:
            id_match = any(f["id"] == message["id"] for f in self.id_filters 
                          if f["include"])
            id_block = any(f["id"] == message["id"] for f in self.id_filters 
                          if not f["include"])
            
            # In include mode, we need a match; in exclude mode, we must not have a block
            if (self.include_mode and not id_match) or (not self.include_mode and id_block):
                return None
        
        # Apply data filters
        if self.data_filters:
            data_match = any(f["pattern"].search(message["data"]) for f in self.data_filters 
                            if f["include"])
            data_block = any(f["pattern"].search(message["data"]) for f in self.data_filters 
                            if not f["include"])
            
            # In include mode, we need a match; in exclude mode, we must not have a block
            if (self.include_mode and not data_match) or (not self.include_mode and data_block):
                return None
        
        # Add to message history
        can_id = message["id"]
        if can_id not in self.message_history:
            self.message_history[can_id] = deque(maxlen=self.max_history_per_id)
        
        self.message_history[can_id].append(message)
        self.recent_messages.append(message)
        
        # Check if this represents a change in pattern
        message_with_metadata = dict(message)  # Create a copy
        message_with_metadata["change_detected"] = self.detect_change(message)
        
        return message_with_metadata
    
    def detect_change(self, message):
        """
        Detect if this message represents a significant change in pattern
        
        Args:
            message (dict): Current CAN message
            
        Returns:
            bool: True if a change is detected
        """
        can_id = message["id"]
        
        # Need at least 2 messages to detect a change
        if can_id not in self.message_history or len(self.message_history[can_id]) < 2:
            return False
        
        # Get the previous message for this ID
        previous = self.message_history[can_id][-2]
        
        # Simple change detection: did the data change?
        if previous["data"] != message["data"]:
            logger.debug("Change detected for ID %s: %s -> %s", 
                        can_id, previous["data"], message["data"])
            return True
            
        return False
    
    def analyze_frequency(self, can_id=None, time_window=10):
        """
        Analyze the frequency of messages
        
        Args:
            can_id (str, optional): Specific ID to analyze, or None for all
            time_window (float): Time window in seconds for analysis
            
        Returns:
            dict: Frequency analysis results
        """
        current_time = time.time()
        min_time = current_time - time_window
        
        # Filter recent messages by time window
        if can_id:
            # Analyze specific ID
            if can_id not in self.message_history:
                return {"id": can_id, "frequency": 0, "count": 0}
                
            messages = [m for m in self.message_history[can_id] 
                       if m["timestamp"] >= min_time]
        else:
            # Analyze all messages
            messages = [m for m in self.recent_messages 
                       if m["timestamp"] >= min_time]
        
        count = len(messages)
        if count <= 1:
            frequency = 0
        else:
            # Calculate average time between messages
            timestamps = sorted([m["timestamp"] for m in messages])
            if timestamps[-1] == timestamps[0]:  # Avoid division by zero
                frequency = 0
            else:
                frequency = (count - 1) / (timestamps[-1] - timestamps[0])
        
        result = {
            "id": can_id if can_id else "all",
            "frequency": frequency,  # Hz
            "count": count,
            "window": time_window
        }
        
        return result
    
    def find_correlated_messages(self, target_id, time_window=0.5):
        """
        Find messages that frequently occur close to a target message
        
        Args:
            target_id (str): Target CAN ID
            time_window (float): Time window in seconds to look for correlations
            
        Returns:
            list: List of potentially correlated message IDs
        """
        if target_id not in self.message_history:
            return []
        
        # Get timestamps for target ID
        target_times = [m["timestamp"] for m in self.message_history[target_id]]
        
        # Track correlation counts
        correlations = {}
        
        # Look through recent messages
        for message in self.recent_messages:
            if message["id"] == target_id:
                continue  # Skip the target ID itself
            
            # Check if this message is close to any target message
            msg_time = message["timestamp"]
            is_correlated = any(abs(target_time - msg_time) <= time_window 
                              for target_time in target_times)
            
            if is_correlated:
                correlations[message["id"]] = correlations.get(message["id"], 0) + 1
        
        # Sort by correlation count and return IDs
        correlated_ids = sorted(correlations.keys(), 
                              key=lambda k: correlations[k], 
                              reverse=True)
        
        return correlated_ids[:10]  # Return top 10

if __name__ == "__main__":
    # Test code
    from can_simulator import CANSimulator
    
    simulator = CANSimulator()
    sniffer = CANSniffer(simulator)
    
    # Add a filter for a specific ID
    sniffer.add_id_filter("0x1A2", include=True)
    
    print("Generating and processing 20 messages:")
    for _ in range(20):
        message = simulator.generate_message()
        filtered = sniffer.process_message(message)
        
        if filtered:
            print(f"Passed filter: ID={filtered['id']}, Data={filtered['data']}")