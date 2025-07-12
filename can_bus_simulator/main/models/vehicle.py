#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
import datetime

from .database import Base

class Vehicle(Base):
    """
    Vehicle model for storing information about different vehicles.
    This allows CAN messages to be associated with specific vehicle
    makes, models, and regions.
    """
    __tablename__ = 'vehicles'
    
    id = Column(Integer, primary_key=True)
    make = Column(String(50), nullable=False)
    model = Column(String(50), nullable=False)
    year = Column(String(10), nullable=False)
    region = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    labels = relationship("Label", back_populates="vehicle", cascade="all, delete-orphan")
    
    def __init__(self, make, model, year, region):
        """Initialize a new Vehicle record"""
        self.make = make
        self.model = model
        self.year = year
        self.region = region
    
    def __repr__(self):
        """String representation of the Vehicle"""
        return f'<Vehicle {self.make} {self.model} {self.year} {self.region}>'