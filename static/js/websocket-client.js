/**
 * Simplified WebSocket client for project sharing and active user count
 * Only connects on page load and requests active users once
 */

class ProjectWebSocketClient {
    constructor() {
        this.socket = null;
        this.currentProjectId = null;
        this.isConnected = false;
        this.isAzure = this.detectAzureEnvironment();
        this.connectionState = 'disconnected'; // disconnected, connecting, connected, error
        this.hasRequestedActiveUsers = false; // Track if we've already requested active users
        
        // Event callbacks - simplified
        this.onConnected = null;
        this.onDisconnected = null;
        this.onProjectJoined = null;
        this.onProjectLeft = null;
        this.onActiveUsersUpdate = null;
        this.onUserConnected = null;
        this.onUserDisconnected = null;
        this.onError = null;
    }
    
    /**
     * Detect if running on Azure App Service
     */
    detectAzureEnvironment() {
        // Check for Azure-specific indicators
        const hostname = window.location.hostname;
        const isAzureDomain = hostname.includes('azurewebsites.net') || 
                             hostname.includes('azure.com') ||
                             hostname.includes('canadacentral-01');
        
        // Check for Azure-specific meta tags or data attributes
        const azureMeta = document.querySelector('meta[name="azure-environment"]');
        const isAzureMeta = azureMeta && azureMeta.content === 'true';
        
        // Check for Azure-specific environment variables (if exposed)
        const isAzureEnv = window.AZURE_ENVIRONMENT === true;
        
        const isAzure = isAzureDomain || isAzureMeta || isAzureEnv;
        console.log('Environment detection:', { hostname, isAzureDomain, isAzureMeta, isAzureEnv, isAzure });
        
        return isAzure;
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
     * Clean up resources and disconnect
     */
    destroy() {
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
     * Initialize WebSocket connection - ultra-simplified version
     */
    connect() {
        try {
            // Check if Socket.IO is available
            if (typeof io === 'undefined') {
                console.warn('Socket.IO not available, sharing features disabled');
                this.connectionState = 'error';
                return;
            }
            
            // Prevent multiple simultaneous connections
            if (this.connectionState === 'connecting' || this.connectionState === 'connected') {
                console.log('Connection already in progress or established, skipping...');
                return;
            }
            
            // Check if we already have a socket
            if (this.socket) {
                console.log('Socket already exists, skipping connection...');
                return;
            }
            
            this.connectionState = 'connecting';
            
            // Ultra-simple Socket.IO connection configuration - no reconnection at all
            const config = {
                transports: ['polling'], // Only polling to avoid WebSocket issues
                upgrade: false, // Disable WebSocket upgrade
                timeout: 5000, // Shorter timeout
                reconnection: false, // Absolutely no reconnection
                reconnectionAttempts: 0, // No attempts
                reconnectionDelay: 0, // No delay
                reconnectionDelayMax: 0, // No max delay
                autoConnect: true
            };
            
            console.log('Connecting to WebSocket for sharing features (polling only)...');
            this.socket = io(config);
            
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
     * Set up Socket.IO event handlers - simplified for sharing only
     */
    setupEventHandlers() {
        // Connection events
        this.socket.on('connect', () => {
            console.log('WebSocket connected for sharing features');
            this.isConnected = true;
            this.connectionState = 'connected';
            
            if (this.onConnected) {
                this.onConnected();
            }
            
            // Auto-join project if we're on a project page
            const projectIdMatch = window.location.pathname.match(/\/projects\/(\d+)/);
            if (projectIdMatch) {
                const projectId = parseInt(projectIdMatch[1]);
                this.currentProjectId = projectId;
                this.joinProject(projectId);
                
                // Request active users once after joining
                setTimeout(() => {
                    this.requestActiveUsers();
                }, 1000);
            }
        });
        
        this.socket.on('disconnect', (reason) => {
            console.log('WebSocket disconnected:', reason);
            this.isConnected = false;
            this.connectionState = 'disconnected';
            
            if (this.onDisconnected) {
                this.onDisconnected(reason);
            }
        });
        
        this.socket.on('connect_error', (error) => {
            console.error('WebSocket connection error:', error);
            this.connectionState = 'error';
            
            if (this.onError) {
                this.onError('connection_error', error.message);
            }
        });
        
        // Project events
        this.socket.on('joined_project', (data) => {
            console.log('Joined project for sharing:', data);
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
        
        // Active users events
        this.socket.on('active_users', (data) => {
            console.log('Active users update:', data);
            if (this.onActiveUsersUpdate) {
                this.onActiveUsersUpdate(data.users);
            }
        });
        
        // User join/leave events for sharing
        this.socket.on('user_connected', (data) => {
            console.log('User connected:', data);
            if (this.onUserConnected) {
                this.onUserConnected(data);
            }
            // Request updated active users list
            this.requestActiveUsers();
        });
        
        this.socket.on('user_disconnected', (data) => {
            console.log('User disconnected:', data);
            if (this.onUserDisconnected) {
                this.onUserDisconnected(data);
            }
            // Request updated active users list
            this.requestActiveUsers();
        });
        
        this.socket.on('error', (data) => {
            console.error('WebSocket error:', data);
            if (this.onError) {
                this.onError('server_error', data.message);
            }
        });
    }
    
    /**
     * Join a project room for sharing features
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
     * Request active users for the current project
     */
    requestActiveUsers() {
        if (!this.isConnected || !this.currentProjectId) {
            return;
        }
        
        // Only request once per connection to avoid spam
        if (this.hasRequestedActiveUsers) {
            return;
        }
        
        this.hasRequestedActiveUsers = true;
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
}

// Global WebSocket client instance
let wsClient = null;
let isInitializing = false; // Prevent multiple initializations

/**
 * Initialize WebSocket client for the current page - DISABLED to stop request flood
 */
function initializeWebSocket() {
    console.log('WebSocket functionality temporarily disabled to prevent request flood');
    return null;
}

/**
 * Simple function to initialize WebSocket if needed
 */
function ensureWebSocketConnection() {
    if (!wsClient) {
        initializeWebSocket();
    }
}

/**
 * Show WebSocket connection status - simplified for sharing only
 * @param {string} status - Connection status
 * @param {string} message - Optional message
 */
function showWebSocketStatus(status, message = '') {
    const statusElement = document.getElementById('websocket-status');
    
    if (!statusElement) return;
    
    statusElement.className = `websocket-status ${status}`;
    
    switch (status) {
        case 'connected':
            statusElement.textContent = '🟢 Connected';
            break;
        case 'disconnected':
            statusElement.textContent = '🔴 Disconnected';
            break;
        case 'error':
            statusElement.textContent = `⚠️ Error: ${message}`;
            break;
        case 'project_joined':
            statusElement.textContent = '🟢 Connected';
            break;
        case 'connecting':
            statusElement.textContent = '🔄 Connecting...';
            break;
        default:
            statusElement.textContent = status;
    }
    
    // Auto-hide status after successful connection to reduce UI clutter
    if (status === 'connected' || status === 'project_joined') {
        setTimeout(() => {
            if (statusElement.classList.contains('connected') || statusElement.classList.contains('project_joined')) {
                statusElement.style.opacity = '0.5';
                statusElement.style.fontSize = '0.75rem';
            }
        }, 2000);
    } else {
        // Reset opacity and font size for error/disconnected states
        statusElement.style.opacity = '1';
        statusElement.style.fontSize = '';
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
    if (window.notifications && window.notifications.show) {
        return window.notifications.show(message, type, 5000);
    }
    console.log(`Notification: ${message}`);
}

// WebSocket will be initialized manually by project pages when needed
// No automatic initialization to prevent multiple connections

// Clean up WebSocket connection when page unloads
window.addEventListener('beforeunload', () => {
    if (wsClient) {
        wsClient.disconnect();
    }
});

// Expose global functions
window.ensureWebSocketConnection = ensureWebSocketConnection;