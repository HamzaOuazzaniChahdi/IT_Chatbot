// Global variables
let currentChatId = initialChatId;
let isDeepSearchActive = false;
let isDeepThinkActive = false;
let isEphemeralActive = false;
let hasAttachedImage = false;
let pendingConfirmation = false;

// DOM Elements
const sidebar = document.getElementById('sidebar');
const toggleSidebarBtn = document.getElementById('toggleSidebar');
const chatArea = document.querySelector('.chat-area');
const messagesContainer = document.getElementById('messagesContainer');
const welcomeMessage = document.getElementById('welcomeMessage');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const newChatButton = document.getElementById('newChatButton');
const chatHistory = document.getElementById('chatHistory');
const deepSearchButton = document.getElementById('deepSearchButton');
const deepThinkButton = document.getElementById('deepThinkButton');
const imageInput = document.getElementById('imageInput');
const ephemeralToggle = document.getElementById('ephemeralToggle');
const confirmationModal = document.getElementById('confirmationModal');
const confirmYesButton = document.getElementById('confirmYes');
const confirmNoButton = document.getElementById('confirmNo');
const loadingIndicator = document.getElementById('loadingIndicator');

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    // Setup event listeners
    setupEventListeners();
    
    // Load chat history
    loadChatHistory();
    
    // Load messages for current chat
    loadMessages(currentChatId);
});

// Setup all event listeners
function setupEventListeners() {
    // Sidebar toggle
    toggleSidebarBtn.addEventListener('click', toggleSidebar);
    
    // Message input auto-resize
    messageInput.addEventListener('input', autoResizeTextarea);
    
    // Send message
    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // New chat
    newChatButton.addEventListener('click', createNewChat);
    
    // Mode toggles
    deepSearchButton.addEventListener('click', toggleDeepSearch);
    deepThinkButton.addEventListener('click', toggleDeepThink);
    
    // Image upload
    imageInput.addEventListener('change', handleImageUpload);
    
    // Ephemeral messages toggle
    ephemeralToggle.addEventListener('click', toggleEphemeral);
    
    // Confirmation modal buttons
    confirmYesButton.addEventListener('click', () => handleConfirmation('Y'));
    confirmNoButton.addEventListener('click', () => handleConfirmation('N'));
}

// Toggle sidebar visibility
function toggleSidebar() {
    sidebar.classList.toggle('open');
    toggleSidebarBtn.classList.toggle('shifted');
    chatArea.classList.toggle('sidebar-open');
}

// Auto-resize textarea as user types
function autoResizeTextarea() {
    messageInput.style.height = 'auto';
    messageInput.style.height = (messageInput.scrollHeight) + 'px';
}

// Send a message
function sendMessage() {
    const message = messageInput.value.trim();
    
    // Don't send if empty message and no image
    if (!message && !hasAttachedImage) return;
    
    // Display user message immediately
    if (message || hasAttachedImage) {
        appendMessage({
            content: hasAttachedImage ? 'Image ajoutée' : message,
            sender: 'user',
            has_image: hasAttachedImage
        });
        
        // Hide welcome message if visible
        if (!welcomeMessage.classList.contains('hidden')) {
            welcomeMessage.classList.add('hidden');
        }
        
        // Clear input and reset height
        messageInput.value = '';
        messageInput.style.height = 'auto';
        
        // Show loading indicator
        loadingIndicator.style.display = 'block';
        
        // Send to server
        const requestData = {
            chat_id: currentChatId,
            message: message,
            deep_search: isDeepSearchActive,
            deep_think: isDeepThinkActive,
            has_image: hasAttachedImage
        };
        
        fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        })
        .then(response => response.json())
        .then(data => {
            // Hide loading indicator
            loadingIndicator.style.display = 'none';
            
            // Check if confirmation is required (DeepThink mode)
            if (data.require_confirmation) {
                pendingConfirmation = true;
                confirmationModal.classList.add('show');
                document.querySelector('.modal-message').textContent = data.message;
            } else if (data.response) {
                // Display bot response
                appendMessage({
                    content: data.response,
                    sender: 'bot'
                });
            }
            
            // Reset image flag after sending
            hasAttachedImage = false;
        })
        .catch(error => {
            console.error('Error sending message:', error);
            loadingIndicator.style.display = 'none';
            hasAttachedImage = false;
        });
    }
}

// Handle confirmation modal response
function handleConfirmation(answer) {
    confirmationModal.classList.remove('show');
    pendingConfirmation = false;
    
    // Show loading indicator
    loadingIndicator.style.display = 'block';
    
    // Send confirmation to server
    fetch('/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            chat_id: currentChatId,
            confirmation: answer,
            deep_think: true
        })
    })
    .then(response => response.json())
    .then(data => {
        // Hide loading indicator
        loadingIndicator.style.display = 'none';
        
        // Display bot response
        if (data.response) {
            appendMessage({
                content: data.response,
                sender: 'bot'
            });
        }
    })
    .catch(error => {
        console.error('Error sending confirmation:', error);
        loadingIndicator.style.display = 'none';
    });
}

// Create a new chat
function createNewChat() {
    fetch('/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ new_chat: true })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update current chat ID
            currentChatId = data.chat_id;
            
            // Reload chat history
            loadChatHistory();
            
            // Show welcome message
            welcomeMessage.classList.remove('hidden');
            
            // Clear messages
            messagesContainer.innerHTML = '';
            messagesContainer.appendChild(welcomeMessage);
            
            // Reset special modes
            isDeepSearchActive = false;
            isDeepThinkActive = false;
            deepSearchButton.classList.remove('active');
            deepThinkButton.classList.remove('active');
            
            // Reset ephemeral status
            isEphemeralActive = false;
            ephemeralToggle.classList.remove('active');
        }
    })
    .catch(error => {
        console.error('Error creating new chat:', error);
    });
}

// Load chat history
function loadChatHistory() {
    fetch('/chat_history')
    .then(response => response.json())
    .then(chats => {
        // Clear current history
        chatHistory.innerHTML = '';
        
        // Add each chat to the sidebar
        chats.forEach(chat => {
            const chatItem = document.createElement('div');
            chatItem.classList.add('chat-item');
            chatItem.setAttribute('data-id', chat.id);
            
            if (chat.id === currentChatId) {
                chatItem.classList.add('active');
            }
            
            chatItem.innerHTML = `
                <div class="chat-item-name">${chat.name}</div>
                <button class="rename-button">
                    <i class="fas fa-edit"></i>
                </button>
            `;
            
            // Chat item click
            chatItem.addEventListener('click', (e) => {
                if (e.target.closest('.rename-button') || e.target.closest('.rename-input')) {
                    return; // Don't load messages if renaming
                }
                loadMessages(chat.id);
            });
            
            // Setup rename functionality
            const renameButton = chatItem.querySelector('.rename-button');
            renameButton.addEventListener('click', () => {
                enableRenaming(chatItem, chat.id, chat.name);
            });
            
            chatHistory.appendChild(chatItem);
        });
    })
    .catch(error => {
        console.error('Error loading chat history:', error);
    });
}

// Enable renaming of a chat
function enableRenaming(chatItem, chatId, currentName) {
    const nameElement = chatItem.querySelector('.chat-item-name');
    const originalContent = nameElement.innerHTML;
    
    // Create input field
    nameElement.innerHTML = `<input type="text" class="rename-input" value="${currentName}">`;
    const inputField = nameElement.querySelector('.rename-input');
    inputField.focus();
    inputField.select();
    
    // Submit on Enter or blur
    const submitRename = () => {
        const newName = inputField.value.trim();
        if (newName && newName !== currentName) {
            // Send rename request
            fetch('/rename_chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    chat_id: chatId,
                    name: newName
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    nameElement.innerHTML = data.name;
                } else {
                    nameElement.innerHTML = originalContent;
                }
            })
            .catch(error => {
                console.error('Error renaming chat:', error);
                nameElement.innerHTML = originalContent;
            });
        } else {
            nameElement.innerHTML = originalContent;
        }
    };
    
    inputField.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            submitRename();
        } else if (e.key === 'Escape') {
            nameElement.innerHTML = originalContent;
        }
    });
    
    inputField.addEventListener('blur', submitRename);
}

// Load messages for a specific chat
function loadMessages(chatId) {
    fetch(`/chat_messages?chat_id=${chatId}`)
    .then(response => response.json())
    .then(data => {
        // Update current chat ID
        currentChatId = chatId;
        
        // Update active chat in sidebar
        document.querySelectorAll('.chat-item').forEach(item => {
            item.classList.remove('active');
            if (item.getAttribute('data-id') === chatId) {
                item.classList.add('active');
            }
        });
        
        // Update ephemeral status
        isEphemeralActive = data.chat.ephemeral;
        if (isEphemeralActive) {
            ephemeralToggle.classList.add('active');
        } else {
            ephemeralToggle.classList.remove('active');
        }
        
        // Clear current messages
        messagesContainer.innerHTML = '';
        
        // Recreate welcome message (needed after clearing)
        const welcomeMsg = document.createElement('div');
        welcomeMsg.id = 'welcomeMessage';
        welcomeMsg.className = 'welcome-message';
        welcomeMsg.innerHTML = '<div class="welcome-text">Comment puis-je vous aider ?</div>';
        messagesContainer.appendChild(welcomeMsg);
        
        // Show welcome message if no messages
        if (data.messages.length === 0) {
            welcomeMsg.classList.remove('hidden');
        } else {
            welcomeMsg.classList.add('hidden');
            
            // Display messages
            data.messages.forEach(message => {
                appendMessage(message);
            });
        }
        
        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    })
    .catch(error => {
        console.error('Error loading messages:', error);
    });
}

// Append a message to the chat
function appendMessage(message) {
    // Create message wrapper
    const messageWrapper = document.createElement('div');
    messageWrapper.className = 'message-wrapper';
    
    // Create message container
    const messageElement = document.createElement('div');
    messageElement.className = 'message';
    
    // Create avatar
    const avatar = document.createElement('div');
    avatar.className = `avatar ${message.sender}`;
    avatar.innerHTML = message.sender === 'user' 
        ? '<i class="fas fa-user"></i>' 
        : '<i class="fas fa-robot"></i>';
    
    // Create message content
    const content = document.createElement('div');
    content.className = `message-content ${message.sender}`;
    content.textContent = message.content;
    
    // Assemble message
    messageElement.appendChild(avatar);
    messageElement.appendChild(content);
    messageWrapper.appendChild(messageElement);
    
    // Add to messages container
    messagesContainer.appendChild(messageWrapper);
    
    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Toggle DeepSearch mode
function toggleDeepSearch() {
    isDeepSearchActive = !isDeepSearchActive;
    deepSearchButton.classList.toggle('active');
    
    // Deactivate DeepThink if DeepSearch is activated
    if (isDeepSearchActive && isDeepThinkActive) {
        isDeepThinkActive = false;
        deepThinkButton.classList.remove('active');
    }
}

// Toggle DeepThink mode
function toggleDeepThink() {
    isDeepThinkActive = !isDeepThinkActive;
    deepThinkButton.classList.toggle('active');
    
    // Deactivate DeepSearch if DeepThink is activated
    if (isDeepThinkActive && isDeepSearchActive) {
        isDeepSearchActive = false;
        deepSearchButton.classList.remove('active');
    }
}

// Handle image upload
function handleImageUpload(event) {
    const file = event.target.files[0];
    if (file) {
        hasAttachedImage = true;
        // You could display a preview here
        messageInput.placeholder = "Image attachée. Ajouter un commentaire ?";
    }
}

// Toggle ephemeral messages
function toggleEphemeral() {
    fetch('/toggle_ephemeral', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ chat_id: currentChatId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            isEphemeralActive = data.ephemeral;
            ephemeralToggle.classList.toggle('active', isEphemeralActive);
            
            // Show confirmation message
            const status = isEphemeralActive ? 'activés' : 'désactivés';
            appendMessage({
                content: `Messages éphémères ${status}. ${isEphemeralActive ? 'Les messages expireront après 5 minutes.' : ''}`,
                sender: 'bot'
            });
        }
    })
    .catch(error => {
        console.error('Error toggling ephemeral mode:', error);
    });
}
