// Reminders Panel JavaScript
document.addEventListener('DOMContentLoaded', function() {
    const remindersPanel = document.getElementById('reminders-panel');
    const remindersToggle = document.getElementById('reminders-panel-toggle');
    const remindersContainer = document.getElementById('reminders-panel-container');
    const remindersClose = document.getElementById('reminders-panel-close');
    const remindersContent = document.getElementById('reminders-content');
    const refreshBtn = document.getElementById('refresh-reminders');
    const remindersBadge = document.getElementById('reminders-badge');
    
    if (!remindersPanel || !remindersToggle || !remindersContainer) {
        console.error('Reminders panel elements not found');
        return;
    }
    
    let isOpen = false;
    let currentProjectId = null;
    let remindersData = null;
    
    // Get project ID from page
    function getProjectId() {
        const projectElement = document.querySelector('[data-project-id]');
        return projectElement ? parseInt(projectElement.dataset.projectId) : null;
    }
    
    // Check if user is project owner
    function isProjectOwner() {
        const projectElement = document.querySelector('[data-project-id]');
        const userId = projectElement ? parseInt(projectElement.dataset.userId) : null;
        // We'll check this via the API response (403 if not owner)
        return true; // Assume true, API will handle permission check
    }
    
    // Toggle panel open/close
    function togglePanel() {
        isOpen = !isOpen;
        if (isOpen) {
            remindersContainer.classList.remove('hidden');
            const projectId = getProjectId();
            if (projectId && projectId !== currentProjectId) {
                currentProjectId = projectId;
                loadReminders();
            } else if (projectId) {
                loadReminders();
            }
        } else {
            remindersContainer.classList.add('hidden');
        }
    }
    
    // Load reminders from API
    async function loadReminders() {
        const projectId = getProjectId();
        if (!projectId) {
            showEmptyState();
            return;
        }
        
        // Show loading state
        showLoadingState();
        
        try {
            const response = await fetch(`/api/projects/${projectId}/reminders`, {
                method: 'GET',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            // Check if response is ok before parsing JSON
            if (!response.ok) {
                // Handle different error statuses
                if (response.status === 403) {
                    // User is not project owner, hide panel
                    remindersPanel.style.display = 'none';
                    return;
                }
                
                // Try to parse error response
                let errorData;
                try {
                    errorData = await response.json();
                } catch (e) {
                    // If response isn't JSON, use status text
                    errorData = { error: `HTTP ${response.status}: ${response.statusText}` };
                }
                
                console.error('Error loading reminders:', errorData.error || errorData.message || 'Unknown error');
                showErrorState();
                return;
            }
            
            // Parse JSON response
            const data = await response.json();
            remindersData = data;
            displayReminders(data);
            updateBadge(data);
            
        } catch (error) {
            console.error('Error loading reminders:', error);
            // Check if it's a network error
            if (error.message && (error.message.includes('Failed to fetch') || error.message.includes('NetworkError'))) {
                console.error('Network error - is the Flask server running?');
            }
            showErrorState();
        }
    }
    
    // Display reminders
    function displayReminders(data) {
        hideAllStates();
        
        const hasReminders = (data.stale_tasks && data.stale_tasks.length > 0) || 
                            (data.at_risk_tasks && data.at_risk_tasks.length > 0);
        
        if (!hasReminders) {
            showEmptyState();
            return;
        }
        
        // Show AI reminder message if available
        if (data.ai_reminder) {
            const aiReminderDiv = document.getElementById('ai-reminder-message');
            const aiReminderText = document.getElementById('ai-reminder-text');
            if (aiReminderDiv && aiReminderText) {
                aiReminderText.textContent = data.ai_reminder;
                aiReminderDiv.classList.remove('hidden');
            }
        }
        
        // Display stale tasks
        if (data.stale_tasks && data.stale_tasks.length > 0) {
            displayStaleTasks(data.stale_tasks);
        }
        
        // Display at-risk tasks
        if (data.at_risk_tasks && data.at_risk_tasks.length > 0) {
            displayAtRiskTasks(data.at_risk_tasks);
        }
    }
    
    // Display stale tasks
    function displayStaleTasks(tasks) {
        const section = document.getElementById('stale-tasks-section');
        const list = document.getElementById('stale-tasks-list');
        const count = document.getElementById('stale-tasks-count');
        
        if (!section || !list) return;
        
        section.classList.remove('hidden');
        if (count) {
            count.textContent = tasks.length;
        }
        
        list.innerHTML = '';
        tasks.forEach(task => {
            const taskItem = createTaskItem(task, 'stale');
            list.appendChild(taskItem);
        });
    }
    
    // Display at-risk tasks
    function displayAtRiskTasks(tasks) {
        const section = document.getElementById('at-risk-tasks-section');
        const list = document.getElementById('at-risk-tasks-list');
        const count = document.getElementById('at-risk-tasks-count');
        
        if (!section || !list) return;
        
        section.classList.remove('hidden');
        if (count) {
            count.textContent = tasks.length;
        }
        
        list.innerHTML = '';
        tasks.forEach(task => {
            const taskItem = createTaskItem(task, 'at-risk');
            list.appendChild(taskItem);
        });
    }
    
    // Create task item element
    function createTaskItem(task, type) {
        const item = document.createElement('div');
        item.className = 'bg-gray-800/50 rounded-lg p-3 border border-gray-700 hover:bg-gray-800/70 transition-colors cursor-pointer';
        
        const statusIcon = type === 'stale' ? 'fa-clock' : 'fa-exclamation-triangle';
        const statusBgColor = type === 'stale' ? 'bg-orange-500/20' : 'bg-red-500/20';
        const statusTextColor = type === 'stale' ? 'text-orange-400' : 'text-red-400';
        
        let statusText = '';
        if (type === 'stale') {
            statusText = `${task.days_stale} days stale`;
        } else {
            statusText = task.is_overdue 
                ? `${Math.abs(task.days_until_due)} days overdue`
                : `${task.days_until_due} days remaining`;
        }
        
        item.innerHTML = `
            <div class="flex items-start justify-between">
                <div class="flex-1">
                    <h5 class="text-white text-sm font-medium mb-1 line-clamp-2">${escapeHtml(task.title)}</h5>
                    <div class="flex items-center space-x-2 text-xs text-gray-400">
                        <span class="inline-flex items-center px-2 py-0.5 rounded ${statusBgColor} ${statusTextColor}">
                            <i class="fas ${statusIcon} mr-1"></i>
                            ${statusText}
                        </span>
                        <span class="text-gray-500">•</span>
                        <span>${task.workflow_status || task.status}</span>
                    </div>
                </div>
                <a href="${task.url}" class="ml-2 text-blue-400 hover:text-blue-300 transition-colors" title="View task">
                    <i class="fas fa-external-link-alt"></i>
                </a>
            </div>
        `;
        
        // Make entire item clickable
        item.addEventListener('click', function(e) {
            if (e.target.tagName !== 'A' && e.target.closest('a') === null) {
                window.location.href = task.url;
            }
        });
        
        return item;
    }
    
    // Update badge count
    function updateBadge(data) {
        if (!remindersBadge) return;
        
        const totalCount = (data.stale_tasks?.length || 0) + (data.at_risk_tasks?.length || 0);
        if (totalCount > 0) {
            remindersBadge.textContent = totalCount > 99 ? '99+' : totalCount;
            remindersBadge.classList.remove('hidden');
        } else {
            remindersBadge.classList.add('hidden');
        }
    }
    
    // Show loading state
    function showLoadingState() {
        hideAllStates();
        const loading = document.getElementById('reminders-loading');
        if (loading) loading.classList.remove('hidden');
    }
    
    // Show empty state
    function showEmptyState() {
        hideAllStates();
        const empty = document.getElementById('reminders-empty');
        if (empty) empty.classList.remove('hidden');
    }
    
    // Show error state
    function showErrorState() {
        hideAllStates();
        remindersContent.innerHTML = `
            <div class="text-center py-8">
                <i class="fas fa-exclamation-circle text-red-400 text-4xl mb-3"></i>
                <p class="text-gray-300 text-sm">Failed to load reminders</p>
                <button onclick="loadReminders()" class="mt-3 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors">
                    Retry
                </button>
            </div>
        `;
    }
    
    // Hide all states
    function hideAllStates() {
        const loading = document.getElementById('reminders-loading');
        const empty = document.getElementById('reminders-empty');
        const staleSection = document.getElementById('stale-tasks-section');
        const atRiskSection = document.getElementById('at-risk-tasks-section');
        const aiReminder = document.getElementById('ai-reminder-message');
        
        if (loading) loading.classList.add('hidden');
        if (empty) empty.classList.add('hidden');
        if (staleSection) staleSection.classList.add('hidden');
        if (atRiskSection) atRiskSection.classList.add('hidden');
        if (aiReminder) aiReminder.classList.add('hidden');
    }
    
    // Escape HTML to prevent XSS
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // Event listeners
    remindersToggle.addEventListener('click', togglePanel);
    if (remindersClose) {
        remindersClose.addEventListener('click', togglePanel);
    }
    if (refreshBtn) {
        refreshBtn.addEventListener('click', loadReminders);
    }
    
    // Close panel when clicking outside
    document.addEventListener('click', function(e) {
        if (isOpen && !remindersPanel.contains(e.target)) {
            togglePanel();
        }
    });
    
    // Prevent panel from closing when clicking inside
    remindersContainer.addEventListener('click', function(e) {
        e.stopPropagation();
    });
    
    // Load reminders on page load (to update badge)
    const projectId = getProjectId();
    if (projectId) {
        currentProjectId = projectId;
        loadReminders();
        
        // Refresh reminders every 5 minutes
        setInterval(loadReminders, 5 * 60 * 1000);
    }
});

