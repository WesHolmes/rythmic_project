/**
 * Shared Notification System
 * 
 * Provides a centralized notification system with proper stacking,
 * consistent styling, and easy-to-use API for all JavaScript modules.
 */

class NotificationManager {
    constructor() {
        this.container = null;
        this.notifications = new Set();
    }

    /**
     * Show a notification message
     * @param {string} message - The message to display
     * @param {string} type - Type of notification ('success', 'error', 'info', 'warning')
     * @param {number} duration - Duration in milliseconds (default: 4000)
     * @param {boolean} dismissible - Whether the notification can be manually dismissed (default: true)
     */
    show(message, type = 'info', duration = 4000, dismissible = true) {
        // Create container if it doesn't exist
        if (!this.container) {
            this.createContainer();
        }

        // Create notification element
        const notification = this.createNotification(message, type, dismissible);
        
        // Add to container and track it
        this.container.appendChild(notification);
        this.notifications.add(notification);

        // Animate in
        setTimeout(() => {
            notification.classList.remove('translate-x-full');
        }, 100);

        // Auto-remove after duration
        if (duration > 0) {
            setTimeout(() => {
                this.remove(notification);
            }, duration);
        }

        return notification;
    }

    /**
     * Show success notification
     */
    success(message, duration = 4000) {
        return this.show(message, 'success', duration);
    }

    /**
     * Show error notification
     */
    error(message, duration = 6000) {
        return this.show(message, 'error', duration);
    }

    /**
     * Show info notification
     */
    info(message, duration = 4000) {
        return this.show(message, 'info', duration);
    }

    /**
     * Show warning notification
     */
    warning(message, duration = 5000) {
        return this.show(message, 'warning', duration);
    }

    /**
     * Remove a specific notification
     */
    remove(notification) {
        if (!this.notifications.has(notification)) return;

        // Animate out
        notification.classList.add('translate-x-full');
        
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
                this.notifications.delete(notification);
                
                // Remove container if empty
                if (this.notifications.size === 0 && this.container) {
                    this.container.remove();
                    this.container = null;
                }
            }
        }, 300);
    }

    /**
     * Clear all notifications
     */
    clear() {
        this.notifications.forEach(notification => {
            this.remove(notification);
        });
    }

    /**
     * Create the notification container
     */
    createContainer() {
        this.container = document.createElement('div');
        this.container.id = 'notification-container';
        this.container.className = 'fixed top-4 right-4 z-50 space-y-2 pointer-events-none max-w-sm';
        document.body.appendChild(this.container);
    }

    /**
     * Create a notification element
     */
    createNotification(message, type, dismissible) {
        const notification = document.createElement('div');
        notification.className = `px-6 py-4 rounded-lg shadow-lg transition-all duration-300 transform translate-x-full pointer-events-auto`;

        const styles = {
            success: 'bg-green-500/20 border border-green-400 text-green-400',
            error: 'bg-red-500/20 border border-red-400 text-red-400',
            info: 'bg-blue-500/20 border border-blue-400 text-blue-400',
            warning: 'bg-yellow-500/20 border border-yellow-400 text-yellow-400'
        };

        const icons = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            info: 'fas fa-info-circle',
            warning: 'fas fa-exclamation-triangle'
        };

        notification.className += ` ${styles[type] || styles.info}`;

        const dismissButton = dismissible ? `
            <button class="ml-3 text-current hover:opacity-70 transition-opacity" 
                    onclick="window.notifications.remove(this.closest('.transform'))">
                <i class="fas fa-times"></i>
            </button>
        ` : '';

        notification.innerHTML = `
            <div class="flex items-center justify-between">
                <div class="flex items-center">
                    <i class="${icons[type] || icons.info} mr-3"></i>
                    <span class="text-sm font-medium">${message}</span>
                </div>
                ${dismissButton}
            </div>
        `;

        return notification;
    }
}

// Create global instance
window.notifications = new NotificationManager();

// Legacy support - global functions for backward compatibility
window.showNotification = (message, type, duration) => {
    return window.notifications.show(message, type, duration);
};

window.showUserNotification = (message, type) => {
    return window.notifications.show(message, type);
};