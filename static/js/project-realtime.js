/**
 * Real-time updates for project detail page
 * Handles task and project updates via WebSocket
 */

class ProjectRealtimeManager {
    constructor(projectId) {
        this.projectId = projectId;
        this.wsClient = null;
        this.conflictResolution = new Map(); // Track conflicts
        this.lastUpdateTimestamp = new Map(); // Track last update times
        this.isInitialized = false;
        
        this.init();
    }
    
    init() {
        // Initialize WebSocket client
        this.wsClient = initializeWebSocket();
        
        if (!this.wsClient) {
            console.error('Failed to initialize WebSocket client');
            return;
        }
        
        // Set up event handlers
        this.setupEventHandlers();
        
        // Join project room when connected
        const joinProject = () => {
            if (this.wsClient.isWebSocketConnected()) {
                this.wsClient.joinProject(this.projectId);
                this.isInitialized = true;
            } else {
                setTimeout(joinProject, 100);
            }
        };
        
        joinProject();
    }
    
    setupEventHandlers() {
        // Override the default handlers with project-specific ones
        this.wsClient.onTaskUpdate = (taskData, user) => {
            this.handleTaskUpdate(taskData, user);
        };
        
        this.wsClient.onProjectUpdate = (projectData, user) => {
            this.handleProjectUpdate(projectData, user);
        };
        
        this.wsClient.onActiveUsersUpdate = (users) => {
            this.updateActiveUsers(users);
        };
        
        this.wsClient.onUserConnected = (userData) => {
            this.showNotification(`${userData.user_name} joined the project`, 'info');
            this.wsClient.requestActiveUsers();
        };
        
        this.wsClient.onUserDisconnected = (userData) => {
            this.showNotification(`${userData.user_name} left the project`, 'info');
            this.wsClient.requestActiveUsers();
        };
    }
    
    handleTaskUpdate(taskData, user) {
        const { task_data, update_type } = taskData;
        
        // Skip updates from current user to avoid conflicts
        if (user.id === window.currentUserId) {
            return;
        }
        
        // Check for conflicts
        if (this.detectConflict(task_data.id, task_data.updated_at)) {
            this.handleConflict(task_data, user, update_type);
            return;
        }
        
        // Update last timestamp
        this.lastUpdateTimestamp.set(task_data.id, task_data.updated_at);
        
        switch (update_type) {
            case 'task_create':
                this.addTaskToUI(task_data, user);
                break;
            case 'task_update':
                this.updateTaskInUI(task_data, user);
                break;
            case 'task_delete':
                this.removeTaskFromUI(task_data, user);
                break;
        }
        
        this.showNotification(`${user.name} ${this.getUpdateActionText(update_type)} task "${task_data.title}"`, 'info');
    }
    
    handleProjectUpdate(projectData, user) {
        const { project_data, update_type } = projectData;
        
        // Skip updates from current user
        if (user.id === window.currentUserId) {
            return;
        }
        
        // Update project information in UI
        this.updateProjectInUI(project_data, user);
        
        this.showNotification(`${user.name} updated the project`, 'info');
    }
    
    addTaskToUI(taskData, user) {
        const tasksContainer = document.getElementById('tasks-container');
        if (!tasksContainer) return;
        
        // Check if task already exists
        const existingTask = document.querySelector(`[data-task-id="${taskData.id}"]`);
        if (existingTask) {
            this.updateTaskInUI(taskData, user);
            return;
        }
        
        // Create new task element
        const taskElement = this.createTaskElement(taskData);
        
        // Insert in correct position based on sort order or append at end
        const tasks = Array.from(tasksContainer.children);
        let inserted = false;
        
        for (let i = 0; i < tasks.length; i++) {
            const existingSortOrder = parseInt(tasks[i].dataset.sortOrder) || 0;
            if ((taskData.sort_order || 0) < existingSortOrder) {
                tasksContainer.insertBefore(taskElement, tasks[i]);
                inserted = true;
                break;
            }
        }
        
        if (!inserted) {
            tasksContainer.appendChild(taskElement);
        }
        
        // Update task count
        this.updateTaskCount();
        
        // Animate the new task
        taskElement.style.opacity = '0';
        taskElement.style.transform = 'translateY(-10px)';
        setTimeout(() => {
            taskElement.style.transition = 'all 0.3s ease';
            taskElement.style.opacity = '1';
            taskElement.style.transform = 'translateY(0)';
        }, 100);
    }
    
    updateTaskInUI(taskData, user) {
        const taskElement = document.querySelector(`[data-task-id="${taskData.id}"]`);
        if (!taskElement) {
            // Task doesn't exist, create it
            this.addTaskToUI(taskData, user);
            return;
        }
        
        // Update task content
        const titleElement = taskElement.querySelector('h3 a');
        const descriptionElement = taskElement.querySelector('.text-gray-400');
        const statusIcon = taskElement.querySelector('.fas');
        const priorityBadge = taskElement.querySelector('.inline-flex');
        
        if (titleElement) {
            titleElement.textContent = taskData.title;
        }
        
        if (descriptionElement && taskData.description) {
            const truncatedDesc = taskData.description.length > 100 
                ? taskData.description.substring(0, 100) + '...' 
                : taskData.description;
            descriptionElement.textContent = truncatedDesc;
        }
        
        // Update status icon
        if (statusIcon) {
            statusIcon.className = this.getStatusIconClass(taskData.status);
        }
        
        // Update priority badge
        if (priorityBadge) {
            priorityBadge.className = this.getPriorityBadgeClass(taskData.priority);
            priorityBadge.textContent = taskData.priority.charAt(0).toUpperCase() + taskData.priority.slice(1);
        }
        
        // Update data attributes
        taskElement.dataset.riskLevel = taskData.risk_level;
        
        // Add visual feedback for update
        taskElement.style.backgroundColor = 'rgba(59, 130, 246, 0.1)';
        setTimeout(() => {
            taskElement.style.backgroundColor = '';
        }, 2000);
    }
    
    removeTaskFromUI(taskData, user) {
        const taskElement = document.querySelector(`[data-task-id="${taskData.id}"]`);
        if (!taskElement) return;
        
        // Animate removal
        taskElement.style.transition = 'all 0.3s ease';
        taskElement.style.opacity = '0';
        taskElement.style.transform = 'translateX(-100%)';
        
        setTimeout(() => {
            taskElement.remove();
            this.updateTaskCount();
        }, 300);
    }
    
    updateProjectInUI(projectData, user) {
        // Update project title
        const titleElement = document.querySelector('h1');
        if (titleElement && projectData.name) {
            titleElement.textContent = projectData.name;
        }
        
        // Update project description
        const descriptionElement = document.querySelector('.text-gray-400.text-lg');
        if (descriptionElement && projectData.description) {
            descriptionElement.textContent = projectData.description;
        }
        
        // Add visual feedback for project update
        const projectHeader = document.querySelector('.max-w-7xl');
        if (projectHeader) {
            projectHeader.style.backgroundColor = 'rgba(34, 197, 94, 0.1)';
            setTimeout(() => {
                projectHeader.style.backgroundColor = '';
            }, 2000);
        }
    }
    
    createTaskElement(taskData) {
        const taskElement = document.createElement('div');
        taskElement.className = 'task-item px-6 py-4 hover:bg-gray-800/30 transition-colors duration-200';
        taskElement.dataset.taskId = taskData.id;
        taskElement.dataset.parentId = taskData.parent_id || '';
        taskElement.dataset.sortOrder = taskData.sort_order || 0;
        taskElement.dataset.riskLevel = taskData.risk_level;
        
        const statusIconClass = this.getStatusIconClass(taskData.status);
        const priorityBadgeClass = this.getPriorityBadgeClass(taskData.priority);
        
        taskElement.innerHTML = `
            <div class="flex items-center justify-between">
                <div class="flex items-center space-x-4">
                    <div class="drag-handle cursor-move text-gray-500 hover:text-gray-300" style="display: none;">
                        <i class="fas fa-grip-vertical"></i>
                    </div>
                    <div class="w-4"></div>
                    <div class="flex-shrink-0">
                        <i class="${statusIconClass}"></i>
                    </div>
                    <div class="flex-1">
                        <div class="flex items-center space-x-2">
                            <h3 class="text-lg font-medium text-white">
                                <a href="/projects/${this.projectId}/tasks/${taskData.id}/edit"
                                   class="hover:text-blue-400 transition-colors duration-200">
                                    ${taskData.title}
                                </a>
                            </h3>
                        </div>
                        ${taskData.description ? `<p class="text-gray-400 mt-1">${taskData.description.length > 100 ? taskData.description.substring(0, 100) + '...' : taskData.description}</p>` : ''}
                        <div class="flex items-center space-x-4 mt-3 text-sm">
                            <span class="${priorityBadgeClass}">
                                ${taskData.priority.charAt(0).toUpperCase() + taskData.priority.slice(1)}
                            </span>
                            <span class="text-gray-500">${taskData.owner_name}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        return taskElement;
    }
    
    getStatusIconClass(status) {
        const iconClasses = {
            'completed': 'fas fa-check-circle text-green-400 text-xl',
            'in_progress': 'fas fa-play-circle text-blue-400 text-xl',
            'blocked': 'fas fa-exclamation-circle text-red-400 text-xl',
            'default': 'fas fa-circle text-gray-500 text-xl'
        };
        
        return iconClasses[status] || iconClasses.default;
    }
    
    getPriorityBadgeClass(priority) {
        const badgeClasses = {
            'high': 'inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-red-500/20 text-red-400',
            'medium': 'inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-yellow-500/20 text-yellow-400',
            'low': 'inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-500/20 text-green-400'
        };
        
        return badgeClasses[priority] || badgeClasses.medium;
    }
    
    detectConflict(taskId, updateTimestamp) {
        const lastTimestamp = this.lastUpdateTimestamp.get(taskId);
        if (!lastTimestamp) return false;
        
        // Simple timestamp comparison for conflict detection
        return new Date(updateTimestamp) < new Date(lastTimestamp);
    }
    
    handleConflict(taskData, user, updateType) {
        // Show conflict resolution dialog
        const conflictId = `conflict_${taskData.id}_${Date.now()}`;
        this.conflictResolution.set(conflictId, {
            taskData,
            user,
            updateType,
            timestamp: Date.now()
        });
        
        this.showConflictDialog(conflictId, taskData, user, updateType);
    }
    
    showConflictDialog(conflictId, taskData, user, updateType) {
        const dialog = document.createElement('div');
        dialog.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        dialog.innerHTML = `
            <div class="bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
                <h3 class="text-lg font-semibold text-white mb-4">
                    <i class="fas fa-exclamation-triangle text-yellow-400 mr-2"></i>
                    Conflict Detected
                </h3>
                <p class="text-gray-300 mb-4">
                    ${user.name} ${this.getUpdateActionText(updateType)} task "${taskData.title}" 
                    but you may have newer changes. What would you like to do?
                </p>
                <div class="flex space-x-3">
                    <button onclick="projectRealtime.resolveConflict('${conflictId}', 'accept')"
                            class="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg">
                        Accept Their Changes
                    </button>
                    <button onclick="projectRealtime.resolveConflict('${conflictId}', 'reject')"
                            class="flex-1 bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-lg">
                        Keep My Changes
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(dialog);
        
        // Auto-resolve after 10 seconds
        setTimeout(() => {
            if (document.body.contains(dialog)) {
                this.resolveConflict(conflictId, 'accept');
            }
        }, 10000);
    }
    
    resolveConflict(conflictId, resolution) {
        const conflict = this.conflictResolution.get(conflictId);
        if (!conflict) return;
        
        // Remove dialog
        const dialog = document.querySelector('.fixed.inset-0');
        if (dialog) {
            dialog.remove();
        }
        
        if (resolution === 'accept') {
            // Apply the conflicted update
            const { taskData, user, updateType } = conflict;
            this.lastUpdateTimestamp.set(taskData.id, taskData.updated_at);
            
            switch (updateType) {
                case 'task_create':
                    this.addTaskToUI(taskData, user);
                    break;
                case 'task_update':
                    this.updateTaskInUI(taskData, user);
                    break;
                case 'task_delete':
                    this.removeTaskFromUI(taskData, user);
                    break;
            }
            
            this.showNotification('Conflict resolved: Applied remote changes', 'success');
        } else {
            this.showNotification('Conflict resolved: Kept local changes', 'info');
        }
        
        this.conflictResolution.delete(conflictId);
    }
    
    updateActiveUsers(users) {
        const activeUsersElement = document.getElementById('active-users');
        const activeUserCountElement = document.getElementById('active-user-count');
        
        if (activeUserCountElement) {
            activeUserCountElement.textContent = users.length;
        }
        
        if (!activeUsersElement) return;
        
        activeUsersElement.innerHTML = '';
        
        users.forEach(user => {
            const userElement = document.createElement('div');
            userElement.className = 'active-user flex items-center space-x-1';
            userElement.innerHTML = `
                <img src="${user.avatar_url || '/static/images/default-avatar.png'}" 
                     alt="${user.name}" 
                     class="w-8 h-8 rounded-full border-2 border-green-400"
                     title="${user.name}">
            `;
            activeUsersElement.appendChild(userElement);
        });
    }
    
    updateTaskCount() {
        const taskCountElement = document.getElementById('task-count');
        if (taskCountElement) {
            const taskElements = document.querySelectorAll('.task-item');
            taskCountElement.textContent = taskElements.length;
        }
    }
    
    getUpdateActionText(updateType) {
        const actions = {
            'task_create': 'created',
            'task_update': 'updated',
            'task_delete': 'deleted'
        };
        
        return actions[updateType] || 'modified';
    }
    
    showNotification(message, type = 'info') {
        // Use the global notification system
        return window.notifications.show(message, type, 5000);
    }
    
    // Public methods for external use
    sendTaskUpdate(taskData, updateType = 'task_update') {
        if (this.wsClient && this.isInitialized) {
            this.wsClient.sendTaskUpdate(this.projectId, taskData, updateType);
        }
    }
    
    sendProjectUpdate(projectData, updateType = 'project_update') {
        if (this.wsClient && this.isInitialized) {
            this.wsClient.sendProjectUpdate(this.projectId, projectData, updateType);
        }
    }
    
    disconnect() {
        if (this.wsClient) {
            this.wsClient.leaveProject();
            this.wsClient.disconnect();
        }
    }
}

// Global instance
let projectRealtime = null;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const projectElement = document.querySelector('[data-project-id]');
    if (projectElement) {
        const projectId = parseInt(projectElement.dataset.projectId);
        window.currentUserId = parseInt(document.body.dataset.userId || '0');
        
        projectRealtime = new ProjectRealtimeManager(projectId);
        
        // Make it globally accessible
        window.projectRealtime = projectRealtime;
    }
});

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    if (projectRealtime) {
        projectRealtime.disconnect();
    }
});

// Override global functions for compatibility
window.updateTaskInUI = function(taskData, user) {
    if (projectRealtime) {
        projectRealtime.handleTaskUpdate(taskData, user);
    }
};

window.updateProjectInUI = function(projectData, user) {
    if (projectRealtime) {
        projectRealtime.handleProjectUpdate(projectData, user);
    }
};