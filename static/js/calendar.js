// Calendar View JavaScript
class CalendarView {
    constructor(tasksData) {
        this.tasks = tasksData || [];
        this.currentDate = new Date();
        this.currentView = 'month'; // day, week, month
        this.calendarContainer = null;
        this.currentDateElement = null;
        this.expandedTasks = new Set(); // Track expanded tasks in day view
        this.eventListenersSetup = false; // Flag to prevent duplicate listeners
        this.taskEventListenersSetup = false; // Flag to prevent duplicate task listeners
        
        this.init();
    }
    
    init() {
        this.calendarContainer = document.getElementById('calendar-container');
        this.currentDateElement = document.getElementById('calendar-current-date');
        
        if (!this.calendarContainer) {
            console.error('Calendar container not found!');
            return;
        }
        
        this.setupEventListeners();
        this.render();
    }
    
    setupEventListeners() {
        // Prevent duplicate event listeners
        if (this.eventListenersSetup) {
            return;
        }
        
        // View toggle buttons
        const dayViewBtn = document.getElementById('calendar-day-view');
        const weekViewBtn = document.getElementById('calendar-week-view');
        const monthViewBtn = document.getElementById('calendar-month-view');
        
        if (dayViewBtn) dayViewBtn.addEventListener('click', () => this.setView('day'));
        if (weekViewBtn) weekViewBtn.addEventListener('click', () => this.setView('week'));
        if (monthViewBtn) monthViewBtn.addEventListener('click', () => this.setView('month'));
        
        // Navigation buttons
        const prevBtn = document.getElementById('calendar-prev');
        const nextBtn = document.getElementById('calendar-next');
        const todayBtn = document.getElementById('calendar-today');
        
        if (prevBtn) prevBtn.addEventListener('click', () => this.previous());
        if (nextBtn) nextBtn.addEventListener('click', () => this.next());
        if (todayBtn) todayBtn.addEventListener('click', () => this.today());
        
        // Modal close
        const closeModalBtn = document.getElementById('close-calendar-task-modal');
        const modal = document.getElementById('calendar-task-modal');
        
        if (closeModalBtn) {
            closeModalBtn.addEventListener('click', () => {
                if (modal) modal.classList.add('hidden');
            });
        }
        
        // Close modal on backdrop click
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target.id === 'calendar-task-modal') {
                    modal.classList.add('hidden');
                }
            });
        }
        
        // Set up task event listeners (only once)
        this.setupTaskEventListeners();
        
        this.eventListenersSetup = true;
    }
    
    setupTaskEventListeners() {
        // Prevent duplicate listeners
        if (this.taskEventListenersSetup) {
            return;
        }
        
        // Use document-level event delegation for task actions
        // This works even when calendarContainer is replaced on each render
        // We check if the click is within the calendar container
        document.addEventListener('click', (e) => {
            // Only handle clicks within calendar container
            if (!this.calendarContainer || !this.calendarContainer.contains(e.target)) {
                return;
            }
            
            if (e.target.closest('.task-details-toggle')) {
                const button = e.target.closest('.task-details-toggle');
                const taskId = parseInt(button.dataset.taskId);
                this.toggleTaskDetailsInDayView(taskId);
                e.stopPropagation();
            }
        });
        
        this.taskEventListenersSetup = true;
    }
    
    setView(view) {
        this.currentView = view;
        this.updateViewButtons();
        this.render();
    }
    
    updateViewButtons() {
        // Reset all buttons
        document.getElementById('calendar-day-view').className = 'px-3 py-1 text-xs font-medium rounded-md transition-all duration-200 text-gray-300 hover:text-white hover:bg-gray-700';
        document.getElementById('calendar-week-view').className = 'px-3 py-1 text-xs font-medium rounded-md transition-all duration-200 text-gray-300 hover:text-white hover:bg-gray-700';
        document.getElementById('calendar-month-view').className = 'px-3 py-1 text-xs font-medium rounded-md transition-all duration-200 text-gray-300 hover:text-white hover:bg-gray-700';
        
        // Highlight current view
        const currentButton = document.getElementById(`calendar-${this.currentView}-view`);
        currentButton.className = 'px-3 py-1 text-xs font-medium rounded-md transition-all duration-200 bg-blue-600 text-white';
    }
    
    previous() {
        switch (this.currentView) {
            case 'day':
                this.currentDate.setDate(this.currentDate.getDate() - 1);
                break;
            case 'week':
                this.currentDate.setDate(this.currentDate.getDate() - 7);
                break;
            case 'month':
                // Save the current day
                const currentDay = this.currentDate.getDate();
                // Move to first day of month to avoid setMonth() overflow issues
                this.currentDate.setDate(1);
                // Go back one month
                this.currentDate.setMonth(this.currentDate.getMonth() - 1);
                // Get the last day of the new month
                const lastDayOfMonth = new Date(this.currentDate.getFullYear(), this.currentDate.getMonth() + 1, 0).getDate();
                // Set to the appropriate day (use min to handle month-end dates)
                this.currentDate.setDate(Math.min(currentDay, lastDayOfMonth));
                break;
        }
        this.render();
    }
    
    next() {
        switch (this.currentView) {
            case 'day':
                this.currentDate.setDate(this.currentDate.getDate() + 1);
                break;
            case 'week':
                this.currentDate.setDate(this.currentDate.getDate() + 7);
                break;
            case 'month':
                // Save the current day
                const currentDay = this.currentDate.getDate();
                // Move to first day of month to avoid setMonth() overflow issues
                this.currentDate.setDate(1);
                // Go forward one month
                this.currentDate.setMonth(this.currentDate.getMonth() + 1);
                // Get the last day of the new month
                const lastDayOfMonth = new Date(this.currentDate.getFullYear(), this.currentDate.getMonth() + 1, 0).getDate();
                // Set to the appropriate day (use min to handle month-end dates)
                this.currentDate.setDate(Math.min(currentDay, lastDayOfMonth));
                break;
        }
        this.render();
    }
    
    today() {
        this.currentDate = new Date();
        this.render();
    }
    
    render() {
        this.updateCurrentDateDisplay();
        
        switch (this.currentView) {
            case 'day':
                this.renderDayView();
                break;
            case 'week':
                this.renderWeekView();
                break;
            case 'month':
                this.renderMonthView();
                break;
        }
    }
    
    updateCurrentDateDisplay() {
        const options = {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        };
        
        if (this.currentView === 'week') {
            const startOfWeek = this.getStartOfWeek(this.currentDate);
            const endOfWeek = new Date(startOfWeek);
            endOfWeek.setDate(startOfWeek.getDate() + 6);
            
            this.currentDateElement.textContent = 
                `${startOfWeek.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${endOfWeek.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`;
        } else {
            this.currentDateElement.textContent = this.currentDate.toLocaleDateString('en-US', options);
        }
    }
    
    getStartOfWeek(date) {
        const startOfWeek = new Date(date);
        const day = startOfWeek.getDay();
        const diff = startOfWeek.getDate() - day;
        startOfWeek.setDate(diff);
        return startOfWeek;
    }
    
    renderDayView() {
        const dateStr = this.currentDate.toISOString().split('T')[0];
        const tasksForDay = this.getTasksForDate(this.currentDate);
        
        let html = `
            <div class="bg-gray-800/30 rounded-xl p-6">
                <div class="flex items-center justify-between mb-4">
                    <h4 class="text-lg font-semibold text-white">${this.currentDate.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</h4>
                    <div class="flex items-center space-x-3">
                        <button onclick="window.calendarView.setView('month')" class="px-3 py-1 text-xs font-medium text-gray-300 hover:text-white hover:bg-gray-700 rounded-lg transition-all duration-200">
                            <i class="fas fa-arrow-left mr-1"></i>Back to Month
                        </button>
                        <span class="text-sm text-gray-400">${tasksForDay.length} task${tasksForDay.length !== 1 ? 's' : ''}</span>
                    </div>
                </div>
                <div class="space-y-3">
        `;
        
        if (tasksForDay.length === 0) {
            html += '<p class="text-gray-400 text-center py-8">No tasks for this day</p>';
        } else {
            tasksForDay.forEach(task => {
                html += this.renderTaskItem(task);
            });
        }
        
        html += '</div></div>';
        this.calendarContainer.innerHTML = html;
        
        // Event listeners are already set up via document-level delegation in setupTaskEventListeners()
    }
    
    renderWeekView() {
        const startOfWeek = this.getStartOfWeek(this.currentDate);
        const days = [];
        
        for (let i = 0; i < 7; i++) {
            const day = new Date(startOfWeek);
            day.setDate(startOfWeek.getDate() + i);
            days.push(day);
        }
        
        let html = '<div class="grid grid-cols-7 gap-4">';
        
        days.forEach((day, index) => {
            const tasksForDay = this.getTasksForDate(day);
            const isToday = day.toDateString() === new Date().toDateString();
            const isCurrentMonth = day.getMonth() === this.currentDate.getMonth();
            
            html += `
                <div class="bg-gray-800/30 rounded-xl p-4 ${!isCurrentMonth ? 'opacity-50' : ''}">
                    <div class="flex items-center justify-between mb-3">
                        <h5 class="text-sm font-semibold ${isToday ? 'text-blue-400' : 'text-white'}">
                            ${day.toLocaleDateString('en-US', { weekday: 'short' })}
                        </h5>
                        <span class="text-xs ${isToday ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300'} px-2 py-1 rounded-full">
                            ${day.getDate()}
                        </span>
                    </div>
                    <div class="space-y-2 min-h-[100px]">
            `;
            
            if (tasksForDay.length === 0) {
                html += '<p class="text-xs text-gray-500 text-center">No tasks</p>';
            } else {
                tasksForDay.slice(0, 3).forEach(task => {
                    html += this.renderTaskCard(task, true); // compact view
                });
                
                if (tasksForDay.length > 3) {
                    html += `<p class="text-xs text-gray-400 text-center">+${tasksForDay.length - 3} more</p>`;
                }
            }
            
            html += '</div></div>';
        });
        
        html += '</div>';
        this.calendarContainer.innerHTML = html;
    }
    
    renderMonthView() {
        const year = this.currentDate.getFullYear();
        const month = this.currentDate.getMonth();
        
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        const startDate = this.getStartOfWeek(firstDay);
        
        const days = [];
        const today = new Date();
        
        for (let i = 0; i < 42; i++) { // 6 weeks * 7 days
            const day = new Date(startDate);
            day.setDate(startDate.getDate() + i);
            days.push(day);
        }
        
        let html = `
            <div class="bg-gray-800/30 rounded-xl p-6">
                <div class="grid grid-cols-7 gap-1 mb-4">
                    <div class="text-center text-sm font-semibold text-gray-400 py-2">Sun</div>
                    <div class="text-center text-sm font-semibold text-gray-400 py-2">Mon</div>
                    <div class="text-center text-sm font-semibold text-gray-400 py-2">Tue</div>
                    <div class="text-center text-sm font-semibold text-gray-400 py-2">Wed</div>
                    <div class="text-center text-sm font-semibold text-gray-400 py-2">Thu</div>
                    <div class="text-center text-sm font-semibold text-gray-400 py-2">Fri</div>
                    <div class="text-center text-sm font-semibold text-gray-400 py-2">Sat</div>
                </div>
                <div class="grid grid-cols-7 gap-1">
        `;
        
        days.forEach((day, index) => {
            const tasksForDay = this.getTasksForDate(day);
            const isToday = day.toDateString() === today.toDateString();
            const isCurrentMonth = day.getMonth() === month;
            
            html += `
                <div class="min-h-[120px] p-2 border border-gray-700 rounded-lg ${!isCurrentMonth ? 'opacity-30' : ''} ${isToday ? 'bg-blue-900/30 border-blue-500' : 'hover:bg-gray-700/30'} transition-colors duration-200 cursor-pointer"
                     onclick="window.calendarView.zoomToDay(new Date('${day.toISOString()}'))">
                    <div class="flex items-center justify-between mb-1">
                        <span class="text-sm font-medium ${isToday ? 'text-blue-400' : isCurrentMonth ? 'text-white' : 'text-gray-500'}">
                            ${day.getDate()}
                        </span>
                        ${tasksForDay.length > 0 ? `<span class="text-xs bg-gray-600 text-gray-300 px-1.5 py-0.5 rounded-full">${tasksForDay.length}</span>` : ''}
                    </div>
                    <div class="space-y-1" onclick="event.stopPropagation()">
            `;
            
            tasksForDay.slice(0, 2).forEach(task => {
                // In month view, make tasks clickable to go to edit page
                html += this.renderTaskCard(task, true, true); // compact view, clickable
            });
            
            if (tasksForDay.length > 2) {
                html += `<p class="text-xs text-gray-400">+${tasksForDay.length - 2} more</p>`;
            }
            
            html += '</div></div>';
        });
        
        html += '</div></div>';
        this.calendarContainer.innerHTML = html;
    }
    
    getTasksForDate(date) {
        const dateStr = date.toISOString().split('T')[0];
        const tasks = [];
        
        this.tasks.forEach(task => {
            let taskDate = null;
            
            // If task has an end_date, use that
            if (task.end_date) {
                taskDate = new Date(task.end_date);
            }
            // If task has a start_date but no end_date, use start_date
            else if (task.start_date) {
                taskDate = new Date(task.start_date);
            }
            // If no dates at all, use created_at
            else if (task.created_at) {
                taskDate = new Date(task.created_at);
            }
            
            if (taskDate && taskDate.toISOString().split('T')[0] === dateStr) {
                tasks.push(task);
            }
        });
        
        return tasks.sort((a, b) => {
            // Sort by priority, then by title
            const priorityOrder = { 'high': 3, 'medium': 2, 'low': 1 };
            const aPriority = priorityOrder[a.priority] || 0;
            const bPriority = priorityOrder[b.priority] || 0;
            
            if (aPriority !== bPriority) {
                return bPriority - aPriority;
            }
            
            return a.title.localeCompare(b.title);
        });
    }
    
    renderTaskCard(task, compact = false, clickable = false) {
        const isCompleted = task.status === 'completed';
        const isOverdue = task.end_date && new Date(task.end_date) < new Date() && !isCompleted;
        const hasDueDate = task.end_date;
        const isCreatedDate = !hasDueDate && task.created_at;
        
        let colorClass = 'bg-blue-500';
        if (isCompleted) {
            colorClass = 'bg-green-500';
        } else if (isOverdue) {
            colorClass = 'bg-red-500';
        } else if (isCreatedDate) {
            colorClass = 'bg-purple-500';
        }
        
        const cardClass = compact ? 'text-xs p-2' : 'text-sm p-3';
        const titleClass = compact ? 'font-medium truncate' : 'font-semibold';
        
        // If clickable, switch to day view to show task details with all buttons
        const onClick = clickable 
            ? `window.calendarView.showTaskInDayView(${task.id})`
            : `window.calendarView.showTaskModal(${task.id})`;
        
        return `
            <div class="bg-gray-700/50 rounded-lg ${cardClass} cursor-pointer hover:bg-gray-600/50 transition-colors duration-200" 
                 onclick="${onClick}">
                <div class="flex items-center space-x-2">
                    <div class="w-2 h-2 rounded-full ${colorClass} flex-shrink-0"></div>
                    <div class="flex-1 min-w-0">
                        <div class="${titleClass} text-white truncate">${task.title}</div>
                        ${!compact ? `<div class="text-xs text-gray-400 mt-1">${task.status} • ${task.priority}</div>` : ''}
                    </div>
                </div>
            </div>
        `;
    }
    
    renderTaskItem(task) {
        // Render task using the same structure as the main task view
        // This matches the task-item structure from project_detail.html
        const isCompleted = task.status === 'completed';
        const isOverdue = task.end_date && new Date(task.end_date) < new Date() && !isCompleted;
        const userPermissions = window.userPermissions || {};
        const projectId = window.projectId || 0;
        
        // Status icon
        let statusIcon = 'fa-circle text-gray-500';
        if (task.status === 'completed') {
            statusIcon = 'fa-check-circle text-green-400';
        } else if (task.status === 'in_progress') {
            statusIcon = 'fa-play-circle text-blue-400';
        } else if (task.status === 'blocked') {
            statusIcon = 'fa-exclamation-circle text-red-400';
        }
        
        // Priority badge
        const priorityClass = task.priority === 'high' 
            ? 'bg-red-500/20 text-red-400' 
            : task.priority === 'medium' 
            ? 'bg-yellow-500/20 text-yellow-400' 
            : 'bg-green-500/20 text-green-400';
        
        // Size badge
        const sizeClass = task.size === 'large' 
            ? 'bg-purple-500/20 text-purple-400' 
            : task.size === 'medium' 
            ? 'bg-blue-500/20 text-blue-400' 
            : 'bg-gray-500/20 text-gray-400';
        
        // Risk indicator
        let riskBadge = '';
        if (task.risk_level && task.risk_level !== 'low') {
            const riskClass = task.risk_level === 'critical' 
                ? 'bg-red-500/20 text-red-400' 
                : task.risk_level === 'high' 
                ? 'bg-orange-500/20 text-orange-400' 
                : 'bg-yellow-500/20 text-yellow-400';
            riskBadge = `<span class="risk-indicator inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${riskClass}">
                <i class="fas fa-exclamation-triangle mr-1"></i>
                ${task.risk_level.charAt(0).toUpperCase() + task.risk_level.slice(1)} Risk
            </span>`;
        }
        
        // Flag indicator
        let flagBadge = '';
        if (task.is_flagged) {
            const flagClass = task.flag_resolved ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400';
            flagBadge = `<span class="flag-indicator inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${flagClass}">
                <i class="fas fa-flag mr-1"></i>
                ${task.flag_resolved ? 'Flag Resolved' : 'Flagged'}
            </span>`;
        }
        
        // Labels
        let labelsHtml = '';
        if (task.labels && task.labels.length > 0) {
            labelsHtml = `<div class="flex flex-wrap gap-1 max-w-32">
                ${task.labels.map(label => `
                    <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium" style="background-color: ${label.color}20; color: ${label.color};">
                        ${label.icon ? `<i class="${label.icon} mr-1 text-xs"></i>` : ''}
                        ${label.name}
                    </span>
                `).join('')}
            </div>`;
        }
        
        // Dates
        let dateInfo = '';
        if (task.start_date || task.end_date) {
            const start = task.start_date ? new Date(task.start_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '';
            const end = task.end_date ? new Date(task.end_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '';
            dateInfo = start && end ? `<span class="text-gray-500">${start} → ${end}</span>` : 
                      start ? `<span class="text-gray-500">${start}</span>` : 
                      end ? `<span class="text-gray-500">→ ${end}</span>` : '';
        }
        
        // Description preview
        let descriptionPreview = '';
        if (task.description) {
            const desc = task.description.length > 100 ? task.description.substring(0, 100) + '...' : task.description;
            descriptionPreview = `<p class="text-gray-400 mt-1">${this.escapeHtml(desc)}</p>`;
        }
        
        // Task Actions buttons
        let actionButtons = '';
        if (userPermissions.can_edit_tasks || userPermissions.can_flag_tasks || userPermissions.can_assign_tasks) {
            actionButtons = `<div class="flex items-center space-x-1">
                ${userPermissions.can_edit_tasks ? `
                <button class="workflow-btn px-3 py-1.5 text-xs font-medium text-white rounded-md transition-all duration-200 bg-blue-600 hover:bg-blue-700" 
                        data-task-id="${task.id}" data-workflow-status="${task.workflow_status || 'backlog'}" 
                        title="Workflow: ${task.workflow_button_text || 'Start'}">
                    <i class="fas fa-play mr-1"></i>${task.workflow_button_text || 'Start'}
                </button>
                ` : ''}
                ${userPermissions.can_create_tasks ? `
                <button class="create-child-task-btn px-3 py-1.5 text-xs font-medium text-white rounded-md transition-all duration-200 bg-purple-600 hover:bg-purple-700" 
                        data-task-id="${task.id}" data-task-title="${this.escapeHtml(task.title)}" title="Create Child Tasks">
                    <i class="fas fa-plus mr-1"></i>Add Child
                </button>
                ` : ''}
            </div>`;
        }
        
        // Task details dropdown content (hidden by default)
        let taskDetailsContent = this.renderTaskDetailsContent(task, userPermissions, projectId);
        
        return `
            <div class="task-item px-6 py-4 hover:bg-gray-800/30 transition-colors duration-200" 
                 data-task-id="${task.id}" data-parent-id="${task.parent_id || ''}">
                <div class="flex items-center justify-between">
                    <div class="flex items-center space-x-4 flex-1">
                        <div class="w-4"></div>
                        <div class="flex-shrink-0">
                            <i class="fas ${statusIcon} text-xl"></i>
                        </div>
                        <div class="flex-1">
                            <div class="flex items-center space-x-2">
                                <h3 class="text-lg font-medium text-white cursor-pointer hover:text-blue-400 transition-colors duration-200"
                                    onclick="window.calendarView.toggleTaskDetailsInDayView(${task.id})">
                                    ${this.escapeHtml(task.title)}
                                </h3>
                                ${riskBadge}
                                ${flagBadge}
                            </div>
                            ${descriptionPreview}
                            <div class="flex items-center space-x-4 mt-3 text-sm">
                                <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${priorityClass}">
                                    ${task.priority ? task.priority.charAt(0).toUpperCase() + task.priority.slice(1) : 'Medium'}
                                </span>
                                <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${sizeClass}">
                                    ${task.size ? task.size.charAt(0).toUpperCase() + task.size.slice(1) : 'Medium'}
                                </span>
                                <span class="text-gray-500">${task.owner_name || 'Unknown'}</span>
                                ${dateInfo}
                            </div>
                        </div>
                    </div>
                    <div class="flex items-center space-x-2">
                        ${labelsHtml}
                        ${actionButtons}
                        <button class="task-details-toggle text-gray-500 hover:text-blue-400 p-1.5 rounded-md hover:bg-blue-500/10 transition-all duration-200" 
                                data-task-id="${task.id}" title="View Task Details">
                            <i class="fas fa-chevron-down text-sm transition-transform duration-200"></i>
                        </button>
                    </div>
                </div>
                ${taskDetailsContent}
            </div>
        `;
    }
    
    renderTaskDetailsContent(task, userPermissions, projectId) {
        // Render the task details dropdown content matching the template structure
        const isCompleted = task.status === 'completed';
        const isOverdue = task.end_date && new Date(task.end_date) < new Date() && !isCompleted;
        
        // Flag button
        let flagButton = '';
        if (userPermissions.can_flag_tasks) {
            const flagStatus = task.is_flagged 
                ? (task.flag_resolved ? 'resolved' : 'flagged') 
                : 'not_flagged';
            const flagClass = flagStatus === 'resolved' 
                ? 'bg-green-600 hover:bg-green-700' 
                : flagStatus === 'flagged' 
                ? 'bg-red-600 hover:bg-red-700' 
                : 'bg-orange-600 hover:bg-orange-700';
            const flagText = flagStatus === 'resolved' 
                ? 'Flag Resolved' 
                : flagStatus === 'flagged' 
                ? 'Flagged' 
                : (task.discussion_comments ? 'View Discussion' : 'Flag Task');
            flagButton = `<button class="task-flag-btn px-4 py-2 text-sm font-medium text-white rounded-lg transition-all duration-200 ${flagClass}" 
                            data-task-id="${task.id}" data-flag-status="${flagStatus}">
                            <i class="fas fa-flag mr-2"></i>${flagText}
                        </button>`;
        }
        
        // Other action buttons
        let manageDepsButton = '';
        if (userPermissions.can_edit_tasks) {
            manageDepsButton = `<button class="manage-dependencies px-4 py-2 text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 rounded-lg transition-all duration-200" 
                                      data-task-id="${task.id}" title="Manage Dependencies">
                                      <i class="fas fa-project-diagram mr-2"></i>Manage Dependencies
                                  </button>`;
        }
        
        let assignButton = '';
        if (userPermissions.can_assign_tasks) {
            assignButton = `<button class="assign-task px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-lg transition-all duration-200" 
                                   data-task-id="${task.id}" data-assigned-to="${task.assigned_to || ''}" title="Assign Task">
                                   <i class="fas fa-user-plus mr-2"></i>Assign Task
                               </button>`;
        }
        
        let deleteButton = '';
        if (userPermissions.can_edit_tasks) {
            deleteButton = `<form method="POST" action="/projects/${projectId}/tasks/${task.id}/delete" class="inline" 
                                 onsubmit="return confirm('Are you sure you want to delete this task?')">
                                 <button type="submit" class="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-all duration-200" 
                                         title="Delete Task">
                                     <i class="fas fa-trash mr-2"></i>Delete Task
                                 </button>
                             </form>`;
        }
        
        // Description
        let descriptionHtml = '';
        if (task.description) {
            descriptionHtml = `<div>
                <h4 class="text-sm font-semibold text-gray-300 mb-2 flex items-center">
                    <i class="fas fa-align-left mr-2 text-blue-400"></i>Description
                </h4>
                <div class="text-gray-300 text-sm leading-relaxed whitespace-pre-wrap">${this.escapeHtml(task.description)}</div>
            </div>`;
        }
        
        // Risk information
        let riskHtml = '';
        if (task.risk_level && task.risk_level !== 'low') {
            const riskClass = task.risk_level === 'critical' 
                ? 'bg-red-500/20 text-red-400' 
                : task.risk_level === 'high' 
                ? 'bg-orange-500/20 text-orange-400' 
                : 'bg-yellow-500/20 text-yellow-400';
            riskHtml = `<div>
                <h4 class="text-sm font-semibold text-gray-300 mb-2 flex items-center">
                    <i class="fas fa-exclamation-triangle mr-2 text-orange-400"></i>Risk Assessment
                </h4>
                <div class="space-y-2">
                    <div class="flex items-center space-x-2">
                        <span class="text-xs text-gray-400">Level:</span>
                        <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${riskClass}">
                            ${task.risk_level.charAt(0).toUpperCase() + task.risk_level.slice(1)}
                        </span>
                    </div>
                    ${task.risk_description ? `<div><span class="text-xs text-gray-400 block mb-1">Description:</span><div class="text-gray-300 text-sm">${this.escapeHtml(task.risk_description)}</div></div>` : ''}
                    ${task.mitigation_plan ? `<div><span class="text-xs text-gray-400 block mb-1">Mitigation Plan:</span><div class="text-gray-300 text-sm">${this.escapeHtml(task.mitigation_plan)}</div></div>` : ''}
                </div>
            </div>`;
        }
        
        // Dates
        const startDate = task.start_date ? new Date(task.start_date).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }) : null;
        const endDate = task.end_date ? new Date(task.end_date).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }) : null;
        const createdDate = task.created_at ? new Date(task.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }) : null;
        const updatedDate = task.updated_at ? new Date(task.updated_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }) : null;
        
        return `
            <div class="task-details-content hidden bg-gray-800/30 border-t border-gray-700 px-6 py-4">
                <div class="mb-6 pb-4 border-b border-gray-700">
                    <h4 class="text-sm font-semibold text-gray-300 mb-3 flex items-center">
                        <i class="fas fa-cogs mr-2 text-blue-400"></i>Task Actions
                    </h4>
                    <div class="flex flex-wrap gap-3">
                        ${flagButton}
                        ${manageDepsButton}
                        ${assignButton}
                        ${deleteButton}
                    </div>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div class="space-y-4">
                        ${descriptionHtml}
                        ${riskHtml}
                    </div>
                    <div class="space-y-4">
                        <div>
                            <h4 class="text-sm font-semibold text-gray-300 mb-2 flex items-center">
                                <i class="fas fa-info-circle mr-2 text-green-400"></i>Task Information
                            </h4>
                            <div class="space-y-2 text-sm">
                                <div class="flex justify-between">
                                    <span class="text-gray-400">Status:</span>
                                    <span class="text-white">${task.status ? task.status.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()) : 'Backlog'}</span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-gray-400">Priority:</span>
                                    <span class="text-white">${task.priority ? task.priority.charAt(0).toUpperCase() + task.priority.slice(1) : 'Medium'}</span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-gray-400">Size:</span>
                                    <span class="text-white">${task.size ? task.size.charAt(0).toUpperCase() + task.size.slice(1) : 'Medium'}</span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-gray-400">Owner:</span>
                                    <span class="text-white">${task.owner_name || 'Unknown'}</span>
                                </div>
                                ${startDate ? `<div class="flex justify-between"><span class="text-gray-400">Start Date:</span><span class="text-white">${startDate}</span></div>` : ''}
                                ${endDate ? `<div class="flex justify-between"><span class="text-gray-400">End Date:</span><span class="text-white">${endDate}</span></div>` : ''}
                                ${createdDate ? `<div class="flex justify-between"><span class="text-gray-400">Created:</span><span class="text-white">${createdDate}</span></div>` : ''}
                                ${updatedDate ? `<div class="flex justify-between"><span class="text-gray-400">Updated:</span><span class="text-white">${updatedDate}</span></div>` : ''}
                            </div>
                        </div>
                        ${task.dependencies && task.dependencies.length > 0 ? `
                        <div>
                            <h4 class="text-sm font-semibold text-gray-300 mb-2 flex items-center">
                                <i class="fas fa-project-diagram mr-2 text-purple-400"></i>Dependencies
                            </h4>
                            <div class="space-y-1">
                                ${task.dependencies.map(dep => `
                                    <div class="flex items-center space-x-2">
                                        <i class="fas fa-arrow-right text-gray-400 text-xs"></i>
                                        <span class="text-gray-300 text-sm">${this.escapeHtml(dep.depends_on_title)}</span>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
    }
    
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    renderExpandableTaskCard(task) {
        const isCompleted = task.status === 'completed';
        const isOverdue = task.end_date && new Date(task.end_date) < new Date() && !isCompleted;
        const hasDueDate = task.end_date;
        const isCreatedDate = !hasDueDate && task.created_at;
        const isExpanded = this.expandedTasks.has(task.id);
        
        let colorClass = 'bg-blue-500';
        if (isCompleted) {
            colorClass = 'bg-green-500';
        } else if (isOverdue) {
            colorClass = 'bg-red-500';
        } else if (isCreatedDate) {
            colorClass = 'bg-purple-500';
        }
        
        let statusColor = 'text-blue-400';
        if (isCompleted) {
            statusColor = 'text-green-400';
        } else if (isOverdue) {
            statusColor = 'text-red-400';
        } else if (isCreatedDate) {
            statusColor = 'text-purple-400';
        }
        
        return `
            <div class="bg-gray-700/50 rounded-lg border border-gray-600 overflow-hidden">
                <div class="p-4 cursor-pointer hover:bg-gray-600/50 transition-colors duration-200" 
                     onclick="window.calendarView.toggleTaskExpand(${task.id})">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center space-x-3 flex-1 min-w-0">
                            <div class="w-3 h-3 rounded-full ${colorClass} flex-shrink-0"></div>
                            <div class="flex-1 min-w-0">
                                <div class="font-semibold text-white">${task.title}</div>
                                <div class="text-xs text-gray-400 mt-1">${task.status} • ${task.priority}</div>
                            </div>
                        </div>
                        <button class="text-gray-400 hover:text-white transition-colors">
                            <i class="fas fa-chevron-${isExpanded ? 'up' : 'down'}"></i>
                        </button>
                    </div>
                </div>
                ${isExpanded ? `
                <div class="px-4 pb-4 pt-2 border-t border-gray-600 bg-gray-800/30">
                    <div class="space-y-3">
                        ${task.description ? `
                        <div>
                            <span class="text-xs font-medium text-gray-400 uppercase">Description</span>
                            <p class="text-sm text-gray-300 mt-1">${task.description || 'No description'}</p>
                        </div>
                        ` : ''}
                        
                        <div class="grid grid-cols-2 gap-4 text-sm">
                            <div>
                                <span class="text-gray-400">Status:</span>
                                <span class="ml-2 ${statusColor} font-medium">${task.status}</span>
                            </div>
                            <div>
                                <span class="text-gray-400">Priority:</span>
                                <span class="ml-2 text-white font-medium">${task.priority}</span>
                            </div>
                            ${task.start_date ? `
                            <div>
                                <span class="text-gray-400">Start Date:</span>
                                <span class="ml-2 text-white">${new Date(task.start_date).toLocaleDateString()}</span>
                            </div>
                            ` : ''}
                            ${task.end_date ? `
                            <div>
                                <span class="text-gray-400">Due Date:</span>
                                <span class="ml-2 text-white">${new Date(task.end_date).toLocaleDateString()}</span>
                            </div>
                            ` : ''}
                            ${!hasDueDate && task.created_at ? `
                            <div>
                                <span class="text-gray-400">Created:</span>
                                <span class="ml-2 text-white">${new Date(task.created_at).toLocaleDateString()}</span>
                            </div>
                            ` : ''}
                        </div>
                        
                        ${task.labels && task.labels.length > 0 ? `
                        <div>
                            <span class="text-xs font-medium text-gray-400 uppercase">Labels</span>
                            <div class="flex flex-wrap gap-1 mt-2">
                                ${task.labels.map(label => `
                                    <span class="px-2 py-1 text-xs rounded-full" style="background-color: ${label.color}20; color: ${label.color};">
                                        ${label.name}
                                    </span>
                                `).join('')}
                            </div>
                        </div>
                        ` : ''}
                    </div>
                </div>
                ` : ''}
            </div>
        `;
    }
    
    toggleTaskExpand(taskId) {
        if (this.expandedTasks.has(taskId)) {
            this.expandedTasks.delete(taskId);
        } else {
            this.expandedTasks.add(taskId);
        }
        // Only re-render if we're in day view
        if (this.currentView === 'day') {
            this.render();
        }
    }
    
    zoomToDay(day) {
        this.currentDate = new Date(day);
        this.setView('day');
    }
    
    showTaskInDayView(taskId) {
        const task = this.tasks.find(t => t.id === taskId);
        if (!task) return;
        
        // Determine which date to show
        let targetDate = new Date();
        if (task.end_date) {
            targetDate = new Date(task.end_date);
        } else if (task.start_date) {
            targetDate = new Date(task.start_date);
        } else if (task.created_at) {
            targetDate = new Date(task.created_at);
        }
        
        // Switch to day view for that date
        this.currentDate = targetDate;
        this.setView('day');
        
        // After rendering, expand the task details
        setTimeout(() => {
            this.toggleTaskDetailsInDayView(taskId);
        }, 100);
    }
    
    toggleTaskDetailsInDayView(taskId) {
        const taskItem = this.calendarContainer.querySelector(`[data-task-id="${taskId}"].task-item`);
        if (!taskItem) return;
        
        const detailsContent = taskItem.querySelector('.task-details-content');
        const toggleButton = taskItem.querySelector('.task-details-toggle');
        
        if (!detailsContent || !toggleButton) return;
        
        const chevronIcon = toggleButton.querySelector('i');
        
        if (detailsContent.classList.contains('hidden')) {
            // Show details
            detailsContent.classList.remove('hidden');
            chevronIcon.style.transform = 'rotate(180deg)';
            toggleButton.title = 'Hide Task Details';
            
            // Add smooth animation
            detailsContent.style.maxHeight = '0';
            detailsContent.style.overflow = 'hidden';
            detailsContent.style.transition = 'max-height 0.3s ease-out';
            
            // Trigger reflow
            detailsContent.offsetHeight;
            
            // Set final height
            detailsContent.style.maxHeight = detailsContent.scrollHeight + 'px';
            
            // Remove height constraint after animation
            setTimeout(() => {
                detailsContent.style.maxHeight = 'none';
                detailsContent.style.overflow = 'visible';
            }, 300);
        } else {
            // Hide details
            detailsContent.style.maxHeight = detailsContent.scrollHeight + 'px';
            detailsContent.style.overflow = 'hidden';
            detailsContent.style.transition = 'max-height 0.3s ease-in';
            
            // Trigger reflow
            detailsContent.offsetHeight;
            
            // Collapse
            detailsContent.style.maxHeight = '0';
            
            setTimeout(() => {
                detailsContent.classList.add('hidden');
                detailsContent.style.maxHeight = 'none';
                detailsContent.style.overflow = 'visible';
                detailsContent.style.transition = 'none';
            }, 300);
            
            chevronIcon.style.transform = 'rotate(0deg)';
            toggleButton.title = 'View Task Details';
        }
    }
    
    showTaskModal(taskId) {
        const task = this.tasks.find(t => t.id === taskId);
        if (!task) return;
        
        const modal = document.getElementById('calendar-task-modal');
        const content = document.getElementById('calendar-task-content');
        
        const isCompleted = task.status === 'completed';
        const isOverdue = task.end_date && new Date(task.end_date) < new Date() && !isCompleted;
        const hasDueDate = task.end_date;
        const isCreatedDate = !hasDueDate && task.created_at;
        
        let statusColor = 'text-blue-400';
        if (isCompleted) {
            statusColor = 'text-green-400';
        } else if (isOverdue) {
            statusColor = 'text-red-400';
        } else if (isCreatedDate) {
            statusColor = 'text-purple-400';
        }
        
        content.innerHTML = `
            <div class="space-y-4">
                <div>
                    <h4 class="text-lg font-semibold text-white mb-2">${task.title}</h4>
                    ${task.description ? `<p class="text-gray-300 text-sm">${task.description}</p>` : ''}
                </div>
                
                <div class="grid grid-cols-2 gap-4 text-sm">
                    <div>
                        <span class="text-gray-400">Status:</span>
                        <span class="ml-2 ${statusColor} font-medium">${task.status}</span>
                    </div>
                    <div>
                        <span class="text-gray-400">Priority:</span>
                        <span class="ml-2 text-white font-medium">${task.priority}</span>
                    </div>
                    ${task.start_date ? `
                    <div>
                        <span class="text-gray-400">Start Date:</span>
                        <span class="ml-2 text-white">${new Date(task.start_date).toLocaleDateString()}</span>
                    </div>
                    ` : ''}
                    ${task.end_date ? `
                    <div>
                        <span class="text-gray-400">Due Date:</span>
                        <span class="ml-2 text-white">${new Date(task.end_date).toLocaleDateString()}</span>
                    </div>
                    ` : ''}
                    ${!hasDueDate && task.created_at ? `
                    <div>
                        <span class="text-gray-400">Created:</span>
                        <span class="ml-2 text-white">${new Date(task.created_at).toLocaleDateString()}</span>
                    </div>
                    ` : ''}
                </div>
                
                ${task.labels && task.labels.length > 0 ? `
                <div>
                    <span class="text-gray-400 text-sm">Labels:</span>
                    <div class="flex flex-wrap gap-1 mt-1">
                        ${task.labels.map(label => `
                            <span class="px-2 py-1 text-xs rounded-full" style="background-color: ${label.color}20; color: ${label.color};">
                                ${label.name}
                            </span>
                        `).join('')}
                    </div>
                </div>
                ` : ''}
            </div>
        `;
        
        modal.classList.remove('hidden');
    }
}

// Global calendar instance
let calendarView = null;

// Initialize calendar when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // This will be initialized when the calendar view is shown
    if (typeof tasksData !== 'undefined') {
        calendarView = new CalendarView(tasksData);
    }
});

// Function to initialize calendar with tasks data
function initializeCalendar(tasks) {
    calendarView = new CalendarView(tasks);
}

// Function to re-setup event listeners (useful when calendar is shown after DOM load)
function setupCalendarEventListeners() {
    if (window.calendarView) {
        window.calendarView.setupEventListeners();
    }
}
