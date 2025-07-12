# CAN-BUS Simulator and Web Application

This application provides a web-based environment for simulating CAN-BUS communication, supporting message sniffing, event calibration, CAN message labelling, and playback functionality.

## Overview

This project simulates a CAN-BUS environment without requiring physical hardware. It allows users to:
- Sniff CAN messages in real-time
- Calibrate and detect events (like Horn, AC, etc.)
- Label CAN ID + Data combinations
- Store labelled events by Vehicle (Make/Model/Year/Region)
- Playback previously labelled messages

## Features

- **CAN Simulator Engine**: Generates realistic CAN-BUS traffic
- **CAN Sniffer & Filter**: Monitors and filters the simulated bus traffic
- **Calibration Mode**: Detects CAN messages associated with user-triggered events
- **Label Manager**: Associates CAN messages with human-readable labels
- **Vehicle Database**: Stores vehicle-specific CAN message mappings
- **Playback Engine**: Replays stored CAN messages
- **Interactive Web UI**: User-friendly interface for all operations

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/can-bus-simulator.git
   cd can-bus-simulator
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python app.py
   ```

4. Access the web interface at: http://localhost:5000

## System Requirements

- Python 3.7+
- Modern web browser (Chrome, Firefox, Edge, Safari)
- Operating System: Windows, macOS, or Linux

## Project Structure

```
can_bus_simulator/
├── app/
│   ├── controllers/      # Application controllers
│   ├── models/           # Data models
│   ├── static/           # CSS, JS, and static assets
│   └── templates/        # HTML templates
├── app.py                # Main application entry point
├── config.py             # Configuration settings
├── requirements.txt      # Project dependencies
└── README.md             # This file
```

## Usage Guide

### Vehicle Selection
- Use the dropdown menus to select the vehicle Make/Model/Year/Region
- This information is stored alongside any labelled CAN messages

### CAN-BUS Simulation
- The simulator automatically begins generating CAN messages when launched
- Each message contains an ID (hex), DATA (8 bytes), and Timestamp

### Sniff & Filter Mode
- View live CAN messages in the main interface
- Use filters to isolate messages by ID or data pattern
- System will highlight significant changes in message patterns

### Calibration Mode
1. Select "Calibration Mode" from the navigation menu
2. Follow on-screen prompts to perform actions (e.g., "Press Horn")
3. The system will detect and display CAN messages that changed during the action
4. Choose the correct message and provide a label
5. Save the labelled event to the database

### Playback Mode
1. Select "Playback Mode" from the navigation menu
2. Choose a previously saved vehicle configuration
3. Select from available labelled events
4. Click "Replay" to send the message to the simulated CAN bus
5. View confirmation in the status log

## Database Schema

The application uses a local SQLite database with the following main tables:
- `vehicles`: Stores vehicle make, model, year, and region
- `can_messages`: Stores CAN message IDs, data payloads, and timestamps
- `labels`: Maps CAN messages to human-readable labels
- `events`: Links labels to specific vehicles

## Development

### Technology Stack
- Backend: Python with Flask
- CAN Simulation: python-can with custom simulation loop
- Database: SQLite (local)
- Frontend: Bootstrap with jQuery
- Real-time Updates: WebSockets

### Future Extensions
- Integration with real CAN hardware (CANable, MCP2515, etc.)
- Export functionality for labelled CAN logs (CSV/JSON)
- Cloud synchronization for fleet-wide data collection
- AI/ML model for automatic event detection

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

For questions or support, please contact: your.email@example.com