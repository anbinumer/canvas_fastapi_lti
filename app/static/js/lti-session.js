/**
 * LTI Session Management for Canvas Integration
 * Handles LTI 1.3 session state, iframe communication, and Canvas-specific features
 */

/**
 * LTI Session Manager
 */
window.LTISession = {
  // Session state
  state: {
    isLTIContext: false,
    sessionData: null,
    lastValidation: null,
    validationInterval: null
  },
  
  // Configuration
  config: {
    validationFrequency: 5 * 60 * 1000, // 5 minutes
    sessionEndpoint: '/lti/session',
    maxRetries: 3,
    retryDelay: 2000
  },
  
  // Event callbacks
  callbacks: {
    onSessionValid: [],
    onSessionInvalid: [],
    onSessionError: [],
    onUserContextUpdate: []
  }
};

/**
 * Initialize LTI session management
 */
LTISession.init = function() {
  console.log('[LTI Session] Initializing LTI session management...');
  
  // Detect LTI context
  this.detectLTIContext();
  
  // Set up Canvas iframe communication
  this.setupCanvasMessaging();
  
  // Start session validation if in LTI context
  if (this.state.isLTIContext) {
    this.startSessionValidation();
  }
  
  // Set up Canvas-specific features
  this.setupCanvasFeatures();
  
  console.log('[LTI Session] LTI session management initialized');
};

/**
 * Detect if running in LTI context
 */
LTISession.detectLTIContext = function() {
  // Check for LTI indicators
  const hasLTIParams = window.location.search.includes('lti') || 
                       window.location.pathname.includes('/lti/');
  
  const isInIframe = window.self !== window.top;
  
  const hasLTIElements = document.querySelector('[data-lti-context]') !== null;
  
  this.state.isLTIContext = hasLTIParams || isInIframe || hasLTIElements;
  
  console.log('[LTI Session] LTI context detected:', this.state.isLTIContext);
  
  // Add LTI class to body for CSS targeting
  if (this.state.isLTIContext) {
    document.body.classList.add('lti-context');
  }
  
  return this.state.isLTIContext;
};

/**
 * Set up Canvas iframe messaging
 */
LTISession.setupCanvasMessaging = function() {
  // Listen for Canvas messages
  window.addEventListener('message', (event) => {
    this.handleCanvasMessage(event);
  });
  
  // Send ready message to Canvas
  if (this.state.isLTIContext && window.parent !== window) {
    this.sendToCanvas('lti.ready', {
      tool: 'ACU QA Automation',
      version: '1.0.0'
    });
  }
};

/**
 * Handle messages from Canvas
 */
LTISession.handleCanvasMessage = function(event) {
  // Validate origin (basic security)
  if (!this.isValidCanvasOrigin(event.origin)) {
    console.warn('[LTI Session] Invalid Canvas message origin:', event.origin);
    return;
  }
  
  const { type, data } = event.data || {};
  
  console.log('[LTI Session] Canvas message received:', { type, data });
  
  switch (type) {
    case 'canvas.session.check':
      this.validateSession();
      break;
      
    case 'canvas.resize':
      this.handleCanvasResize(data);
      break;
      
    case 'canvas.theme.change':
      this.handleThemeChange(data);
      break;
      
    case 'canvas.navigation':
      this.handleNavigation(data);
      break;
      
    default:
      console.log('[LTI Session] Unknown Canvas message type:', type);
  }
};

/**
 * Send message to Canvas parent
 */
LTISession.sendToCanvas = function(type, data = {}) {
  if (window.parent !== window) {
    const message = {
      type: type,
      data: data,
      timestamp: Date.now(),
      source: 'acu-qa-tool'
    };
    
    window.parent.postMessage(message, '*');
    console.log('[LTI Session] Sent to Canvas:', message);
  }
};

/**
 * Validate Canvas origin
 */
LTISession.isValidCanvasOrigin = function(origin) {
  const allowedOrigins = [
    'https://canvas.instructure.com',
    'https://acu.instructure.com',
    'https://canvas.test.instructure.com',
    'http://localhost:3000' // Development
  ];
  
  return allowedOrigins.some(allowed => origin.includes(allowed));
};

/**
 * Start session validation
 */
LTISession.startSessionValidation = function() {
  // Initial validation
  this.validateSession();
  
  // Set up periodic validation
  if (this.state.validationInterval) {
    clearInterval(this.state.validationInterval);
  }
  
  this.state.validationInterval = setInterval(() => {
    this.validateSession();
  }, this.config.validationFrequency);
  
  console.log('[LTI Session] Session validation started');
};

/**
 * Stop session validation
 */
LTISession.stopSessionValidation = function() {
  if (this.state.validationInterval) {
    clearInterval(this.state.validationInterval);
    this.state.validationInterval = null;
    console.log('[LTI Session] Session validation stopped');
  }
};

/**
 * Validate current session
 */
LTISession.validateSession = function() {
  console.log('[LTI Session] Validating session...');
  
  return this.makeRequest(this.config.sessionEndpoint)
    .then(data => {
      this.state.sessionData = data;
      this.state.lastValidation = Date.now();
      
      if (data.valid) {
        console.log('[LTI Session] Session valid:', data);
        this.triggerCallbacks('onSessionValid', data);
        
        // Update Canvas with session status
        this.sendToCanvas('lti.session.valid', data);
        
      } else {
        console.warn('[LTI Session] Session invalid:', data);
        this.triggerCallbacks('onSessionInvalid', data);
        
        // Update Canvas with session status
        this.sendToCanvas('lti.session.invalid', data);
      }
      
      // Trigger user context update
      if (data.user || data.canvas) {
        this.triggerCallbacks('onUserContextUpdate', {
          user: data.user,
          canvas: data.canvas
        });
      }
      
      return data;
    })
    .catch(error => {
      console.error('[LTI Session] Session validation failed:', error);
      this.triggerCallbacks('onSessionError', error);
      
      // Inform Canvas of error
      this.sendToCanvas('lti.session.error', {
        error: error.message
      });
      
      throw error;
    });
};

/**
 * Make API request with retry logic
 */
LTISession.makeRequest = function(url, options = {}, retryCount = 0) {
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
    })
    .catch(error => {
      if (retryCount < this.config.maxRetries) {
        console.log(`[LTI Session] Request failed, retrying... (${retryCount + 1}/${this.config.maxRetries})`);
        
        return new Promise(resolve => {
          setTimeout(() => {
            resolve(this.makeRequest(url, options, retryCount + 1));
          }, this.config.retryDelay);
        });
      }
      
      throw error;
    });
};

/**
 * Handle Canvas resize events
 */
LTISession.handleCanvasResize = function(data) {
  const { width, height } = data || {};
  
  console.log('[LTI Session] Canvas resize:', { width, height });
  
  // Adjust application layout
  const container = document.querySelector('.canvas-lti-container');
  if (container && height) {
    container.style.maxHeight = `${height}px`;
  }
  
  // Trigger global resize event
  window.dispatchEvent(new Event('canvas.resize'));
};

/**
 * Handle Canvas theme changes
 */
LTISession.handleThemeChange = function(data) {
  const { theme } = data || {};
  
  console.log('[LTI Session] Canvas theme change:', theme);
  
  // Apply theme to body
  document.body.className = document.body.className.replace(/canvas-theme-\w+/g, '');
  
  if (theme) {
    document.body.classList.add(`canvas-theme-${theme}`);
  }
  
  // Trigger theme change event
  window.dispatchEvent(new CustomEvent('canvas.theme.change', { detail: data }));
};

/**
 * Handle Canvas navigation
 */
LTISession.handleNavigation = function(data) {
  console.log('[LTI Session] Canvas navigation:', data);
  
  // Update breadcrumb if present
  this.updateBreadcrumb(data);
  
  // Trigger navigation event
  window.dispatchEvent(new CustomEvent('canvas.navigation', { detail: data }));
};

/**
 * Update breadcrumb navigation
 */
LTISession.updateBreadcrumb = function(navigationData) {
  const breadcrumb = document.querySelector('.canvas-breadcrumb');
  if (!breadcrumb) return;
  
  const { course, module, assignment } = navigationData || {};
  
  let html = '';
  
  if (course) {
    html += `<a href="#" class="canvas-breadcrumb-item">${this.escapeHtml(course.name)}</a>`;
    html += '<span class="canvas-breadcrumb-separator">›</span>';
  }
  
  if (module) {
    html += `<a href="#" class="canvas-breadcrumb-item">${this.escapeHtml(module.name)}</a>`;
    html += '<span class="canvas-breadcrumb-separator">›</span>';
  }
  
  if (assignment) {
    html += `<span class="canvas-breadcrumb-current">${this.escapeHtml(assignment.name)}</span>`;
  } else {
    html += '<span class="canvas-breadcrumb-current">QA Automation</span>';
  }
  
  breadcrumb.innerHTML = html;
};

/**
 * Set up Canvas-specific features
 */
LTISession.setupCanvasFeatures = function() {
  // Set up Canvas-compatible scrolling
  this.setupCanvasScrolling();
  
  // Set up Canvas keyboard navigation
  this.setupCanvasKeyboard();
  
  // Set up Canvas accessibility features
  this.setupCanvasAccessibility();
};

/**
 * Set up Canvas-compatible scrolling
 */
LTISession.setupCanvasScrolling = function() {
  // Smooth scrolling for Canvas iframe
  if (this.state.isLTIContext) {
    document.documentElement.style.scrollBehavior = 'smooth';
    
    // Prevent horizontal scrolling
    document.body.style.overflowX = 'hidden';
  }
};

/**
 * Set up Canvas keyboard navigation
 */
LTISession.setupCanvasKeyboard = function() {
  // Handle Canvas keyboard shortcuts
  document.addEventListener('keydown', (event) => {
    // Escape key handling
    if (event.key === 'Escape') {
      // Close any open modals
      if (window.ACUQAApp && window.ACUQAApp.components.modal) {
        window.ACUQAApp.components.modal.hide();
      }
    }
    
    // Canvas-specific shortcuts can be added here
  });
};

/**
 * Set up Canvas accessibility features
 */
LTISession.setupCanvasAccessibility = function() {
  // Ensure proper focus management
  document.addEventListener('focusin', (event) => {
    const target = event.target;
    
    // Ensure focused elements are visible
    if (target && target.scrollIntoView) {
      target.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  });
  
  // Add skip links for Canvas navigation
  this.addSkipLinks();
};

/**
 * Add skip links for accessibility
 */
LTISession.addSkipLinks = function() {
  const skipLink = document.createElement('a');
  skipLink.className = 'canvas-skip-link';
  skipLink.href = '#main-content';
  skipLink.textContent = 'Skip to main content';
  
  document.body.insertBefore(skipLink, document.body.firstChild);
  
  // Ensure main content has proper ID
  const mainContent = document.querySelector('.canvas-lti-container, main, [role="main"]');
  if (mainContent && !mainContent.id) {
    mainContent.id = 'main-content';
  }
};

/**
 * Register session callback
 */
LTISession.onSessionValid = function(callback) {
  this.callbacks.onSessionValid.push(callback);
};

LTISession.onSessionInvalid = function(callback) {
  this.callbacks.onSessionInvalid.push(callback);
};

LTISession.onSessionError = function(callback) {
  this.callbacks.onSessionError.push(callback);
};

LTISession.onUserContextUpdate = function(callback) {
  this.callbacks.onUserContextUpdate.push(callback);
};

/**
 * Trigger callbacks
 */
LTISession.triggerCallbacks = function(type, data) {
  const callbacks = this.callbacks[type] || [];
  callbacks.forEach(callback => {
    try {
      callback(data);
    } catch (error) {
      console.error(`[LTI Session] Callback error (${type}):`, error);
    }
  });
};

/**
 * Utility: Escape HTML
 */
LTISession.escapeHtml = function(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
};

/**
 * Get current session data
 */
LTISession.getSessionData = function() {
  return this.state.sessionData;
};

/**
 * Check if session is valid
 */
LTISession.isSessionValid = function() {
  return this.state.sessionData && this.state.sessionData.valid;
};

/**
 * Get user context
 */
LTISession.getUserContext = function() {
  return this.state.sessionData ? this.state.sessionData.user : null;
};

/**
 * Get Canvas context
 */
LTISession.getCanvasContext = function() {
  return this.state.sessionData ? this.state.sessionData.canvas : null;
};

/**
 * Initialize when DOM is ready
 */
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    LTISession.init();
  });
} else {
  LTISession.init();
} 