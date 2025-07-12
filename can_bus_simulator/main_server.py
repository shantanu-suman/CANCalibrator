#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import json
import logging
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import threading

# Import configuration
import config

# Import controllers
from main.controllers.can_simulator import CANSimulator
from main.controllers.can_sniffer import CANSniffer
from main.controllers.calibration_controller import CalibrationController
from main.controllers.label_manager import LabelManager
from main.controllers.playback_engine import PlaybackEngine

# Import database models
from main.models.database import init_db, db_session
from main.models.label import Label
from main.models.vehicle import Vehicle
from main.models.can_message import CANMessage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# === Initialize Flask app with explicit template folder ===
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), 'main', 'templates')
)
app.config['SECRET_KEY'] = config.SECRET_KEY
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize controllers
can_simulator = CANSimulator()
can_sniffer = CANSniffer(can_simulator)
calibration_controller = CalibrationController(can_simulator, can_sniffer)
label_manager = LabelManager()
playback_engine = PlaybackEngine(can_simulator)

# Initialize database
init_db()

# Flag to control the message generation thread
message_thread_running = True

def message_generation_thread():
    """Background thread that generates CAN messages and broadcasts to clients"""
    logger.info("Starting message generation thread")
    
    while message_thread_running:
        try:
            # Generate a new CAN message
            message = can_simulator.generate_message()
            
            # Process through sniffer
            processed_message = can_sniffer.process_message(message)
            
            if processed_message:
                # Check if this message has a label
                # (This could be optimized with caching)
                label = db_session.query(Label).filter(
                    Label.can_id == processed_message["id"],
                    Label.data == processed_message["data"]
                ).first()
                
                if label:
                    processed_message["label"] = label.name
                
                # Send to clients
                socketio.emit('can_message', {
                    'type': 'can_message',
                    'data': processed_message
                })
                
                # If calibration is active, record the message
                if calibration_controller.calibration_active:
                    calibration_controller.record_message(processed_message)
            
            # Control message rate
            time.sleep(1.0 / config.MESSAGE_RATE)
            
        except Exception as e:
            logger.error(f"Error in message generation thread: {str(e)}")
            socketio.emit('error', {
                'type': 'error',
                'data': f"Error generating messages: {str(e)}"
            })
            time.sleep(1.0)  # Wait a bit longer on error

# Routes
@app.route('/')
def index():
    """Render the main dashboard page"""
    return render_template('index.html')

@app.route('/calibration')
def calibration():
    """Render the calibration page"""
    return render_template('calibration.html')

@app.route('/labels')
def labels():
    """Render the labels page"""
    return render_template('labels.html')

@app.route('/playback')
def playback():
    """Render the playback page"""
    return render_template('playback.html')

@app.route('/settings')
def settings():
    """Render the settings page"""
    return render_template('settings.html')

# API Routes
@app.route('/api/labels', methods=['GET'])
def get_labels():
    """Get all labels"""
    try:
        # Get all labels with their vehicles
        query = db_session.query(Label, Vehicle).outerjoin(
            Vehicle, Label.vehicle_id == Vehicle.id)
        
        results = []
        for label, vehicle in query.all():
            label_dict = label.to_dict()
            
            # Add vehicle info if available
            if vehicle:
                label_dict['vehicle'] = {
                    'id': vehicle.id,
                    'make': vehicle.make,
                    'model': vehicle.model,
                    'year': vehicle.year,
                    'region': vehicle.region
                }
                
            results.append(label_dict)
            
        return jsonify(results)
    except Exception as e:
        logger.error(f"Error getting labels: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/labels', methods=['POST'])
def create_label():
    """Create a new label"""
    try:
        data = request.json
        
        # Create the label
        label = label_manager.create_label(
            name=data['name'],
            can_id=data['can_id'],
            data=data['data'],
            vehicle_id=data.get('vehicle_id'),
            description=data.get('description')
        )
        
        if label:
            # Also add this to the simulator as an event
            can_simulator.add_event(
                event_name=data['name'],
                can_id=data['can_id'],
                on_data=data['data']
            )
            
            return jsonify({'success': True, 'id': label.id})
        else:
            return jsonify({'success': False, 'error': 'Failed to create label'}), 400
            
    except Exception as e:
        logger.error(f"Error creating label: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/labels/<int:label_id>', methods=['DELETE'])
def delete_label(label_id):
    """Delete a label"""
    try:
        success = label_manager.delete_label(label_id)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Label not found'}), 404
    except Exception as e:
        logger.error(f"Error deleting label: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/vehicles', methods=['GET'])
def get_vehicles():
    """Get all vehicles"""
    try:
        vehicles = db_session.query(Vehicle).all()
        results = [
            {
                'id': v.id,
                'make': v.make,
                'model': v.model,
                'year': v.year,
                'region': v.region
            } for v in vehicles
        ]
        
        return jsonify(results)
    except Exception as e:
        logger.error(f"Error getting vehicles: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/vehicles', methods=['POST'])
def create_vehicle():
    """Create a new vehicle"""
    try:
        data = request.json
        
        # Create the vehicle
        vehicle = Vehicle(
            make=data['make'],
            model=data['model'],
            year=data['year'],
            region=data['region']
        )
        
        db_session.add(vehicle)
        db_session.commit()
        
        return jsonify({'success': True, 'id': vehicle.id})
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error creating vehicle: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/playback/sequences', methods=['GET'])
def get_sequences():
    """Get all playback sequences"""
    try:
        sequences = playback_engine.get_all_sequences()
        return jsonify(sequences)
    except Exception as e:
        logger.error(f"Error getting sequences: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/playback/start', methods=['POST'])
def start_playback():
    """Start a playback sequence"""
    try:
        data = request.json
        
        name = data.get('name')
        loop = data.get('loop', False)
        
        if not name:
            return jsonify({'success': False, 'error': 'Sequence name required'}), 400
            
        success = playback_engine.play_sequence(name, loop)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to start playback'}), 400
            
    except Exception as e:
        logger.error(f"Error starting playback: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/playback/stop', methods=['POST'])
def stop_playback():
    """Stop the current playback"""
    try:
        success = playback_engine.stop_playback()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error stopping playback: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle client connection to WebSocket"""
    logger.info('Client connected to WebSocket')
    emit('status', {
        'type': 'status',
        'data': 'Connected to server'
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection from WebSocket"""
    logger.info('Client disconnected from WebSocket')

@socketio.on('start_calibration')
def handle_start_calibration(data):
    """Start calibration mode"""
    try:
        event_name = data.get('event_name')
        if not event_name:
            emit('error', {
                'type': 'error',
                'data': 'Event name is required'
            })
            return
            
        # Start calibration
        calibration_controller.start_calibration(event_name)
        
        emit('status', {
            'type': 'status',
            'data': f'Calibration started for event: {event_name}'
        })
        
    except Exception as e:
        logger.error(f"Error starting calibration: {str(e)}")
        emit('error', {
            'type': 'error',
            'data': f'Error starting calibration: {str(e)}'
        })

@socketio.on('stop_calibration')
def handle_stop_calibration():
    """Stop calibration mode and analyze results"""
    try:
        # Stop calibration and get results
        candidates = calibration_controller.stop_calibration()
        
        # Send candidates to client
        emit('calibration_results', {
            'type': 'calibration_results',
            'data': candidates
        })
        
    except Exception as e:
        logger.error(f"Error stopping calibration: {str(e)}")
        emit('error', {
            'type': 'error',
            'data': f'Error stopping calibration: {str(e)}'
        })

@socketio.on('confirm_calibration')
def handle_confirm_calibration(data):
    """Confirm a calibration result"""
    try:
        event_name = data.get('event_name')
        can_id = data.get('can_id')
        data_value = data.get('data')
        
        if not all([event_name, can_id, data_value]):
            emit('error', {
                'type': 'error',
                'data': 'Missing required fields for calibration confirmation'
            })
            return
            
        # Confirm calibration
        calibration_controller.confirm_calibration(can_id, data_value)
        
        # Create a label for this calibrated event
        label = label_manager.create_label(
            name=event_name,
            can_id=can_id,
            data=data_value,
            description=f"Calibrated event: {event_name}"
        )
        
        emit('status', {
            'type': 'status',
            'data': f'Calibration confirmed for event: {event_name}'
        })
        
    except Exception as e:
        logger.error(f"Error confirming calibration: {str(e)}")
        emit('error', {
            'type': 'error',
            'data': f'Error confirming calibration: {str(e)}'
        })

@socketio.on('calibration_message')
def handle_calibration_message(data):
    """Manually send a message to calibration"""
    try:
        can_id = data.get('id')
        data_value = data.get('data')
        
        if not all([can_id, data_value]):
            emit('error', {
                'type': 'error',
                'data': 'Missing ID or data for calibration message'
            })
            return
            
        # Create a message with current timestamp
        message = {
            'id': can_id,
            'data': data_value,
            'timestamp': time.time()
        }
        
        # Record in calibration if active
        if calibration_controller.calibration_active:
            calibration_controller.record_message(message)
            
            emit('status', {
                'type': 'status',
                'data': f'Message sent to calibration: {can_id}'
            })
        else:
            emit('error', {
                'type': 'error',
                'data': 'Calibration is not active'
            })
        
    except Exception as e:
        logger.error(f"Error handling calibration message: {str(e)}")
        emit('error', {
            'type': 'error',
            'data': f'Error: {str(e)}'
        })

# Application startup
def start_message_thread():
    """Start the message generation thread"""
    global message_thread_running
    message_thread_running = True
    
    thread = threading.Thread(target=message_generation_thread)
    thread.daemon = True
    thread.start()
    
    return thread

# Create some initial test data
def create_test_data():
    """Create some test data for development purposes"""
    try:
        # Create a test vehicle if none exist
        if db_session.query(Vehicle).count() == 0:
            vehicle = Vehicle(
                make="Toyota",
                model="Corolla",
                year="2020",
                region="NA"
            )
            db_session.add(vehicle)
            db_session.commit()
            logger.info(f"Created test vehicle: Toyota Corolla 2020")
            
            # Create some test labels
            labels = [
                {"name": "Horn", "can_id": "0x1A2", "data": "FF00000000000000", 
                 "description": "Horn button pressed"},
                {"name": "Turn Signal Left", "can_id": "0x1B4", "data": "010000000000000", 
                 "description": "Left turn signal activated"},
                {"name": "Turn Signal Right", "can_id": "0x1B4", "data": "020000000000000", 
                 "description": "Right turn signal activated"},
                {"name": "Brake", "can_id": "0x224", "data": "FF000000FFFF0000", 
                 "description": "Brake pedal pressed"}
            ]
            
            for label_data in labels:
                label = Label(
                    name=label_data["name"],
                    can_id=label_data["can_id"],
                    data=label_data["data"],
                    vehicle_id=vehicle.id,
                    description=label_data["description"]
                )
                db_session.add(label)
                
                # Also add to simulator as events
                can_simulator.add_event(
                    event_name=label_data["name"],
                    can_id=label_data["can_id"],
                    on_data=label_data["data"]
                )
                
            db_session.commit()
            logger.info(f"Created {len(labels)} test labels")
            
        # Create test playback sequences
        if len(playback_engine.sequences) == 0:
            # Sequence 1: Turn left and then right
            turn_sequence = [
                {"id": "0x1B4", "data": "010000000000000", "delay": 0.5},  # Left turn
                {"id": "0x1B4", "data": "000000000000000", "delay": 1.0},  # Off
                {"id": "0x1B4", "data": "020000000000000", "delay": 0.5},  # Right turn
                {"id": "0x1B4", "data": "000000000000000", "delay": 0.5}   # Off
            ]
            playback_engine.create_sequence("Turn Signals Test", turn_sequence)
            
            # Sequence 2: Horn test
            horn_sequence = [
                {"id": "0x1A2", "data": "FF00000000000000", "delay": 0.3},  # Horn on
                {"id": "0x1A2", "data": "0000000000000000", "delay": 0.5},  # Horn off
                {"id": "0x1A2", "data": "FF00000000000000", "delay": 0.3},  # Horn on
                {"id": "0x1A2", "data": "0000000000000000", "delay": 0.2}   # Horn off
            ]
            playback_engine.create_sequence("Horn Test", horn_sequence)
            
            logger.info("Created test playback sequences")
    
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error creating test data: {str(e)}")

# Run the application
if __name__ == '__main__':
    try:
        # Create test data for development
        if config.DEVELOPMENT_MODE:
            create_test_data()
        
        # Start the message generation thread
        message_thread = start_message_thread()
        
        # Start the Flask SocketIO server
        logger.info(f"Starting CAN Bus Simulator on port {config.PORT}")
        socketio.run(app, host=config.HOST, port=config.PORT, debug=config.DEBUG)
        
    except KeyboardInterrupt:
        logger.info("Shutting down CAN Bus Simulator...")
        message_thread_running = False
        time.sleep(1)  # Give thread time
