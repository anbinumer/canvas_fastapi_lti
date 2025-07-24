/**
 * QA Progress Tracking Components
 * Story 2.3: QA Results Dashboard & User Interface
 * Real-time progress monitoring with WebSocket integration
 */

/**
 * QA Progress Tracker Component
 */
function QAProgressTracker() {
  this.container = document.getElementById('qa-progress-container');
  this.isActive = false;
  this.currentStage = '';
  this.currentProgress = 0;
  this.stats = {
    processed: 0,
    total: 0,
    errors: 0,
    found: 0
  };
  this.messages = [];
  this.startTime = null;
}

QAProgressTracker.prototype.start = function() {
  if (!this.container) {
    console.warn('[QA Progress] Progress container not found');
    return;
  }
  
  this.isActive = true;
  this.startTime = Date.now();
  this.currentStage = 'Initializing...';
  this.currentProgress = 0;
  this.stats = { processed: 0, total: 0, errors: 0, found: 0 };
  this.messages = [];
  
  this.render();
  this.show();
  
  console.log('[QA Progress] Progress tracker started');
};

QAProgressTracker.prototype.update = function(progressData) {
  if (!this.isActive) return;
  
  const { stage, current, total, message, status, stats } = progressData;
  
  // Update progress data
  if (stage) this.currentStage = stage;
  if (typeof current === 'number' && typeof total === 'number') {
    this.currentProgress = total > 0 ? (current / total) * 100 : 0;
    this.stats.processed = current;
    this.stats.total = total;
  }
  
  if (stats) {
    this.stats = { ...this.stats, ...stats };
  }
  
  // Add message to history
  if (message) {
    this.messages.push({
      timestamp: new Date().toLocaleTimeString(),
      message: message,
      type: status || 'info'
    });
    
    // Keep only last 10 messages
    if (this.messages.length > 10) {
      this.messages = this.messages.slice(-10);
    }
  }
  
  this.render();
  
  console.log('[QA Progress] Progress updated:', progressData);
};

QAProgressTracker.prototype.complete = function(results) {
  if (!this.isActive) return;
  
  this.currentStage = 'Completed Successfully';
  this.currentProgress = 100;
  
  // Add completion message
  this.messages.push({
    timestamp: new Date().toLocaleTimeString(),
    message: 'QA task completed successfully',
    type: 'success'
  });
  
  this.render();
  
  // Auto-hide after 3 seconds
  setTimeout(() => {
    this.hide();
  }, 3000);
  
  console.log('[QA Progress] Progress tracker completed');
};

QAProgressTracker.prototype.error = function(errorMessage) {
  if (!this.isActive) return;
  
  this.currentStage = 'Error Occurred';
  
  this.messages.push({
    timestamp: new Date().toLocaleTimeString(),
    message: errorMessage || 'An error occurred during QA task execution',
    type: 'error'
  });
  
  this.render();
  
  console.log('[QA Progress] Progress tracker error:', errorMessage);
};

QAProgressTracker.prototype.render = function() {
  if (!this.container || !this.isActive) return;
  
  const elapsedTime = this.startTime ? Date.now() - this.startTime : 0;
  const estimatedTotal = this.currentProgress > 0 ? 
    (elapsedTime / this.currentProgress) * 100 : 0;
  const remainingTime = Math.max(0, estimatedTotal - elapsedTime);
  
  let html = `
    <div class="qa-progress-header">
      <h3 class="acu-heading-3 acu-mb-0">QA Task Progress</h3>
      <button class="qa-cancel-task" onclick="ACUQAApp.qa.cancelTask()" title="Cancel Task">
        Cancel
      </button>
    </div>
    
    <div class="qa-progress-content">
      <div class="qa-progress-stage">${ACUQAApp.utils.escapeHtml(this.currentStage)}</div>
      
      <div class="qa-progress-bar-container">
        <div class="qa-progress-bar" style="width: ${this.currentProgress}%"></div>
      </div>
      
      <div class="qa-progress-details">
        <div class="qa-progress-stat">
          <div class="qa-progress-stat-value">${Math.round(this.currentProgress)}%</div>
          <div class="qa-progress-stat-label">Complete</div>
        </div>
        
        <div class="qa-progress-stat">
          <div class="qa-progress-stat-value">${this.stats.processed}/${this.stats.total}</div>
          <div class="qa-progress-stat-label">Items Processed</div>
        </div>
        
        <div class="qa-progress-stat">
          <div class="qa-progress-stat-value">${this.stats.found || 0}</div>
          <div class="qa-progress-stat-label">URLs Found</div>
        </div>
        
        <div class="qa-progress-stat">
          <div class="qa-progress-stat-value">${this.formatTime(remainingTime)}</div>
          <div class="qa-progress-stat-label">Est. Remaining</div>
        </div>
      </div>
      
      <div class="qa-progress-messages">
        ${this.renderMessages()}
      </div>
    </div>
  `;
  
  this.container.innerHTML = html;
};

QAProgressTracker.prototype.renderMessages = function() {
  if (this.messages.length === 0) {
    return '<div class="acu-text-center acu-text-muted">No messages yet...</div>';
  }
  
  return this.messages.map(msg => `
    <div class="qa-progress-message qa-progress-message-${msg.type}">
      <span class="acu-text-muted">${msg.timestamp}</span> - ${ACUQAApp.utils.escapeHtml(msg.message)}
    </div>
  `).join('');
};

QAProgressTracker.prototype.formatTime = function(milliseconds) {
  if (milliseconds <= 0) return '0s';
  
  const seconds = Math.floor(milliseconds / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  
  if (hours > 0) {
    return `${hours}h ${minutes % 60}m`;
  } else if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`;
  } else {
    return `${seconds}s`;
  }
};

QAProgressTracker.prototype.show = function() {
  if (this.container) {
    this.container.classList.add('active');
    this.container.style.display = 'block';
  }
};

QAProgressTracker.prototype.hide = function() {
  if (this.container) {
    this.container.classList.remove('active');
    this.container.style.display = 'none';
  }
  
  this.isActive = false;
  this.startTime = null;
  
  console.log('[QA Progress] Progress tracker hidden');
};

/**
 * QA WebSocket Manager Component
 */
function QAWebSocketManager() {
  this.websocket = null;
  this.connected = false;
  this.reconnectAttempts = 0;
  this.maxReconnectAttempts = 5;
  this.reconnectDelay = 1000; // Start with 1 second
  this.subscribedTaskId = null;
  this.userId = null;
}

QAWebSocketManager.prototype.connect = function() {
  if (this.websocket && this.connected) {
    console.log('[QA WebSocket] Already connected');
    return;
  }
  
  // Get user ID from session context
  if (ACUQAApp.state.userContext && ACUQAApp.state.userContext.id) {
    this.userId = ACUQAApp.state.userContext.id;
  } else {
    console.warn('[QA WebSocket] No user ID available');
    return;
  }
  
  const wsUrl = this.buildWebSocketUrl();
  console.log('[QA WebSocket] Connecting to:', wsUrl);
  
  try {
    this.websocket = new WebSocket(wsUrl);
    this.setupEventHandlers();
  } catch (error) {
    console.error('[QA WebSocket] Connection failed:', error);
    this.handleConnectionError();
  }
};

QAWebSocketManager.prototype.buildWebSocketUrl = function() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  const endpoint = ACUQAApp.qa.endpoints.websocket.replace('{userId}', this.userId);
  
  return `${protocol}//${host}${endpoint}`;
};

QAWebSocketManager.prototype.setupEventHandlers = function() {
  if (!this.websocket) return;
  
  this.websocket.onopen = (event) => {
    console.log('[QA WebSocket] Connected successfully');
    this.connected = true;
    this.reconnectAttempts = 0;
    this.reconnectDelay = 1000;
    
    // Subscribe to task updates if we have a task ID
    if (this.subscribedTaskId) {
      this.subscribe(this.subscribedTaskId);
    }
  };
  
  this.websocket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    } catch (error) {
      console.error('[QA WebSocket] Failed to parse message:', error);
    }
  };
  
  this.websocket.onclose = (event) => {
    console.log('[QA WebSocket] Connection closed:', event.code, event.reason);
    this.connected = false;
    this.websocket = null;
    
    // Attempt to reconnect if it wasn't a normal closure
    if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
      this.attemptReconnect();
    }
  };
  
  this.websocket.onerror = (error) => {
    console.error('[QA WebSocket] WebSocket error:', error);
    this.handleConnectionError();
  };
};

QAWebSocketManager.prototype.handleMessage = function(data) {
  console.log('[QA WebSocket] Message received:', data);
  
  const { type, task_id, ...payload } = data;
  
  switch (type) {
    case 'progress_update':
      this.handleProgressUpdate(payload);
      break;
    case 'task_completed':
      this.handleTaskCompleted(payload);
      break;
    case 'task_failed':
      this.handleTaskFailed(payload);
      break;
    case 'task_cancelled':
      this.handleTaskCancelled(payload);
      break;
    case 'connection_confirmed':
      console.log('[QA WebSocket] Connection confirmed');
      break;
    default:
      console.log('[QA WebSocket] Unknown message type:', type);
  }
};

QAWebSocketManager.prototype.handleProgressUpdate = function(progressData) {
  if (ACUQAApp.qa.components.progressTracker) {
    ACUQAApp.qa.components.progressTracker.update(progressData);
  }
};

QAWebSocketManager.prototype.handleTaskCompleted = function(data) {
  console.log('[QA WebSocket] Task completed:', data);
  
  if (ACUQAApp.qa.components.progressTracker) {
    ACUQAApp.qa.components.progressTracker.complete(data.results);
  }
  
  // Handle task completion in main QA app
  ACUQAApp.qa.handleTaskCompletion('completed', data.results);
};

QAWebSocketManager.prototype.handleTaskFailed = function(data) {
  console.log('[QA WebSocket] Task failed:', data);
  
  if (ACUQAApp.qa.components.progressTracker) {
    ACUQAApp.qa.components.progressTracker.error(data.error || 'Task execution failed');
  }
  
  // Handle task failure in main QA app
  ACUQAApp.qa.handleTaskCompletion('failed');
};

QAWebSocketManager.prototype.handleTaskCancelled = function(data) {
  console.log('[QA WebSocket] Task cancelled:', data);
  
  if (ACUQAApp.qa.components.progressTracker) {
    ACUQAApp.qa.components.progressTracker.hide();
  }
  
  // Handle task cancellation in main QA app
  ACUQAApp.qa.handleTaskCompletion('cancelled');
};

QAWebSocketManager.prototype.subscribe = function(taskId) {
  this.subscribedTaskId = taskId;
  
  if (this.connected && this.websocket) {
    const message = {
      action: 'subscribe',
      task_id: taskId
    };
    
    this.websocket.send(JSON.stringify(message));
    console.log('[QA WebSocket] Subscribed to task:', taskId);
  } else {
    console.log('[QA WebSocket] Will subscribe when connected:', taskId);
  }
};

QAWebSocketManager.prototype.unsubscribe = function() {
  if (this.connected && this.websocket && this.subscribedTaskId) {
    const message = {
      action: 'unsubscribe',
      task_id: this.subscribedTaskId
    };
    
    this.websocket.send(JSON.stringify(message));
    console.log('[QA WebSocket] Unsubscribed from task:', this.subscribedTaskId);
  }
  
  this.subscribedTaskId = null;
};

QAWebSocketManager.prototype.disconnect = function() {
  this.unsubscribe();
  
  if (this.websocket) {
    this.websocket.close(1000, 'Normal closure');
    this.websocket = null;
  }
  
  this.connected = false;
  this.reconnectAttempts = 0;
  
  console.log('[QA WebSocket] Disconnected');
};

QAWebSocketManager.prototype.attemptReconnect = function() {
  this.reconnectAttempts++;
  console.log(`[QA WebSocket] Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
  
  setTimeout(() => {
    this.connect();
  }, this.reconnectDelay);
  
  // Exponential backoff for reconnection delay
  this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000); // Max 30 seconds
};

QAWebSocketManager.prototype.handleConnectionError = function() {
  this.connected = false;
  
  if (this.reconnectAttempts < this.maxReconnectAttempts) {
    ACUQAApp.components.notifications.show('warning', 'Connection lost. Attempting to reconnect...');
    this.attemptReconnect();
  } else {
    ACUQAApp.components.notifications.show('error', 'Connection lost. Please refresh the page to continue.');
  }
}; 