/**
 * CAN Bus Simulator - Playback JavaScript
 * 
 * This file handles the frontend functionality for the Playback page,
 * including sequence management, playback controls, and recording.
 */

// WebSocket connection for real-time CAN messages
let socket = null;
let sequences = []; // Array to store available sequences
let selectedSequence = null; // Currently selected sequence
let recordedMessages = []; // Array to store recorded messages
let playbackActive = false;
let playbackPaused = false;
let playbackStartTime = null;
let playbackInterval = null;

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
        } else if (message.type === "playback_status") {
            handlePlaybackStatus(message.data);
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
    // Add source information (playback or live)
    if (!message.source) {
        if (playbackActive) {
            message.source = 'playback';
        } else {
            message.source = 'live';
        }
    }
    
    // Record message if recording is enabled and it's not from playback
    if (document.getElementById('record-messages').checked && message.source !== 'playback') {
        recordMessage(message);
    }
    
    // Update message table
    updateLiveMessagesTable(message);
}

// Handle playback status updates from server
function handlePlaybackStatus(status) {
    if (status.active) {
        // Playback started or updated
        playbackActive = true;
        playbackPaused = status.paused || false;
        
        // Update UI
        document.getElementById('no-playback').style.display = 'none';
        document.getElementById('active-playback').style.display = 'block';
        
        // Update sequence info
        document.getElementById('current-sequence-name').textContent = status.sequence_name;
        document.getElementById('current-message-index').textContent = status.current_index;
        document.getElementById('total-message-count').textContent = status.total_messages;
        
        // Update progress
        const progressPercent = (status.current_index / status.total_messages) * 100;
        document.getElementById('playback-progress').style.width = `${progressPercent}%`;
        
        // Update elapsed time
        document.getElementById('elapsed-time').textContent = formatTime(status.elapsed_time);
        
        // Update pause button text
        const pauseBtn = document.getElementById('pause-playback-btn');
        if (status.paused) {
            pauseBtn.textContent = 'Resume';
            pauseBtn.classList.remove('btn-warning');
            pauseBtn.classList.add('btn-success');
        } else {
            pauseBtn.textContent = 'Pause';
            pauseBtn.classList.remove('btn-success');
            pauseBtn.classList.add('btn-warning');
        }
        
    } else {
        // Playback stopped
        stopPlayback();
    }
}

// Record a message
function recordMessage(message) {
    // Store timestamp if not present
    if (!message.timestamp) {
        message.timestamp = Date.now() / 1000;
    }
    
    // Calculate delay from previous message
    if (recordedMessages.length > 0) {
        const prevMsg = recordedMessages[recordedMessages.length - 1];
        message.delay = message.timestamp - prevMsg.timestamp;
    } else {
        message.delay = 0;
    }
    
    // Add to recorded messages
    recordedMessages.push(message);
}

// Update the live messages table
function updateLiveMessagesTable(message) {
    const tableBody = document.getElementById('live-messages-body');
    
    // Create a new row
    const row = document.createElement('tr');
    
    // Format timestamp
    const time = new Date(message.timestamp * 1000);
    const timeString = time.toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        fractionalSecondDigits: 3
    });
    
    // Set row class based on source
    if (message.source === 'playback') {
        row.className = 'table-primary'; // Highlight playback messages
    }
    
    // Create cells
    row.innerHTML = `
        <td>${timeString}</td>
        <td class="can-id">${message.id}</td>
        <td class="can-data">${message.data}</td>
        <td>${message.source === 'playback' ? 'Playback' : 'Live'}</td>
    `;
    
    // Add to top of table
    if (tableBody.firstChild) {
        tableBody.insertBefore(row, tableBody.firstChild);
    } else {
        tableBody.appendChild(row);
    }
    
    // Limit number of rows
    if (tableBody.childNodes.length > 100) {
        tableBody.removeChild(tableBody.lastChild);
    }
}

// Load sequences from server
function loadSequences() {
    document.getElementById('loading-sequences').style.display = 'block';
    
    fetch('/api/playback/sequences')
    .then(response => response.json())
    .then(data => {
        sequences = data;
        document.getElementById('loading-sequences').style.display = 'none';
        updateSequencesList();
    })
    .catch(error => {
        document.getElementById('loading-sequences').style.display = 'none';
        showStatusMessage(`Error loading sequences: ${error.message}`, "error");
    });
}

// Update sequences list in UI
function updateSequencesList() {
    const container = document.getElementById('sequences-container');
    
    // Clear container except loading indicator
    const loadingElement = document.getElementById('loading-sequences');
    container.innerHTML = '';
    container.appendChild(loadingElement);
    loadingElement.style.display = 'none';
    
    // Filter sequences if search is active
    const searchText = document.getElementById('search-sequences').value.toLowerCase();
    const filteredSequences = searchText ? 
        sequences.filter(seq => seq.name.toLowerCase().includes(searchText)) : 
        sequences;
    
    if (filteredSequences.length === 0) {
        const noResults = document.createElement('div');
        noResults.className = 'text-center py-3';
        noResults.innerHTML = '<p class="text-muted">No sequences found</p>';
        container.appendChild(noResults);
        return;
    }
    
    // Add sequences to list
    filteredSequences.forEach(sequence => {
        const sequenceElement = document.createElement('div');
        sequenceElement.className = 'sequence-item';
        if (selectedSequence && selectedSequence.name === sequence.name) {
            sequenceElement.classList.add('active');
        }
        
        // Calculate total duration
        let totalDuration = 0;
        sequence.messages.forEach(msg => totalDuration += msg.delay || 0);
        
        sequenceElement.innerHTML = `
            <div class="d-flex justify-content-between">
                <h6>${sequence.name}</h6>
                <span class="badge bg-secondary">${sequence.message_count} messages</span>
            </div>
            <p class="text-muted mb-0">Duration: ${totalDuration.toFixed(1)}s</p>
        `;
        
        sequenceElement.addEventListener('click', function() {
            // Select this sequence
            selectSequence(sequence);
        });
        
        container.appendChild(sequenceElement);
    });
}

// Select a sequence
function selectSequence(sequence) {
    selectedSequence = sequence;
    
    // Update UI
    updateSequencesList();
    
    // Show sequence details
    document.getElementById('no-sequence-selected').style.display = 'none';
    document.getElementById('sequence-details').style.display = 'block';
    
    // Update sequence info
    document.getElementById('detail-sequence-name').textContent = sequence.name;
    document.getElementById('detail-message-count').textContent = sequence.message_count;
    
    // Calculate total duration
    let totalDuration = 0;
    sequence.messages.forEach(msg => totalDuration += msg.delay || 0);
    document.getElementById('detail-duration').textContent = totalDuration.toFixed(1);
    
    // Update title
    document.getElementById('sequence-detail-title').textContent = `Sequence Details: ${sequence.name}`;
    
    // Load messages into table
    const tableBody = document.getElementById('sequence-messages-body');
    tableBody.innerHTML = '';
    
    sequence.messages.forEach((message, index) => {
        const row = document.createElement('tr');
        
        // Check if this message has a label
        let label = '';
        if (message.label) {
            label = message.label;
        }
        
        row.innerHTML = `
            <td>${index + 1}</td>
            <td class="can-id">${message.id}</td>
            <td class="can-data">${message.data}</td>
            <td>${message.delay ? message.delay.toFixed(2) : '0.00'}</td>
            <td>${label}</td>
        `;
        
        tableBody.appendChild(row);
    });
}

// Play the selected sequence
function playSequence() {
    if (!selectedSequence) {
        showStatusMessage("Please select a sequence to play", "error");
        return;
    }
    
    // Get loop setting
    const loopPlayback = document.getElementById('loop-playback').checked;
    
    // Send to server
    fetch('/api/playback/start', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            name: selectedSequence.name,
            loop: loopPlayback
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showStatusMessage(`Started playback of "${selectedSequence.name}"`, "success");
            playbackStartTime = Date.now();
            
            // Show active playback UI
            document.getElementById('no-playback').style.display = 'none';
            document.getElementById('active-playback').style.display = 'block';
            
            // Update UI initially
            document.getElementById('current-sequence-name').textContent = selectedSequence.name;
            document.getElementById('current-message-index').textContent = "0";
            document.getElementById('total-message-count').textContent = selectedSequence.message_count;
            document.getElementById('elapsed-time').textContent = "00:00";
            document.getElementById('playback-progress').style.width = "0%";
            
            // Start playback updates
            startPlaybackUpdates();
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
    
    // Update UI
    document.getElementById('no-playback').style.display = 'block';
    document.getElementById('active-playback').style.display = 'none';
    
    // Stop playback updates
    stopPlaybackUpdates();
    
    // Reset state
    playbackActive = false;
    playbackPaused = false;
}

// Pause or resume playback
function togglePlaybackPause() {
    const action = playbackPaused ? 'resume' : 'pause';
    
    fetch(`/api/playback/${action}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            playbackPaused = !playbackPaused;
            
            // Update button
            const pauseBtn = document.getElementById('pause-playback-btn');
            if (playbackPaused) {
                pauseBtn.textContent = 'Resume';
                pauseBtn.classList.remove('btn-warning');
                pauseBtn.classList.add('btn-success');
                showStatusMessage("Playback paused", "info");
            } else {
                pauseBtn.textContent = 'Pause';
                pauseBtn.classList.remove('btn-success');
                pauseBtn.classList.add('btn-warning');
                showStatusMessage("Playback resumed", "info");
            }
        } else {
            showStatusMessage(`Error: ${data.error}`, "error");
        }
    })
    .catch(error => {
        showStatusMessage(`Error: ${error.message}`, "error");
    });
}

// Start playback status updates
function startPlaybackUpdates() {
    playbackActive = true;
    
    // Update playback progress every 100ms
    playbackInterval = setInterval(updatePlaybackProgress, 100);
}

// Stop playback status updates
function stopPlaybackUpdates() {
    if (playbackInterval) {
        clearInterval(playbackInterval);
        playbackInterval = null;
    }
}

// Update playback progress UI
function updatePlaybackProgress() {
    if (!playbackActive || !playbackStartTime) return;
    
    // Calculate elapsed time
    const elapsed = playbackPaused ? 
        document.getElementById('elapsed-time').textContent : 
        formatTime((Date.now() - playbackStartTime) / 1000);
    
    document.getElementById('elapsed-time').textContent = elapsed;
}

// Format time in MM:SS format
function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

// Clear recorded messages
function clearRecordedMessages() {
    if (recordedMessages.length === 0) return;
    
    if (confirm('Are you sure you want to clear all recorded messages?')) {
        recordedMessages = [];
        showStatusMessage("Recorded messages cleared", "info");
    }
}

// Save recorded messages as a new sequence
function saveRecordedSequence() {
    if (recordedMessages.length === 0) {
        showStatusMessage("No messages recorded to save", "error");
        return;
    }
    
    // Show create sequence modal
    const modal = document.getElementById('sequence-modal');
    document.getElementById('sequence-modal-title').textContent = "Save Recorded Sequence";
    document.getElementById('sequence-name').value = `Recorded Sequence ${new Date().toLocaleString()}`;
    
    // Clear existing messages
    const tableBody = document.getElementById('sequence-edit-body');
    tableBody.innerHTML = '';
    
    // Add recorded messages to table
    recordedMessages.forEach((message, index) => {
        addMessageRow(message.id, message.data, message.delay, index);
    });
    
    const modalInstance = new bootstrap.Modal(modal);
    modalInstance.show();
}

// Show the create sequence modal
function showCreateSequenceModal() {
    const modal = document.getElementById('sequence-modal');
    document.getElementById('sequence-modal-title').textContent = "Create New Sequence";
    document.getElementById('sequence-name').value = "";
    
    // Clear existing messages
    const tableBody = document.getElementById('sequence-edit-body');
    tableBody.innerHTML = '';
    
    // Add a few empty rows
    for (let i = 0; i < 3; i++) {
        addMessageRow('', '', 0.5);
    }
    
    const modalInstance = new bootstrap.Modal(modal);
    modalInstance.show();
}

// Add a message row to the sequence editor
function addMessageRow(id = '', data = '', delay = 0.5, index = null) {
    const tableBody = document.getElementById('sequence-edit-body');
    const row = document.createElement('tr');
    
    // If index is null, add at the end
    if (index === null) {
        index = tableBody.children.length;
    }
    
    row.innerHTML = `
        <td>${index + 1}</td>
        <td>
            <input type="text" class="form-control form-control-sm" value="${id}" 
                   placeholder="e.g., 0x1A2">
        </td>
        <td>
            <input type="text" class="form-control form-control-sm" value="${data}" 
                   placeholder="e.g., FF000000">
        </td>
        <td>
            <input type="number" class="form-control form-control-sm" value="${delay}" 
                   step="0.1" min="0">
        </td>
        <td>
            <button class="btn btn-sm btn-outline-danger">Remove</button>
        </td>
    `;
    
    // Add event listener for remove button
    row.querySelector('button').addEventListener('click', function() {
        tableBody.removeChild(row);
        updateSequenceRowNumbers();
    });
    
    tableBody.appendChild(row);
}

// Update row numbers in sequence editor
function updateSequenceRowNumbers() {
    const tableBody = document.getElementById('sequence-edit-body');
    Array.from(tableBody.children).forEach((row, index) => {
        row.children[0].textContent = index + 1;
    });
}

// Save the sequence from the editor
function saveSequence() {
    const name = document.getElementById('sequence-name').value.trim();
    
    if (!name) {
        showStatusMessage("Please enter a sequence name", "error");
        return;
    }
    
    // Get messages from table
    const tableBody = document.getElementById('sequence-edit-body');
    const messages = [];
    
    for (let i = 0; i < tableBody.children.length; i++) {
        const row = tableBody.children[i];
        const inputs = row.querySelectorAll('input');
        
        const id = inputs[0].value.trim();
        const data = inputs[1].value.trim();
        const delay = parseFloat(inputs[2].value) || 0;
        
        if (!id || !data) continue; // Skip empty rows
        
        messages.push({
            id: id,
            data: data,
            delay: delay
        });
    }
    
    if (messages.length === 0) {
        showStatusMessage("Sequence must contain at least one message", "error");
        return;
    }
    
    // Get loop preference
    const defaultLoop = document.getElementById('edit-loop-playback').checked;
    
    // Create the sequence
    const sequence = {
        name: name,
        messages: messages,
        default_loop: defaultLoop
    };
    
    // Send to server
    fetch('/api/playback/sequences', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(sequence)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showStatusMessage(`Sequence "${name}" saved successfully`, "success");
            
            // Hide modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('sequence-modal'));
            modal.hide();
            
            // Reload sequences
            loadSequences();
            
            // Clear recorded messages if this was a save from recording
            if (document.getElementById('sequence-modal-title').textContent === "Save Recorded Sequence") {
                recordedMessages = [];
            }
        } else {
            showStatusMessage(`Error: ${data.error}`, "error");
        }
    })
    .catch(error => {
        showStatusMessage(`Error: ${error.message}`, "error");
    });
}

// Delete the selected sequence
function deleteSequence() {
    if (!selectedSequence) return;
    
    if (!confirm(`Are you sure you want to delete the sequence "${selectedSequence.name}"?`)) {
        return;
    }
    
    fetch(`/api/playback/sequences/${encodeURIComponent(selectedSequence.name)}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showStatusMessage(`Sequence "${selectedSequence.name}" deleted`, "success");
            
            // Reset selection
            selectedSequence = null;
            document.getElementById('no-sequence-selected').style.display = 'block';
            document.getElementById('sequence-details').style.display = 'none';
            
            // Reload sequences
            loadSequences();
        } else {
            showStatusMessage(`Error: ${data.error}`, "error");
        }
    })
    .catch(error => {
        showStatusMessage(`Error: ${error.message}`, "error");
    });
}

// Show the edit sequence modal
function showEditSequenceModal() {
    if (!selectedSequence) return;
    
    const modal = document.getElementById('sequence-modal');
    document.getElementById('sequence-modal-title').textContent = `Edit Sequence: ${selectedSequence.name}`;
    document.getElementById('sequence-name').value = selectedSequence.name;
    
    // Clear existing messages
    const tableBody = document.getElementById('sequence-edit-body');
    tableBody.innerHTML = '';
    
    // Add sequence messages to table
    selectedSequence.messages.forEach((message, index) => {
        addMessageRow(message.id, message.data, message.delay, index);
    });
    
    // Set loop preference
    document.getElementById('edit-loop-playback').checked = selectedSequence.default_loop || false;
    
    const modalInstance = new bootstrap.Modal(modal);
    modalInstance.show();
}

// Export the selected sequence
function exportSequence() {
    if (!selectedSequence) return;
    
    // Create a JSON blob
    const blob = new Blob([JSON.stringify(selectedSequence, null, 2)], {type: 'application/json'});
    
    // Create download link
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${selectedSequence.name.replace(/\s+/g, '_')}.json`;
    
    // Trigger download
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    showStatusMessage(`Exported sequence "${selectedSequence.name}"`, "success");
}

// Show the import sequence modal
function showImportModal() {
    const modal = document.getElementById('import-modal');
    document.getElementById('import-file').value = '';
    document.getElementById('import-name').value = '';
    
    const modalInstance = new bootstrap.Modal(modal);
    modalInstance.show();
}

// Import a sequence
function importSequence() {
    const fileInput = document.getElementById('import-file');
    const nameInput = document.getElementById('import-name');
    
    if (!fileInput.files || fileInput.files.length === 0) {
        showStatusMessage("Please select a file to import", "error");
        return;
    }
    
    const file = fileInput.files[0];
    const reader = new FileReader();
    
    reader.onload = function(e) {
        try {
            // Parse the file (assuming JSON for now)
            const imported = JSON.parse(e.target.result);
            
            // Validate imported data
            if (!imported.messages || !Array.isArray(imported.messages)) {
                showStatusMessage("Invalid sequence format", "error");
                return;
            }
            
            // Use provided name or file name
            const name = nameInput.value.trim() || file.name.replace(/\.[^/.]+$/, "");
            
            // Create the sequence
            const sequence = {
                name: name,
                messages: imported.messages
            };
            
            // Send to server
            fetch('/api/playback/sequences', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(sequence)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showStatusMessage(`Sequence "${name}" imported successfully`, "success");
                    
                    // Hide modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('import-modal'));
                    modal.hide();
                    
                    // Reload sequences
                    loadSequences();
                } else {
                    showStatusMessage(`Error: ${data.error}`, "error");
                }
            })
            .catch(error => {
                showStatusMessage(`Error: ${error.message}`, "error");
            });
            
        } catch (error) {
            showStatusMessage(`Error parsing file: ${error.message}`, "error");
        }
    };
    
    reader.readAsText(file);
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
    
    // Load sequences
    loadSequences();
    
    // Setup event listeners
    document.getElementById('search-sequences').addEventListener('input', updateSequencesList);
    document.getElementById('play-sequence-btn').addEventListener('click', playSequence);
    document.getElementById('stop-playback-btn').addEventListener('click', stopPlayback);
    document.getElementById('pause-playback-btn').addEventListener('click', togglePlaybackPause);
    document.getElementById('clear-recorded-btn').addEventListener('click', clearRecordedMessages);
    document.getElementById('save-recording-btn').addEventListener('click', saveRecordedSequence);
    document.getElementById('create-sequence-btn').addEventListener('click', showCreateSequenceModal);
    document.getElementById('edit-sequence-btn').addEventListener('click', showEditSequenceModal);
    document.getElementById('delete-sequence-btn').addEventListener('click', deleteSequence);
    document.getElementById('export-sequence-btn').addEventListener('click', exportSequence);
    document.getElementById('import-sequence-btn').addEventListener('click', showImportModal);
    document.getElementById('confirm-import-btn').addEventListener('click', importSequence);
    document.getElementById('add-message-btn').addEventListener('click', () => addMessageRow());
    document.getElementById('save-sequence-btn').addEventListener('click', saveSequence);
    
    // Show starting message
    showStatusMessage("Playback page loaded", "info");
});