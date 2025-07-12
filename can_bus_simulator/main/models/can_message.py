#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, DateTime
import datetime

from .database import Base

class CANMessage(Base):
    """
    Model for storing CAN messages that have been captured or simulated.
    This provides a historical record of all interesting messages.
    """
    __tablename__ = 'can_messages'
    
    id = Column(Integer, primary_key=True)
    can_id = Column(String(20), nullable=False, index=True)
    data = Column(String(100), nullable=False)
    timestamp = Column(Float, nullable=False, index=True)
    
    # Optional fields
    event_id = Column(Integer, ForeignKey('labels.id'), nullable=True)
    vehicle_id = Column(Integer, ForeignKey('vehicles.id'), nullable=True)
    is_significant = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    def __init__(self, can_id, data, timestamp, vehicle_id=None, 
                event_id=None, is_significant=False):
        """Initialize a new CAN Message record"""
        self.can_id = can_id
        self.data = data
        self.timestamp = timestamp
        self.vehicle_id = vehicle_id
        self.event_id = event_id
        self.is_significant = is_significant
    
    def __repr__(self):
        """String representation of the CAN Message"""
        return f'<CANMessage ID={self.can_id} Data={self.data} TS={self.timestamp}>'
    
    @staticmethod
    def from_dict(message_dict):
        """
        Create a CANMessage from a dictionary representation
        
        Args:
            message_dict (dict): Dictionary with keys id, data, timestamp
            
        Returns:
            CANMessage: New CANMessage instance
        """
        return CANMessage(
            can_id=message_dict.get('id'),
            data=message_dict.get('data'),
            timestamp=message_dict.get('timestamp'),
            is_significant=message_dict.get('is_significant', False)
        )