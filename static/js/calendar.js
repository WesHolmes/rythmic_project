// Calendar View JavaScript
class CalendarView {
    constructor(tasksData) {
        this.tasks = tasksData || [];
        this.currentDate = new Date();
        this.currentView = 'day'; // day, week, month
        this.calendarContainer = null;
        this.currentDateElement = null;
        
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
        // View toggle buttons
        document.getElementById('calendar-day-view').addEventListener('click', () => this.setView('day'));
        document.getElementById('calendar-week-view').addEventListener('click', () => this.setView('week'));
        document.getElementById('calendar-month-view').addEventListener('click', () => this.setView('month'));
        
        // Navigation buttons
        document.getElementById('calendar-prev').addEventListener('click', () => this.previous());
        document.getElementById('calendar-next').addEventListener('click', () => this.next());
        document.getElementById('calendar-today').addEventListener('click', () => this.today());
        
        // Modal close
        document.getElementById('close-calendar-task-modal').addEventListener('click', () => {
            document.getElementById('calendar-task-modal').classList.add('hidden');
        });
        
        // Close modal on backdrop click
        document.getElementById('calendar-task-modal').addEventListener('click', (e) => {
            if (e.target.id === 'calendar-task-modal') {
                document.getElementById('calendar-task-modal').classList.add('hidden');
            }
        });
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
                this.currentDate.setMonth(this.currentDate.getMonth() - 1);
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
                this.currentDate.setMonth(this.currentDate.getMonth() + 1);
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
                    <span class="text-sm text-gray-400">${tasksForDay.length} task${tasksForDay.length !== 1 ? 's' : ''}</span>
                </div>
                <div class="space-y-3">
        `;
        
        if (tasksForDay.length === 0) {
            html += '<p class="text-gray-400 text-center py-8">No tasks for this day</p>';
        } else {
            tasksForDay.forEach(task => {
                html += this.renderTaskCard(task);
            });
        }
        
        html += '</div></div>';
        this.calendarContainer.innerHTML = html;
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
                <div class="min-h-[120px] p-2 border border-gray-700 rounded-lg ${!isCurrentMonth ? 'opacity-30' : ''} ${isToday ? 'bg-blue-900/30 border-blue-500' : 'hover:bg-gray-700/30'} transition-colors duration-200">
                    <div class="flex items-center justify-between mb-1">
                        <span class="text-sm font-medium ${isToday ? 'text-blue-400' : isCurrentMonth ? 'text-white' : 'text-gray-500'}">
                            ${day.getDate()}
                        </span>
                        ${tasksForDay.length > 0 ? `<span class="text-xs bg-gray-600 text-gray-300 px-1.5 py-0.5 rounded-full">${tasksForDay.length}</span>` : ''}
                    </div>
                    <div class="space-y-1">
            `;
            
            tasksForDay.slice(0, 2).forEach(task => {
                html += this.renderTaskCard(task, true); // compact view
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
    
    renderTaskCard(task, compact = false) {
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
        
        return `
            <div class="bg-gray-700/50 rounded-lg ${cardClass} cursor-pointer hover:bg-gray-600/50 transition-colors duration-200" 
                 onclick="calendarView.showTaskModal(${task.id})">
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
