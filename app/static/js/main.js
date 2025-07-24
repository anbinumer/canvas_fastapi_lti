/**
 * ACU QA Automation Tool - Main JavaScript Application
 * Canvas LTI Integration with ACU Branding
 */

// Application namespace
window.ACUQAApp = {
  config: {
    debug: true,
    baseUrl: '',
    endpoints: {
      session: '/lti/session',
      health: '/health',
      ltiInfo: '/lti-info'
    }
  },
  
  // Application state
  state: {
    initialized: false,
    sessionValid: false,
    userContext: null,
    canvasContext: null,
    isLoading: false
  },
  
  // Component registry
  components: {},
  
  // Event handlers
  events: {},
  
  // Utility functions
  utils: {}
};

/**
 * Initialize the application
 */
ACUQAApp.init = function() {
  if (this.state.initialized) {
    console.warn('[ACU QA] Application already initialized');
    return;
  }
  
  console.log('[ACU QA] Initializing ACU QA Automation Tool...');
  
  // Initialize components
  this.initializeComponents();
  
  // Set up event handlers
  this.setupEventHandlers();
  
  // Validate session if in LTI context
  this.validateSession();
  
  // Mark as initialized
  this.state.initialized = true;
  
  console.log('[ACU QA] Application initialized successfully');
};

/**
 * Initialize all components
 */
ACUQAApp.initializeComponents = function() {
  // Initialize loading states
  this.components.loading = new LoadingManager();
  
  // Initialize user context display
  this.components.userContext = new UserContextDisplay();
  
  // Initialize session manager
  this.components.sessionManager = new SessionManager();
  
  // Initialize notifications
  this.components.notifications = new NotificationManager();
  
  // Initialize modal system
  this.components.modal = new ModalManager();
};

/**
 * Set up global event handlers
 */
ACUQAApp.setupEventHandlers = function() {
  // Handle clicks on ACU buttons
  document.addEventListener('click', (e) => {
    if (e.target.matches('.acu-btn[data-action]')) {
      this.handleButtonAction(e.target, e);
    }
  });
  
  // Handle form submissions
  document.addEventListener('submit', (e) => {
    if (e.target.matches('.acu-form')) {
      this.handleFormSubmission(e.target, e);
    }
  });
  
  // Handle responsive adjustments
  window.addEventListener('resize', this.utils.debounce(() => {
    this.handleResize();
  }, 250));
  
  // Handle Canvas iframe message passing
  window.addEventListener('message', (e) => {
    this.handleCanvasMessage(e);
  });
};

/**
 * Handle button actions
 */
ACUQAApp.handleButtonAction = function(button, event) {
  event.preventDefault();
  
  const action = button.dataset.action;
  const target = button.dataset.target;
  
  console.log(`[ACU QA] Button action: ${action}`, { target, button });
  
  switch (action) {
    case 'refresh-session':
      this.validateSession();
      break;
    case 'show-modal':
      this.components.modal.show(target);
      break;
    case 'hide-modal':
      this.components.modal.hide();
      break;
    case 'toggle-details':
      this.toggleDetails(target);
      break;
    default:
      console.warn(`[ACU QA] Unknown button action: ${action}`);
  }
};

/**
 * Handle form submissions
 */
ACUQAApp.handleFormSubmission = function(form, event) {
  event.preventDefault();
  
  const action = form.dataset.action || form.action;
  const method = form.dataset.method || form.method || 'POST';
  
  console.log(`[ACU QA] Form submission: ${action}`, { method, form });
  
  // Show loading state
  this.components.loading.show(form);
  
  // Collect form data
  const formData = new FormData(form);
  const data = Object.fromEntries(formData);
  
  // Submit form
  this.utils.apiRequest(action, {
    method: method,
    body: JSON.stringify(data),
    headers: {
      'Content-Type': 'application/json'
    }
  })
  .then(response => {
    this.components.notifications.show('success', 'Form submitted successfully');
    this.components.loading.hide(form);
  })
  .catch(error => {
    console.error('[ACU QA] Form submission error:', error);
    this.components.notifications.show('error', 'Form submission failed');
    this.components.loading.hide(form);
  });
};

/**
 * Validate LTI session
 */
ACUQAApp.validateSession = function() {
  console.log('[ACU QA] Validating LTI session...');
  
  this.state.isLoading = true;
  this.components.loading.showGlobal('Validating session...');
  
  return this.utils.apiRequest(this.config.endpoints.session)
    .then(data => {
      console.log('[ACU QA] Session validation successful:', data);
      
      this.state.sessionValid = data.valid;
      this.state.userContext = data.user;
      this.state.canvasContext = data.canvas;
      
      // Update user context display
      this.components.userContext.update(data);
      
      // Hide loading
      this.components.loading.hideGlobal();
      this.state.isLoading = false;
      
      return data;
    })
    .catch(error => {
      console.error('[ACU QA] Session validation failed:', error);
      
      this.state.sessionValid = false;
      this.components.notifications.show('warning', 'Session validation failed - some features may not work');
      
      // Hide loading
      this.components.loading.hideGlobal();
      this.state.isLoading = false;
      
      throw error;
    });
};

/**
 * Handle window resize
 */
ACUQAApp.handleResize = function() {
  // Adjust for Canvas iframe constraints
  const container = document.querySelector('.canvas-lti-container');
  if (container) {
    const height = window.innerHeight;
    const maxHeight = Math.min(height * 0.85, 800); // 85% of viewport or 800px max
    container.style.maxHeight = `${maxHeight}px`;
  }
  
  // Trigger component resize events
  Object.values(this.components).forEach(component => {
    if (component.handleResize) {
      component.handleResize();
    }
  });
};

/**
 * Handle Canvas iframe messages
 */
ACUQAApp.handleCanvasMessage = function(event) {
  // Validate origin for security
  if (!this.utils.isValidCanvasOrigin(event.origin)) {
    console.warn('[ACU QA] Invalid message origin:', event.origin);
    return;
  }
  
  const { type, data } = event.data;
  
  console.log('[ACU QA] Canvas message received:', { type, data });
  
  switch (type) {
    case 'canvas.resize':
      this.handleCanvasResize(data);
      break;
    case 'canvas.navigation':
      this.handleCanvasNavigation(data);
      break;
    default:
      console.log('[ACU QA] Unknown Canvas message type:', type);
  }
};

/**
 * Handle Canvas resize events
 */
ACUQAApp.handleCanvasResize = function(data) {
  const { width, height } = data;
  console.log('[ACU QA] Canvas resize:', { width, height });
  
  // Adjust application layout
  this.handleResize();
};

/**
 * Handle Canvas navigation events
 */
ACUQAApp.handleCanvasNavigation = function(data) {
  console.log('[ACU QA] Canvas navigation:', data);
  // Handle any navigation-specific logic
};

/**
 * Toggle details sections
 */
ACUQAApp.toggleDetails = function(targetId) {
  const target = document.getElementById(targetId);
  if (!target) {
    console.warn('[ACU QA] Toggle target not found:', targetId);
    return;
  }
  
  const isHidden = target.style.display === 'none' || target.hasAttribute('hidden');
  
  if (isHidden) {
    target.style.display = '';
    target.removeAttribute('hidden');
    target.classList.add('acu-fade-in');
  } else {
    target.style.display = 'none';
    target.setAttribute('hidden', '');
    target.classList.remove('acu-fade-in');
  }
};

/**
 * Utility Functions
 */
ACUQAApp.utils = {
  /**
   * Debounce function calls
   */
  debounce: function(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  },
  
  /**
   * Make API requests
   */
  apiRequest: function(url, options = {}) {
    const defaultOptions = {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
      },
      credentials: 'same-origin'
    };
    
    const requestOptions = { ...defaultOptions, ...options };
    
    return fetch(url, requestOptions)
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
      });
  },
  
  /**
   * Validate Canvas origin
   */
  isValidCanvasOrigin: function(origin) {
    const allowedOrigins = [
      'https://canvas.instructure.com',
      'https://canvas.test.instructure.com',
      'http://localhost:3000' // Development
    ];
    
    return allowedOrigins.some(allowed => origin.startsWith(allowed));
  },
  
  /**
   * Format dates for display
   */
  formatDate: function(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
  },
  
  /**
   * Escape HTML to prevent XSS
   */
  escapeHtml: function(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  },
  
  /**
   * Generate unique IDs
   */
  generateId: function(prefix = 'acu') {
    return `${prefix}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
};

/**
 * Loading Manager Component
 */
function LoadingManager() {
  this.activeLoaders = new Set();
  this.globalLoader = null;
}

LoadingManager.prototype.show = function(element, message = 'Loading...') {
  if (!element) return;
  
  const loaderId = ACUQAApp.utils.generateId('loader');
  this.activeLoaders.add(loaderId);
  
  // Create loading overlay
  const overlay = document.createElement('div');
  overlay.className = 'canvas-loading-overlay';
  overlay.dataset.loaderId = loaderId;
  overlay.innerHTML = `
    <div class="canvas-loading">
      <div class="canvas-loading-spinner"></div>
      <span>${ACUQAApp.utils.escapeHtml(message)}</span>
    </div>
  `;
  
  // Position overlay
  const rect = element.getBoundingClientRect();
  overlay.style.cssText = `
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(249, 244, 241, 0.8);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 100;
  `;
  
  // Add to element
  element.style.position = 'relative';
  element.appendChild(overlay);
  
  return loaderId;
};

LoadingManager.prototype.hide = function(element) {
  if (!element) return;
  
  const overlay = element.querySelector('.canvas-loading-overlay');
  if (overlay) {
    const loaderId = overlay.dataset.loaderId;
    this.activeLoaders.delete(loaderId);
    overlay.remove();
  }
};

LoadingManager.prototype.showGlobal = function(message = 'Loading...') {
  this.hideGlobal(); // Remove any existing global loader
  
  this.globalLoader = document.createElement('div');
  this.globalLoader.className = 'canvas-loading-global';
  this.globalLoader.innerHTML = `
    <div class="canvas-loading">
      <div class="canvas-loading-spinner"></div>
      <span>${ACUQAApp.utils.escapeHtml(message)}</span>
    </div>
  `;
  
  this.globalLoader.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(249, 244, 241, 0.9);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  `;
  
  document.body.appendChild(this.globalLoader);
};

LoadingManager.prototype.hideGlobal = function() {
  if (this.globalLoader) {
    this.globalLoader.remove();
    this.globalLoader = null;
  }
};

/**
 * User Context Display Component
 */
function UserContextDisplay() {
  this.container = document.getElementById('user-context');
}

UserContextDisplay.prototype.update = function(sessionData) {
  if (!this.container) return;
  
  const { user, canvas, session } = sessionData;
  
  let html = '<div class="acu-card acu-card-purple">';
  html += '<div class="acu-card-header">';
  html += '<h3 class="acu-heading-4 acu-mb-0">Session Information</h3>';
  html += '</div>';
  html += '<div class="acu-card-body">';
  
  if (user) {
    html += `
      <div class="acu-flex acu-items-center acu-gap-md acu-mb-md">
        <div class="acu-flex-1">
          <div class="acu-body-small acu-text-muted">User</div>
          <div class="acu-body">${ACUQAApp.utils.escapeHtml(user.name || 'Unknown User')}</div>
        </div>
        <div class="acu-status-badge acu-status-success">
          ${ACUQAApp.utils.escapeHtml(user.role || 'User')}
        </div>
      </div>
    `;
  }
  
  if (canvas) {
    html += `
      <div class="acu-mb-md">
        <div class="acu-body-small acu-text-muted">Course</div>
        <div class="acu-body">${ACUQAApp.utils.escapeHtml(canvas.course_name || 'Unknown Course')}</div>
      </div>
    `;
  }
  
  if (session) {
    html += `
      <div class="acu-flex acu-items-center acu-justify-between">
        <div>
          <div class="acu-body-small acu-text-muted">Session</div>
          <div class="acu-caption">Valid until ${ACUQAApp.utils.formatDate(session.expires || Date.now())}</div>
        </div>
        <div class="acu-status-badge acu-status-${sessionData.valid ? 'success' : 'error'}">
          ${sessionData.valid ? 'Active' : 'Invalid'}
        </div>
      </div>
    `;
  }
  
  html += '</div>';
  html += '<div class="acu-card-footer">';
  html += '<button class="acu-btn acu-btn-outline acu-btn-sm" data-action="refresh-session">Refresh Session</button>';
  html += '</div>';
  html += '</div>';
  
  this.container.innerHTML = html;
};

/**
 * Session Manager Component
 */
function SessionManager() {
  this.checkInterval = null;
  this.checkFrequency = 5 * 60 * 1000; // 5 minutes
}

SessionManager.prototype.startMonitoring = function() {
  if (this.checkInterval) return;
  
  this.checkInterval = setInterval(() => {
    ACUQAApp.validateSession().catch(error => {
      console.warn('[ACU QA] Session check failed:', error);
    });
  }, this.checkFrequency);
  
  console.log('[ACU QA] Session monitoring started');
};

SessionManager.prototype.stopMonitoring = function() {
  if (this.checkInterval) {
    clearInterval(this.checkInterval);
    this.checkInterval = null;
    console.log('[ACU QA] Session monitoring stopped');
  }
};

/**
 * Notification Manager Component
 */
function NotificationManager() {
  this.container = this.createContainer();
  this.notifications = new Map();
}

NotificationManager.prototype.createContainer = function() {
  let container = document.getElementById('acu-notifications');
  if (!container) {
    container = document.createElement('div');
    container.id = 'acu-notifications';
    container.className = 'acu-notifications-container';
    container.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 1050;
      max-width: 400px;
    `;
    document.body.appendChild(container);
  }
  return container;
};

NotificationManager.prototype.show = function(type, message, duration = 5000) {
  const id = ACUQAApp.utils.generateId('notification');
  
  const notification = document.createElement('div');
  notification.className = `canvas-alert canvas-alert-${type} acu-mb-sm`;
  notification.dataset.notificationId = id;
  notification.innerHTML = `
    <div class="canvas-alert-content">
      <p class="canvas-alert-message">${ACUQAApp.utils.escapeHtml(message)}</p>
    </div>
    <button class="canvas-modal-close" onclick="ACUQAApp.components.notifications.hide('${id}')">&times;</button>
  `;
  
  this.container.appendChild(notification);
  this.notifications.set(id, notification);
  
  // Auto-hide after duration
  if (duration > 0) {
    setTimeout(() => {
      this.hide(id);
    }, duration);
  }
  
  return id;
};

NotificationManager.prototype.hide = function(id) {
  const notification = this.notifications.get(id);
  if (notification) {
    notification.remove();
    this.notifications.delete(id);
  }
};

/**
 * Modal Manager Component
 */
function ModalManager() {
  this.activeModal = null;
}

ModalManager.prototype.show = function(modalId) {
  const modal = document.getElementById(modalId);
  if (!modal) {
    console.warn('[ACU QA] Modal not found:', modalId);
    return;
  }
  
  this.hide(); // Close any existing modal
  
  modal.style.display = 'flex';
  modal.classList.add('canvas-modal-overlay');
  this.activeModal = modal;
  
  // Handle escape key
  this.escapeHandler = (e) => {
    if (e.key === 'Escape') {
      this.hide();
    }
  };
  document.addEventListener('keydown', this.escapeHandler);
  
  // Focus management
  const firstFocusable = modal.querySelector('input, button, select, textarea, [tabindex]:not([tabindex="-1"])');
  if (firstFocusable) {
    firstFocusable.focus();
  }
};

ModalManager.prototype.hide = function() {
  if (this.activeModal) {
    this.activeModal.style.display = 'none';
    this.activeModal.classList.remove('canvas-modal-overlay');
    this.activeModal = null;
  }
  
  if (this.escapeHandler) {
    document.removeEventListener('keydown', this.escapeHandler);
    this.escapeHandler = null;
  }
};

/**
 * Initialize when DOM is ready
 */
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    ACUQAApp.init();
  });
} else {
  ACUQAApp.init();
} 