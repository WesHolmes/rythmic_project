// Main JavaScript file for Rhythmic Project - Dark Theme

// Auto-hide flash messages with smooth animation
document.addEventListener('DOMContentLoaded', function() {
    const flashMessages = document.querySelectorAll('.bg-blue-500\\/10');
    flashMessages.forEach(function(message) {
        setTimeout(function() {
            message.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            message.style.opacity = '0';
            message.style.transform = 'translateY(-10px)';
            setTimeout(function() {
                message.remove();
            }, 500);
        }, 5000);
    });
});

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Add loading states to forms (excluding forms with custom handlers)
document.querySelectorAll('form').forEach(form => {
    // Skip forms that have custom handlers (like sharing forms)
    if (form.id === 'email-sharing-form' || form.id === 'link-sharing-form') {
        return;
    }
    
    form.addEventListener('submit', function() {
        const submitBtn = this.querySelector('button[type="submit"]');
        if (submitBtn) {
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<div class="spinner mr-2"></div>Loading...';
            submitBtn.disabled = true;
            
            // Re-enable after 10 seconds as fallback
            setTimeout(() => {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }, 10000);
        }
    });
});

// Add hover effects to cards
document.querySelectorAll('.card-hover').forEach(card => {
    card.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-4px)';
    });
    
    card.addEventListener('mouseleave', function() {
        this.style.transform = 'translateY(0)';
    });
});


// Add intersection observer for fade-in animations
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('animate-fadeInUp');
        }
    });
}, observerOptions);

// Observe all cards and sections
document.querySelectorAll('.card-hover, .glass').forEach(el => {
    observer.observe(el);
});

// Add keyboard navigation support
document.addEventListener('keydown', function(e) {
    // ESC key to close modals or clear focus
    if (e.key === 'Escape') {
        const activeElement = document.activeElement;
        if (activeElement && activeElement.blur) {
            activeElement.blur();
        }
    }
});

// Add form validation feedback
document.querySelectorAll('input, textarea, select').forEach(input => {
    input.addEventListener('blur', function() {
        if (this.checkValidity()) {
            this.classList.add('border-green-500');
            this.classList.remove('border-red-500');
        } else {
            this.classList.add('border-red-500');
            this.classList.remove('border-green-500');
        }
    });
    
    input.addEventListener('input', function() {
        if (this.classList.contains('border-red-500') && this.checkValidity()) {
            this.classList.remove('border-red-500');
            this.classList.add('border-green-500');
        }
    });
});

// Project Board Drag and Drop Functionality
document.addEventListener('DOMContentLoaded', function() {
    const projectsBoard = document.getElementById('projects-board');
    const projectCards = document.querySelectorAll('.project-card');
    const dropIndicator = document.getElementById('drop-indicator');
    
    if (!projectsBoard || projectCards.length === 0) return;
    
    let draggedElement = null;
    let draggedIndex = null;
    let dropTargetIndex = null;
    
    // Initialize drag and drop for each project card
    projectCards.forEach((card, index) => {
        card.addEventListener('dragstart', handleDragStart);
        card.addEventListener('dragend', handleDragEnd);
        card.addEventListener('dragover', handleDragOver);
        card.addEventListener('dragenter', handleDragEnter);
        card.addEventListener('dragleave', handleDragLeave);
        card.addEventListener('drop', handleDrop);
    });
    
    function handleDragStart(e) {
        draggedElement = this;
        draggedIndex = Array.from(projectCards).indexOf(this);
        
        this.classList.add('dragging');
        projectsBoard.classList.add('drag-active');
        
        // Set drag data
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/html', this.outerHTML);
        
        // Add visual feedback
        setTimeout(() => {
            this.style.opacity = '0.5';
        }, 0);
    }
    
    function handleDragEnd(e) {
        this.classList.remove('dragging');
        projectsBoard.classList.remove('drag-active');
        this.style.opacity = '';
        
        // Remove drag over effects from all cards
        projectCards.forEach(card => {
            card.classList.remove('drag-over');
        });
        
        hideDropIndicator();
        
        // Reset variables
        draggedElement = null;
        draggedIndex = null;
        dropTargetIndex = null;
    }
    
    function handleDragOver(e) {
        if (e.preventDefault) {
            e.preventDefault();
        }
        
        e.dataTransfer.dropEffect = 'move';
        return false;
    }
    
    function handleDragEnter(e) {
        if (this !== draggedElement) {
            this.classList.add('drag-over');
            dropTargetIndex = Array.from(projectCards).indexOf(this);
            showDropIndicator(this);
        }
    }
    
    function handleDragLeave(e) {
        // Only remove drag-over if we're actually leaving the element
        if (!this.contains(e.relatedTarget)) {
            this.classList.remove('drag-over');
        }
    }
    
    function handleDrop(e) {
        if (e.stopPropagation) {
            e.stopPropagation();
        }
        
        if (draggedElement !== this) {
            // Swap the positions
            swapElements(draggedElement, this);
            
            // Show success feedback
            showDropSuccess();
        }
        
        this.classList.remove('drag-over');
        return false;
    }
    
    function swapElements(elem1, elem2) {
        const parent = elem1.parentNode;
        const next1 = elem1.nextElementSibling;
        const next2 = elem2.nextElementSibling;
        
        if (next1 === elem2) {
            parent.insertBefore(elem2, elem1);
        } else if (next2 === elem1) {
            parent.insertBefore(elem1, elem2);
        } else {
            if (next1) {
                parent.insertBefore(elem2, next1);
            } else {
                parent.appendChild(elem2);
            }
            
            if (next2) {
                parent.insertBefore(elem1, next2);
            } else {
                parent.appendChild(elem1);
            }
        }
        
        // Add animation effect
        elem1.classList.add('drag-pulse');
        elem2.classList.add('drag-pulse');
        
        setTimeout(() => {
            elem1.classList.remove('drag-pulse');
            elem2.classList.remove('drag-pulse');
        }, 1500);
    }
    
    function showDropIndicator(targetElement) {
        const rect = targetElement.getBoundingClientRect();
        dropIndicator.style.left = rect.left + 'px';
        dropIndicator.style.top = (rect.top - 60) + 'px';
        dropIndicator.style.width = rect.width + 'px';
        dropIndicator.classList.remove('hidden');
    }
    
    function hideDropIndicator() {
        dropIndicator.classList.add('hidden');
    }
    
    function showDropSuccess() {
        // Create a temporary success message
        const successMsg = document.createElement('div');
        successMsg.className = 'fixed top-4 right-4 bg-green-500/20 border border-green-400 text-green-400 px-4 py-2 rounded-lg z-50';
        successMsg.innerHTML = '<i class="fas fa-check mr-2"></i>Project position updated!';
        document.body.appendChild(successMsg);
        
        setTimeout(() => {
            successMsg.style.opacity = '0';
            successMsg.style.transform = 'translateX(100%)';
            setTimeout(() => successMsg.remove(), 300);
        }, 2000);
    }
    
    // Add keyboard support for accessibility
    projectCards.forEach(card => {
        card.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                // Toggle selection for keyboard users
                this.classList.toggle('drag-pulse');
            }
        });
    });
    
    // Save layout to localStorage (optional persistence)
    function saveLayout() {
        const layout = Array.from(projectCards).map(card => ({
            id: card.dataset.projectId,
            name: card.dataset.projectName
        }));
        localStorage.setItem('projectsLayout', JSON.stringify(layout));
    }
    
    // Auto-save layout after drag operations
    projectsBoard.addEventListener('dragend', saveLayout);
});
