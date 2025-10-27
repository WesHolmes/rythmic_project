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
    
    // Toggle panel open/close
    function togglePanel() {
        isOpen = !isOpen;
        if (isOpen) {
            aiPanelContainer.classList.remove('hidden');
            // Focus on input when opened
            setTimeout(() => aiChatInput.focus(), 100);
        } else {
            aiPanelContainer.classList.add('hidden');
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

