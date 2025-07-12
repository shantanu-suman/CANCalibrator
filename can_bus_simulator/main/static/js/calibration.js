/**
 * CAN Bus Simulator - Calibration JavaScript
 * 
 * This file handles the frontend functionality for the Calibration page,
 * including calibration mode controls, vehicle management, and event detection.
 */

// WebSocket connection for real-time CAN messages
let socket = null;
let calibrationActive = false;
let calibrationCountdown = 5; // 5 seconds for calibration
let calibrationInterval = null;
let selectedCandidateId = null;
let currentEventName = null;
let canMessages = []; // Array to store messages during calibration
const MAX_MESSAGES = 200; // Maximum number of messages to store

// Connect to WebSocket
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    const wsUrl = protocol + window.location.host + '/ws/can';
    
    socket = new WebSocket(wsUrl);
    
    socket.onopen = function(e) {
        console.log("WebSocket connection established");
        showStatusMessage("Connected to CAN simulator", "success");
        document.getElementById('connection-status').className = 'connected';
    };
    
    socket.onmessage = function(event) {
        const message = JSON.parse(event.data);
        
        if (message.type === "can_message") {
            handleCanMessage(message.data);
        } else if (message.type === "calibration_results") {
            handleCalibrationResults(message.data);
        } else if (message.type === "status") {
            showStatusMessage(message.data, "info");
        } else if (message.type === "error") {
            showStatusMessage(message.data, "error");
        }
    };
    
    socket.onclose = function(event) {
        if (event.wasClean) {
            console.log(`Connection closed cleanly, code=${event.code}, reason=${event.reason}`);
        } else {
            console.error('Connection died');
            showStatusMessage("Connection lost. Reconnecting...", "error");
        }
        document.getElementById('connection-status').className = 'disconnected';
        
        // Reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
    };
    
    socket.onerror = function(error) {
        console.error(`WebSocket error: ${error.message}`);
        showStatusMessage("WebSocket error", "error");
    };
}

// Handle incoming CAN messages
function handleCanMessage(message) {
    // Only process during calibration
    if (calibrationActive) {
        // Add to message list
        canMessages.unshift(message);
        if (canMessages.length > MAX_MESSAGES) {
            canMessages.pop(); // Remove oldest message if limit reached
        }
        
        // Update UI
        updateMessageTable();
    }
}

// Handle calibration results from server
function handleCalibrationResults(results) {
    // Stop calibration mode
    stopCalibration();
    
    // Show results
    document.getElementById('calibration-inactive').style.display = 'none';
    document.getElementById('calibration-active').style.display = 'none';
    document.getElementById('calibration-results').style.display = 'block';
    
    // Update event name in results
    document.getElementById('result-event-name').textContent = currentEventName;
    
    // Populate candidate messages
    const candidatesContainer = document.getElementById('candidate-messages');
    candidatesContainer.innerHTML = '';
    
    if (results.length === 0) {
        candidatesContainer.innerHTML = '<div class="alert alert-warning">No candidate messages detected. Try again.</div>';
        return;
    }
    
    // Create candidate message elements
    results.forEach((candidate, index) => {
        const candidateEl = document.createElement('div');
        candidateEl.className = 'candidate-message';
        candidateEl.dataset.id = candidate.id;
        candidateEl.dataset.data = candidate.data;
        candidateEl.dataset.index = index;
        
        // Format score as percentage
        const scorePercent = (candidate.score * 100).toFixed(0);
        
        candidateEl.innerHTML = `
            <div class="d-flex justify-content-between">
                <div>
                    <strong>ID: ${candidate.id}</strong> 
                    <span class="badge bg-info">${candidate.count} occurrences</span>
                </div>
                <div>
                    <span class="badge bg-success">${scorePercent}% match</span>
                </div>
            </div>
            <div class="can-data mt-1">${candidate.data}</div>
        `;
        
        candidateEl.addEventListener('click', function() {
            // Select this candidate
            selectCandidate(this);
        });
        
        candidatesContainer.appendChild(candidateEl);
    });
    
    // Select the first candidate by default
    selectCandidate(candidatesContainer.children[0]);
}

// Select a candidate message
function selectCandidate(element) {
    // Remove selection from all candidates
    const candidates = document.querySelectorAll('.candidate-message');
    candidates.forEach(el => el.classList.remove('selected'));
    
    // Add selection to this candidate
    element.classList.add('selected');
    
    // Store selection
    selectedCandidateId = element.dataset.index;
}

// Update the message table with current messages
function updateMessageTable() {
    const tableBody = document.getElementById('calibration-messages-body');
    const displayCount = Math.min(50, canMessages.length); // Display at most 50 rows
    const highlightChanges = document.getElementById('highlight-changes').checked;
    
    // Clear existing rows
    tableBody.innerHTML = '';
    
    // Track changes by ID
    const lastDataByID = {};
    
    // Add new rows
    for (let i = 0; i < displayCount; i++) {
        const message = canMessages[i];
        const row = document.createElement('tr');
        
        // Check for data changes
        let changeText = '';
        if (message.id in lastDataByID) {
            if (lastDataByID[message.id] !== message.data) {
                changeText = '✓';
                if (highlightChanges) {
                    row.classList.add('change-detected');
                }
            }
        }
        lastDataByID[message.id] = message.data;
        
        // Format timestamp
        const time = new Date(message.timestamp * 1000);
        const timeString = time.toLocaleTimeString('en-US', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            fractionalSecondDigits: 3
        });
        
        // Create cells
        row.innerHTML = `
            <td>${timeString}</td>
            <td class="can-id">${message.id}</td>
            <td class="can-data">${message.data}</td>
            <td class="text-center">${changeText}</td>
        `;
        
        tableBody.appendChild(row);
    }
}

// Start calibration mode
function startCalibration() {
    const eventName = document.getElementById('event-name').value.trim();
    
    if (!eventName) {
        showStatusMessage("Please enter an event name", "error");
        return;
    }
    
    // Store event name
    currentEventName = eventName;
    
    // Clear message list
    canMessages = [];
    
    // Show calibration UI
    document.getElementById('calibration-inactive').style.display = 'none';
    document.getElementById('calibration-active').style.display = 'block';
    document.getElementById('calibration-results').style.display = 'none';
    document.getElementById('active-event-name').textContent = eventName;
    
    // Set calibration state
    calibrationActive = true;
    calibrationCountdown = 5;
    
    // Send start calibration message to server
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            type: 'start_calibration',
            event_name: eventName
        }));
    }
    
    // Start countdown
    updateCountdown();
    calibrationInterval = setInterval(updateCountdown, 1000);
    
    showStatusMessage(`Started calibration for "${eventName}"`, "info");
}

// Update calibration countdown
function updateCountdown() {
    if (calibrationCountdown <= 0) {
        // Time's up - stop calibration
        stopCalibration();
        return;
    }
    
    document.getElementById('calibration-countdown').textContent = `${calibrationCountdown} seconds remaining`;
    document.getElementById('calibration-progress').style.width = `${(5 - calibrationCountdown) * 20}%`;
    calibrationCountdown--;
}

// Stop calibration mode
function stopCalibration() {
    // Clear interval
    if (calibrationInterval) {
        clearInterval(calibrationInterval);
        calibrationInterval = null;
    }
    
    // Set calibration state
    calibrationActive = false;
    
    // Send stop calibration message to server
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            type: 'stop_calibration'
        }));
    }
}

// Cancel calibration and return to start view
function cancelCalibration() {
    document.getElementById('calibration-inactive').style.display = 'block';
    document.getElementById('calibration-active').style.display = 'none';
    document.getElementById('calibration-results').style.display = 'none';
    
    selectedCandidateId = null;
    currentEventName = null;
    
    showStatusMessage("Calibration cancelled", "info");
}

// Confirm selected calibration
function confirmCalibration() {
    if (selectedCandidateId === null) {
        showStatusMessage("Please select a message", "error");
        return;
    }
    
    // Get the selected candidate
    const candidates = document.querySelectorAll('.candidate-message');
    const selectedCandidate = candidates[selectedCandidateId];
    
    const canId = selectedCandidate.dataset.id;
    const data = selectedCandidate.dataset.data;
    
    // Send confirmation to server
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            type: 'confirm_calibration',
            event_name: currentEventName,
            can_id: canId,
            data: data
        }));
    }
    
    // Return to start view
    document.getElementById('calibration-inactive').style.display = 'block';
    document.getElementById('calibration-active').style.display = 'none';
    document.getElementById('calibration-results').style.display = 'none';
    
    // Reset state
    selectedCandidateId = null;
    currentEventName = null;
    
    showStatusMessage(`Calibration confirmed for "${currentEventName}"`, "success");
    
    // Update calibrated events list
    loadCalibratedEvents();
}

// Load calibrated events from server
function loadCalibratedEvents() {
    fetch('/api/labels')
    .then(response => response.json())
    .then(data => {
        const tableBody = document.getElementById('calibrated-events-body');
        tableBody.innerHTML = '';
        
        if (data.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="5" class="text-center">No calibrated events yet</td></tr>';
            return;
        }
        
        data.forEach(label => {
            const row = document.createElement('tr');
            
            // Get vehicle info
            const vehicle = label.vehicle ? 
                `${label.vehicle.make} ${label.vehicle.model} (${label.vehicle.year})` : 
                'Not specified';
            
            row.innerHTML = `
                <td>${label.name}</td>
                <td class="can-id">${label.can_id}</td>
                <td class="can-data">${label.data}</td>
                <td>${vehicle}</td>
                <td>
                    <button class="btn btn-sm btn-outline-danger" 
                            onclick="deleteLabel(${label.id})">Delete</button>
                </td>
            `;
            
            tableBody.appendChild(row);
        });
    })
    .catch(error => {
        showStatusMessage(`Error loading calibrated events: ${error.message}`, "error");
    });
}

// Delete a label
function deleteLabel(labelId) {
    if (!confirm('Are you sure you want to delete this calibrated event?')) {
        return;
    }
    
    fetch(`/api/labels/${labelId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showStatusMessage("Label deleted successfully", "success");
            loadCalibratedEvents();
        } else {
            showStatusMessage(`Error: ${data.error}`, "error");
        }
    })
    .catch(error => {
        showStatusMessage(`Error: ${error.message}`, "error");
    });
}

// Save vehicle information
function saveVehicleInfo() {
    const vehicleData = {
        make: document.getElementById('vehicle-make').value.trim(),
        model: document.getElementById('vehicle-model').value.trim(),
        year: document.getElementById('vehicle-year').value.trim(),
        region: document.getElementById('vehicle-region').value
    };
    
    // Validate
    if (!vehicleData.make || !vehicleData.model || !vehicleData.year) {
        showStatusMessage("Please fill in all required vehicle fields", "error");
        return;
    }
    
    // Send to server
    fetch('/api/vehicles', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(vehicleData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showStatusMessage("Vehicle information saved", "success");
        } else {
            showStatusMessage(`Error: ${data.error}`, "error");
        }
    })
    .catch(error => {
        showStatusMessage(`Error: ${error.message}`, "error");
    });
}

// Show a status message
function showStatusMessage(message, type = "info") {
    const statusArea = document.getElementById('status-messages');
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    statusArea.appendChild(alertDiv);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        alertDiv.classList.remove('show');
        setTimeout(() => alertDiv.remove(), 150);
    }, 5000);
}

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    // Connect to WebSocket
    connectWebSocket();
    
    // Load calibrated events
    loadCalibratedEvents();
    
    // Setup event listeners
    document.getElementById('start-calibration-btn').addEventListener('click', startCalibration);
    document.getElementById('stop-calibration-btn').addEventListener('click', stopCalibration);
    document.getElementById('cancel-calibration-btn').addEventListener('click', cancelCalibration);
    document.getElementById('confirm-calibration-btn').addEventListener('click', confirmCalibration);
    document.getElementById('save-vehicle-btn').addEventListener('click', saveVehicleInfo);
    
    // Highlight changes checkbox
    document.getElementById('highlight-changes').addEventListener('change', updateMessageTable);
    
    // Event name input - allow Enter key to start calibration
    document.getElementById('event-name').addEventListener('keyup', function(event) {
        if (event.key === 'Enter') {
            startCalibration();
        }
    });
    
    // Show starting message
    showStatusMessage("Calibration mode ready", "info");
});