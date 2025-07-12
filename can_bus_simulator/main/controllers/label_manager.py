#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import json
import os
import time
from main.models.database import db_session
from main.models.label import Label
from main.models.vehicle import Vehicle

logger = logging.getLogger(__name__)

class LabelManager:
    """
    Manages the labeling of CAN messages, including:
    - Creating, updating, and deleting labels
    - Associating labels with vehicles
    - Searching and filtering labels
    - Importing/exporting label data
    """
    
    def __init__(self):
        """Initialize the Label Manager"""
        logger.info("Label Manager initialized")
    
    def create_label(self, name, can_id, data, vehicle_id=None, description=None):
        """
        Create a new label for a CAN message
        
        Args:
            name (str): Label name (e.g., "Horn")
            can_id (str): CAN ID (e.g., "0x1A2")
            data (str): Data payload (e.g., "AAFFBBCC00000000")
            vehicle_id (int, optional): ID of associated vehicle
            description (str, optional): Additional description
            
        Returns:
            Label: The created Label object
        """
        label = Label(
            name=name,
            can_id=can_id,
            data=data,
            vehicle_id=vehicle_id,
            description=description
        )
        
        try:
            db_session.add(label)
            db_session.commit()
            logger.info("Created label '%s' for ID=%s", name, can_id)
            return label
        except Exception as e:
            db_session.rollback()
            logger.error("Error creating label: %s", str(e))
            return None
    
    def update_label(self, label_id, **kwargs):
        """
        Update an existing label
        
        Args:
            label_id (int): ID of the label to update
            **kwargs: Fields to update (name, can_id, data, vehicle_id, description)
            
        Returns:
            Label: The updated Label object, or None if not found/error
        """
        try:
            label = db_session.query(Label).filter(Label.id == label_id).first()
            if not label:
                logger.warning("Label ID %d not found", label_id)
                return None
            
            # Update fields
            for field, value in kwargs.items():
                if hasattr(label, field):
                    setattr(label, field, value)
            
            db_session.commit()
            logger.info("Updated label ID %d", label_id)
            return label
        except Exception as e:
            db_session.rollback()
            logger.error("Error updating label ID %d: %s", label_id, str(e))
            return None
    
    def delete_label(self, label_id):
        """
        Delete a label
        
        Args:
            label_id (int): ID of the label to delete
            
        Returns:
            bool: Success status
        """
        try:
            label = db_session.query(Label).filter(Label.id == label_id).first()
            if not label:
                logger.warning("Label ID %d not found for deletion", label_id)
                return False
            
            db_session.delete(label)
            db_session.commit()
            logger.info("Deleted label ID %d", label_id)
            return True
        except Exception as e:
            db_session.rollback()
            logger.error("Error deleting label ID %d: %s", label_id, str(e))
            return False
    
    def get_label(self, label_id):
        """
        Get a label by ID
        
        Args:
            label_id (int): Label ID
            
        Returns:
            dict: Label data or None if not found
        """
        try:
            label = db_session.query(Label).filter(Label.id == label_id).first()
            if not label:
                return None
                
            return {
                "id": label.id,
                "name": label.name,
                "can_id": label.can_id,
                "data": label.data,
                "vehicle_id": label.vehicle_id,
                "description": label.description
            }
        except Exception as e:
            logger.error("Error getting label ID %d: %s", label_id, str(e))
            return None
    
    def get_labels_by_vehicle(self, vehicle_id):
        """
        Get all labels for a specific vehicle
        
        Args:
            vehicle_id (int): Vehicle ID
            
        Returns:
            list: List of label dictionaries
        """
        try:
            labels = db_session.query(Label).filter(Label.vehicle_id == vehicle_id).all()
            
            result = []
            for label in labels:
                result.append({
                    "id": label.id,
                    "name": label.name,
                    "can_id": label.can_id,
                    "data": label.data,
                    "vehicle_id": label.vehicle_id,
                    "description": label.description
                })
                
            return result
        except Exception as e:
            logger.error("Error getting labels for vehicle ID %d: %s", vehicle_id, str(e))
            return []
    
    def search_labels(self, search_term=None, vehicle_make=None, vehicle_model=None, 
                     vehicle_year=None, vehicle_region=None):
        """
        Search for labels with various filters
        
        Args:
            search_term (str, optional): Term to search in name/description
            vehicle_make (str, optional): Vehicle make filter
            vehicle_model (str, optional): Vehicle model filter
            vehicle_year (str, optional): Vehicle year filter
            vehicle_region (str, optional): Vehicle region filter
            
        Returns:
            list: Matching label dictionaries
        """
        try:
            # Start with base query
            query = db_session.query(Label, Vehicle).join(
                Vehicle, Label.vehicle_id == Vehicle.id)
            
            # Apply filters
            if search_term:
                query = query.filter(
                    (Label.name.like(f'%{search_term}%')) | 
                    (Label.description.like(f'%{search_term}%'))
                )
            
            if vehicle_make:
                query = query.filter(Vehicle.make == vehicle_make)
                
            if vehicle_model:
                query = query.filter(Vehicle.model == vehicle_model)
                
            if vehicle_year:
                query = query.filter(Vehicle.year == vehicle_year)
                
            if vehicle_region:
                query = query.filter(Vehicle.region == vehicle_region)
            
            # Execute query
            results = query.all()
            
            # Format results
            formatted_results = []
            for label, vehicle in results:
                formatted_results.append({
                    "id": label.id,
                    "name": label.name,
                    "can_id": label.can_id,
                    "data": label.data,
                    "description": label.description,
                    "vehicle": {
                        "id": vehicle.id,
                        "make": vehicle.make,
                        "model": vehicle.model,
                        "year": vehicle.year,
                        "region": vehicle.region
                    }
                })
            
            return formatted_results
        except Exception as e:
            logger.error("Error searching labels: %s", str(e))
            return []
    
    def export_labels(self, vehicle_id=None, export_path=None):
        """
        Export labels to JSON file
        
        Args:
            vehicle_id (int, optional): Export only labels for this vehicle
            export_path (str, optional): File path for export
            
        Returns:
            str: Path to export file or JSON string if no path provided
        """
        try:
            # Get labels
            if vehicle_id:
                labels = self.get_labels_by_vehicle(vehicle_id)
                # Get vehicle info
                vehicle = db_session.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
                vehicle_info = {
                    "id": vehicle.id,
                    "make": vehicle.make,
                    "model": vehicle.model,
                    "year": vehicle.year,
                    "region": vehicle.region
                } if vehicle else {}
            else:
                # Get all labels
                labels = db_session.query(Label).all()
                labels = [
                    {
                        "id": label.id,
                        "name": label.name,
                        "can_id": label.can_id,
                        "data": label.data,
                        "vehicle_id": label.vehicle_id,
                        "description": label.description
                    } for label in labels
                ]
                vehicle_info = {}
            
            # Create export data
            export_data = {
                "vehicle": vehicle_info,
                "labels": labels,
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
                    
                logger.info("Exported %d labels to %s", len(labels), export_path)
                return export_path
            else:
                # Return JSON string
                return json_data
                
        except Exception as e:
            logger.error("Error exporting labels: %s", str(e))
            return None
    
    def import_labels(self, import_data, overwrite=False):
        """
        Import labels from JSON data
        
        Args:
            import_data (str or dict): JSON string or data object with labels
            overwrite (bool): Whether to overwrite existing labels
            
        Returns:
            dict: Import stats (added, updated, skipped, errors)
        """
        stats = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
        
        try:
            # Parse JSON if string
            if isinstance(import_data, str):
                data = json.loads(import_data)
            else:
                data = import_data
                
            # Get vehicle info and create if needed
            vehicle_info = data.get("vehicle", {})
            vehicle_id = None
            
            if vehicle_info:
                # Check if vehicle exists
                query = db_session.query(Vehicle)
                for attr in ["make", "model", "year", "region"]:
                    if attr in vehicle_info:
                        query = query.filter(getattr(Vehicle, attr) == vehicle_info[attr])
                
                vehicle = query.first()
                
                # Create vehicle if it doesn't exist
                if not vehicle:
                    vehicle = Vehicle(
                        make=vehicle_info.get("make", "Unknown"),
                        model=vehicle_info.get("model", "Unknown"),
                        year=vehicle_info.get("year", "Unknown"),
                        region=vehicle_info.get("region", "Unknown")
                    )
                    db_session.add(vehicle)
                    db_session.commit()
                
                vehicle_id = vehicle.id
            
            # Process labels
            for label_data in data.get("labels", []):
                try:
                    # Use vehicle ID from import data or from vehicle we just created/found
                    label_vehicle_id = label_data.get("vehicle_id", vehicle_id)
                    
                    # Check if label exists (by name + vehicle_id)
                    existing_label = db_session.query(Label).filter(
                        Label.name == label_data["name"],
                        Label.vehicle_id == label_vehicle_id
                    ).first()
                    
                    if existing_label and overwrite:
                        # Update existing label
                        self.update_label(
                            existing_label.id,
                            can_id=label_data["can_id"],
                            data=label_data["data"],
                            description=label_data.get("description", "")
                        )
                        stats["updated"] += 1
                    elif not existing_label:
                        # Create new label
                        self.create_label(
                            name=label_data["name"],
                            can_id=label_data["can_id"],
                            data=label_data["data"],
                            vehicle_id=label_vehicle_id,
                            description=label_data.get("description", "")
                        )
                        stats["added"] += 1
                    else:
                        # Skip (exists but no overwrite)
                        stats["skipped"] += 1
                        
                except Exception as e:
                    logger.error("Error processing label during import: %s", str(e))
                    stats["errors"] += 1
                    
            return stats
                
        except Exception as e:
            logger.error("Error importing labels: %s", str(e))
            return stats

if __name__ == "__main__":
    # Simple test
    from app.models.database import init_db
    
    # Initialize database
    init_db()
    
    manager = LabelManager()
    
    # Create a vehicle
    vehicle = Vehicle(make="Toyota", model="Corolla", year="2018", region="NA")
    db_session.add(vehicle)
    db_session.commit()
    
    # Create some labels
    manager.create_label("Horn", "0x1A2", "AAFFBBCC00000000", vehicle.id, "Horn button pressed")
    manager.create_label("AC", "0x1F3", "00AAFF1100000000", vehicle.id, "A/C button pressed")
    
    # Search for labels
    results = manager.search_labels(vehicle_make="Toyota")
    print(f"Found {len(results)} labels for Toyota vehicles")
    
    # Export labels
    export_data = manager.export_labels(vehicle_id=vehicle.id)
    print("Export data:", export_data)