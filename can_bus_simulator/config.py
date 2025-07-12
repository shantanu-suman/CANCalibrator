#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

# Get absolute path to the project root (where this file lives)
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

# Flask application settings
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_key_for_can_bus_simulator')
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
HOST = os.environ.get('HOST', '0.0.0.0')
PORT = int(os.environ.get('PORT', 5000))

# File paths
DATA_DIR = os.path.join(PROJECT_ROOT, 'app', 'data')
EXPORT_DIR = os.path.join(DATA_DIR, 'exports')

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

# Database configuration (absolute path to SQLite database)
DATABASE_PATH = os.path.join(DATA_DIR, 'can_simulator.db')
DATABASE_URI = os.environ.get('DATABASE_URI', f'sqlite:///{DATABASE_PATH}')

# CAN Simulator settings
MESSAGE_RATE = float(os.environ.get('MESSAGE_RATE', 10))  # Messages per second
DEFAULT_MESSAGE_COUNT = int(os.environ.get('DEFAULT_MESSAGE_COUNT', 100))
RANDOM_NOISE_PROBABILITY = float(os.environ.get('RANDOM_NOISE_PROBABILITY', 0.05))

# Development mode (enables test data creation)
DEVELOPMENT_MODE = os.environ.get('DEVELOPMENT_MODE', 'True').lower() == 'true'

# DBC File Path (absolute example)
DBC_FILE_PATH = os.environ.get('DBC_FILE_PATH', r"C:\Users\admin\Downloads\FORD_CADS.dbc")
