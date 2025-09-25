// Sharing Management JavaScript
class SharingManager {
    constructor(projectId, userPermissions = {}) {
        this.projectId = projectId;
        this.userPermissions = userPermissions;
        this.currentCollaborators = [];
        this.currentTokens = [];
        this.currentActivity = [];
        this.activityPage = 1;
        this.activityFilters = {};
        
        this.initializeEventListeners();
        this.initializeModals();
    }

    initializeEventListeners() {
        // Use event delegation for better reliability
        document.addEventListener('click', (e) => {
            // Main sharing button
            if (e.target.id === 'manage-sharing-btn') {
                this.openSharingModal();
            }
            
            // Collaborators button
            if (e.target.id === 'manage-collaborators-btn') {
                this.openCollaboratorModal();
            }
            
            // Close buttons
            if (e.target.id === 'close-sharing-modal' || e.target.closest('#close-sharing-modal')) {
                e.preventDefault();
                e.stopPropagation();
                this.closeModal(document.getElementById('sharing-modal'));
            }
            
            if (e.target.id === 'close-collaborator-modal' || e.target.closest('#close-collaborator-modal')) {
                e.preventDefault();
                e.stopPropagation();
                this.closeModal(document.getElementById('collaborator-modal'));
            }
            
            // Close collaborator modal button (bottom close button)
            if (e.target.id === 'close-collaborator-modal-btn') {
                e.preventDefault();
                e.stopPropagation();
                this.closeModal(document.getElementById('collaborator-modal'));
            }
            
            if (e.target.id === 'close-activity-log-modal' || e.target.closest('#close-activity-log-modal')) {
                e.preventDefault();
                e.stopPropagation();
                this.closeModal(document.getElementById('activity-log-modal'));
            }
            
            // Activity log button
            if (e.target.id === 'view-activity-log-btn') {
                this.openActivityLogModal();
            }
            
            // Generate buttons
            if (e.target.id === 'generate-link-btn') {
                this.generateSharingLink();
            }
            
            if (e.target.id === 'generate-text-btn') {
                this.generateTextMessage();
            }
            
            // Copy buttons
            if (e.target.id === 'copy-link-btn') {
                this.copyToClipboard('generated-link');
            }
            
            if (e.target.id === 'copy-text-btn') {
                this.copyTextMessage();
            }
            
            // Cancel buttons for sharing modal
            if (e.target.id === 'cancel-email-share') {
                e.preventDefault();
                e.stopPropagation();
                this.closeModal(document.getElementById('sharing-modal'));
            }
            
            if (e.target.id === 'cancel-link-share') {
                e.preventDefault();
                e.stopPropagation();
                this.closeModal(document.getElementById('sharing-modal'));
            }
            
            if (e.target.id === 'cancel-text-share') {
                e.preventDefault();
                e.stopPropagation();
                this.closeModal(document.getElementById('sharing-modal'));
            }
        });

        // Sharing modal tabs
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('sharing-tab')) {
                this.switchSharingTab(e.target.id.replace('tab-', ''));
            }
        });

        // Form submissions - only add listener once
        if (!window.sharingFormListenerAdded) {
            document.addEventListener('submit', (e) => {
                if (e.target.id === 'email-sharing-form') {
                    this.handleEmailShare(e);
                }
            });
            window.sharingFormListenerAdded = true;
        }
    }



    initializeModals() {
        // Close modals when clicking outside
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('fixed') && e.target.classList.contains('inset-0')) {
                this.closeModal(e.target);
            }
        });

        // ESC key to close modals
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const openModal = document.querySelector('[id$="-modal"]:not(.hidden)');
                if (openModal) {
                    e.preventDefault();
                    this.closeModal(openModal);
                }
            }
        });
    }

    // Modal Management
    openSharingModal() {
        const modal = document.getElementById('sharing-modal');
        if (modal) {
            modal.classList.remove('hidden');
            this.switchSharingTab('email'); // Default to email tab
        }
    }

    openCollaboratorModal() {
        const modal = document.getElementById('collaborator-modal');
        if (modal) {
            modal.classList.remove('hidden');
            this.updateModalForUserRole();
            this.loadCollaborators();
            if (this.userPermissions.can_manage_share_links) {
                this.loadSharingTokens();
            }
        }
    }

    updateModalForUserRole() {
        const modal = document.getElementById('collaborator-modal');
        if (!modal) return;

        // Update modal title
        const titleElement = document.getElementById('collaborators-modal-title');
        if (titleElement) {
            titleElement.textContent = this.userPermissions.can_manage_collaborators ? 
                'Manage Collaborators' : 'View Collaborators';
        }

        // Show/hide readonly notice
        const readonlyNotice = document.getElementById('collaborators-readonly-notice');
        if (readonlyNotice) {
            if (this.userPermissions.can_manage_collaborators) {
                readonlyNotice.classList.add('hidden');
            } else {
                readonlyNotice.classList.remove('hidden');
            }
        }

        // Show/hide sharing links section
        const sharingSection = document.getElementById('sharing-links-section');
        if (sharingSection) {
            if (this.userPermissions.can_manage_share_links) {
                sharingSection.classList.remove('hidden');
            } else {
                sharingSection.classList.add('hidden');
            }
        }

        // Show/hide invite button
        const inviteBtn = document.getElementById('invite-collaborator-btn');
        if (inviteBtn) {
            if (this.userPermissions.can_manage_collaborators) {
                inviteBtn.classList.remove('hidden');
            } else {
                inviteBtn.classList.add('hidden');
            }
        }
    }

    openActivityLogModal() {
        // Use the dedicated ActivityLogManager
        if (window.activityLogManager) {
            window.activityLogManager.showActivityLogModal(this.projectId);
        } else {
            // Fallback if ActivityLogManager is not available
            showActivityLogModal(this.projectId);
        }
    }

    closeModal(modal) {
        if (modal) {
            modal.classList.add('hidden');
            // Reset forms
            const forms = modal.querySelectorAll('form');
            forms.forEach(form => form.reset());
            
            // Hide generated content
            const generatedContainers = modal.querySelectorAll('[id*="generated-"]');
            generatedContainers.forEach(container => container.classList.add('hidden'));
        }
    }

    switchSharingTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.sharing-tab').forEach(tab => {
            tab.classList.remove('active', 'bg-blue-600', 'text-white');
            tab.classList.add('text-gray-400');
        });
        
        const activeTab = document.getElementById(`tab-${tabName}`);
        if (activeTab) {
            activeTab.classList.add('active', 'bg-blue-600', 'text-white');
            activeTab.classList.remove('text-gray-400');
        }

        // Update panels
        document.querySelectorAll('.sharing-panel').forEach(panel => {
            panel.classList.add('hidden');
        });
        
        const activePanel = document.getElementById(`panel-${tabName}`);
        if (activePanel) {
            activePanel.classList.remove('hidden');
        }
    }

    // Sharing Functions
    async handleEmailShare(e) {
        e.preventDefault();
        console.log('handleEmailShare called - preventing duplicate submission');
        
        // Prevent double submission
        if (this.isSubmittingEmail) {
            console.log('Email submission already in progress, ignoring duplicate');
            return;
        }
        this.isSubmittingEmail = true;
        
        const email = document.getElementById('share-email').value;
        const role = document.getElementById('share-role-email').value;
        const message = document.getElementById('share-message').value;
        const expiresHours = document.getElementById('share-expiration-email').value;

        const submitBtn = e.target.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        
        try {
            submitBtn.innerHTML = '<div class="spinner mr-2"></div>Sending...';
            submitBtn.disabled = true;

            const response = await fetch(`/api/projects/${this.projectId}/share`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    method: 'email',
                    email: email,
                    role: role,
                    message: message,
                    expires_hours: parseInt(expiresHours)
                })
            });

            const result = await response.json();

            if (response.ok) {
                if (result.method === 'direct_add') {
                    // User already exists - they were added directly
                    this.showNotification(`${result.user_name} has been added to the project!`, 'success');
                } else if (result.method === 'email') {
                    // New user - invitation email sent
                    this.showNotification('Invitation sent successfully!', 'success');
                }
                
                this.closeModal(document.getElementById('sharing-modal'));
                
                // Refresh collaborators if modal is open
                if (!document.getElementById('collaborator-modal').classList.contains('hidden')) {
                    this.loadCollaborators();
                }
            } else {
                this.showNotification(result.error || 'Failed to send invitation', 'error');
            }
        } catch (error) {
            console.error('Error sending invitation:', error);
            this.showNotification('Failed to send invitation', 'error');
        } finally {
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
            this.isSubmittingEmail = false;
        }
    }

    async generateSharingLink() {
        const role = document.getElementById('share-role-link').value;
        const expiresHours = document.getElementById('share-expiration-link').value;
        const maxUses = document.getElementById('share-max-uses').value;

        const generateBtn = document.getElementById('generate-link-btn');
        const originalText = generateBtn.innerHTML;

        try {
            generateBtn.innerHTML = '<div class="spinner mr-2"></div>Generating...';
            generateBtn.disabled = true;

            const response = await fetch(`/api/projects/${this.projectId}/share`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    method: 'link',
                    role: role,
                    expires_hours: parseInt(expiresHours),
                    max_uses: parseInt(maxUses)
                })
            });

            const result = await response.json();

            if (response.ok) {
                this.displayGeneratedLink(result.sharing_url, expiresHours, maxUses);
                this.showNotification('Sharing link generated!', 'success');
            } else {
                this.showNotification(result.error || 'Failed to generate link', 'error');
            }
        } catch (error) {
            console.error('Error generating link:', error);
            this.showNotification('Failed to generate link', 'error');
        } finally {
            generateBtn.innerHTML = originalText;
            generateBtn.disabled = false;
        }
    }

    async generateTextMessage() {
        const role = document.getElementById('share-role-text').value;
        const expiresHours = document.getElementById('share-expiration-text').value;

        const generateBtn = document.getElementById('generate-text-btn');
        const originalText = generateBtn.innerHTML;

        try {
            generateBtn.innerHTML = '<div class="spinner mr-2"></div>Generating...';
            generateBtn.disabled = true;

            const response = await fetch(`/api/projects/${this.projectId}/share`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    method: 'text',
                    role: role,
                    expires_hours: parseInt(expiresHours)
                })
            });

            const result = await response.json();

            if (response.ok) {
                this.displayGeneratedText(result.message, result.sharing_url);
                this.showNotification('Text message generated!', 'success');
            } else {
                this.showNotification(result.error || 'Failed to generate message', 'error');
            }
        } catch (error) {
            console.error('Error generating text:', error);
            this.showNotification('Failed to generate message', 'error');
        } finally {
            generateBtn.innerHTML = originalText;
            generateBtn.disabled = false;
        }
    }

    displayGeneratedLink(url, expiresHours, maxUses) {
        const container = document.getElementById('generated-link-container');
        const linkInput = document.getElementById('generated-link');
        const expiryText = document.getElementById('link-expiry-text');
        const usesText = document.getElementById('link-uses-text');

        linkInput.value = url;
        expiryText.textContent = this.formatExpiration(expiresHours);
        usesText.textContent = maxUses === -1 ? 'unlimited times' : `${maxUses} time${maxUses > 1 ? 's' : ''}`;

        container.classList.remove('hidden');
    }

    displayGeneratedText(message, url) {
        const container = document.getElementById('generated-text-container');
        const messageElement = document.getElementById('generated-text-message');

        messageElement.textContent = message;
        container.classList.remove('hidden');
        
        // Store the message for copying
        container.dataset.message = message;
        container.dataset.url = url;
    }

    formatExpiration(hours) {
        if (hours < 24) {
            return `${hours} hour${hours > 1 ? 's' : ''}`;
        } else if (hours < 168) {
            const days = Math.floor(hours / 24);
            return `${days} day${days > 1 ? 's' : ''}`;
        } else {
            const weeks = Math.floor(hours / 168);
            return `${weeks} week${weeks > 1 ? 's' : ''}`;
        }
    }

    // Collaborator Management
    async loadCollaborators() {
        const loadingElement = document.getElementById('collaborators-loading');
        const emptyElement = document.getElementById('collaborators-empty');
        const listElement = document.getElementById('collaborators-list');

        // Show loading
        loadingElement.classList.remove('hidden');
        emptyElement.classList.add('hidden');

        try {
            const response = await fetch(`/api/projects/${this.projectId}/collaborators`);
            const result = await response.json();

            if (response.ok) {
                this.currentCollaborators = result.collaborators || [];
                // Update permissions from API response
                if (result.can_manage_collaborators !== undefined) {
                    this.userPermissions.can_manage_collaborators = result.can_manage_collaborators;
                }
                if (result.can_manage_share_links !== undefined) {
                    this.userPermissions.can_manage_share_links = result.can_manage_share_links;
                }
                this.renderCollaborators();
            } else {
                this.showNotification(result.error || 'Failed to load collaborators', 'error');
            }
        } catch (error) {
            console.error('Error loading collaborators:', error);
            this.showNotification('Failed to load collaborators', 'error');
        } finally {
            loadingElement.classList.add('hidden');
        }
    }

    renderCollaborators() {
        const listElement = document.getElementById('collaborators-list');
        const emptyElement = document.getElementById('collaborators-empty');
        const loadingElement = document.getElementById('collaborators-loading');

        // Clear existing content except loading/empty states
        const existingItems = listElement.querySelectorAll('.collaborator-item');
        existingItems.forEach(item => item.remove());

        if (this.currentCollaborators.length === 0) {
            emptyElement.classList.remove('hidden');
            return;
        }

        emptyElement.classList.add('hidden');

        this.currentCollaborators.forEach(collaborator => {
            const item = this.createCollaboratorItem(collaborator);
            listElement.appendChild(item);
        });
    }

    createCollaboratorItem(collaborator) {
        console.log('Creating collaborator:', collaborator.name, 'is_owner:', collaborator.is_owner, 'role:', collaborator.role);
        const item = document.createElement('div');
        item.className = 'collaborator-item bg-gray-800/30 rounded-lg p-4 flex items-center justify-between hover:bg-gray-800/50 transition-colors';
        
        const roleColor = this.getRoleColor(collaborator.is_owner ? 'owner' : collaborator.role);
        const roleIcon = this.getRoleIcon(collaborator.is_owner ? 'owner' : collaborator.role);
        
        item.innerHTML = `
            <div class="flex items-center space-x-4">
                <div class="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
                    <span class="text-white font-semibold text-sm">${(collaborator.name || 'U').charAt(0).toUpperCase()}</span>
                </div>
                <div>
                    <h4 class="text-white font-medium">${collaborator.name || 'Unknown'}</h4>
                    <p class="text-gray-400 text-sm">${collaborator.email || 'No email'}</p>
                    <div class="flex items-center space-x-2 mt-1">
                        <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${roleColor}">
                            <i class="${roleIcon} mr-1"></i>${collaborator.is_owner ? 'Owner' : (collaborator.role || 'viewer').charAt(0).toUpperCase() + (collaborator.role || 'viewer').slice(1)}
                        </span>
                        <span class="text-xs text-gray-500">
                            ${collaborator.status === 'pending' ? 'Invitation pending' : `Joined ${this.formatDate(collaborator.accepted_at)}`}
                        </span>
                    </div>
                </div>
            </div>
            <div class="flex items-center space-x-2">
                ${!collaborator.is_owner && collaborator.role !== 'owner' ? `
                    ${this.userPermissions.can_manage_collaborators ? `
                        <select class="role-select px-3 py-1 bg-gray-700 border border-gray-600 rounded text-white text-sm" 
                                data-user-id="${collaborator.user_id || collaborator.id || 'undefined'}" data-current-role="${collaborator.role || 'viewer'}" data-collaborator-id="${collaborator.id || 'undefined'}">
                            <option value="viewer" ${(collaborator.role || 'viewer') === 'viewer' ? 'selected' : ''}>Viewer</option>
                            <option value="editor" ${(collaborator.role || 'viewer') === 'editor' ? 'selected' : ''}>Editor</option>
                            <option value="admin" ${(collaborator.role || 'viewer') === 'admin' ? 'selected' : ''}>Admin</option>
                        </select>
                        <button class="remove-collaborator-btn text-red-400 hover:text-red-300 p-2 rounded-lg hover:bg-red-500/10 transition-colors"
                                data-user-id="${collaborator.user_id || ''}" data-user-name="${collaborator.name || 'Unknown'}">
                            <i class="fas fa-user-times"></i>
                        </button>
                    ` : `
                        <span class="text-xs text-gray-500 px-3 py-1">${(collaborator.role || 'viewer').charAt(0).toUpperCase() + (collaborator.role || 'viewer').slice(1)}</span>
                    `}
                ` : `
                    <span class="text-xs text-gray-500 px-3 py-1">Project Owner</span>
                `}
            </div>
        `;

        // Add event listeners
        const roleSelect = item.querySelector('.role-select');
        if (roleSelect) {
            roleSelect.addEventListener('change', (e) => this.handleRoleChange(e));
        }

        const removeBtn = item.querySelector('.remove-collaborator-btn');
        if (removeBtn) {
            removeBtn.addEventListener('click', (e) => this.handleRemoveCollaborator(e));
        }

        return item;
    }

    getRoleColor(role) {
        const colors = {
            owner: 'bg-red-500/20 text-red-400',
            admin: 'bg-orange-500/20 text-orange-400',
            editor: 'bg-blue-500/20 text-blue-400',
            viewer: 'bg-gray-500/20 text-gray-400'
        };
        return colors[role] || colors.viewer;
    }

    getRoleIcon(role) {
        const icons = {
            owner: 'fas fa-crown',
            admin: 'fas fa-user-shield',
            editor: 'fas fa-edit',
            viewer: 'fas fa-eye'
        };
        return icons[role] || icons.viewer;
    }

    formatDate(dateString) {
        if (!dateString) return 'Unknown';
        const date = new Date(dateString);
        return date.toLocaleDateString();
    }

    // Utility Functions
    async copyToClipboard(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            try {
                await navigator.clipboard.writeText(element.value);
                this.showNotification('Copied to clipboard!', 'success');
            } catch (error) {
                // Fallback for older browsers
                element.select();
                document.execCommand('copy');
                this.showNotification('Copied to clipboard!', 'success');
            }
        }
    }

    async copyTextMessage() {
        const container = document.getElementById('generated-text-container');
        const message = container.dataset.message;
        
        if (message) {
            try {
                await navigator.clipboard.writeText(message);
                this.showNotification('Message copied to clipboard!', 'success');
            } catch (error) {
                this.showNotification('Failed to copy message', 'error');
            }
        }
    }

    showNotification(message, type = 'info') {
        // Use the global notification system
        return window.notifications.show(message, type);
    }

    toggleCustomDateRange() {
        const dateFilter = document.getElementById('activity-date-filter');
        const customRange = document.getElementById('custom-date-range');
        const customRangeTo = document.getElementById('custom-date-range-to');
        
        if (dateFilter.value === 'custom') {
            customRange.classList.remove('hidden');
            customRangeTo.classList.remove('hidden');
        } else {
            customRange.classList.add('hidden');
            customRangeTo.classList.add('hidden');
        }
    }

    // Sharing Tokens Management
    async loadSharingTokens() {
        const loadingElement = document.getElementById('tokens-loading');
        const emptyElement = document.getElementById('tokens-empty');
        const listElement = document.getElementById('sharing-tokens-list');

        loadingElement.classList.remove('hidden');
        emptyElement.classList.add('hidden');

        try {
            const response = await fetch(`/api/projects/${this.projectId}/sharing/tokens`);
            const result = await response.json();

            if (response.ok) {
                this.currentTokens = result.tokens || [];
                this.renderSharingTokens();
            } else {
                this.showNotification(result.error || 'Failed to load sharing tokens', 'error');
            }
        } catch (error) {
            console.error('Error loading sharing tokens:', error);
            this.showNotification('Failed to load sharing tokens', 'error');
        } finally {
            loadingElement.classList.add('hidden');
        }
    }

    renderSharingTokens() {
        const listElement = document.getElementById('sharing-tokens-list');
        const emptyElement = document.getElementById('tokens-empty');

        // Clear existing items
        const existingItems = listElement.querySelectorAll('.token-item');
        existingItems.forEach(item => item.remove());

        if (this.currentTokens.length === 0) {
            emptyElement.classList.remove('hidden');
            return;
        }

        emptyElement.classList.add('hidden');

        this.currentTokens.forEach(token => {
            const item = this.createTokenItem(token);
            listElement.appendChild(item);
        });
    }

    createTokenItem(token) {
        const item = document.createElement('div');
        item.className = 'token-item bg-gray-800/30 rounded-lg p-4 flex items-center justify-between hover:bg-gray-800/50 transition-colors';
        
        const isExpired = new Date(token.expires_at) < new Date();
        const usesRemaining = token.max_uses === -1 ? '∞' : (token.max_uses - token.current_uses);
        
        item.innerHTML = `
            <div class="flex items-center space-x-4">
                <div class="w-10 h-10 ${isExpired ? 'bg-red-500/20' : 'bg-purple-500/20'} rounded-full flex items-center justify-center">
                    <i class="fas fa-link ${isExpired ? 'text-red-400' : 'text-purple-400'}"></i>
                </div>
                <div>
                    <div class="flex items-center space-x-2 mb-1">
                        <span class="text-white font-medium">Sharing Link</span>
                        <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${this.getRoleColor(token.role)}">
                            ${token.role.charAt(0).toUpperCase() + token.role.slice(1)}
                        </span>
                        ${isExpired ? '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-500/20 text-red-400">Expired</span>' : ''}
                    </div>
                    <div class="text-sm text-gray-400">
                        <div>Created: ${this.formatDate(token.created_at)}</div>
                        <div>Expires: ${this.formatDate(token.expires_at)}</div>
                        <div>Uses: ${token.current_uses}/${token.max_uses === -1 ? '∞' : token.max_uses} (${usesRemaining} remaining)</div>
                    </div>
                </div>
            </div>
            <div class="flex items-center space-x-2">
                ${!isExpired ? `
                    <button class="copy-token-btn text-blue-400 hover:text-blue-300 p-2 rounded-lg hover:bg-blue-500/10 transition-colors"
                            data-token="${token.token}" title="Copy Link">
                        <i class="fas fa-copy"></i>
                    </button>
                ` : ''}
                <button class="revoke-token-btn text-red-400 hover:text-red-300 p-2 rounded-lg hover:bg-red-500/10 transition-colors"
                        data-token-id="${token.id}" title="Revoke Token">
                    <i class="fas fa-ban"></i>
                </button>
            </div>
        `;

        // Add event listeners
        const copyBtn = item.querySelector('.copy-token-btn');
        if (copyBtn) {
            copyBtn.addEventListener('click', () => this.copyTokenLink(token.token));
        }

        const revokeBtn = item.querySelector('.revoke-token-btn');
        if (revokeBtn) {
            revokeBtn.addEventListener('click', () => this.revokeToken(token.id));
        }

        return item;
    }

    async copyTokenLink(token) {
        const fullUrl = `${window.location.origin}/sharing/accept/${token}`;
        try {
            await navigator.clipboard.writeText(fullUrl);
            this.showNotification('Sharing link copied to clipboard!', 'success');
        } catch (error) {
            this.showNotification('Failed to copy link', 'error');
        }
    }

    async revokeToken(tokenId) {
        if (!confirm('Are you sure you want to revoke this sharing link? This action cannot be undone.')) {
            return;
        }

        try {
            const response = await fetch(`/api/sharing/tokens/${tokenId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.showNotification('Sharing link revoked successfully', 'success');
                this.loadSharingTokens(); // Refresh the list
            } else {
                const result = await response.json();
                this.showNotification(result.error || 'Failed to revoke token', 'error');
            }
        } catch (error) {
            console.error('Error revoking token:', error);
            this.showNotification('Failed to revoke token', 'error');
        }
    }

    // Activity Log Management
    async loadActivityLog() {
        const loadingElement = document.getElementById('activity-loading');
        const emptyElement = document.getElementById('activity-empty');
        const timelineElement = document.getElementById('activity-timeline');

        loadingElement.classList.remove('hidden');
        emptyElement.classList.add('hidden');

        try {
            const params = new URLSearchParams({
                page: this.activityPage,
                ...this.activityFilters
            });

            const response = await fetch(`/api/projects/${this.projectId}/sharing/activity?${params}`);
            const result = await response.json();

            if (response.ok) {
                if (this.activityPage === 1) {
                    this.currentActivity = result.activities || [];
                } else {
                    this.currentActivity = [...this.currentActivity, ...(result.activities || [])];
                }
                
                this.renderActivityLog();
                
                // Show/hide load more button
                const loadMoreContainer = document.getElementById('load-more-container');
                if (result.has_more) {
                    loadMoreContainer.classList.remove('hidden');
                } else {
                    loadMoreContainer.classList.add('hidden');
                }
            } else {
                this.showNotification(result.error || 'Failed to load activity log', 'error');
            }
        } catch (error) {
            console.error('Error loading activity log:', error);
            this.showNotification('Failed to load activity log', 'error');
        } finally {
            loadingElement.classList.add('hidden');
        }
    }

    renderActivityLog() {
        const timelineElement = document.getElementById('activity-timeline');
        const emptyElement = document.getElementById('activity-empty');

        // Clear existing items except loading/empty states
        const existingItems = timelineElement.querySelectorAll('.activity-item');
        existingItems.forEach(item => item.remove());

        if (this.currentActivity.length === 0) {
            emptyElement.classList.remove('hidden');
            return;
        }

        emptyElement.classList.add('hidden');

        this.currentActivity.forEach(activity => {
            const item = this.createActivityItem(activity);
            timelineElement.appendChild(item);
        });
    }

    createActivityItem(activity) {
        const template = document.getElementById('activity-item-template');
        const item = template.content.cloneNode(true);
        
        const container = item.querySelector('.activity-item');
        const icon = item.querySelector('.activity-icon');
        const iconClass = item.querySelector('.activity-icon-class');
        const description = item.querySelector('.activity-description');
        const details = item.querySelector('.activity-details');
        const time = item.querySelector('.activity-time');
        const ipAddress = item.querySelector('.ip-address');
        const userAgent = item.querySelector('.user-agent');

        // Set activity type class and icon
        const activityClass = `activity-${activity.action.replace('_', '-')}`;
        icon.classList.add(activityClass);
        
        const activityIcons = {
            'project_shared': 'fas fa-share-alt',
            'collaborator_added': 'fas fa-user-plus',
            'collaborator_removed': 'fas fa-user-minus',
            'role_changed': 'fas fa-user-edit',
            'access_granted': 'fas fa-unlock',
            'access_revoked': 'fas fa-lock',
            'token_generated': 'fas fa-link',
            'token_used': 'fas fa-external-link-alt',
            'suspicious_access': 'fas fa-exclamation-triangle'
        };
        
        iconClass.className = `activity-icon-class ${activityIcons[activity.action] || 'fas fa-info-circle'}`;

        // Set content
        description.textContent = this.getActivityDescription(activity);
        details.textContent = activity.details || '';
        time.textContent = this.formatRelativeTime(activity.created_at);
        ipAddress.textContent = activity.ip_address || 'Unknown';
        userAgent.textContent = this.truncateUserAgent(activity.user_agent || 'Unknown');

        // Add click handler for details
        const viewDetailsBtn = item.querySelector('.view-details-btn');
        viewDetailsBtn.addEventListener('click', () => this.showActivityDetails(activity));

        return item;
    }

    getActivityDescription(activity) {
        const descriptions = {
            'project_shared': 'Project shared via invitation',
            'collaborator_added': `${activity.user_name || 'User'} was added as collaborator`,
            'collaborator_removed': `${activity.user_name || 'User'} was removed from project`,
            'role_changed': `${activity.user_name || 'User'}'s role was changed`,
            'access_granted': `Access granted to ${activity.user_name || 'user'}`,
            'access_revoked': `Access revoked for ${activity.user_name || 'user'}`,
            'token_generated': 'Sharing link was generated',
            'token_used': 'Sharing link was used',
            'suspicious_access': 'Suspicious access attempt detected'
        };
        
        return descriptions[activity.action] || 'Unknown activity';
    }

    formatRelativeTime(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        
        return date.toLocaleDateString();
    }

    truncateUserAgent(userAgent) {
        if (userAgent.length > 50) {
            return userAgent.substring(0, 47) + '...';
        }
        return userAgent;
    }

    showActivityDetails(activity) {
        const modal = document.getElementById('activity-detail-modal');
        const content = document.getElementById('activity-detail-content');
        
        content.innerHTML = `
            <div class="space-y-4">
                <div>
                    <h4 class="text-lg font-semibold text-white mb-2">${this.getActivityDescription(activity)}</h4>
                    <p class="text-gray-400">${activity.details || 'No additional details available.'}</p>
                </div>
                
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-300 mb-1">Timestamp</label>
                        <p class="text-white">${new Date(activity.created_at).toLocaleString()}</p>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-300 mb-1">User</label>
                        <p class="text-white">${activity.user_name || 'System'}</p>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-300 mb-1">IP Address</label>
                        <p class="text-white font-mono">${activity.ip_address || 'Unknown'}</p>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-300 mb-1">Action Type</label>
                        <p class="text-white">${activity.action.replace('_', ' ').toUpperCase()}</p>
                    </div>
                </div>
                
                ${activity.user_agent ? `
                    <div>
                        <label class="block text-sm font-medium text-gray-300 mb-1">User Agent</label>
                        <p class="text-white text-sm font-mono bg-gray-800 p-2 rounded">${activity.user_agent}</p>
                    </div>
                ` : ''}
            </div>
        `;
        
        modal.classList.remove('hidden');
    }

    applyActivityFilters() {
        const actionFilter = document.getElementById('activity-action-filter').value;
        const dateFilter = document.getElementById('activity-date-filter').value;
        const dateFrom = document.getElementById('activity-date-from').value;
        const dateTo = document.getElementById('activity-date-to').value;

        this.activityFilters = {};
        
        if (actionFilter) {
            this.activityFilters.action = actionFilter;
        }
        
        if (dateFilter && dateFilter !== 'all') {
            if (dateFilter === 'custom') {
                if (dateFrom) this.activityFilters.date_from = dateFrom;
                if (dateTo) this.activityFilters.date_to = dateTo;
            } else {
                this.activityFilters.date_range = dateFilter;
            }
        }

        this.activityPage = 1;
        this.loadActivityLog();
    }

    // Collaborator Management
    handleRoleChange(e) {
        const userId = e.target.dataset.userId;
        const currentRole = e.target.dataset.currentRole;
        const newRole = e.target.value;
        
        
        if (currentRole === newRole) return;

        // Show confirmation modal
        this.showRoleChangeConfirmation(userId, currentRole, newRole, e.target);
    }

    showRoleChangeConfirmation(userId, currentRole, newRole, selectElement) {
        const modal = document.getElementById('role-change-modal');
        const userSpan = document.getElementById('role-change-user');
        const fromSpan = document.getElementById('role-change-from');
        const toSpan = document.getElementById('role-change-to');
        
        // Find user name
        const collaborator = this.currentCollaborators.find(c => c.user_id == userId);
        userSpan.textContent = collaborator ? collaborator.name : 'User';
        fromSpan.textContent = currentRole.charAt(0).toUpperCase() + currentRole.slice(1);
        toSpan.textContent = newRole.charAt(0).toUpperCase() + newRole.slice(1);
        
        modal.classList.remove('hidden');
        
        // Handle confirmation
        const confirmBtn = document.getElementById('confirm-role-change');
        const cancelBtn = document.getElementById('cancel-role-change');
        
        const handleConfirm = () => {
            this.updateCollaboratorRole(userId, newRole);
            modal.classList.add('hidden');
            confirmBtn.removeEventListener('click', handleConfirm);
            cancelBtn.removeEventListener('click', handleCancel);
        };
        
        const handleCancel = () => {
            selectElement.value = currentRole; // Reset select
            modal.classList.add('hidden');
            confirmBtn.removeEventListener('click', handleConfirm);
            cancelBtn.removeEventListener('click', handleCancel);
        };
        
        confirmBtn.addEventListener('click', handleConfirm);
        cancelBtn.addEventListener('click', handleCancel);
    }

    async updateCollaboratorRole(userId, newRole) {
        try {
            if (!userId || userId === 'undefined' || userId === '') {
                this.showNotification('Invalid user ID for role update', 'error');
                return;
            }
            
            const response = await fetch(`/api/projects/${this.projectId}/collaborators/${userId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ role: newRole })
            });

            const result = await response.json();

            if (response.ok) {
                this.showNotification('Role updated successfully', 'success');
                this.loadCollaborators(); // Refresh the list
            } else {
                this.showNotification(result.error || 'Failed to update role', 'error');
                this.loadCollaborators(); // Refresh to reset UI
            }
        } catch (error) {
            console.error('Error updating role:', error);
            this.showNotification('Failed to update role', 'error');
            this.loadCollaborators();
        }
    }

    handleRemoveCollaborator(e) {
        const userId = e.target.dataset.userId;
        const userName = e.target.dataset.userName;
        
        this.showRemoveCollaboratorConfirmation(userId, userName);
    }

    showRemoveCollaboratorConfirmation(userId, userName) {
        const modal = document.getElementById('remove-collaborator-modal');
        const userSpan = document.getElementById('remove-collaborator-user');
        
        userSpan.textContent = userName;
        modal.classList.remove('hidden');
        
        const confirmBtn = document.getElementById('confirm-remove-collaborator');
        const cancelBtn = document.getElementById('cancel-remove-collaborator');
        
        const handleConfirm = () => {
            this.removeCollaborator(userId);
            modal.classList.add('hidden');
            confirmBtn.removeEventListener('click', handleConfirm);
            cancelBtn.removeEventListener('click', handleCancel);
        };
        
        const handleCancel = () => {
            modal.classList.add('hidden');
            confirmBtn.removeEventListener('click', handleConfirm);
            cancelBtn.removeEventListener('click', handleCancel);
        };
        
        confirmBtn.addEventListener('click', handleConfirm);
        cancelBtn.addEventListener('click', handleCancel);
    }

    async removeCollaborator(userId) {
        try {
            const response = await fetch(`/api/projects/${this.projectId}/collaborators/${userId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.showNotification('Collaborator removed successfully', 'success');
                this.loadCollaborators(); // Refresh the list
            } else {
                const result = await response.json();
                this.showNotification(result.error || 'Failed to remove collaborator', 'error');
            }
        } catch (error) {
            console.error('Error removing collaborator:', error);
            this.showNotification('Failed to remove collaborator', 'error');
        }
    }
}

// Initialize sharing manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Get project ID from the page (you might need to adjust this based on your template)
    const projectIdElement = document.querySelector('[data-project-id]');
    if (projectIdElement && !window.sharingManager) {
        const projectId = projectIdElement.dataset.projectId;
        window.sharingManager = new SharingManager(projectId);
    }
});