/**
 * Activity Log Management JavaScript
 * Handles displaying, filtering, and managing project activity logs
 */

class ActivityLogManager {
    constructor() {
        this.currentProjectId = null;
        this.currentPage = 1;
        this.currentFilters = {};
        this.isLoading = false;
        this.hasMoreData = true;
        
        this.initializeEventListeners();
    }
    
    initializeEventListeners() {
        // Modal controls
        document.addEventListener('click', (e) => {
            if (e.target.id === 'close-activity-log-modal') {
                e.preventDefault();
                e.stopPropagation();
                this.closeActivityLogModal();
            }
            
            if (e.target.id === 'close-activity-detail-modal') {
                e.preventDefault();
                e.stopPropagation();
                this.closeActivityDetailModal();
            }
            
            // Close modal when clicking outside
            if (e.target.classList.contains('fixed') && e.target.classList.contains('inset-0')) {
                if (e.target.id === 'activity-log-modal') {
                    this.closeActivityLogModal();
                } else if (e.target.id === 'activity-detail-modal') {
                    this.closeActivityDetailModal();
                }
            }
        });
        
        // ESC key to close modals
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const activityModal = document.getElementById('activity-log-modal');
                const detailModal = document.getElementById('activity-detail-modal');
                
                if (activityModal && !activityModal.classList.contains('hidden')) {
                    e.preventDefault();
                    this.closeActivityLogModal();
                } else if (detailModal && !detailModal.classList.contains('hidden')) {
                    e.preventDefault();
                    this.closeActivityDetailModal();
                }
            }
        });
        
        // Filter controls
        const actionFilter = document.getElementById('activity-action-filter');
        const dateFilter = document.getElementById('activity-date-filter');
        const applyFiltersBtn = document.getElementById('apply-activity-filters');
        const exportBtn = document.getElementById('export-activity-log');
        const loadMoreBtn = document.getElementById('load-more-activity');
        
        if (actionFilter) {
            actionFilter.addEventListener('change', () => this.updateFilters());
        }
        
        if (dateFilter) {
            dateFilter.addEventListener('change', (e) => {
                this.handleDateFilterChange(e.target.value);
            });
        }
        
        if (applyFiltersBtn) {
            applyFiltersBtn.addEventListener('click', () => this.applyFilters());
        }
        
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportActivityLog());
        }
        
        if (loadMoreBtn) {
            loadMoreBtn.addEventListener('click', () => this.loadMoreActivities());
        }
        
        // Activity item clicks
        document.addEventListener('click', (e) => {
            if (e.target.closest('.activity-item')) {
                const activityItem = e.target.closest('.activity-item');
                const activityId = activityItem.dataset.activityId;
                if (activityId) {
                    this.showActivityDetails(activityId);
                }
            }
        });
    }
    
    showActivityLogModal(projectId) {
        this.currentProjectId = projectId;
        this.currentPage = 1;
        this.hasMoreData = true;
        
        const modal = document.getElementById('activity-log-modal');
        if (modal) {
            modal.classList.remove('hidden');
            modal.classList.add('show');
            
            // Reset filters
            this.resetFilters();
            
            // Load initial data
            this.loadActivities(true);
        }
    }
    
    closeActivityLogModal() {
        const modal = document.getElementById('activity-log-modal');
        if (modal) {
            modal.classList.add('hidden');
            modal.classList.remove('show');
        }
    }
    
    closeActivityDetailModal() {
        const modal = document.getElementById('activity-detail-modal');
        if (modal) {
            modal.classList.add('hidden');
            modal.classList.remove('show');
        }
    }
    
    resetFilters() {
        const actionFilter = document.getElementById('activity-action-filter');
        const dateFilter = document.getElementById('activity-date-filter');
        const dateFrom = document.getElementById('activity-date-from');
        const dateTo = document.getElementById('activity-date-to');
        
        if (actionFilter) actionFilter.value = '';
        if (dateFilter) dateFilter.value = 'all';
        if (dateFrom) dateFrom.value = '';
        if (dateTo) dateTo.value = '';
        
        this.hideCustomDateRange();
        this.currentFilters = {};
    }
    
    updateFilters() {
        const actionFilter = document.getElementById('activity-action-filter');
        const dateFilter = document.getElementById('activity-date-filter');
        const dateFrom = document.getElementById('activity-date-from');
        const dateTo = document.getElementById('activity-date-to');
        
        this.currentFilters = {};
        
        if (actionFilter && actionFilter.value) {
            this.currentFilters.action = actionFilter.value;
        }
        
        if (dateFilter && dateFilter.value !== 'all') {
            const now = new Date();
            let fromDate = null;
            
            switch (dateFilter.value) {
                case 'today':
                    fromDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
                    break;
                case 'week':
                    fromDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                    break;
                case 'month':
                    fromDate = new Date(now.getFullYear(), now.getMonth(), 1);
                    break;
                case 'custom':
                    if (dateFrom && dateFrom.value) {
                        fromDate = new Date(dateFrom.value);
                    }
                    if (dateTo && dateTo.value) {
                        this.currentFilters.date_to = new Date(dateTo.value).toISOString();
                    }
                    break;
            }
            
            if (fromDate) {
                this.currentFilters.date_from = fromDate.toISOString();
            }
        }
    }
    
    handleDateFilterChange(value) {
        const customDateRange = document.getElementById('custom-date-range');
        const customDateRangeTo = document.getElementById('custom-date-range-to');
        
        if (value === 'custom') {
            this.showCustomDateRange();
        } else {
            this.hideCustomDateRange();
        }
    }
    
    showCustomDateRange() {
        const customDateRange = document.getElementById('custom-date-range');
        const customDateRangeTo = document.getElementById('custom-date-range-to');
        
        if (customDateRange) customDateRange.classList.remove('hidden');
        if (customDateRangeTo) customDateRangeTo.classList.remove('hidden');
    }
    
    hideCustomDateRange() {
        const customDateRange = document.getElementById('custom-date-range');
        const customDateRangeTo = document.getElementById('custom-date-range-to');
        
        if (customDateRange) customDateRange.classList.add('hidden');
        if (customDateRangeTo) customDateRangeTo.classList.add('hidden');
    }
    
    applyFilters() {
        this.updateFilters();
        this.currentPage = 1;
        this.hasMoreData = true;
        this.loadActivities(true);
    }
    
    async loadActivities(reset = false) {
        if (this.isLoading || !this.currentProjectId) return;
        
        this.isLoading = true;
        this.showLoading();
        
        try {
            const params = new URLSearchParams({
                page: this.currentPage,
                per_page: 20,
                ...this.currentFilters
            });
            
            const response = await fetch(`/api/projects/${this.currentProjectId}/activity?${params}`);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to load activities');
            }
            
            if (reset) {
                this.clearActivityTimeline();
            }
            
            this.renderActivities(data.activities);
            this.updatePagination(data.pagination);
            
            if (data.activities.length === 0 && reset) {
                this.showEmptyState();
            } else {
                this.hideEmptyState();
            }
            
        } catch (error) {
            console.error('Error loading activities:', error);
            this.showError('Failed to load activity log. Please try again.');
        } finally {
            this.isLoading = false;
            this.hideLoading();
        }
    }
    
    async loadMoreActivities() {
        if (!this.hasMoreData || this.isLoading) return;
        
        this.currentPage++;
        await this.loadActivities(false);
    }
    
    renderActivities(activities) {
        const timeline = document.getElementById('activity-timeline');
        const template = document.getElementById('activity-item-template');
        
        if (!timeline || !template) return;
        
        activities.forEach(activity => {
            const activityElement = this.createActivityElement(activity, template);
            timeline.appendChild(activityElement);
        });
    }
    
    createActivityElement(activity, template) {
        const clone = template.content.cloneNode(true);
        const activityItem = clone.querySelector('.activity-item');
        
        // Set activity ID for click handling
        activityItem.dataset.activityId = activity.id;
        
        // Set icon and color based on activity type
        const icon = clone.querySelector('.activity-icon');
        const iconClass = clone.querySelector('.activity-icon-class');
        
        const iconConfig = this.getActivityIconConfig(activity.action);
        icon.className = `activity-icon w-10 h-10 rounded-full flex items-center justify-center ${iconConfig.bgClass}`;
        iconClass.className = `${iconConfig.iconClass} text-sm`;
        
        // Set description
        const description = clone.querySelector('.activity-description');
        description.textContent = this.getActivityDescription(activity);
        
        // Set time
        const time = clone.querySelector('.activity-time');
        time.textContent = this.formatRelativeTime(activity.created_at);
        
        // Set details
        const details = clone.querySelector('.activity-details');
        details.textContent = activity.details || '';
        
        // Set metadata
        const ipAddress = clone.querySelector('.ip-address');
        const userAgent = clone.querySelector('.user-agent');
        
        ipAddress.textContent = activity.ip_address || 'Unknown';
        userAgent.textContent = this.truncateUserAgent(activity.user_agent || 'Unknown');
        
        // Add suspicious indicator
        if (activity.is_suspicious) {
            activityItem.classList.add('border-l-4', 'border-red-500');
            const suspiciousIndicator = document.createElement('div');
            suspiciousIndicator.className = 'absolute top-2 right-2 w-3 h-3 bg-red-500 rounded-full';
            suspiciousIndicator.title = 'Suspicious Activity';
            activityItem.style.position = 'relative';
            activityItem.appendChild(suspiciousIndicator);
        }
        
        return clone;
    }
    
    getActivityIconConfig(action) {
        const configs = {
            'project_shared': { iconClass: 'fas fa-share-alt', bgClass: 'activity-project-shared' },
            'collaborator_added': { iconClass: 'fas fa-user-plus', bgClass: 'activity-collaborator-added' },
            'collaborator_removed': { iconClass: 'fas fa-user-minus', bgClass: 'activity-collaborator-removed' },
            'role_changed': { iconClass: 'fas fa-user-cog', bgClass: 'activity-role-changed' },
            'access_granted': { iconClass: 'fas fa-unlock', bgClass: 'activity-access-granted' },
            'access_revoked': { iconClass: 'fas fa-lock', bgClass: 'activity-access-revoked' },
            'token_generated': { iconClass: 'fas fa-key', bgClass: 'activity-token-generated' },
            'token_used': { iconClass: 'fas fa-sign-in-alt', bgClass: 'activity-token-used' },
            'suspicious_access': { iconClass: 'fas fa-exclamation-triangle', bgClass: 'activity-suspicious-access' },
            'task_created': { iconClass: 'fas fa-plus', bgClass: 'activity-collaborator-added' },
            'task_updated': { iconClass: 'fas fa-edit', bgClass: 'activity-role-changed' },
            'task_deleted': { iconClass: 'fas fa-trash', bgClass: 'activity-collaborator-removed' },
            'project_updated': { iconClass: 'fas fa-edit', bgClass: 'activity-role-changed' }
        };
        
        return configs[action] || { iconClass: 'fas fa-circle', bgClass: 'bg-gray-500' };
    }
    
    getActivityDescription(activity) {
        const userName = activity.user_name || 'System';
        
        const descriptions = {
            'project_shared': `${userName} shared the project`,
            'collaborator_added': `${userName} was added as a collaborator`,
            'collaborator_removed': `${userName} was removed as a collaborator`,
            'role_changed': `${userName}'s role was changed`,
            'access_granted': `${userName} was granted access`,
            'access_revoked': `${userName}'s access was revoked`,
            'token_generated': `${userName} generated a sharing token`,
            'token_used': `${userName} used a sharing token`,
            'suspicious_access': `Suspicious access detected`,
            'task_created': `${userName} created a task`,
            'task_updated': `${userName} updated a task`,
            'task_deleted': `${userName} deleted a task`,
            'project_updated': `${userName} updated the project`
        };
        
        return descriptions[activity.action] || `${userName} performed ${activity.action}`;
    }
    
    formatRelativeTime(timestamp) {
        const now = new Date();
        const time = new Date(timestamp);
        const diffMs = now - time;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);
        
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        
        return time.toLocaleDateString();
    }
    
    truncateUserAgent(userAgent) {
        if (userAgent.length > 50) {
            return userAgent.substring(0, 47) + '...';
        }
        return userAgent;
    }
    
    clearActivityTimeline() {
        const timeline = document.getElementById('activity-timeline');
        if (timeline) {
            // Remove all activity items but keep loading/empty states
            const activityItems = timeline.querySelectorAll('.activity-item');
            activityItems.forEach(item => item.remove());
        }
    }
    
    updatePagination(pagination) {
        this.hasMoreData = pagination.has_next;
        
        const loadMoreContainer = document.getElementById('load-more-container');
        if (loadMoreContainer) {
            if (this.hasMoreData) {
                loadMoreContainer.classList.remove('hidden');
            } else {
                loadMoreContainer.classList.add('hidden');
            }
        }
    }
    
    showLoading() {
        const loading = document.getElementById('activity-loading');
        if (loading) {
            loading.classList.remove('hidden');
        }
    }
    
    hideLoading() {
        const loading = document.getElementById('activity-loading');
        if (loading) {
            loading.classList.add('hidden');
        }
    }
    
    showEmptyState() {
        const empty = document.getElementById('activity-empty');
        if (empty) {
            empty.classList.remove('hidden');
        }
    }
    
    hideEmptyState() {
        const empty = document.getElementById('activity-empty');
        if (empty) {
            empty.classList.add('hidden');
        }
    }
    
    showError(message) {
        // Create or update error message
        let errorDiv = document.getElementById('activity-error');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.id = 'activity-error';
            errorDiv.className = 'text-center py-12';
            
            const timeline = document.getElementById('activity-timeline');
            if (timeline) {
                timeline.appendChild(errorDiv);
            }
        }
        
        errorDiv.innerHTML = `
            <div class="w-16 h-16 bg-red-700 rounded-full flex items-center justify-center mx-auto mb-4">
                <i class="fas fa-exclamation-triangle text-red-400 text-2xl"></i>
            </div>
            <h4 class="text-lg font-medium text-white mb-2">Error Loading Activities</h4>
            <p class="text-gray-400">${message}</p>
            <button onclick="activityLogManager.loadActivities(true)" 
                    class="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors">
                Try Again
            </button>
        `;
        
        errorDiv.classList.remove('hidden');
    }
    
    async showActivityDetails(activityId) {
        try {
            const response = await fetch(`/api/projects/${this.currentProjectId}/activity`);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to load activity details');
            }
            
            const activity = data.activities.find(a => a.id == activityId);
            if (!activity) {
                throw new Error('Activity not found');
            }
            
            this.renderActivityDetails(activity);
            
            const modal = document.getElementById('activity-detail-modal');
            if (modal) {
                modal.classList.remove('hidden');
                modal.classList.add('show');
            }
            
        } catch (error) {
            console.error('Error loading activity details:', error);
            this.showError('Failed to load activity details. Please try again.');
        }
    }
    
    renderActivityDetails(activity) {
        const content = document.getElementById('activity-detail-content');
        if (!content) return;
        
        const iconConfig = this.getActivityIconConfig(activity.action);
        
        content.innerHTML = `
            <div class="space-y-6">
                <div class="flex items-center space-x-4">
                    <div class="activity-icon w-12 h-12 rounded-full flex items-center justify-center ${iconConfig.bgClass}">
                        <i class="${iconConfig.iconClass}"></i>
                    </div>
                    <div>
                        <h4 class="text-lg font-semibold text-white">${this.getActivityDescription(activity)}</h4>
                        <p class="text-gray-400">${this.formatFullTimestamp(activity.created_at)}</p>
                    </div>
                </div>
                
                ${activity.is_suspicious ? `
                    <div class="bg-red-900/20 border border-red-500/30 rounded-lg p-4">
                        <div class="flex items-center space-x-2 text-red-400 mb-2">
                            <i class="fas fa-exclamation-triangle"></i>
                            <span class="font-semibold">Suspicious Activity Detected</span>
                        </div>
                        <p class="text-red-300 text-sm">This activity has been flagged as potentially suspicious based on automated analysis.</p>
                    </div>
                ` : ''}
                
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div class="bg-gray-800/30 rounded-lg p-4">
                        <h5 class="font-semibold text-white mb-2">Action Details</h5>
                        <div class="space-y-2 text-sm">
                            <div class="flex justify-between">
                                <span class="text-gray-400">Action:</span>
                                <span class="text-white">${activity.action}</span>
                            </div>
                            <div class="flex justify-between">
                                <span class="text-gray-400">User:</span>
                                <span class="text-white">${activity.user_name || 'System'}</span>
                            </div>
                            ${activity.details ? `
                                <div class="mt-3">
                                    <span class="text-gray-400 block mb-1">Details:</span>
                                    <span class="text-white text-xs bg-gray-700/50 p-2 rounded block">${activity.details}</span>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                    
                    <div class="bg-gray-800/30 rounded-lg p-4">
                        <h5 class="font-semibold text-white mb-2">Technical Information</h5>
                        <div class="space-y-2 text-sm">
                            <div class="flex justify-between">
                                <span class="text-gray-400">IP Address:</span>
                                <span class="text-white font-mono">${activity.ip_address || 'Unknown'}</span>
                            </div>
                            <div class="mt-3">
                                <span class="text-gray-400 block mb-1">User Agent:</span>
                                <span class="text-white text-xs bg-gray-700/50 p-2 rounded block break-all">${activity.user_agent || 'Unknown'}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    formatFullTimestamp(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleString();
    }
    
    async exportActivityLog() {
        if (!this.currentProjectId) return;
        
        try {
            const params = new URLSearchParams(this.currentFilters);
            const response = await fetch(`/api/projects/${this.currentProjectId}/activity/export?${params}`);
            
            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || 'Failed to export activity log');
            }
            
            // Create download link
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `project_${this.currentProjectId}_activity_log.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
        } catch (error) {
            console.error('Error exporting activity log:', error);
            alert('Failed to export activity log. Please try again.');
        }
    }
}

// Initialize the activity log manager
const activityLogManager = new ActivityLogManager();

// Global function to show activity log modal (called from other scripts)
function showActivityLogModal(projectId) {
    activityLogManager.showActivityLogModal(projectId);
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ActivityLogManager;
}