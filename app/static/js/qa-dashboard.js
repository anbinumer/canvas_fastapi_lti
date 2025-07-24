/**
 * QA Dashboard Component for ACU QA Automation Tool
 * Story 2.3: QA Results Dashboard & User Interface
 * Integrates with existing ACUQAApp framework
 */

// Extend ACUQAApp with QA Dashboard functionality
ACUQAApp.qa = {
  // QA-specific state
  state: {
    selectedTask: null,
    availableTasks: [],
    currentExecution: null,
    urlMappings: [],
    configOptions: {
      caseSensitive: false,
      wholeWord: false,
      previewMode: false
    },
    results: null,
    websocket: null
  },
  
  // QA components
  components: {},
  
  // API endpoints
  endpoints: {
    availableTasks: '/qa/tasks/available',
    startTask: '/qa/tasks/find-replace/start',
    taskStatus: '/qa/tasks/{taskId}/status',
    taskResults: '/qa/tasks/{taskId}/results',
    cancelTask: '/qa/tasks/{taskId}/cancel',
    validateCanvas: '/qa/canvas/validate',
    contentSummary: '/qa/course/content-summary',
    websocket: '/ws/qa/progress/{userId}'
  }
};

/**
 * Initialize QA Dashboard
 */
ACUQAApp.qa.init = function() {
  console.log('[QA Dashboard] Initializing QA Dashboard...');
  
  // Initialize QA components
  this.components.taskSelector = new QATaskSelector();
  this.components.configurationPanel = new QAConfigurationPanel();
  this.components.progressTracker = new QAProgressTracker();
  this.components.resultsDisplay = new QAResultsDisplay();
  this.components.exportManager = new QAExportManager();
  this.components.websocketManager = new QAWebSocketManager();
  
  // Load available tasks
  this.loadAvailableTasks();
  
  // Validate Canvas access
  this.validateCanvasAccess();
  
  console.log('[QA Dashboard] QA Dashboard initialized successfully');
};

/**
 * Load available QA tasks
 */
ACUQAApp.qa.loadAvailableTasks = function() {
  console.log('[QA Dashboard] Loading available QA tasks...');
  
  return ACUQAApp.utils.apiRequest(this.endpoints.availableTasks)
    .then(data => {
      console.log('[QA Dashboard] Available tasks loaded:', data);
      this.state.availableTasks = data.tasks || [];
      this.components.taskSelector.render(this.state.availableTasks);
      return data;
    })
    .catch(error => {
      console.error('[QA Dashboard] Failed to load available tasks:', error);
      ACUQAApp.components.notifications.show('error', 'Failed to load available QA tasks');
      this.components.taskSelector.renderError('Failed to load available tasks');
    });
};

/**
 * Validate Canvas API access
 */
ACUQAApp.qa.validateCanvasAccess = function() {
  console.log('[QA Dashboard] Validating Canvas API access...');
  
  return ACUQAApp.utils.apiRequest(this.endpoints.validateCanvas)
    .then(data => {
      console.log('[QA Dashboard] Canvas validation result:', data);
      if (!data.valid) {
        ACUQAApp.components.notifications.show('warning', 'Canvas API access validation failed - some features may not work');
      }
      return data;
    })
    .catch(error => {
      console.error('[QA Dashboard] Canvas validation failed:', error);
      ACUQAApp.components.notifications.show('error', 'Cannot validate Canvas API access');
    });
};

/**
 * Select a QA task
 */
ACUQAApp.qa.selectTask = function(taskId) {
  const task = this.state.availableTasks.find(t => t.id === taskId);
  if (!task) {
    console.warn('[QA Dashboard] Task not found:', taskId);
    return;
  }
  
  console.log('[QA Dashboard] Task selected:', task);
  this.state.selectedTask = task;
  
  // Update UI
  this.components.taskSelector.selectTask(taskId);
  this.components.configurationPanel.loadTask(task);
  
  // Clear previous results
  this.state.results = null;
  this.components.resultsDisplay.clear();
};

/**
 * Add URL mapping
 */
ACUQAApp.qa.addUrlMapping = function() {
  const mapping = {
    id: ACUQAApp.utils.generateId('mapping'),
    findUrl: '',
    replaceUrl: '',
    description: ''
  };
  
  this.state.urlMappings.push(mapping);
  this.components.configurationPanel.renderUrlMappings();
  
  console.log('[QA Dashboard] URL mapping added:', mapping);
};

/**
 * Remove URL mapping
 */
ACUQAApp.qa.removeUrlMapping = function(mappingId) {
  const index = this.state.urlMappings.findIndex(m => m.id === mappingId);
  if (index !== -1) {
    this.state.urlMappings.splice(index, 1);
    this.components.configurationPanel.renderUrlMappings();
    console.log('[QA Dashboard] URL mapping removed:', mappingId);
  }
};

/**
 * Update URL mapping
 */
ACUQAApp.qa.updateUrlMapping = function(mappingId, field, value) {
  const mapping = this.state.urlMappings.find(m => m.id === mappingId);
  if (mapping) {
    mapping[field] = value;
    console.log('[QA Dashboard] URL mapping updated:', mappingId, field, value);
  }
};

/**
 * Update configuration options
 */
ACUQAApp.qa.updateConfigOption = function(option, value) {
  this.state.configOptions[option] = value;
  console.log('[QA Dashboard] Config option updated:', option, value);
};

/**
 * Start QA task execution
 */
ACUQAApp.qa.startTask = function() {
  if (!this.state.selectedTask) {
    ACUQAApp.components.notifications.show('warning', 'Please select a QA task first');
    return;
  }
  
  if (this.state.urlMappings.length === 0) {
    ACUQAApp.components.notifications.show('warning', 'Please add at least one URL mapping');
    return;
  }
  
  // Validate URL mappings
  const validation = this.validateUrlMappings();
  if (!validation.valid) {
    ACUQAApp.components.notifications.show('error', validation.message);
    return;
  }
  
  console.log('[QA Dashboard] Starting QA task execution...');
  
  const taskConfig = {
    task_type: this.state.selectedTask.id,
    url_mappings: this.state.urlMappings.map(m => ({
      find_url: m.findUrl,
      replace_url: m.replaceUrl,
      description: m.description
    })),
    options: this.state.configOptions
  };
  
  // Show progress tracker
  this.components.progressTracker.start();
  
  // Start WebSocket connection for progress updates
  this.components.websocketManager.connect();
  
  return ACUQAApp.utils.apiRequest(this.endpoints.startTask, {
    method: 'POST',
    body: JSON.stringify(taskConfig),
    headers: {
      'Content-Type': 'application/json'
    }
  })
  .then(data => {
    console.log('[QA Dashboard] Task started successfully:', data);
    this.state.currentExecution = data;
    
    // Subscribe to progress updates
    this.components.websocketManager.subscribe(data.task_id);
    
    ACUQAApp.components.notifications.show('success', 'QA task started successfully');
    return data;
  })
  .catch(error => {
    console.error('[QA Dashboard] Failed to start task:', error);
    ACUQAApp.components.notifications.show('error', 'Failed to start QA task');
    this.components.progressTracker.hide();
    this.components.websocketManager.disconnect();
    throw error;
  });
};

/**
 * Cancel QA task execution
 */
ACUQAApp.qa.cancelTask = function() {
  if (!this.state.currentExecution) {
    console.warn('[QA Dashboard] No active task to cancel');
    return;
  }
  
  const taskId = this.state.currentExecution.task_id;
  const endpoint = this.endpoints.cancelTask.replace('{taskId}', taskId);
  
  console.log('[QA Dashboard] Cancelling task:', taskId);
  
  return ACUQAApp.utils.apiRequest(endpoint, {
    method: 'POST'
  })
  .then(data => {
    console.log('[QA Dashboard] Task cancelled successfully:', data);
    this.handleTaskCompletion('cancelled');
    ACUQAApp.components.notifications.show('info', 'QA task cancelled');
    return data;
  })
  .catch(error => {
    console.error('[QA Dashboard] Failed to cancel task:', error);
    ACUQAApp.components.notifications.show('error', 'Failed to cancel QA task');
  });
};

/**
 * Handle task completion
 */
ACUQAApp.qa.handleTaskCompletion = function(status, results = null) {
  console.log('[QA Dashboard] Task completed with status:', status);
  
  // Hide progress tracker
  this.components.progressTracker.hide();
  
  // Disconnect WebSocket
  this.components.websocketManager.disconnect();
  
  // Clear current execution
  this.state.currentExecution = null;
  
  if (status === 'completed' && results) {
    // Store and display results
    this.state.results = results;
    this.components.resultsDisplay.render(results);
    ACUQAApp.components.notifications.show('success', 'QA task completed successfully');
  } else if (status === 'failed') {
    ACUQAApp.components.notifications.show('error', 'QA task failed');
    this.components.resultsDisplay.renderError('Task execution failed');
  } else if (status === 'cancelled') {
    this.components.resultsDisplay.clear();
  }
};

/**
 * Validate URL mappings
 */
ACUQAApp.qa.validateUrlMappings = function() {
  for (const mapping of this.state.urlMappings) {
    if (!mapping.findUrl.trim()) {
      return { valid: false, message: 'All find URLs must be specified' };
    }
    if (!mapping.replaceUrl.trim()) {
      return { valid: false, message: 'All replace URLs must be specified' };
    }
    
    // Basic URL validation
    try {
      new URL(mapping.findUrl);
      new URL(mapping.replaceUrl);
    } catch (e) {
      return { valid: false, message: 'Invalid URL format detected' };
    }
  }
  
  return { valid: true };
};

/**
 * QA Task Selector Component
 */
function QATaskSelector() {
  this.container = document.getElementById('qa-task-selector');
  this.selectedTaskId = null;
}

QATaskSelector.prototype.render = function(tasks) {
  if (!this.container) {
    console.warn('[QA TaskSelector] Container not found');
    return;
  }
  
  if (!tasks || tasks.length === 0) {
    this.renderEmpty();
    return;
  }
  
  let html = '<div class="qa-task-selector-header">';
  html += '<h3 class="acu-heading-3 acu-mb-0">Available QA Tasks</h3>';
  html += '</div>';
  html += '<div class="qa-available-tasks">';
  
  tasks.forEach(task => {
    const isSelected = this.selectedTaskId === task.id;
    html += `
      <div class="qa-task-card ${isSelected ? 'selected' : ''}" 
           data-task-id="${task.id}" 
           onclick="ACUQAApp.qa.selectTask('${task.id}')"
           tabindex="0"
           role="button"
           aria-pressed="${isSelected}">
        <div class="qa-task-title">${ACUQAApp.utils.escapeHtml(task.name)}</div>
        <div class="qa-task-description">${ACUQAApp.utils.escapeHtml(task.description)}</div>
        <div class="qa-task-capabilities">
          ${task.capabilities ? task.capabilities.map(cap => 
            `<span class="qa-capability-badge">${ACUQAApp.utils.escapeHtml(cap)}</span>`
          ).join('') : ''}
        </div>
        <div class="qa-task-requirements">${ACUQAApp.utils.escapeHtml(task.requirements || '')}</div>
      </div>
    `;
  });
  
  html += '</div>';
  this.container.innerHTML = html;
};

QATaskSelector.prototype.renderEmpty = function() {
  this.container.innerHTML = `
    <div class="qa-task-selector-header">
      <h3 class="acu-heading-3 acu-mb-0">Available QA Tasks</h3>
    </div>
    <div class="qa-available-tasks">
      <div class="acu-text-center acu-p-xl">
        <p class="acu-text-muted">No QA tasks available at this time.</p>
      </div>
    </div>
  `;
};

QATaskSelector.prototype.renderError = function(message) {
  this.container.innerHTML = `
    <div class="qa-task-selector-header">
      <h3 class="acu-heading-3 acu-mb-0">Available QA Tasks</h3>
    </div>
    <div class="qa-available-tasks">
      <div class="qa-error-container">
        <div class="qa-error-icon">⚠️</div>
        <div class="qa-error-title">Error Loading Tasks</div>
        <div class="qa-error-message">${ACUQAApp.utils.escapeHtml(message)}</div>
        <div class="qa-error-actions">
          <button class="acu-btn acu-btn-primary" onclick="ACUQAApp.qa.loadAvailableTasks()">
            Retry
          </button>
        </div>
      </div>
    </div>
  `;
};

QATaskSelector.prototype.selectTask = function(taskId) {
  // Update visual selection
  this.container.querySelectorAll('.qa-task-card').forEach(card => {
    card.classList.remove('selected');
    card.setAttribute('aria-pressed', 'false');
  });
  
  const selectedCard = this.container.querySelector(`[data-task-id="${taskId}"]`);
  if (selectedCard) {
    selectedCard.classList.add('selected');
    selectedCard.setAttribute('aria-pressed', 'true');
  }
  
  this.selectedTaskId = taskId;
};

/**
 * QA Configuration Panel Component
 */
function QAConfigurationPanel() {
  this.container = document.getElementById('qa-configuration-panel');
  this.currentTask = null;
}

QAConfigurationPanel.prototype.loadTask = function(task) {
  this.currentTask = task;
  this.render();
};

QAConfigurationPanel.prototype.render = function() {
  if (!this.container || !this.currentTask) return;
  
  let html = `
    <div class="qa-configuration-header">
      <h3 class="acu-heading-3 acu-mb-0">Configure ${ACUQAApp.utils.escapeHtml(this.currentTask.name)}</h3>
      <button class="acu-btn acu-btn-secondary acu-btn-sm" onclick="ACUQAApp.qa.startTask()">
        Start QA Task
      </button>
    </div>
    <div class="qa-configuration-content">
      <div class="qa-url-mapping-form">
        <div id="qa-url-mappings-container">
          <!-- URL mappings will be rendered here -->
        </div>
        <button class="qa-add-mapping" onclick="ACUQAApp.qa.addUrlMapping()">
          <span>➕</span> Add URL Mapping
        </button>
        
        <div class="qa-configuration-options">
          <div class="qa-options-title">Configuration Options</div>
          <div class="qa-option-group">
            <label class="qa-checkbox-option">
              <input type="checkbox" class="qa-checkbox" id="case-sensitive" 
                     onchange="ACUQAApp.qa.updateConfigOption('caseSensitive', this.checked)">
              <span class="qa-option-label">Case Sensitive</span>
            </label>
            
            <label class="qa-checkbox-option">
              <input type="checkbox" class="qa-checkbox" id="whole-word" 
                     onchange="ACUQAApp.qa.updateConfigOption('wholeWord', this.checked)">
              <span class="qa-option-label">Whole Word Only</span>
            </label>
            
            <label class="qa-checkbox-option">
              <input type="checkbox" class="qa-checkbox" id="preview-mode" 
                     onchange="ACUQAApp.qa.updateConfigOption('previewMode', this.checked)">
              <span class="qa-option-label">Preview Mode (No Changes)</span>
            </label>
          </div>
        </div>
      </div>
    </div>
  `;
  
  this.container.innerHTML = html;
  this.renderUrlMappings();
};

QAConfigurationPanel.prototype.renderUrlMappings = function() {
  const container = document.getElementById('qa-url-mappings-container');
  if (!container) return;
  
  if (ACUQAApp.qa.state.urlMappings.length === 0) {
    container.innerHTML = `
      <div class="acu-text-center acu-p-lg acu-text-muted">
        <p>No URL mappings configured. Click "Add URL Mapping" to get started.</p>
      </div>
    `;
    return;
  }
  
  let html = '';
  ACUQAApp.qa.state.urlMappings.forEach((mapping, index) => {
    html += `
      <div class="qa-url-mapping-pair" data-mapping-id="${mapping.id}">
        <div class="qa-url-mapping-header">
          <div class="qa-mapping-title">URL Mapping ${index + 1}</div>
          <button class="qa-remove-mapping" 
                  onclick="ACUQAApp.qa.removeUrlMapping('${mapping.id}')"
                  title="Remove this mapping">
            ✕
          </button>
        </div>
        
        <div class="qa-url-inputs">
          <div class="qa-input-group">
            <label class="qa-input-label" for="find-${mapping.id}">Find URL</label>
            <input type="url" class="qa-input-field" id="find-${mapping.id}" 
                   value="${ACUQAApp.utils.escapeHtml(mapping.findUrl)}"
                   placeholder="https://example.com/old-url"
                   onchange="ACUQAApp.qa.updateUrlMapping('${mapping.id}', 'findUrl', this.value)">
          </div>
          
          <div class="qa-input-group">
            <label class="qa-input-label" for="replace-${mapping.id}">Replace URL</label>
            <input type="url" class="qa-input-field" id="replace-${mapping.id}" 
                   value="${ACUQAApp.utils.escapeHtml(mapping.replaceUrl)}"
                   placeholder="https://example.com/new-url"
                   onchange="ACUQAApp.qa.updateUrlMapping('${mapping.id}', 'replaceUrl', this.value)">
          </div>
        </div>
        
        <div class="qa-input-group">
          <label class="qa-input-label" for="description-${mapping.id}">Description (optional)</label>
          <input type="text" class="qa-input-field" id="description-${mapping.id}" 
                 value="${ACUQAApp.utils.escapeHtml(mapping.description)}"
                 placeholder="Brief description of this URL change"
                 onchange="ACUQAApp.qa.updateUrlMapping('${mapping.id}', 'description', this.value)">
        </div>
      </div>
    `;
  });
  
  container.innerHTML = html;
};

// Initialize QA Dashboard when the main app is ready
ACUQAApp.events.onInitialized = function() {
  if (document.getElementById('qa-dashboard')) {
    ACUQAApp.qa.init();
  }
}; 