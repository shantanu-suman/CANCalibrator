#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
import datetime

from .database import Base


class Label(Base):
    """
    Model for storing labeled CAN messages that represent specific vehicle actions or states.
    These labels are used to identify known patterns in CAN bus traffic.
    """
    __tablename__ = 'labels'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    can_id = Column(String(20), nullable=False)
    data = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    vehicle_id = Column(Integer, ForeignKey('vehicles.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    vehicle = relationship("Vehicle", back_populates="labels")
    
    def __init__(self, name, can_id, data, vehicle_id=None, description=None):
        """Initialize a new Label record"""
        self.name = name
        self.can_id = can_id
        self.data = data
        self.vehicle_id = vehicle_id
        self.description = description
    
    def __repr__(self):
        """String representation of the Label"""
        return f'<Label {self.name} ID={self.can_id} Data={self.data}>'
    
    def to_dict(self):
        """
        Convert to dictionary representation
        
        Returns:
            dict: Dictionary representation of this label
        """
        return {
            'id': self.id,
            'name': self.name,
            'can_id': self.can_id,
            'data': self.data,
            'description': self.description,
            'vehicle_id': self.vehicle_id
        }