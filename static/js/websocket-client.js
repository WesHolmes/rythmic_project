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
        this.isAzure = this.detectAzureEnvironment();
        this.maxReconnectAttempts = this.isAzure ? 3 : 5; // Different limits for Azure vs local
        this.reconnectDelay = this.isAzure ? 10000 : 3000; // Different delays for Azure vs local
        this.lastSyncTimestamp = null;
        this.connectionState = 'disconnected'; // disconnected, connecting, connected, error
        this.pageVisibilityHandler = null;
        this.focusHandler = null;
        
        // Event debouncing to reduce redundant broadcasts
        this.eventDebounceTimers = {};
        this.debounceDelay = 100; // 100ms debounce for events
        
        // Connection management - Azure optimized
        this.connectionDebounceTimer = null;
        this.lastConnectionAttempt = 0;
        this.minConnectionInterval = this.isAzure ? 45000 : 10000; // Azure needs longer intervals due to proxy layer
        this.lastSuccessfulConnection = 0;
        this.connectionLock = false; // Prevent concurrent connection attempts
        this.healthCheckEnabled = true;
        this.connectionQuality = 'unknown'; // unknown, good, poor, failed
        
        // Azure-specific connection management
        this.azureProxyRetryCount = 0;
        this.maxAzureProxyRetries = 3;
        this.azureConnectionStability = 0; // Track connection stability
        
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
     * Set up page visibility and focus handlers for reconnection
     */
    setupPageVisibilityHandlers() {
        // Handle page visibility changes (tab switching, minimizing) - Much more conservative
        this.pageVisibilityHandler = () => {
            if (document.hidden) {
                // Page hidden - don't do anything, just log
                console.log('Page hidden, maintaining connection...');
                return;
            }
            
            // Page visible - only reconnect if truly disconnected and it's been a while
            const timeSinceLastConnection = Date.now() - this.lastConnectionAttempt;
            const timeSinceLastSuccess = Date.now() - this.lastSuccessfulConnection;
            
            // Azure needs longer delays due to proxy layer and connection overhead
            const minAttemptDelay = this.isAzure ? 60000 : 30000; // 1 minute for Azure, 30s for local
            const minSuccessDelay = this.isAzure ? 120000 : 60000; // 2 minutes for Azure, 1 minute for local
            
            if (this.shouldBeConnected() && 
                this.connectionState === 'disconnected' && 
                timeSinceLastConnection > minAttemptDelay &&
                timeSinceLastSuccess > minSuccessDelay) {
                console.log('Page became visible after extended time, checking connection...');
                this.smartReconnect();
            }
        };
        
        // Handle window focus (returning to the page) - Very conservative
        this.focusHandler = () => {
            // Only reconnect if we've been disconnected for a long time
            const timeSinceLastConnection = Date.now() - this.lastConnectionAttempt;
            const timeSinceLastSuccess = Date.now() - this.lastSuccessfulConnection;
            
            // Azure needs much longer delays due to proxy layer
            const minAttemptDelay = this.isAzure ? 120000 : 60000; // 2 minutes for Azure, 1 minute for local
            const minSuccessDelay = this.isAzure ? 300000 : 120000; // 5 minutes for Azure, 2 minutes for local
            
            if (this.shouldBeConnected() && !document.hidden && 
                this.connectionState === 'disconnected' && 
                timeSinceLastConnection > minAttemptDelay &&
                timeSinceLastSuccess > minSuccessDelay) {
                console.log('Window focused after extended time, checking connection...');
                setTimeout(() => {
                    if (this.shouldBeConnected() && !document.hidden && this.connectionState === 'disconnected') {
                        this.smartReconnect();
                    }
                }, this.isAzure ? 1000 : 500); // Longer delay for Azure
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
        
        // Clear all event debounce timers
        Object.values(this.eventDebounceTimers).forEach(timer => {
            clearTimeout(timer);
        });
        this.eventDebounceTimers = {};
        
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
     * Smart reconnection that only reconnects when truly needed
     */
    smartReconnect() {
        // Check if we're already connected or connecting
        if (this.isWebSocketConnected() || this.connectionState === 'connecting') {
            console.log('Already connected or connecting, skipping smart reconnect...');
            return;
        }
        
        // Check if we should be connected
        if (!this.shouldBeConnected()) {
            console.log('Should not be connected, skipping smart reconnect...');
            return;
        }
        
        // Check connection lock
        if (this.connectionLock) {
            console.log('Connection locked, skipping smart reconnect...');
            return;
        }
        
        // Check minimum interval
        const now = Date.now();
        if (now - this.lastConnectionAttempt < this.minConnectionInterval) {
            console.log(`Smart reconnect too recent, waiting ${this.minConnectionInterval - (now - this.lastConnectionAttempt)}ms...`);
            return;
        }
        
        // Proceed with smart reconnection
        this.ensureConnection();
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
            console.log(`Connection attempt too recent, debouncing for ${this.minConnectionInterval - (now - this.lastConnectionAttempt)}ms...`);
            this.connectionDebounceTimer = setTimeout(() => {
                // Double-check we still need connection after delay
                if (this.shouldBeConnected()) {
                    this.smartReconnect();
                }
            }, this.minConnectionInterval - (now - this.lastConnectionAttempt));
            return;
        }
        
        // Additional throttling: prevent multiple simultaneous connection attempts
        if (this.connectionState === 'connecting' || this.connectionLock) {
            console.log('Already connecting or locked, skipping duplicate attempt...');
            return;
        }
        
        // Proceed with connection attempt
        this.smartReconnect();
    }
    
    /**
     * Ensure WebSocket connection is active when it should be
     */
    ensureConnection() {
        if (!this.shouldBeConnected()) {
            console.log('WebSocket not needed for current page');
            return;
        }
        
        // Check connection lock
        if (this.connectionLock) {
            console.log('Connection locked, skipping ensureConnection...');
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
     * Force reconnection with proper state management and locking
     */
    forceReconnect() {
        // Don't force reconnect if already connecting or locked
        if (this.connectionState === 'connecting' || this.connectionLock) {
            console.log('Already connecting or locked, skipping force reconnect...');
            return;
        }
        
        console.log('Force reconnecting WebSocket...');
        this.connectionLock = true; // Lock to prevent concurrent attempts
        this.connectionState = 'connecting';
        this.reconnectAttempts = 0; // Reset attempts for immediate reconnection
        this.reconnectDelay = 1000; // Reduced delay for faster reconnection
        
        // Show connecting status
        if (this.onDisconnected) {
            this.onDisconnected('force_reconnect');
        }
        
        if (this.socket) {
            this.socket.disconnect();
        }
        
        // Connect with a smaller delay to allow cleanup
        setTimeout(() => {
            if (this.shouldBeConnected()) {
                this.connect();
            }
        }, 200); // Reduced from 500ms to 200ms
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
            
            // Prevent multiple simultaneous connections
            if (this.connectionState === 'connecting' || this.connectionState === 'connected') {
                console.log('Connection already in progress or established, skipping...');
                return;
            }
            
            // Check minimum connection interval
            const now = Date.now();
            if (now - this.lastConnectionAttempt < this.minConnectionInterval) {
                console.log('Connection throttled, too soon since last attempt');
                return;
            }
            
            this.lastConnectionAttempt = now;
            this.connectionState = 'connecting';
            
            // Initialize Socket.IO connection with environment-specific settings
            const config = this.isAzure ? {
                // Azure-optimized settings - allow WebSocket upgrade for better performance
                transports: ['polling', 'websocket'], // Allow both transports
                upgrade: true, // Enable WebSocket upgrade for better performance
                rememberUpgrade: true, // Remember successful upgrades
                timeout: 20000, // Reduced timeout for faster failure detection
                forceNew: false, // Don't force new connections unnecessarily
                reconnection: false, // Disable automatic reconnection (we handle it manually)
                pingTimeout: 120000, // 2 minutes for Azure (reduced from 5 minutes)
                pingInterval: 60000, // 1 minute for Azure (reduced from 2 minutes)
                autoConnect: true
            } : {
                // Local development settings
                transports: ['websocket', 'polling'], // WebSocket first for local
                upgrade: true, // Allow WebSocket upgrade
                rememberUpgrade: true, // Remember successful upgrades
                timeout: 10000, // Standard timeout for local
                forceNew: false, // Don't force new connections
                reconnection: false, // Disable automatic reconnection (we handle it manually)
                pingTimeout: 60000, // 1 minute for local
                pingInterval: 25000, // 25 seconds for local
                autoConnect: true
            };
            
            console.log('Socket.IO config for', this.isAzure ? 'Azure' : 'Local', ':', config);
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
     * Set up Socket.IO event handlers
     */
    setupEventHandlers() {
        // Connection events
        this.socket.on('connect', () => {
            console.log('WebSocket connected');
            this.isConnected = true;
            this.connectionState = 'connected';
            this.connectionLock = false; // Release lock on successful connection
            this.lastSuccessfulConnection = Date.now();
            this.connectionQuality = 'good';
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;
            
            // Azure-specific connection tracking
            if (this.isAzure) {
                this.azureConnectionStability++;
                this.azureProxyRetryCount = 0; // Reset proxy retry count on successful connection
                console.log(`Azure connection stability: ${this.azureConnectionStability}`);
            }
            
            if (this.onConnected) {
                this.onConnected();
            }
            
            // Auto-rejoin project if we were in one or detect current project
            const projectIdMatch = window.location.pathname.match(/\/projects\/(\d+)/);
            if (projectIdMatch) {
                const projectId = parseInt(projectIdMatch[1]);
                this.currentProjectId = projectId;
                this.joinProject(projectId);
                
                // Azure needs longer sync delay due to proxy layer
                const syncDelay = this.isAzure ? 1000 : 500;
                setTimeout(() => {
                    this.synchronizeState();
                }, syncDelay);
            }
        });
        
        this.socket.on('disconnect', (reason) => {
            console.log('WebSocket disconnected:', reason);
            this.isConnected = false;
            this.connectionState = 'disconnected';
            this.connectionLock = false; // Release lock on disconnect
            this.connectionQuality = 'poor'; // Mark connection as poor after disconnect
            
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
                }, 30000); // Increased to 30 seconds
                return;
            }
            
            // For other disconnections, wait much longer before reconnecting
            if (this.shouldBeConnected() && reason !== 'io client disconnect') {
                setTimeout(() => {
                    if (this.shouldBeConnected()) {
                        this.attemptReconnect();
                    }
                }, 20000); // Increased to 20 seconds
            }
        });
        
        this.socket.on('connect_error', (error) => {
            console.error('WebSocket connection error:', error);
            this.connectionState = 'error';
            this.connectionLock = false; // Release lock on error
            
            // Azure-specific error handling
            if (this.isAzure) {
                this.azureProxyRetryCount++;
                console.log(`Azure proxy retry count: ${this.azureProxyRetryCount}`);
                
                // If too many proxy errors, increase delays significantly
                if (this.azureProxyRetryCount >= this.maxAzureProxyRetries) {
                    this.minConnectionInterval = 300000; // 5 minutes for Azure after multiple failures
                    console.log('Azure proxy errors exceeded, increasing connection interval to 5 minutes');
                }
            }
            
            if (this.onError) {
                this.onError('connection_error', error.message);
            }
            
            // For 400 errors, wait much longer before retrying and try different transport
            if (error.message && (error.message.includes('400') || error.message.includes('Bad Request'))) {
                const retryDelay = this.isAzure ? 60000 : 20000; // 1 minute for Azure, 20s for local
                console.log(`Received 400 error, waiting ${retryDelay/1000}s before retry...`);
                setTimeout(() => {
                    if (this.shouldBeConnected()) {
                        // Try with polling only for 400 errors
                        this.connectWithPollingOnly();
                    }
                }, retryDelay);
            } else if (this.shouldBeConnected()) {
                // Wait much longer before attempting reconnection for other errors
                const retryDelay = this.isAzure ? 45000 : 15000; // 45s for Azure, 15s for local
                setTimeout(() => {
                    if (this.shouldBeConnected()) {
                        this.attemptReconnect();
                    }
                }, retryDelay);
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
                this.reconnectDelay = 10000; // Start with 10 seconds
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
        
        // Exponential backoff with jitter, cap at 30 seconds for Azure stability
        const baseDelay = Math.min(this.reconnectDelay * 1.5, 30000);
        const jitter = Math.random() * 1000; // Add up to 1 second of jitter
        this.reconnectDelay = Math.floor(baseDelay + jitter);
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
        
        // Check if we've attempted connection too recently
        const now = Date.now();
        if (now - this.lastConnectionAttempt < this.minConnectionInterval) {
            console.log('Polling connection attempt too recent, skipping...');
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
     * Send a task update to other collaborators with debouncing
     * @param {number} projectId - The project ID
     * @param {object} taskData - The task data
     * @param {string} updateType - Type of update (task_create, task_update, task_delete)
     */
    sendTaskUpdate(projectId, taskData, updateType = 'task_update') {
        if (!this.isConnected) {
            console.warn('Cannot send task update: WebSocket not connected');
            return;
        }
        
        // Debounce task updates to prevent spam
        const eventKey = `task_${projectId}_${taskData.id || 'new'}`;
        this._debounceEvent(eventKey, () => {
            this.socket.emit('task_update', {
                project_id: projectId,
                task_data: taskData,
                update_type: updateType
            });
        });
    }
    
    /**
     * Send a project update to other collaborators with debouncing
     * @param {number} projectId - The project ID
     * @param {object} projectData - The project data
     * @param {string} updateType - Type of update
     */
    sendProjectUpdate(projectId, projectData, updateType = 'project_update') {
        if (!this.isConnected) {
            console.warn('Cannot send project update: WebSocket not connected');
            return;
        }
        
        // Debounce project updates to prevent spam
        const eventKey = `project_${projectId}_${updateType}`;
        this._debounceEvent(eventKey, () => {
            this.socket.emit('project_update', {
                project_id: projectId,
                project_data: projectData,
                update_type: updateType
            });
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
     * Debounce events to prevent spam
     * @param {string} eventKey - Unique key for the event
     * @param {Function} callback - Function to execute after debounce delay
     */
    _debounceEvent(eventKey, callback) {
        // Clear existing timer for this event
        if (this.eventDebounceTimers[eventKey]) {
            clearTimeout(this.eventDebounceTimers[eventKey]);
        }
        
        // Set new timer
        this.eventDebounceTimers[eventKey] = setTimeout(() => {
            callback();
            delete this.eventDebounceTimers[eventKey];
        }, this.debounceDelay);
    }
    
    /**
     * Start connection health monitoring with Azure-optimized logic
     */
    startHealthMonitoring() {
        // Azure needs longer health check intervals due to proxy layer
        const healthCheckInterval = this.isAzure ? 120000 : 60000; // 2 minutes for Azure, 1 minute for local
        
        this.healthCheckInterval = setInterval(() => {
            if (!this.healthCheckEnabled) {
                return; // Skip if health check is disabled
            }
            
            if (this.shouldBeConnected() && !this.isWebSocketConnected()) {
                // Only attempt reconnection if we've been disconnected for a while
                const timeSinceLastConnection = Date.now() - this.lastConnectionAttempt;
                const timeSinceLastSuccess = Date.now() - this.lastSuccessfulConnection;
                
                // Azure needs much longer delays due to proxy layer and connection overhead
                const minConnectionDelay = this.isAzure ? 180000 : 60000; // 3 minutes for Azure, 1 minute for local
                const minSuccessDelay = this.isAzure ? 300000 : 120000; // 5 minutes for Azure, 2 minutes for local
                
                if (timeSinceLastConnection > minConnectionDelay && timeSinceLastSuccess > minSuccessDelay) {
                    console.log('Health check failed after extended time, attempting reconnection...');
                    this.smartReconnect();
                } else {
                    console.log('Health check failed but too recent, skipping reconnection...');
                }
            }
        }, healthCheckInterval);
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
let connectionAttempts = 0;
const MAX_CONNECTION_ATTEMPTS = 3; // Maximum attempts per minute
let lastConnectionReset = Date.now();

/**
 * Initialize WebSocket client for the current page
 */
function initializeWebSocket() {
    // Reset connection attempts every minute
    const now = Date.now();
    if (now - lastConnectionReset > 60000) {
        connectionAttempts = 0;
        lastConnectionReset = now;
    }
    
    // Limit connection attempts
    if (connectionAttempts >= MAX_CONNECTION_ATTEMPTS) {
        console.log('Too many connection attempts, throttling...');
        return null;
    }
    
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
    
    connectionAttempts++;
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
        // Only ensure connection if we're actually disconnected and it's been a while
        if (wsClient.connectionState === 'disconnected') {
            const timeSinceLastConnection = Date.now() - wsClient.lastConnectionAttempt;
            if (timeSinceLastConnection > 30000) { // 30 seconds
                console.log('WebSocket disconnected for extended time, attempting smart reconnection...');
                wsClient.smartReconnect();
            } else {
                console.log('WebSocket disconnected but too recent, skipping...');
            }
        } else {
            console.log('WebSocket already connected, skipping...');
        }
    } else {
        // Initialize if not already done
        const isProjectPage = window.location.pathname.includes('/projects/');
        const isSharingPage = window.location.pathname.includes('/sharing/');
        
        if (isProjectPage || isSharingPage) {
            console.log('Initializing WebSocket for project/sharing page...');
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

// Handle page navigation (for SPAs or programmatic navigation) - Very conservative
window.addEventListener('popstate', () => {
    // Handle browser back/forward navigation - only if we're on a project page
    setTimeout(() => {
        if (window.location.pathname.includes('/projects/')) {
            console.log('Navigation detected, checking if WebSocket connection needed...');
            // Only ensure connection if we're actually disconnected and it's been a while
            if (wsClient && wsClient.connectionState === 'disconnected') {
                const timeSinceLastConnection = Date.now() - wsClient.lastConnectionAttempt;
                if (timeSinceLastConnection > 30000) { // 30 seconds
                    ensureWebSocketConnection();
                }
            }
        }
    }, 500); // Increased delay to prevent rapid reconnections
});

// Note: Window focus is handled by the WebSocket client's own focus handler
// to avoid duplicate connection attempts

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

// Note: Page visibility is handled by the WebSocket client's own visibility handler
// to avoid duplicate connection attempts

// Expose global functions for manual connection management
window.ensureWebSocketConnection = ensureWebSocketConnection;
window.handlePageNavigation = handlePageNavigation;