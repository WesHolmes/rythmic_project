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
        this.maxReconnectAttempts = 2; // Further reduced
        this.reconnectDelay = 5000; // Much longer initial delay
        this.lastSyncTimestamp = null;
        this.connectionState = 'disconnected'; // disconnected, connecting, connected, error
        this.pageVisibilityHandler = null;
        this.focusHandler = null;
        
        // Debouncing for connection attempts
        this.connectionDebounceTimer = null;
        this.lastConnectionAttempt = 0;
        this.minConnectionInterval = 10000; // Minimum 10 seconds between connection attempts
        
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
        
        // Set up page visibility and focus handlers for immediate reconnection
        this.setupPageVisibilityHandlers();
    }
    
    /**
     * Set up page visibility and focus handlers for reconnection
     */
    setupPageVisibilityHandlers() {
        // Handle page visibility changes (tab switching, minimizing)
        this.pageVisibilityHandler = () => {
            if (!document.hidden && this.shouldBeConnected()) {
                // Debounce visibility change reconnections
                this.debouncedEnsureConnection();
            }
        };
        
        // Handle window focus (returning to the page) - only if visibility change didn't already handle it
        this.focusHandler = () => {
            if (this.shouldBeConnected() && !document.hidden) {
                // Only trigger if visibility change didn't already handle it
                setTimeout(() => {
                    if (this.shouldBeConnected() && !document.hidden) {
                        this.debouncedEnsureConnection();
                    }
                }, 100);
            }
        };
        
        document.addEventListener('visibilitychange', this.pageVisibilityHandler);
        window.addEventListener('focus', this.focusHandler);
    }
    
    /**
     * Clean up resources and disconnect
     */
    destroy() {
        // Clear debounce timer
        if (this.connectionDebounceTimer) {
            clearTimeout(this.connectionDebounceTimer);
            this.connectionDebounceTimer = null;
        }
        
        // Remove event listeners
        if (this.pageVisibilityHandler) {
            document.removeEventListener('visibilitychange', this.pageVisibilityHandler);
            this.pageVisibilityHandler = null;
        }
        
        if (this.focusHandler) {
            window.removeEventListener('focus', this.focusHandler);
            this.focusHandler = null;
        }
        
        // Disconnect socket
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
        
        // Reset state
        this.isConnected = false;
        this.connectionState = 'disconnected';
        this.currentProjectId = null;
    }
    
    /**
     * Check if WebSocket should be connected based on current page
     */
    shouldBeConnected() {
        const isProjectPage = window.location.pathname.includes('/projects/');
        const isSharingPage = window.location.pathname.includes('/sharing/');
        return isProjectPage || isSharingPage;
    }
    
    /**
     * Debounced version of ensureConnection to prevent rapid reconnection attempts
     */
    debouncedEnsureConnection() {
        // Clear existing timer
        if (this.connectionDebounceTimer) {
            clearTimeout(this.connectionDebounceTimer);
        }
        
        // Check if we've attempted connection too recently
        const now = Date.now();
        if (now - this.lastConnectionAttempt < this.minConnectionInterval) {
            console.log('Connection attempt too recent, debouncing...');
            this.connectionDebounceTimer = setTimeout(() => {
                this.ensureConnection();
            }, this.minConnectionInterval - (now - this.lastConnectionAttempt));
            return;
        }
        
        // Proceed with connection attempt
        this.ensureConnection();
    }
    
    /**
     * Ensure WebSocket connection is active when it should be
     */
    ensureConnection() {
        if (!this.shouldBeConnected()) {
            console.log('WebSocket not needed for current page');
            return;
        }
        
        // Update last connection attempt time
        this.lastConnectionAttempt = Date.now();
        
        console.log(`Ensuring WebSocket connection - Current state: ${this.connectionState}, Connected: ${this.isWebSocketConnected()}`);
        
        // Only reconnect if we're not already connecting or connected
        if (this.connectionState === 'connecting') {
            console.log('Already connecting, skipping...');
            return;
        }
        
        // If not connected or connection is stale, reconnect
        if (!this.isWebSocketConnected() || this.connectionState === 'error') {
            console.log('WebSocket needs reconnection...');
            this.forceReconnect();
            return;
        }
        
        // If we have a project ID but haven't joined, join it
        const projectIdMatch = window.location.pathname.match(/\/projects\/(\d+)/);
        if (projectIdMatch) {
            const projectId = parseInt(projectIdMatch[1]);
            if (this.currentProjectId !== projectId) {
                console.log(`Switching to project ${projectId} from ${this.currentProjectId}`);
                this.switchProject(projectId);
            } else if (this.isWebSocketConnected() && this.currentProjectId === projectId) {
                console.log(`Already connected to project ${projectId}`);
            }
        }
    }
    
    /**
     * Force reconnection with proper state management
     */
    forceReconnect() {
        // Don't force reconnect if already connecting
        if (this.connectionState === 'connecting') {
            console.log('Already connecting, skipping force reconnect...');
            return;
        }
        
        console.log('Force reconnecting WebSocket...');
        this.connectionState = 'connecting';
        this.reconnectAttempts = 0; // Reset attempts for immediate reconnection
        this.reconnectDelay = 2000; // Reset delay
        
        // Show connecting status
        if (this.onDisconnected) {
            this.onDisconnected('force_reconnect');
        }
        
        if (this.socket) {
            this.socket.disconnect();
        }
        
        // Connect with a small delay to allow cleanup
        setTimeout(() => {
            if (this.shouldBeConnected()) {
                this.connect();
            }
        }, 500);
    }
    
    /**
     * Switch to a different project
     */
    switchProject(newProjectId) {
        if (this.currentProjectId && this.currentProjectId !== newProjectId) {
            this.leaveProject();
        }
        
        this.currentProjectId = newProjectId;
        
        if (this.isWebSocketConnected()) {
            this.joinProject(newProjectId);
        }
    }
    
    /**
     * Initialize WebSocket connection
     */
    connect() {
        try {
            // Check if Socket.IO is available
            if (typeof io === 'undefined') {
                console.warn('Socket.IO not available, real-time features disabled');
                this.connectionState = 'error';
                return;
            }
            
            this.connectionState = 'connecting';
            
            // Initialize Socket.IO connection with Azure-optimized settings
            this.socket = io({
                transports: ['polling', 'websocket'], // Start with polling for Azure compatibility
                upgrade: true,
                rememberUpgrade: false, // Don't remember upgrade on Azure
                timeout: 15000, // Longer timeout for Azure
                forceNew: false, // Don't force new connections unless necessary
                reconnection: true,
                reconnectionAttempts: 3, // Reduced attempts
                reconnectionDelay: 3000, // Longer initial delay
                reconnectionDelayMax: 15000, // Longer max delay
                maxReconnectionAttempts: 3,
                pingTimeout: 60000,
                pingInterval: 25000,
                autoConnect: true
            });
            
            this.setupEventHandlers();
            
        } catch (error) {
            console.error('Failed to initialize WebSocket connection:', error);
            this.connectionState = 'error';
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
            this.connectionState = 'connected';
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;
            
            if (this.onConnected) {
                this.onConnected();
            }
            
            // Auto-rejoin project if we were in one or detect current project
            const projectIdMatch = window.location.pathname.match(/\/projects\/(\d+)/);
            if (projectIdMatch) {
                const projectId = parseInt(projectIdMatch[1]);
                this.currentProjectId = projectId;
                this.joinProject(projectId);
                
                // Synchronize state after reconnection
                setTimeout(() => {
                    this.synchronizeState();
                }, 500); // Reduced delay for faster sync
            }
        });
        
        this.socket.on('disconnect', (reason) => {
            console.log('WebSocket disconnected:', reason);
            this.isConnected = false;
            this.connectionState = 'disconnected';
            
            if (this.onDisconnected) {
                this.onDisconnected(reason);
            }
            
            // Only reconnect for certain disconnect reasons and with much longer delays
            if (reason === 'io server disconnect') {
                // Server initiated disconnect, wait much longer before reconnecting
                setTimeout(() => {
                    if (this.shouldBeConnected()) {
                        this.attemptReconnect();
                    }
                }, 15000); // 15 seconds
                return;
            }
            
            // For other disconnections, wait much longer before reconnecting
            if (this.shouldBeConnected() && reason !== 'io client disconnect') {
                setTimeout(() => {
                    if (this.shouldBeConnected()) {
                        this.attemptReconnect();
                    }
                }, 10000); // 10 seconds
            }
        });
        
        this.socket.on('connect_error', (error) => {
            console.error('WebSocket connection error:', error);
            this.connectionState = 'error';
            
            if (this.onError) {
                this.onError('connection_error', error.message);
            }
            
            // For 400 errors, wait much longer before retrying and try different transport
            if (error.message && (error.message.includes('400') || error.message.includes('Bad Request'))) {
                console.log('Received 400 error, waiting much longer before retry...');
                setTimeout(() => {
                    if (this.shouldBeConnected()) {
                        // Try with polling only for 400 errors
                        this.connectWithPollingOnly();
                    }
                }, 20000); // Much longer delay for 400 errors
            } else if (this.shouldBeConnected()) {
                // Wait much longer before attempting reconnection for other errors
                setTimeout(() => {
                    if (this.shouldBeConnected()) {
                        this.attemptReconnect();
                    }
                }, 15000); // Much longer delay
            }
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
        // Don't reconnect if we shouldn't be connected
        if (!this.shouldBeConnected()) {
            return;
        }
        
        // Don't reconnect if already connecting
        if (this.connectionState === 'connecting') {
            console.log('Already connecting, skipping reconnect attempt...');
            return;
        }
        
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            this.connectionState = 'error';
            if (this.onError) {
                this.onError('max_reconnect_attempts', 'Failed to reconnect after maximum attempts');
            }
            
            // Reset attempts after a much longer delay to allow for manual retry
            setTimeout(() => {
                this.reconnectAttempts = 0;
                this.reconnectDelay = 5000;
            }, 300000); // Reset after 5 minutes
            return;
        }
        
        this.reconnectAttempts++;
        this.connectionState = 'connecting';
        
        console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${this.reconnectDelay}ms...`);
        
        setTimeout(() => {
            if (this.shouldBeConnected() && this.connectionState === 'connecting') { // Double-check before reconnecting
                console.log(`Executing reconnect attempt ${this.reconnectAttempts}...`);
                if (this.socket) {
                    this.socket.connect();
                } else {
                    this.connect();
                }
            }
        }, this.reconnectDelay);
        
        // Exponential backoff, but cap at 60 seconds for much better stability
        this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, 60000);
    }
    
    /**
     * Connect using polling only (for 400 error recovery)
     */
    connectWithPollingOnly() {
        // Don't attempt if already connecting
        if (this.connectionState === 'connecting') {
            console.log('Already connecting, skipping polling-only attempt...');
            return;
        }
        
        try {
            console.log('Attempting connection with polling only...');
            this.connectionState = 'connecting';
            
            // Disconnect existing socket if any
            if (this.socket) {
                this.socket.disconnect();
            }
            
            // Initialize Socket.IO connection with polling only
            this.socket = io({
                transports: ['polling'], // Only polling
                upgrade: false, // Disable upgrade to websocket
                timeout: 20000, // Longer timeout
                forceNew: false, // Don't force new connection
                reconnection: true,
                reconnectionAttempts: 2, // Reduced attempts for polling
                reconnectionDelay: 5000, // Longer delay for polling
                reconnectionDelayMax: 20000,
                pingTimeout: 60000,
                pingInterval: 30000 // Longer ping interval for polling
            });
            
            this.setupEventHandlers();
            
        } catch (error) {
            console.error('Failed to connect with polling only:', error);
            this.connectionState = 'error';
            if (this.onError) {
                this.onError('polling_connection_failed', error.message);
            }
        }
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
        // Stop health monitoring
        this.stopHealthMonitoring();
        
        // Clean up event listeners
        if (this.pageVisibilityHandler) {
            document.removeEventListener('visibilitychange', this.pageVisibilityHandler);
        }
        if (this.focusHandler) {
            window.removeEventListener('focus', this.focusHandler);
        }
        
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
        this.isConnected = false;
        this.connectionState = 'disconnected';
        this.currentProjectId = null;
    }
    
    /**
     * Check if WebSocket is connected
     * @returns {boolean}
     */
    isWebSocketConnected() {
        return this.isConnected && this.socket && this.socket.connected;
    }
    
    /**
     * Start connection health monitoring
     */
    startHealthMonitoring() {
        // Check connection health every 30 seconds
        this.healthCheckInterval = setInterval(() => {
            if (this.shouldBeConnected() && !this.isWebSocketConnected()) {
                console.log('Health check failed, attempting reconnection...');
                this.ensureConnection();
            }
        }, 30000);
    }
    
    /**
     * Stop connection health monitoring
     */
    stopHealthMonitoring() {
        if (this.healthCheckInterval) {
            clearInterval(this.healthCheckInterval);
            this.healthCheckInterval = null;
        }
    }
}

// Global WebSocket client instance
let wsClient = null;

/**
 * Initialize WebSocket client for the current page
 */
function initializeWebSocket() {
    if (wsClient) {
        // If client exists, ensure it's connected for the current page
        wsClient.ensureConnection();
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
    
    // Start health monitoring
    wsClient.startHealthMonitoring();
    
    return wsClient;
}

/**
 * Ensure WebSocket connection when navigating to project pages
 * Call this function when navigating to project pages programmatically
 */
function ensureWebSocketConnection() {
    if (wsClient) {
        wsClient.ensureConnection();
    } else {
        // Initialize if not already done
        const isProjectPage = window.location.pathname.includes('/projects/');
        const isSharingPage = window.location.pathname.includes('/sharing/');
        
        if (isProjectPage || isSharingPage) {
            initializeWebSocket();
        }
    }
}

/**
 * Global function to handle page navigation and WebSocket management
 */
function handlePageNavigation() {
    // This can be called by navigation handlers or SPA routers
    ensureWebSocketConnection();
}

/**
 * Show WebSocket connection status
 * @param {string} status - Connection status
 * @param {string} message - Optional message
 */
function showWebSocketStatus(status, message = '') {
    const statusElement = document.getElementById('websocket-status');
    const reconnectBtn = document.getElementById('manual-reconnect-btn');
    
    if (!statusElement) return;
    
    statusElement.className = `websocket-status ${status}`;
    
    switch (status) {
        case 'connected':
            statusElement.textContent = '🟢 Real-time updates active';
            if (reconnectBtn) reconnectBtn.style.display = 'none';
            break;
        case 'disconnected':
            statusElement.textContent = '🔴 Real-time updates disconnected';
            if (reconnectBtn) reconnectBtn.style.display = 'inline-block';
            break;
        case 'error':
            statusElement.textContent = `⚠️ Connection error: ${message}`;
            if (reconnectBtn) reconnectBtn.style.display = 'inline-block';
            break;
        case 'project_joined':
            statusElement.textContent = '🟢 Joined project for real-time updates';
            if (reconnectBtn) reconnectBtn.style.display = 'none';
            break;
        case 'connecting':
            statusElement.textContent = '🔄 Connecting to real-time updates...';
            if (reconnectBtn) reconnectBtn.style.display = 'none';
            break;
        default:
            statusElement.textContent = status;
    }
    
    // Auto-hide status after successful connection to reduce UI clutter
    if (status === 'connected' || status === 'project_joined') {
        setTimeout(() => {
            if (statusElement.classList.contains('connected') || statusElement.classList.contains('project_joined')) {
                statusElement.style.opacity = '0.7';
                statusElement.style.fontSize = '0.75rem';
            }
        }, 3000);
    } else {
        // Reset opacity and font size for error states
        statusElement.style.opacity = '1';
        statusElement.style.fontSize = '';
    }
}

/**
 * Set up manual reconnect button
 */
function setupManualReconnectButton() {
    const reconnectBtn = document.getElementById('manual-reconnect-btn');
    if (reconnectBtn) {
        reconnectBtn.addEventListener('click', () => {
            console.log('Manual reconnect triggered');
            showWebSocketStatus('connecting');
            
            if (wsClient) {
                wsClient.forceReconnect();
            } else {
                initializeWebSocket();
            }
        });
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
    initializeWebSocketForCurrentPage();
});

// Handle page navigation (for SPAs or programmatic navigation)
window.addEventListener('popstate', () => {
    // Handle browser back/forward navigation
    setTimeout(() => {
        ensureWebSocketConnection();
    }, 100);
});

// Handle page focus to ensure connection when returning to tab
window.addEventListener('focus', () => {
    ensureWebSocketConnection();
});

// Initialize WebSocket for the current page
function initializeWebSocketForCurrentPage() {
    const isProjectPage = window.location.pathname.includes('/projects/');
    const isSharingPage = window.location.pathname.includes('/sharing/');
    
    if (isProjectPage || isSharingPage) {
        console.log('Initializing WebSocket for current page:', window.location.pathname);
        initializeWebSocket();
        
        // Set up manual reconnect button if on project page
        if (isProjectPage) {
            setupManualReconnectButton();
        }
    }
}

// Clean up WebSocket connection when page unloads
window.addEventListener('beforeunload', () => {
    if (wsClient) {
        // Don't fully disconnect on page unload - let the page visibility handler manage it
        // This allows for faster reconnection when returning to the page
        if (wsClient.currentProjectId) {
            wsClient.leaveProject();
        }
    }
});

// Handle page visibility changes for better connection management
document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
        // Page became visible, ensure connection
        setTimeout(() => {
            ensureWebSocketConnection();
        }, 100);
    }
});

// Expose global functions for manual connection management
window.ensureWebSocketConnection = ensureWebSocketConnection;
window.handlePageNavigation = handlePageNavigation;