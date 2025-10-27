// AI Panel JavaScript
document.addEventListener('DOMContentLoaded', function() {
    const aiPanel = document.getElementById('ai-panel');
    const aiPanelToggle = document.getElementById('ai-panel-toggle');
    const aiPanelContainer = document.getElementById('ai-panel-container');
    const aiPanelClose = document.getElementById('ai-panel-close');
    const aiChatForm = document.getElementById('ai-chat-form');
    const aiChatInput = document.getElementById('ai-chat-input');
    const aiChatMessages = document.getElementById('ai-chat-messages');
    const aiTypingIndicator = document.getElementById('ai-typing-indicator');
    
    if (!aiPanel || !aiPanelToggle || !aiPanelContainer || !aiChatForm) {
        console.error('AI panel elements not found');
        return;
    }
    
    let isOpen = false;
    let insightsLoaded = false;
    
    // Toggle panel open/close
    function togglePanel() {
        isOpen = !isOpen;
        if (isOpen) {
            aiPanelContainer.classList.remove('hidden');
            // Focus on input when opened
            setTimeout(() => aiChatInput.focus(), 100);
            // Load insights if not already loaded
            if (!insightsLoaded) {
                loadInsights();
                insightsLoaded = true;
            }
        } else {
            aiPanelContainer.classList.add('hidden');
        }
    }
    
    // Load and display AI insights
    async function loadInsights() {
        try {
            const response = await fetch('/api/ai-insights');
            const data = await response.json();
            
            if (data.stale_tasks && data.stale_tasks.length > 0 || data.at_risk_tasks && data.at_risk_tasks.length > 0) {
                let insightsHtml = '<div class="ai-message bot-message">';
                insightsHtml += '<div class="message-content">';
                insightsHtml += '<div class="message-avatar"><i class="fas fa-robot"></i></div>';
                insightsHtml += '<div class="message-bubble">';
                insightsHtml += '<h4 class="text-orange-400 mb-2">⚠️ Task Reminders:</h4>';
                
                if (data.stale_tasks && data.stale_tasks.length > 0) {
                    insightsHtml += `<p class="text-sm mb-2"><strong>Stale Tasks (${data.stale_tasks.length}):</strong> Not updated in 30+ days</p>`;
                    insightsHtml += '<ul class="list-disc list-inside space-y-1 text-sm">';
                    data.stale_tasks.slice(0, 5).forEach(task => {
                        insightsHtml += `<li><strong>${task.title}</strong> - ${task.days_stale} days stale</li>`;
                    });
                    insightsHtml += '</ul>';
                    if (data.stale_tasks.length > 5) {
                        insightsHtml += `<p class="text-sm text-gray-400 mt-1">...and ${data.stale_tasks.length - 5} more</p>`;
                    }
                }
                
                if (data.at_risk_tasks && data.at_risk_tasks.length > 0) {
                    insightsHtml += `<p class="text-sm mt-2 mb-2"><strong>At-Risk Tasks (${data.at_risk_tasks.length}):</strong> Due within 7 days or overdue</p>`;
                    insightsHtml += '<ul class="list-disc list-inside space-y-1 text-sm">';
                    data.at_risk_tasks.slice(0, 5).forEach(task => {
                        const statusText = task.is_overdue 
                            ? `${Math.abs(task.days_until_due)} days overdue` 
                            : `${task.days_until_due} days remaining`;
                        insightsHtml += `<li><strong>${task.title}</strong> - ${statusText}</li>`;
                    });
                    insightsHtml += '</ul>';
                    if (data.at_risk_tasks.length > 5) {
                        insightsHtml += `<p class="text-sm text-gray-400 mt-1">...and ${data.at_risk_tasks.length - 5} more</p>`;
                    }
                }
                
                insightsHtml += '<p class="text-sm mt-3 text-gray-300">Ask me "show stale tasks" or "show at-risk tasks" for more details.</p>';
                insightsHtml += '</div></div></div>';
                
                // Insert after welcome message (first message)
                const firstMessage = aiChatMessages.querySelector('.ai-message');
                if (firstMessage && firstMessage.nextSibling) {
                    aiChatMessages.insertBefore(
                        document.createRange().createContextualFragment(insightsHtml),
                        firstMessage.nextSibling
                    );
                } else if (firstMessage) {
                    // If no nextSibling, append after the first message
                    firstMessage.insertAdjacentHTML('afterend', insightsHtml);
                }
                
                // Scroll to bottom to show the insights
                setTimeout(() => {
                    aiChatMessages.scrollTop = aiChatMessages.scrollHeight;
                }, 100);
            }
        } catch (error) {
            console.error('Error loading insights:', error);
        }
    }
    
    // Event listeners
    aiPanelToggle.addEventListener('click', togglePanel);
    aiPanelClose.addEventListener('click', togglePanel);
    
    // Close panel when clicking outside
    document.addEventListener('click', function(e) {
        if (isOpen && !aiPanel.contains(e.target)) {
            togglePanel();
        }
    });
    
    // Prevent panel from closing when clicking inside
    aiPanelContainer.addEventListener('click', function(e) {
        e.stopPropagation();
    });
    
    // Add message to chat
    function addMessage(content, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `ai-message ${isUser ? 'user-message' : 'bot-message'}`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = isUser ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';
        
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        bubble.innerHTML = content;
        
        messageContent.appendChild(avatar);
        messageContent.appendChild(bubble);
        messageDiv.appendChild(messageContent);
        
        aiChatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        aiChatMessages.scrollTop = aiChatMessages.scrollHeight;
        
        return messageDiv;
    }
    
    // Show typing indicator
    function showTypingIndicator() {
        aiTypingIndicator.classList.remove('hidden');
    }
    
    // Hide typing indicator
    function hideTypingIndicator() {
        aiTypingIndicator.classList.add('hidden');
    }
    
    // Handle chat form submission
    aiChatForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const message = aiChatInput.value.trim();
        if (!message) return;
        
        // Clear input
        aiChatInput.value = '';
        
        // Add user message
        addMessage(message, true);
        
        // Show typing indicator
        showTypingIndicator();
        
        try {
            // Send message to backend
            const response = await fetch('/api/ai-chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    timestamp: new Date().toISOString()
                })
            });
            
            const data = await response.json();
            
            // Hide typing indicator
            hideTypingIndicator();
            
            if (data.response) {
                addMessage(data.response, false);
            } else {
                addMessage('I apologize, but I encountered an error processing your request.', false);
            }
        } catch (error) {
            console.error('AI chat error:', error);
            hideTypingIndicator();
            addMessage('I apologize, but there was an error connecting to the AI service.', false);
        }
    });
    
    // Keyboard shortcuts
    aiChatInput.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            if (isOpen) {
                togglePanel();
            }
        }
    });
});

