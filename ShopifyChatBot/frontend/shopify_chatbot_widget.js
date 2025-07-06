// Configuration
const API_BASE_URL = 'https://shopify-chatbot-trial.onrender.com/api/chat';
const HISTORY_API_URL = 'https://shopify-chatbot-trial.onrender.com/api/session';
const CUSTOMER_UPDATE_URL = 'https://shopify-chatbot-trial.onrender.com/api/customer/update';
let sessionId = localStorage.getItem('shopifyChatbotSessionId') || null;
let customerName = localStorage.getItem('shopifyChatbotCustomerName') || null;

console.log('Script loaded. Initial sessionId:', sessionId);
console.log('Initial customerName:', customerName);

const widgetContainer = document.getElementById('shopify-chatbot-widget');
if (widgetContainer) {
    widgetContainer.innerHTML = `
        <button id="chat-toggle-button" class="chat-toggle-button">💬</button>
        <div id="chat-window" class="chat-window chat-window-hidden">
            <div class="chat-header">
                <span>Shopify Chatbot</span>
                <button id="chat-close-button" class="chat-close-button">&times;</button>
            </div>
            <div id="chat-messages" class="chat-messages"></div>
            <div class="chat-input-area">
                <input id="chat-input" class="chat-input" type="text" placeholder="Type your message..." autocomplete="off" />
                <button id="chat-send-button" class="chat-send-button">Send</button>
            </div>
            <button id="new-chat-button" class="new-chat-button">New Chat</button>
        </div>
    `;
}

// DOM Elements
const chatToggleButton = document.getElementById('chat-toggle-button');
const chatCloseButton = document.getElementById('chat-close-button');
const chatWindow = document.getElementById('chat-window');
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const chatSendButton = document.getElementById('chat-send-button');
const newChatButton = document.getElementById('new-chat-button'); // New chat button

// Helper to check if user is logged into Shopify
async function checkShopifyCustomer() {
    try {
        // Placeholder for Shopify customer check
        // Implement your logic here if needed
        return null;
    } catch (error) {
        console.error('Error checking Shopify customer:', error);
        return null;
    }
}

// Helper to update customer info
async function updateCustomerInfo(name) {
    if (!sessionId) return;
    try {
        const response = await fetch(CUSTOMER_UPDATE_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, session_id: sessionId }),
        });
        const data = await response.json();
        if (data.success) {
            customerName = name;
            localStorage.setItem('shopifyChatbotCustomerName', customerName);
        }
    } catch (error) {
        console.error('Error updating customer info:', error);
    }
}

// Check cart and prompt for recovery   
function checkCartAndPrompt() {
    fetch('/cart.js')
      .then(res => res.json())
      .then(cart => {
        if (cart.items && cart.items.length > 0) {
          // Show a recovery message in the chat
          showBotMessage("You have items in your cart! Need help checking out or have questions?");
          // Optionally, list the items
          cart.items.forEach(item => {
            showBotMessage(`- ${item.quantity} x ${item.product_title}`);
          });
          // Example upsell
          showBotMessage("Customers who bought these items also loved our accessories! Would you like a recommendation?");
        }
      });
  }

// Helper to render all messages in the chat UI
function renderMessages(messages) {
    chatMessages.innerHTML = ''; // Clear existing messages
    messages.forEach(msg => {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        if (msg.role === 'user') {
            messageDiv.classList.add('user-message');
        } else {
            messageDiv.classList.add('bot-message');
        }
        messageDiv.textContent = msg.content;
        chatMessages.appendChild(messageDiv);
    });
    scrollToBottom();
}

// Helper to scroll messages to the bottom
function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Load history when chat window opens
async function loadChatHistory() {
    console.log('loadChatHistory called. Current sessionId:', sessionId);
    if (sessionId) {
        try {
            const response = await fetch(`${HISTORY_API_URL}/${sessionId}`);
            const data = await response.json();
            // Check if the history array exists and is not empty
            if (data && data.history && data.history.length > 0) {
                renderMessages(data.history);
            } else {
                // If no history, check for customer name and prompt if needed
                if (!customerName) {
                    addInitialBotMessage("Hi! I'd like to personalize our chat. What's your name?");
                } else {
                    addInitialBotMessage(`Hello ${customerName}! How can I assist you today?`);
                }
            }
        } catch (error) {
            console.error('Error fetching chat history:', error);
            addInitialBotMessage("Hello! How can I assist you today?");
        }
    } else {
        // No session ID, so this is a new visitor
        if (!customerName) {
            addInitialBotMessage("Hi! I'd like to personalize our chat. What's your name?");
        } else {
            addInitialBotMessage(`Hello ${customerName}! How can I assist you today?`);
        }
    }
}

function addInitialBotMessage(message) {
    renderMessages([{
        role: 'bot',
        content: message
    }]);
}

// Toggle chat window visibility
chatToggleButton.addEventListener('click', () => {
    chatWindow.classList.toggle('chat-window-hidden');
    if (!chatWindow.classList.contains('chat-window-hidden')) {
        loadChatHistory();
        chatInput.focus();
        checkCartAndPrompt();
    }
});

// New chat button event listener
if (newChatButton) {
    newChatButton.addEventListener('click', () => {
        // Clear session and customer info from local storage
        localStorage.removeItem('shopifyChatbotSessionId');
        localStorage.removeItem('shopifyChatbotCustomerName');
        
        // Reset in-memory variables
        sessionId = null;
        customerName = null;
        
        // Clear the chat messages and load the initial prompt
        chatMessages.innerHTML = '';
        loadChatHistory();
        
        console.log('New chat started. Session cleared.');
    });
}

chatCloseButton.addEventListener('click', () => {
    chatWindow.classList.add('chat-window-hidden');
});

// Send message function
async function sendMessage() {
    const message = chatInput.value.trim();
    if (!message) return;

    // Handle the case where the user is providing their name
    const isNameSubmission = !customerName && chatMessages.textContent.includes("What's your name?");
    if (isNameSubmission) {
        customerName = message;
        localStorage.setItem('shopifyChatbotCustomerName', customerName);
        await updateCustomerInfo(customerName);
        addInitialBotMessage(`Nice to meet you, ${customerName}! How can I help you?`);
        chatInput.value = '';
        return;
    }

    // Add user message to UI
    const currentMessages = Array.from(chatMessages.children).map(div => ({
        role: div.classList.contains('user-message') ? 'user' : 'bot',
        content: div.textContent
    }));
    renderMessages([...currentMessages, { role: 'user', content: message }]);
    chatInput.value = '';
    scrollToBottom();

    try {
        const response = await fetch(API_BASE_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message, session_id: sessionId }),
        });
        const data = await response.json();
        console.log('Raw API response:', data);

        // Use data.data for the actual response
        const payload = data.data || {};
        if (payload.response && payload.session_id) {
            console.log('Entering SUCCESS block');
            sessionId = payload.session_id;
            localStorage.setItem('shopifyChatbotSessionId', sessionId);
            console.log('Session ID confirmed from backend:', sessionId);

            // Update customer info if it's in the response
            if (payload.customer_info && payload.customer_info.name) {
                customerName = payload.customer_info.name;
                localStorage.setItem('shopifyChatbotCustomerName', customerName);
                console.log('Customer name updated from backend:', customerName);
            }

            // Render the messages
            renderMessages(payload.history);
        } else {
            console.log('Entering ERROR block');
            const errorMessage = data.message || 'Unknown error occurred';
            renderMessages([
                ...(chatMessages.children ? Array.from(chatMessages.children).map(div => ({
                    role: div.classList.contains('user-message') ? 'user' : 'bot',
                    content: div.textContent
                })) : []),
                { role: 'bot', content: `Error from chatbot: ${errorMessage}` }
            ]);
            console.error('API Error:', data);
        }
    } catch (error) {
        renderMessages([
            ...(chatMessages.children ? Array.from(chatMessages.children).map(div => ({
                role: div.classList.contains('user-message') ? 'user' : 'bot',
                content: div.textContent
            })) : []),
            { role: 'bot', content: "Error contacting chatbot." }
        ]);
        console.error('Fetch error:', error);
    }
}

// Event listeners for sending messages
if (chatSendButton) {
    chatSendButton.addEventListener('click', sendMessage);
}
if (chatInput) {
    chatInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            sendMessage();
        }
    });
}

// Optionally, load history or show initial message when the script loads
// window.addEventListener('load', () => {
//     // If the widget is meant to be closed initially, load history only on toggle button click
//     // If you want it open by default and history loaded on page load, uncomment this.
// });

function showBotMessage(message) {
  const chatMessages = document.getElementById('chat-messages');
  const messageDiv = document.createElement('div');
  messageDiv.className = 'message bot-message';
  messageDiv.textContent = message;
  chatMessages.appendChild(messageDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}