/**
 * CAN Bus Simulator JavaScript
 * 
 * This file handles the frontend functionality for the CAN Bus Simulator,
 * including real-time message display, filtering, and visualization.
 */

// WebSocket connection for real-time CAN messages
let socket = null;
let canMessages = []; // Array to store recent messages
const MAX_MESSAGES = 1000; // Maximum number of messages to store
let activeFilters = {
    id: [],
    data: []
};
let isPaused = false;
let chartData = {}; // For tracking data for charts

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
    if (isPaused) return; // Don't process messages if paused
    
    // Filter messages if filters are active
    if (activeFilters.id.length > 0) {
        if (!activeFilters.id.includes(message.id)) return;
    }
    
    if (activeFilters.data.length > 0) {
        let matchesDataFilter = false;
        for (const filter of activeFilters.data) {
            if (message.data.includes(filter)) {
                matchesDataFilter = true;
                break;
            }
        }
        if (!matchesDataFilter) return;
    }
    
    // Add to message list
    canMessages.unshift(message);
    if (canMessages.length > MAX_MESSAGES) {
        canMessages.pop(); // Remove oldest message if limit reached
    }
    
    // Update UI
    updateMessageTable();
    updateCharts(message);
}

// Update the message table with current messages
function updateMessageTable() {
    const tableBody = document.getElementById('can-messages-body');
    const displayCount = Math.min(100, canMessages.length); // Display at most 100 rows
    
    // Clear existing rows
    tableBody.innerHTML = '';
    
    // Add new rows
    for (let i = 0; i < displayCount; i++) {
        const message = canMessages[i];
        const row = document.createElement('tr');
        
        // Determine if this is a significant message (has a label)
        if (message.label) {
            row.className = 'significant';
        }
        
        // Highlight row if it represents a change
        if (message.change_detected) {
            row.className += ' change-detected';
        }
        
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
            <td>${message.label || ''}</td>
            <td>
                <button class="btn btn-sm btn-outline-info action-btn" 
                        onclick="showMessageDetails('${i}')">Details</button>
            </td>
        `;
        
        tableBody.appendChild(row);
    }
    
    // Update counter
    document.getElementById('message-count').textContent = canMessages.length;
}

// Show detailed information about a message
function showMessageDetails(index) {
    const message = canMessages[index];
    const modal = document.getElementById('message-detail-modal');
    const modalTitle = document.getElementById('message-detail-title');
    const modalBody = document.getElementById('message-detail-body');
    
    modalTitle.textContent = `Message Details: ${message.id}`;
    
    // Format timestamp
    const time = new Date(message.timestamp * 1000);
    const timeString = time.toLocaleString('en-US', {
        hour12: false,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        fractionalSecondDigits: 3
    });
    
    // Parse data into bytes
    const bytes = [];
    for (let i = 0; i < message.data.length; i += 2) {
        bytes.push(message.data.substr(i, 2));
    }
    
    // Generate binary representation
    const binary = bytes.map(byte => {
        const num = parseInt(byte, 16);
        return num.toString(2).padStart(8, '0');
    }).join(' ');
    
    modalBody.innerHTML = `
        <table class="table table-sm">
            <tr>
                <th>Timestamp:</th>
                <td>${timeString}</td>
            </tr>
            <tr>
                <th>CAN ID:</th>
                <td>${message.id} (${parseInt(message.id.replace('0x', ''), 16)} decimal)</td>
            </tr>
            <tr>
                <th>Data (Hex):</th>
                <td>${bytes.join(' ')}</td>
            </tr>
            <tr>
                <th>Data (Binary):</th>
                <td><span class="binary-data">${binary}</span></td>
            </tr>
            ${message.label ? `<tr><th>Label:</th><td>${message.label}</td></tr>` : ''}
        </table>
        
        <h5>Actions</h5>
        <div class="btn-group">
            <button class="btn btn-primary" onclick="addIdFilter('${message.id}')">Filter by this ID</button>
            <button class="btn btn-secondary" onclick="createLabel('${message.id}', '${message.data}')">Create Label</button>
            <button class="btn btn-info" onclick="sendToCalibration('${message.id}', '${message.data}')">Use for Calibration</button>
        </div>
    `;
    
    // Show modal
    const modalInstance = new bootstrap.Modal(modal);
    modalInstance.show();
}

// Add a filter for a specific ID
function addIdFilter(id) {
    if (!activeFilters.id.includes(id)) {
        activeFilters.id.push(id);
        updateFilterDisplay();
        showStatusMessage(`Added filter for ID: ${id}`, "info");
    }
}

// Update the display of active filters
function updateFilterDisplay() {
    const filterContainer = document.getElementById('active-filters');
    filterContainer.innerHTML = '';
    
    // Add ID filters
    activeFilters.id.forEach(id => {
        const filterBadge = document.createElement('span');
        filterBadge.className = 'badge bg-primary me-2';
        filterBadge.innerHTML = `ID: ${id} <button class="btn-close btn-close-white" 
            onclick="removeIdFilter('${id}')"></button>`;
        filterContainer.appendChild(filterBadge);
    });
    
    // Add data filters
    activeFilters.data.forEach((pattern, index) => {
        const filterBadge = document.createElement('span');
        filterBadge.className = 'badge bg-secondary me-2';
        filterBadge.innerHTML = `Data: ${pattern} <button class="btn-close btn-close-white" 
            onclick="removeDataFilter(${index})"></button>`;
        filterContainer.appendChild(filterBadge);
    });
}

// Remove an ID filter
function removeIdFilter(id) {
    activeFilters.id = activeFilters.id.filter(f => f !== id);
    updateFilterDisplay();
    showStatusMessage(`Removed filter for ID: ${id}`, "info");
}

// Remove a data filter
function removeDataFilter(index) {
    const pattern = activeFilters.data[index];
    activeFilters.data.splice(index, 1);
    updateFilterDisplay();
    showStatusMessage(`Removed data filter: ${pattern}`, "info");
}

// Add a data filter
function addDataFilter() {
    const pattern = document.getElementById('data-filter-input').value;
    if (pattern && !activeFilters.data.includes(pattern)) {
        activeFilters.data.push(pattern);
        updateFilterDisplay();
        showStatusMessage(`Added data filter: ${pattern}`, "info");
        document.getElementById('data-filter-input').value = '';
    }
}

// Clear all filters
function clearFilters() {
    activeFilters.id = [];
    activeFilters.data = [];
    updateFilterDisplay();
    showStatusMessage("Cleared all filters", "info");
}

// Toggle pause/resume of message display
function togglePause() {
    isPaused = !isPaused;
    const pauseBtn = document.getElementById('pause-btn');
    if (isPaused) {
        pauseBtn.textContent = 'Resume';
        pauseBtn.className = 'btn btn-success';
        showStatusMessage("Message display paused", "info");
    } else {
        pauseBtn.textContent = 'Pause';
        pauseBtn.className = 'btn btn-warning';
        showStatusMessage("Message display resumed", "info");
    }
}

// Clear the message list
function clearMessages() {
    canMessages = [];
    updateMessageTable();
    showStatusMessage("Messages cleared", "info");
}

// Create a label for a message
function createLabel(canId, data) {
    // Show label creation modal
    const modal = document.getElementById('create-label-modal');
    document.getElementById('label-can-id').value = canId;
    document.getElementById('label-data').value = data;
    document.getElementById('label-name').value = '';
    document.getElementById('label-description').value = '';
    
    const modalInstance = new bootstrap.Modal(modal);
    modalInstance.show();
}

// Save a new label
function saveLabel() {
    const labelData = {
        name: document.getElementById('label-name').value,
        can_id: document.getElementById('label-can-id').value,
        data: document.getElementById('label-data').value,
        description: document.getElementById('label-description').value,
        vehicle_id: document.getElementById('vehicle-select').value || null
    };
    
    // Validate
    if (!labelData.name || !labelData.can_id || !labelData.data) {
        showStatusMessage("Please fill in all required fields", "error");
        return;
    }
    
    // Send to server
    fetch('/api/labels', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(labelData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showStatusMessage(`Label "${labelData.name}" created successfully`, "success");
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('create-label-modal'));
            modal.hide();
        } else {
            showStatusMessage(`Error: ${data.error}`, "error");
        }
    })
    .catch(error => {
        showStatusMessage(`Error: ${error.message}`, "error");
    });
}

// Send a message to calibration mode
function sendToCalibration(canId, data) {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            type: 'calibration_message',
            id: canId,
            data: data
        }));
        showStatusMessage(`Message sent to calibration mode: ${canId}`, "info");
    } else {
        showStatusMessage("WebSocket not connected", "error");
    }
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

// Initialize charts for data visualization
function initCharts() {
    const ctx = document.getElementById('message-rate-chart').getContext('2d');
    messageRateChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: Array(30).fill(''),
            datasets: [{
                label: 'Messages per second',
                data: Array(30).fill(0),
                borderColor: 'rgba(75, 192, 192, 1)',
                tension: 0.4,
                fill: false
            }]
        },
        options: {
            scales: {
                y: {
                    beginAtZero: true
                }
            },
            animation: {
                duration: 0
            },
            plugins: {
                legend: {
                    display: true
                }
            }
        }
    });
    
    // Start updating message rate
    setInterval(updateMessageRate, 1000);
}

// Update message rate chart
function updateMessageRate() {
    // Count messages in the last second
    const now = Date.now() / 1000;
    const oneSecondAgo = now - 1;
    
    const recentMessages = canMessages.filter(msg => msg.timestamp >= oneSecondAgo);
    const rate = recentMessages.length;
    
    // Update chart
    messageRateChart.data.labels.shift();
    messageRateChart.data.labels.push('');
    
    messageRateChart.data.datasets[0].data.shift();
    messageRateChart.data.datasets[0].data.push(rate);
    
    messageRateChart.update();
}

// Update visualization charts with new message data
function updateCharts(message) {
    // Track data by ID for visualization
    if (!chartData[message.id]) {
        chartData[message.id] = {
            values: [],
            timestamps: []
        };
    }
    
    // Extract a numeric value from the first byte
    const firstByte = parseInt(message.data.substr(0, 2), 16);
    chartData[message.id].values.push(firstByte);
    chartData[message.id].timestamps.push(message.timestamp);
    
    // Keep only recent data
    const maxDataPoints = 100;
    if (chartData[message.id].values.length > maxDataPoints) {
        chartData[message.id].values.shift();
        chartData[message.id].timestamps.shift();
    }
    
    // Update ID frequency table
    updateIdFrequencyTable();
}

// Update table showing message frequency by ID
function updateIdFrequencyTable() {
    const tableBody = document.getElementById('id-frequency-body');
    const idCounts = {};
    
    // Count messages by ID
    for (const message of canMessages) {
        if (!idCounts[message.id]) {
            idCounts[message.id] = 1;
        } else {
            idCounts[message.id]++;
        }
    }
    
    // Sort IDs by count
    const sortedIds = Object.keys(idCounts).sort((a, b) => idCounts[b] - idCounts[a]);
    
    // Update table
    tableBody.innerHTML = '';
    for (let i = 0; i < Math.min(10, sortedIds.length); i++) {
        const id = sortedIds[i];
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${id}</td>
            <td>${idCounts[id]}</td>
            <td><button class="btn btn-sm btn-primary" onclick="addIdFilter('${id}')">Filter</button></td>
        `;
        tableBody.appendChild(row);
    }
}

// Start a playback sequence
function startPlayback() {
    const sequenceName = document.getElementById('sequence-select').value;
    const loopPlayback = document.getElementById('loop-playback').checked;
    
    if (!sequenceName) {
        showStatusMessage("Please select a sequence to play", "error");
        return;
    }
    
    // Send to server
    fetch('/api/playback/start', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            name: sequenceName,
            loop: loopPlayback
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showStatusMessage(`Started playback of "${sequenceName}"`, "success");
        } else {
            showStatusMessage(`Error: ${data.error}`, "error");
        }
    })
    .catch(error => {
        showStatusMessage(`Error: ${error.message}`, "error");
    });
}

// Stop the current playback
function stopPlayback() {
    fetch('/api/playback/stop', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showStatusMessage("Stopped playback", "success");
        } else {
            showStatusMessage(`Error: ${data.error}`, "error");
        }
    })
    .catch(error => {
        showStatusMessage(`Error: ${error.message}`, "error");
    });
}

// Load sequences into the dropdown
function loadSequences() {
    fetch('/api/playback/sequences')
    .then(response => response.json())
    .then(data => {
        const select = document.getElementById('sequence-select');
        select.innerHTML = '<option value="">Select a sequence</option>';
        
        data.forEach(sequence => {
            const option = document.createElement('option');
            option.value = sequence.name;
            option.textContent = `${sequence.name} (${sequence.message_count} messages)`;
            select.appendChild(option);
        });
    })
    .catch(error => {
        showStatusMessage(`Error loading sequences: ${error.message}`, "error");
    });
}

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    // Connect to WebSocket
    connectWebSocket();
    
    // Initialize charts
    initCharts();
    
    // Load sequences
    loadSequences();
    
    // Setup event listeners
    document.getElementById('add-filter-btn').addEventListener('click', addDataFilter);
    document.getElementById('clear-filters-btn').addEventListener('click', clearFilters);
    document.getElementById('pause-btn').addEventListener('click', togglePause);
    document.getElementById('clear-btn').addEventListener('click', clearMessages);
    document.getElementById('save-label-btn').addEventListener('click', saveLabel);
    document.getElementById('start-playback-btn').addEventListener('click', startPlayback);
    document.getElementById('stop-playback-btn').addEventListener('click', stopPlayback);
    
    // Data filter input - allow Enter key
    document.getElementById('data-filter-input').addEventListener('keyup', function(event) {
        if (event.key === 'Enter') {
            addDataFilter();
        }
    });
    
    // Show starting message
    showStatusMessage("CAN Bus Simulator started", "info");
});