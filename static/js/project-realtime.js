/**
 * Simplified project sharing manager
 * Handles only sharing features and active user count
 */

class ProjectRealtimeManager {
    constructor(projectId) {
        this.projectId = projectId;
        this.wsClient = null;
        this.isInitialized = false;
        
        this.init();
    }
    
    init() {
        // Only initialize if we don't already have a client
        if (window.projectRealtime && window.projectRealtime.wsClient) {
            console.log('WebSocket client already exists, reusing...');
            this.wsClient = window.projectRealtime.wsClient;
            this.setupEventHandlers();
            this.isInitialized = true;
            return;
        }
        
        // Initialize WebSocket client
        this.wsClient = initializeWebSocket();
        
        if (!this.wsClient) {
            console.error('Failed to initialize WebSocket client');
            return;
        }
        
        // Set up event handlers
        this.setupEventHandlers();
        
        // Join project room when connected - with timeout to prevent infinite loops
        let attempts = 0;
        const maxAttempts = 10;
        
        const joinProject = () => {
            if (attempts >= maxAttempts) {
                console.error('Failed to join project after maximum attempts');
                return;
            }
            
            if (this.wsClient.isWebSocketConnected()) {
                this.wsClient.joinProject(this.projectId);
                this.isInitialized = true;
            } else {
                attempts++;
                setTimeout(joinProject, 500); // Longer delay
            }
        };
        
        joinProject();
    }
    
    setupEventHandlers() {
        // Only handle sharing-related events
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
    
    // Real-time update methods removed to reduce complexity and server load
    
    // UI update methods removed - no longer needed for sharing-only functionality
    
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
    
    // Helper methods removed - no longer needed
    
    showNotification(message, type = 'info') {
        // Use the global notification system
        return window.notifications.show(message, type, 5000);
    }
    
    // Public methods removed - no longer needed for sharing-only functionality
    
    disconnect() {
        if (this.wsClient) {
            this.wsClient.leaveProject();
            this.wsClient.disconnect();
        }
    }
}

// Global instance
let projectRealtime = null;
let isProjectRealtimeInitializing = false;

// Initialize when DOM is loaded - with protection against multiple initializations
document.addEventListener('DOMContentLoaded', () => {
    // Prevent multiple initializations
    if (isProjectRealtimeInitializing || projectRealtime) {
        console.log('Project realtime already initialized or initializing, skipping...');
        return;
    }
    
    const projectElement = document.querySelector('[data-project-id]');
    if (projectElement) {
        isProjectRealtimeInitializing = true;
        
        try {
            const projectId = parseInt(projectElement.dataset.projectId);
            window.currentUserId = parseInt(document.body.dataset.userId || '0');
            
            projectRealtime = new ProjectRealtimeManager(projectId);
            
            // Make it globally accessible
            window.projectRealtime = projectRealtime;
        } finally {
            isProjectRealtimeInitializing = false;
        }
    }
});

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    if (projectRealtime) {
        projectRealtime.disconnect();
    }
});

// Global function overrides removed - no longer needed for sharing-only functionality