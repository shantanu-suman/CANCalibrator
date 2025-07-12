#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import logging
from collections import deque, defaultdict

logger = logging.getLogger(__name__)

class CalibrationController:
    """
    Controller for calibration mode that detects CAN messages 
    associated with specific vehicle events.
    
    The calibration process:
    1. User initiates calibration for a specific event (e.g., "Horn")
    2. System begins recording baseline CAN traffic
    3. User performs the action (e.g., presses the horn)
    4. System identifies which messages changed during the action
    5. User confirms the correct message, which is then labeled
    """
    
    def __init__(self, can_simulator, can_sniffer):
        """
        Initialize the Calibration Controller
        
        Args:
            can_simulator: The CAN simulator instance
            can_sniffer: The CAN sniffer instance
        """
        self.can_simulator = can_simulator
        self.can_sniffer = can_sniffer
        
        self.calibration_active = False
        self.current_event_name = None
        self.baseline_messages = defaultdict(list)  # ID -> list of data values
        self.calibration_messages = []  # Messages during calibration
        self.start_time = 0
        self.calibration_window = 5  # seconds
        
        logger.info("Calibration Controller initialized")
    
    def start_calibration(self, event_name):
        """
        Start calibration mode for a specific event
        
        Args:
            event_name (str): Name of the event being calibrated
        """
        self.calibration_active = True
        self.current_event_name = event_name
        self.baseline_messages.clear()
        self.calibration_messages.clear()
        self.start_time = time.time()
        
        # Record baseline for 2 seconds before starting
        logger.info("Started calibration for event: %s", event_name)
        
        # Begin collecting baseline data
        self._collect_baseline()
    
    def _collect_baseline(self, duration=2.0):
        """
        Collect baseline message patterns
        
        Args:
            duration (float): Duration in seconds to collect baseline
        """
        baseline_start = time.time()
        baseline_end = baseline_start + duration
        
        while time.time() < baseline_end:
            message = self.can_simulator.generate_message()
            filtered = self.can_sniffer.process_message(message)
            
            if filtered:
                # Store in baseline
                can_id = filtered["id"]
                data = filtered["data"]
                self.baseline_messages[can_id].append(data)
            
            # Short sleep to not hog CPU
            time.sleep(0.01)
        
        logger.info("Collected baseline data for %s IDs", len(self.baseline_messages))
    
    def record_message(self, message):
        """
        Record a message during calibration
        
        Args:
            message (dict): CAN message to record
        """
        if not self.calibration_active:
            return
        
        # Check if we've reached the calibration window
        elapsed = time.time() - self.start_time
        if elapsed > self.calibration_window:
            # Auto-stop if calibration window exceeded
            self.stop_calibration()
            return
        
        # Store the message
        self.calibration_messages.append(message)
    
    def stop_calibration(self):
        """
        Stop calibration mode and analyze results
        
        Returns:
            list: Candidate messages that may represent the event
        """
        if not self.calibration_active:
            logger.warning("Calibration not active")
            return []
        
        self.calibration_active = False
        
        # Analyze the calibration messages
        candidates = self._analyze_calibration_data()
        
        # Reset calibration state
        self.current_event_name = None
        
        logger.info("Calibration stopped, found %d candidate messages", len(candidates))
        return candidates
    
    def _analyze_calibration_data(self):
        """
        Analyze calibration data to find candidate messages
        
        Returns:
            list: Candidate messages sorted by likelihood
        """
        # Track unique messages by ID+Data that weren't in the baseline
        candidates = []
        
        # Group calibration messages by ID
        calibration_by_id = defaultdict(list)
        for message in self.calibration_messages:
            can_id = message["id"]
            data = message["data"]
            calibration_by_id[can_id].append((data, message["timestamp"]))
        
        # Compare each ID's data with baseline
        for can_id, data_points in calibration_by_id.items():
            # Skip if no baseline for this ID (completely new messages are suspicious)
            if can_id not in self.baseline_messages:
                # But still include with low score if it appeared multiple times
                if len(data_points) > 2:
                    candidates.append({
                        "id": can_id,
                        "data": data_points[0][0],  # First data value
                        "count": len(data_points),
                        "score": 0.5,  # Lower score for new IDs
                        "timestamp": data_points[0][1]
                    })
                continue
            
            baseline_data_set = set(self.baseline_messages[can_id])
            
            # Check each unique data value for this ID
            unique_data_values = set(dp[0] for dp in data_points)
            for data in unique_data_values:
                # If this data wasn't in baseline, it's a candidate
                if data not in baseline_data_set:
                    # Count occurrences
                    count = sum(1 for dp in data_points if dp[0] == data)
                    
                    # Calculate score (higher is better)
                    # Factors:
                    # - Number of occurrences
                    # - Whether the ID had stable baseline (few variations)
                    # - Timestamp (earlier detections may be more relevant)
                    
                    baseline_stability = 1.0 / (len(baseline_data_set) + 1)
                    occurrence_factor = min(count / 3, 1.0)  # Cap at 1.0
                    
                    # Find first timestamp for this data
                    first_timestamp = min(dp[1] for dp in data_points if dp[0] == data)
                    time_factor = 1.0 - min((first_timestamp - self.start_time) / self.calibration_window, 1.0)
                    
                    score = (0.4 * baseline_stability + 
                             0.4 * occurrence_factor + 
                             0.2 * time_factor)
                    
                    candidates.append({
                        "id": can_id,
                        "data": data,
                        "count": count,
                        "score": score,
                        "timestamp": first_timestamp
                    })
        
        # Sort by score (descending)
        candidates.sort(key=lambda c: c["score"], reverse=True)
        
        # Limit to top candidates
        max_candidates = 10
        return candidates[:max_candidates]
    
    def confirm_calibration(self, can_id, data):
        """
        Confirm a calibration result and add to the simulator
        
        Args:
            can_id (str): CAN ID of the confirmed message
            data (str): Data payload of the confirmed message
            
        Returns:
            bool: Success status
        """
        if not self.current_event_name:
            logger.warning("No active calibration to confirm")
            return False
        
        # Add this as an event to the simulator
        self.can_simulator.add_event(
            event_name=self.current_event_name,
            can_id=can_id,
            on_data=data
        )
        
        logger.info("Confirmed calibration for event %s: ID=%s, Data=%s", 
                   self.current_event_name, can_id, data)
        
        return True

if __name__ == "__main__":
    # Simple test
    from can_simulator import CANSimulator
    from can_sniffer import CANSniffer
    
    simulator = CANSimulator()
    sniffer = CANSniffer(simulator)
    calibration = CalibrationController(simulator, sniffer)
    
    print("Starting calibration for 'Horn' event...")
    calibration.start_calibration("Horn")
    
    # Simulate user pressing horn during calibration
    simulator.activate_event("Horn")
    
    # Generate and process some messages
    for _ in range(30):
        message = simulator.generate_message()
        filtered = sniffer.process_message(message)
        if filtered:
            calibration.record_message(filtered)
    
    # Stop calibration
    candidates = calibration.stop_calibration()
    
    print("\nCalibration Results:")
    for i, candidate in enumerate(candidates):
        print(f"{i+1}. ID: {candidate['id']}, Data: {candidate['data']}, Score: {candidate['score']:.2f}")