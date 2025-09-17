/**
 * WebSocket client for real-time project collaboration
 * Handles connection, project joining, and real-time updates
 */

class ProjectWebSocketClient {
    constructor() {
        this.socket = null;
        this.currentProjectId = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // Start with 1 second
        
        // Event callbacks
        this.onConnected = null;
        this.onDisconnected = null;
        this.onProjectJoined = null;
        this.onProjectLeft = null;
        this.onTaskUpdate = null;
        this.onProjectUpdate = null;
        this.onActiveUsersUpdate = null;
        this.onUserConnected = null;
        this.onUserDisconnected = null;
        this.onError = null;
    }
    
    /**
     * Initialize WebSocket connection
     */
    connect() {
        try {
            // Check if Socket.IO is available
            if (typeof io === 'undefined') {
                console.warn('Socket.IO not available, real-time features disabled');
                return;
            }
            
            // Initialize Socket.IO connection
            this.socket = io({
                transports: ['websocket', 'polling'], // Fallback to polling for Azure compatibility
                upgrade: true,
                rememberUpgrade: true
            });
            
            this.setupEventHandlers();
            
        } catch (error) {
            console.error('Failed to initialize WebSocket connection:', error);
            if (this.onError) {
                this.onError('connection_failed', error.message);
            }
        }
    }
    
    /**
     * Set up Socket.IO event handlers
     */
    setupEventHandlers() {
        // Connection events
        this.socket.on('connect', () => {
            console.log('WebSocket connected');
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;
            
            if (this.onConnected) {
                this.onConnected();
            }
            
            // Auto-rejoin project if we were in one
            if (this.currentProjectId) {
                this.joinProject(this.currentProjectId);
                // Synchronize state after reconnection
                setTimeout(() => {
                    this.synchronizeState();
                }, 1000);
            }
        });
        
        this.socket.on('disconnect', (reason) => {
            console.log('WebSocket disconnected:', reason);
            this.isConnected = false;
            
            if (this.onDisconnected) {
                this.onDisconnected(reason);
            }
            
            // Auto-reconnect for certain disconnect reasons
            if (reason === 'io server disconnect') {
                // Server initiated disconnect, don't reconnect
                return;
            }
            
            this.attemptReconnect();
        });
        
        this.socket.on('connect_error', (error) => {
            console.error('WebSocket connection error:', error);
            if (this.onError) {
                this.onError('connection_error', error.message);
            }
            
            this.attemptReconnect();
        });
        
        // Project events
        this.socket.on('joined_project', (data) => {
            console.log('Joined project:', data);
            if (this.onProjectJoined) {
                this.onProjectJoined(data);
            }
        });
        
        this.socket.on('left_project', (data) => {
            console.log('Left project:', data);
            this.currentProjectId = null;
            if (this.onProjectLeft) {
                this.onProjectLeft(data);
            }
        });
        
        // Real-time update events
        this.socket.on('project_update', (data) => {
            console.log('Project update received:', data);
            
            switch (data.type) {
                case 'task_update':
                    if (this.onTaskUpdate) {
                        this.onTaskUpdate(data.data, data.user);
                    }
                    break;
                    
                case 'project_update':
                    if (this.onProjectUpdate) {
                        this.onProjectUpdate(data.data, data.user);
                    }
                    break;
                    
                case 'user_connected':
                    if (this.onUserConnected) {
                        this.onUserConnected(data.data);
                    }
                    break;
                    
                case 'user_disconnected':
                    if (this.onUserDisconnected) {
                        this.onUserDisconnected(data.data);
                    }
                    break;
            }
        });
        
        this.socket.on('active_users', (data) => {
            console.log('Active users update:', data);
            if (this.onActiveUsersUpdate) {
                this.onActiveUsersUpdate(data.users);
            }
        });
        
        this.socket.on('direct_message', (data) => {
            console.log('Direct message received:', data);
            // Handle direct messages (notifications, etc.)
        });
        
        this.socket.on('error', (data) => {
            console.error('WebSocket error:', data);
            if (this.onError) {
                this.onError('server_error', data.message);
            }
        });
    }
    
    /**
     * Attempt to reconnect with exponential backoff
     */
    attemptReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            if (this.onError) {
                this.onError('max_reconnect_attempts', 'Failed to reconnect after maximum attempts');
            }
            return;
        }
        
        this.reconnectAttempts++;
        
        setTimeout(() => {
            console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            this.socket.connect();
        }, this.reconnectDelay);
        
        // Exponential backoff
        this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000); // Max 30 seconds
    }
    
    /**
     * Synchronize state after reconnection
     */
    synchronizeState() {
        if (!this.isConnected || !this.currentProjectId) {
            return;
        }
        
        // Request current active users
        this.requestActiveUsers();
        
        // Request any missed updates (this would need server-side support)
        this.socket.emit('sync_state', {
            project_id: this.currentProjectId,
            last_sync: this.lastSyncTimestamp || new Date().toISOString()
        });
        
        this.lastSyncTimestamp = new Date().toISOString();
    }
    
    /**
     * Join a project room for real-time updates
     * @param {number} projectId - The project ID to join
     */
    joinProject(projectId) {
        if (!this.isConnected) {
            console.warn('Cannot join project: WebSocket not connected');
            return;
        }
        
        this.currentProjectId = projectId;
        this.socket.emit('join_project', { project_id: projectId });
    }
    
    /**
     * Leave the current project room
     */
    leaveProject() {
        if (!this.isConnected || !this.currentProjectId) {
            return;
        }
        
        this.socket.emit('leave_project', { project_id: this.currentProjectId });
        this.currentProjectId = null;
    }
    
    /**
     * Send a task update to other collaborators
     * @param {number} projectId - The project ID
     * @param {object} taskData - The task data
     * @param {string} updateType - Type of update (task_create, task_update, task_delete)
     */
    sendTaskUpdate(projectId, taskData, updateType = 'task_update') {
        if (!this.isConnected) {
            console.warn('Cannot send task update: WebSocket not connected');
            return;
        }
        
        this.socket.emit('task_update', {
            project_id: projectId,
            task_data: taskData,
            update_type: updateType
        });
    }
    
    /**
     * Send a project update to other collaborators
     * @param {number} projectId - The project ID
     * @param {object} projectData - The project data
     * @param {string} updateType - Type of update
     */
    sendProjectUpdate(projectId, projectData, updateType = 'project_update') {
        if (!this.isConnected) {
            console.warn('Cannot send project update: WebSocket not connected');
            return;
        }
        
        this.socket.emit('project_update', {
            project_id: projectId,
            project_data: projectData,
            update_type: updateType
        });
    }
    
    /**
     * Request active users for the current project
     */
    requestActiveUsers() {
        if (!this.isConnected || !this.currentProjectId) {
            return;
        }
        
        this.socket.emit('get_active_users', { project_id: this.currentProjectId });
    }
    
    /**
     * Disconnect from WebSocket
     */
    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
        this.isConnected = false;
        this.currentProjectId = null;
    }
    
    /**
     * Check if WebSocket is connected
     * @returns {boolean}
     */
    isWebSocketConnected() {
        return this.isConnected && this.socket && this.socket.connected;
    }
}

// Global WebSocket client instance
let wsClient = null;

/**
 * Initialize WebSocket client for the current page
 */
function initializeWebSocket() {
    if (wsClient) {
        return wsClient;
    }
    
    // Check if Socket.IO is available
    if (typeof io === 'undefined') {
        console.warn('Socket.IO not available, WebSocket features disabled');
        return null;
    }
    
    wsClient = new ProjectWebSocketClient();
    
    // Set up event handlers
    wsClient.onConnected = () => {
        console.log('WebSocket client connected');
        showWebSocketStatus('connected');
    };
    
    wsClient.onDisconnected = (reason) => {
        console.log('WebSocket client disconnected:', reason);
        showWebSocketStatus('disconnected');
    };
    
    wsClient.onError = (type, message) => {
        console.error('WebSocket error:', type, message);
        showWebSocketStatus('error', message);
    };
    
    wsClient.onProjectJoined = (data) => {
        console.log('Successfully joined project:', data.project_id);
        showWebSocketStatus('project_joined');
    };
    
    wsClient.onTaskUpdate = (taskData, user) => {
        console.log('Task update from', user.name, ':', taskData);
        handleTaskUpdate(taskData, user);
    };
    
    wsClient.onProjectUpdate = (projectData, user) => {
        console.log('Project update from', user.name, ':', projectData);
        handleProjectUpdate(projectData, user);
    };
    
    wsClient.onActiveUsersUpdate = (users) => {
        console.log('Active users:', users);
        updateActiveUsersList(users);
    };
    
    wsClient.onUserConnected = (userData) => {
        console.log('User connected:', userData.user_name);
        showUserNotification(`${userData.user_name} joined the project`, 'info');
    };
    
    wsClient.onUserDisconnected = (userData) => {
        console.log('User disconnected:', userData.user_name);
        showUserNotification(`${userData.user_name} left the project`, 'info');
    };
    
    // Connect to WebSocket
    wsClient.connect();
    
    return wsClient;
}

/**
 * Show WebSocket connection status
 * @param {string} status - Connection status
 * @param {string} message - Optional message
 */
function showWebSocketStatus(status, message = '') {
    const statusElement = document.getElementById('websocket-status');
    if (!statusElement) return;
    
    statusElement.className = `websocket-status ${status}`;
    
    switch (status) {
        case 'connected':
            statusElement.textContent = '🟢 Real-time updates active';
            break;
        case 'disconnected':
            statusElement.textContent = '🔴 Real-time updates disconnected';
            break;
        case 'error':
            statusElement.textContent = `⚠️ Connection error: ${message}`;
            break;
        case 'project_joined':
            statusElement.textContent = '🟢 Joined project for real-time updates';
            break;
        default:
            statusElement.textContent = status;
    }
}

/**
 * Handle incoming task updates
 * @param {object} taskData - Task data
 * @param {object} user - User who made the update
 */
function handleTaskUpdate(taskData, user) {
    // This function should be implemented by the specific page
    // to handle task updates in the UI
    if (typeof updateTaskInUI === 'function') {
        updateTaskInUI(taskData, user);
    }
}

/**
 * Handle incoming project updates
 * @param {object} projectData - Project data
 * @param {object} user - User who made the update
 */
function handleProjectUpdate(projectData, user) {
    // This function should be implemented by the specific page
    // to handle project updates in the UI
    if (typeof updateProjectInUI === 'function') {
        updateProjectInUI(projectData, user);
    }
}

/**
 * Update active users list in the UI
 * @param {Array} users - List of active users
 */
function updateActiveUsersList(users) {
    const activeUsersElement = document.getElementById('active-users');
    const activeUserCountElement = document.getElementById('active-user-count');
    
    if (activeUserCountElement) {
        activeUserCountElement.textContent = users.length;
    }
    
    if (!activeUsersElement) return;
    
    activeUsersElement.innerHTML = '';
    
    users.forEach(user => {
        const userElement = document.createElement('div');
        userElement.className = 'active-user';
        userElement.innerHTML = `
            <img src="${user.avatar_url || '/static/images/default-avatar.png'}" 
                 alt="${user.name}" class="user-avatar">
            <span class="user-name">${user.name}</span>
        `;
        activeUsersElement.appendChild(userElement);
    });
}

/**
 * Show user notification
 * @param {string} message - Notification message
 * @param {string} type - Notification type (info, success, warning, error)
 */
function showUserNotification(message, type = 'info') {
    // Use the global notification system
    return window.notifications.show(message, type, 5000);
}

// Auto-initialize WebSocket when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize if we're on a project page
    if (window.location.pathname.includes('/projects/')) {
        initializeWebSocket();
        
        // Join project if we're on a project detail page
        const projectIdMatch = window.location.pathname.match(/\/projects\/(\d+)/);
        if (projectIdMatch && wsClient) {
            const projectId = parseInt(projectIdMatch[1]);
            
            // Wait for connection before joining
            const joinWhenConnected = () => {
                if (wsClient.isWebSocketConnected()) {
                    wsClient.joinProject(projectId);
                } else {
                    setTimeout(joinWhenConnected, 100);
                }
            };
            
            joinWhenConnected();
        }
    }
});

// Clean up WebSocket connection when page unloads
window.addEventListener('beforeunload', () => {
    if (wsClient) {
        wsClient.disconnect();
    }
});