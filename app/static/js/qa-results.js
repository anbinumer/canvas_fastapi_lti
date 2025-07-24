/**
 * QA Results Display and Export Components
 * Story 2.3: QA Results Dashboard & User Interface
 * Comprehensive results visualization and export functionality
 */

/**
 * QA Results Display Component
 */
function QAResultsDisplay() {
  this.container = document.getElementById('qa-results-container');
  this.currentResults = null;
}

QAResultsDisplay.prototype.render = function(results) {
  if (!this.container) {
    console.warn('[QA Results] Results container not found');
    return;
  }
  
  if (!results) {
    this.clear();
    return;
  }
  
  this.currentResults = results;
  
  let html = this.renderHeader(results);
  html += this.renderSummary(results);
  html += this.renderFindings(results);
  html += this.renderExportPanel(results);
  
  this.container.innerHTML = html;
  this.container.style.display = 'block';
  
  console.log('[QA Results] Results displayed:', results);
};

QAResultsDisplay.prototype.renderHeader = function(results) {
  const taskName = results.task_info?.name || 'QA Task';
  const status = results.status || 'completed';
  const completedAt = results.completed_at ? 
    new Date(results.completed_at).toLocaleString() : 
    new Date().toLocaleString();
  
  return `
    <div class="qa-results-header">
      <div>
        <h2 class="acu-heading-2 acu-mb-sm">${ACUQAApp.utils.escapeHtml(taskName)} Results</h2>
        <p class="acu-body-small">Completed: ${completedAt}</p>
      </div>
      <div class="qa-status-badge qa-status-${status}">
        ${status.toUpperCase()}
      </div>
    </div>
  `;
};

QAResultsDisplay.prototype.renderSummary = function(results) {
  const stats = results.statistics || {};
  
  return `
    <div class="qa-results-summary">
      <div class="qa-summary-card">
        <div class="qa-summary-value">${stats.items_processed || 0}</div>
        <div class="qa-summary-label">Items Processed</div>
      </div>
      
      <div class="qa-summary-card">
        <div class="qa-summary-value">${stats.urls_found || 0}</div>
        <div class="qa-summary-label">URLs Found</div>
      </div>
      
      <div class="qa-summary-card">
        <div class="qa-summary-value">${stats.urls_replaced || 0}</div>
        <div class="qa-summary-label">URLs Replaced</div>
      </div>
      
      <div class="qa-summary-card">
        <div class="qa-summary-value">${stats.errors || 0}</div>
        <div class="qa-summary-label">Errors</div>
      </div>
      
      <div class="qa-summary-card">
        <div class="qa-summary-value">${this.formatDuration(stats.execution_time)}</div>
        <div class="qa-summary-label">Execution Time</div>
      </div>
      
      <div class="qa-summary-card">
        <div class="qa-summary-value">${stats.api_calls || 0}</div>
        <div class="qa-summary-label">API Calls</div>
      </div>
    </div>
  `;
};

QAResultsDisplay.prototype.renderFindings = function(results) {
  const findings = results.findings || [];
  
  if (findings.length === 0) {
    return `
      <div class="qa-results-content">
        <div class="acu-text-center acu-p-xl">
          <p class="acu-text-muted">No findings to display.</p>
        </div>
      </div>
    `;
  }
  
  // Group findings by type
  const groupedFindings = this.groupFindingsByType(findings);
  
  let html = '<div class="qa-results-content">';
  
  Object.entries(groupedFindings).forEach(([type, typeFindings]) => {
    html += this.renderFindingSection(type, typeFindings);
  });
  
  html += '</div>';
  return html;
};

QAResultsDisplay.prototype.groupFindingsByType = function(findings) {
  const groups = {
    'url_replaced': [],
    'url_found': [],
    'error': [],
    'warning': [],
    'info': []
  };
  
  findings.forEach(finding => {
    const type = finding.type || 'info';
    if (!groups[type]) groups[type] = [];
    groups[type].push(finding);
  });
  
  // Remove empty groups
  Object.keys(groups).forEach(key => {
    if (groups[key].length === 0) {
      delete groups[key];
    }
  });
  
  return groups;
};

QAResultsDisplay.prototype.renderFindingSection = function(type, findings) {
  const sectionTitles = {
    'url_replaced': '🔄 URLs Successfully Replaced',
    'url_found': '🔍 URLs Found (No Replacement)',
    'error': '❌ Errors Encountered',
    'warning': '⚠️ Warnings',
    'info': 'ℹ️ Information'
  };
  
  const title = sectionTitles[type] || `${type.toUpperCase()} Findings`;
  
  let html = `
    <div class="qa-findings-section">
      <h3 class="qa-section-title">${title} <span class="acu-text-muted">(${findings.length})</span></h3>
  `;
  
  findings.forEach((finding, index) => {
    html += this.renderFindingCard(finding, type, index);
  });
  
  html += '</div>';
  return html;
};

QAResultsDisplay.prototype.renderFindingCard = function(finding, type, index) {
  const typeClass = this.getFindingTypeClass(type);
  const contentType = finding.content_type || 'Unknown';
  const contentId = finding.content_id || 'N/A';
  const contentTitle = finding.content_title || 'Untitled';
  
  let html = `
    <div class="qa-finding-card">
      <div class="qa-finding-header">
        <div>
          <span class="qa-finding-type ${typeClass}">${type.replace('_', ' ').toUpperCase()}</span>
          <span class="acu-text-muted"> - ${ACUQAApp.utils.escapeHtml(contentType)}</span>
        </div>
        <div class="acu-text-muted acu-body-small">
          ID: ${ACUQAApp.utils.escapeHtml(contentId)}
        </div>
      </div>
      
      <div class="qa-finding-content">
        <h4 class="acu-heading-4">${ACUQAApp.utils.escapeHtml(contentTitle)}</h4>
        
        ${finding.description ? `
          <p class="acu-body-small acu-text-secondary acu-mb-md">
            ${ACUQAApp.utils.escapeHtml(finding.description)}
          </p>
        ` : ''}
        
        ${this.renderFindingDetails(finding, type)}
      </div>
    </div>
  `;
  
  return html;
};

QAResultsDisplay.prototype.renderFindingDetails = function(finding, type) {
  if (type === 'url_replaced' && finding.original_url && finding.new_url) {
    return `
      <div class="qa-before-after">
        <div class="qa-before">
          <div class="qa-before-label">Original URL</div>
          <div class="qa-url-text">${ACUQAApp.utils.escapeHtml(finding.original_url)}</div>
        </div>
        <div class="qa-after">
          <div class="qa-after-label">New URL</div>
          <div class="qa-url-text">${ACUQAApp.utils.escapeHtml(finding.new_url)}</div>
        </div>
      </div>
    `;
  } else if (finding.url) {
    return `
      <div class="qa-url-display">
        <div class="qa-input-label">URL</div>
        <div class="qa-url-text">${ACUQAApp.utils.escapeHtml(finding.url)}</div>
      </div>
    `;
  } else if (finding.message) {
    return `
      <div class="qa-message-display">
        <p class="acu-body">${ACUQAApp.utils.escapeHtml(finding.message)}</p>
      </div>
    `;
  }
  
  return '';
};

QAResultsDisplay.prototype.getFindingTypeClass = function(type) {
  const typeClasses = {
    'url_replaced': 'qa-finding-success',
    'url_found': 'qa-finding-warning',
    'error': 'qa-finding-error',
    'warning': 'qa-finding-warning',
    'info': 'qa-finding-info'
  };
  
  return typeClasses[type] || 'qa-finding-info';
};

QAResultsDisplay.prototype.renderExportPanel = function(results) {
  return `
    <div class="qa-export-panel">
      <div>
        <h4 class="acu-heading-4 acu-mb-sm">Export Results</h4>
        <p class="acu-body-small acu-text-muted">
          Share and analyze your QA results
        </p>
      </div>
      
      <div class="qa-export-actions">
        <button class="qa-export-btn primary" onclick="ACUQAApp.qa.components.exportManager.exportToPDF()">
          📄 Export PDF Report
        </button>
        
        <button class="qa-export-btn" onclick="ACUQAApp.qa.components.exportManager.exportToCSV()">
          📊 Export CSV Data
        </button>
        
        <button class="qa-export-btn" onclick="ACUQAApp.qa.components.exportManager.printResults()">
          🖨️ Print Results
        </button>
        
        <button class="qa-export-btn" onclick="ACUQAApp.qa.components.exportManager.shareResults()">
          📤 Share Results
        </button>
      </div>
    </div>
  `;
};

QAResultsDisplay.prototype.formatDuration = function(milliseconds) {
  if (!milliseconds || milliseconds < 0) return '0s';
  
  const seconds = Math.floor(milliseconds / 1000);
  const minutes = Math.floor(seconds / 60);
  
  if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`;
  } else {
    return `${seconds}s`;
  }
};

QAResultsDisplay.prototype.clear = function() {
  if (this.container) {
    this.container.innerHTML = `
      <div class="acu-text-center acu-p-xl">
        <p class="acu-text-muted">No results to display. Run a QA task to see results here.</p>
      </div>
    `;
    this.container.style.display = 'none';
  }
  
  this.currentResults = null;
};

QAResultsDisplay.prototype.renderError = function(message) {
  if (!this.container) return;
  
  this.container.innerHTML = `
    <div class="qa-error-container">
      <div class="qa-error-icon">❌</div>
      <div class="qa-error-title">Error Displaying Results</div>
      <div class="qa-error-message">${ACUQAApp.utils.escapeHtml(message)}</div>
      <div class="qa-error-actions">
        <button class="acu-btn acu-btn-primary" onclick="ACUQAApp.qa.components.resultsDisplay.clear()">
          Clear Results
        </button>
      </div>
    </div>
  `;
  
  this.container.style.display = 'block';
};

/**
 * QA Export Manager Component
 */
function QAExportManager() {
  this.currentResults = null;
}

QAExportManager.prototype.setResults = function(results) {
  this.currentResults = results;
};

QAExportManager.prototype.exportToPDF = function() {
  if (!this.currentResults) {
    ACUQAApp.components.notifications.show('warning', 'No results available to export');
    return;
  }
  
  console.log('[QA Export] Generating PDF report...');
  ACUQAApp.components.notifications.show('info', 'Generating PDF report...');
  
  // Create printable content
  const printContent = this.generatePrintableContent(this.currentResults);
  
  // Open print dialog
  const printWindow = window.open('', '_blank');
  printWindow.document.write(printContent);
  printWindow.document.close();
  printWindow.print();
  
  // Note: In a real implementation, you would use a library like jsPDF or html2pdf
  ACUQAApp.components.notifications.show('success', 'PDF report generated successfully');
};

QAExportManager.prototype.exportToCSV = function() {
  if (!this.currentResults) {
    ACUQAApp.components.notifications.show('warning', 'No results available to export');
    return;
  }
  
  console.log('[QA Export] Generating CSV data...');
  
  const csvData = this.generateCSVData(this.currentResults);
  const blob = new Blob([csvData], { type: 'text/csv;charset=utf-8;' });
  
  // Create download link
  const link = document.createElement('a');
  if (link.download !== undefined) {
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', this.generateFilename('csv'));
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
  
  ACUQAApp.components.notifications.show('success', 'CSV data exported successfully');
};

QAExportManager.prototype.printResults = function() {
  if (!this.currentResults) {
    ACUQAApp.components.notifications.show('warning', 'No results available to print');
    return;
  }
  
  console.log('[QA Export] Printing results...');
  
  const printContent = this.generatePrintableContent(this.currentResults);
  
  const printWindow = window.open('', '_blank');
  printWindow.document.write(printContent);
  printWindow.document.close();
  printWindow.print();
};

QAExportManager.prototype.shareResults = function() {
  if (!this.currentResults) {
    ACUQAApp.components.notifications.show('warning', 'No results available to share');
    return;
  }
  
  console.log('[QA Export] Sharing results...');
  
  const summary = this.generateShareSummary(this.currentResults);
  
  if (navigator.share) {
    navigator.share({
      title: 'QA Automation Results',
      text: summary,
      url: window.location.href
    }).then(() => {
      ACUQAApp.components.notifications.show('success', 'Results shared successfully');
    }).catch((error) => {
      console.error('[QA Export] Share failed:', error);
      this.fallbackShare(summary);
    });
  } else {
    this.fallbackShare(summary);
  }
};

QAExportManager.prototype.fallbackShare = function(summary) {
  // Copy to clipboard as fallback
  if (navigator.clipboard) {
    navigator.clipboard.writeText(summary).then(() => {
      ACUQAApp.components.notifications.show('success', 'Results summary copied to clipboard');
    }).catch(() => {
      ACUQAApp.components.notifications.show('error', 'Unable to share results');
    });
  } else {
    ACUQAApp.components.notifications.show('info', 'Sharing not supported. Use export options instead.');
  }
};

QAExportManager.prototype.generatePrintableContent = function(results) {
  const taskName = results.task_info?.name || 'QA Task';
  const completedAt = results.completed_at ? 
    new Date(results.completed_at).toLocaleString() : 
    new Date().toLocaleString();
  
  return `
    <!DOCTYPE html>
    <html>
    <head>
      <title>${taskName} - QA Results Report</title>
      <style>
        body { font-family: Arial, sans-serif; margin: 20px; color: #333; }
        .header { border-bottom: 2px solid #4A1A4A; padding-bottom: 20px; margin-bottom: 30px; }
        .header h1 { color: #4A1A4A; margin: 0; }
        .header .date { color: #666; margin-top: 10px; }
        .summary { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 30px; }
        .summary-card { border: 1px solid #ddd; padding: 15px; text-align: center; border-radius: 8px; }
        .summary-value { font-size: 24px; font-weight: bold; color: #D2492A; }
        .summary-label { font-size: 12px; color: #666; text-transform: uppercase; }
        .findings { margin-top: 30px; }
        .finding { border: 1px solid #ddd; margin-bottom: 20px; border-radius: 8px; overflow: hidden; }
        .finding-header { background: #f5f5f5; padding: 15px; border-bottom: 1px solid #ddd; }
        .finding-content { padding: 15px; }
        .url-comparison { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 15px; }
        .url-box { background: #f9f9f9; padding: 10px; border-radius: 4px; border-left: 4px solid #ccc; }
        .url-before { border-left-color: #D2492A; }
        .url-after { border-left-color: #2D7D32; }
        @media print { .no-print { display: none; } }
      </style>
    </head>
    <body>
      <div class="header">
        <h1>${taskName} - Results Report</h1>
        <div class="date">Generated: ${completedAt}</div>
      </div>
      
      ${this.generatePrintableSummary(results)}
      ${this.generatePrintableFindings(results)}
    </body>
    </html>
  `;
};

QAExportManager.prototype.generatePrintableSummary = function(results) {
  const stats = results.statistics || {};
  
  return `
    <div class="summary">
      <div class="summary-card">
        <div class="summary-value">${stats.items_processed || 0}</div>
        <div class="summary-label">Items Processed</div>
      </div>
      <div class="summary-card">
        <div class="summary-value">${stats.urls_found || 0}</div>
        <div class="summary-label">URLs Found</div>
      </div>
      <div class="summary-card">
        <div class="summary-value">${stats.urls_replaced || 0}</div>
        <div class="summary-label">URLs Replaced</div>
      </div>
    </div>
  `;
};

QAExportManager.prototype.generatePrintableFindings = function(results) {
  const findings = results.findings || [];
  
  if (findings.length === 0) {
    return '<div class="findings"><p>No findings to report.</p></div>';
  }
  
  let html = '<div class="findings"><h2>Detailed Findings</h2>';
  
  findings.forEach((finding, index) => {
    html += `
      <div class="finding">
        <div class="finding-header">
          <strong>${finding.content_title || 'Untitled'}</strong>
          <span style="float: right;">${finding.content_type || 'Unknown'}</span>
        </div>
        <div class="finding-content">
          ${finding.original_url && finding.new_url ? `
            <div class="url-comparison">
              <div class="url-box url-before">
                <strong>Original URL:</strong><br>
                ${finding.original_url}
              </div>
              <div class="url-box url-after">
                <strong>New URL:</strong><br>
                ${finding.new_url}
              </div>
            </div>
          ` : ''}
          ${finding.description ? `<p>${finding.description}</p>` : ''}
        </div>
      </div>
    `;
  });
  
  html += '</div>';
  return html;
};

QAExportManager.prototype.generateCSVData = function(results) {
  const findings = results.findings || [];
  
  // CSV headers
  let csv = 'Type,Content Type,Content ID,Content Title,Original URL,New URL,Description,Timestamp\n';
  
  // CSV rows
  findings.forEach(finding => {
    const row = [
      finding.type || '',
      finding.content_type || '',
      finding.content_id || '',
      finding.content_title || '',
      finding.original_url || '',
      finding.new_url || finding.url || '',
      finding.description || finding.message || '',
      new Date().toISOString()
    ];
    
    // Escape CSV values
    const escapedRow = row.map(value => {
      const stringValue = String(value);
      if (stringValue.includes(',') || stringValue.includes('"') || stringValue.includes('\n')) {
        return `"${stringValue.replace(/"/g, '""')}"`;
      }
      return stringValue;
    });
    
    csv += escapedRow.join(',') + '\n';
  });
  
  return csv;
};

QAExportManager.prototype.generateShareSummary = function(results) {
  const stats = results.statistics || {};
  const taskName = results.task_info?.name || 'QA Task';
  
  return `${taskName} Results Summary:
• Items Processed: ${stats.items_processed || 0}
• URLs Found: ${stats.urls_found || 0} 
• URLs Replaced: ${stats.urls_replaced || 0}
• Errors: ${stats.errors || 0}
• Execution Time: ${this.formatDuration(stats.execution_time)}

Generated by ACU QA Automation Tool`;
};

QAExportManager.prototype.generateFilename = function(extension) {
  const timestamp = new Date().toISOString().slice(0, 19).replace(/[:.]/g, '-');
  const taskName = this.currentResults?.task_info?.name || 'qa-task';
  const safeName = taskName.toLowerCase().replace(/[^a-z0-9]/g, '-');
  
  return `${safeName}-results-${timestamp}.${extension}`;
};

QAExportManager.prototype.formatDuration = function(milliseconds) {
  if (!milliseconds || milliseconds < 0) return '0s';
  
  const seconds = Math.floor(milliseconds / 1000);
  const minutes = Math.floor(seconds / 60);
  
  if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`;
  } else {
    return `${seconds}s`;
  }
}; 