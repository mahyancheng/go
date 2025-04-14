const userInput = document.getElementById('userInput');
const sendButton = document.getElementById('sendButton');
const chatHistory = document.getElementById('chatHistory');
const agentActivity = document.getElementById('agentActivity');
const finalResults = document.getElementById('finalResults');
const modelSelect = document.getElementById('modelSelect'); // Get the dropdown

// --- WebSocket Connection ---
// Connects to the FastAPI backend's /ws endpoint
const wsUrl = `ws://${window.location.hostname}:8000/ws`; // Assumes backend on port 8000
let socket;
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;
const reconnectInterval = 5000; // 5 seconds

function connectWebSocket() {
    if (reconnectAttempts >= maxReconnectAttempts) {
        console.error("Max reconnect attempts reached.");
        appendMessage(agentActivity, 'Error: Could not connect to agent. Please check backend and refresh.', 'agent-error');
        return;
    }
    console.log(`Connecting to WebSocket at ${wsUrl} (Attempt ${reconnectAttempts + 1})...`);
    if (reconnectAttempts === 0) { // Clear logs only on first attempt
        agentActivity.innerHTML = '<p class="message agent-activity">Connecting to agent...</p>';
        finalResults.innerHTML = '<p class="message agent-activity">No results yet.</p>';
    }

    socket = new WebSocket(wsUrl);

    socket.onopen = (event) => {
        console.log('WebSocket connection opened:', event);
        reconnectAttempts = 0;
        agentActivity.innerHTML = '<p class="message agent-activity">Connected to agent. Ready for input.</p>';
        if (chatHistory.children.length === 0 || (chatHistory.children.length === 1 && chatHistory.firstElementChild.textContent.includes("Welcome"))) {
            chatHistory.innerHTML = '<p class="message agent-activity">Welcome! Select a model and enter your query.</p>';
        }
    };

    socket.onmessage = (event) => {
        console.log('WebSocket message received:', event.data);
        const message = event.data;

        // Route messages based on prefix
        if (message.startsWith('Agent: Final Response:')) {
            const resultText = message.split("Agent: Final Response:", 1)[1].trim();
            finalResults.innerHTML = ''; // Clear previous final results
            appendMessage(finalResults, resultText, 'agent-final');
        } else if (message.startsWith('Agent Error:')) {
            const errorText = message.split("Agent Error:", 1)[1].trim();
            appendMessage(agentActivity, `Error: ${errorText}`, 'agent-error');
        } else if (message.startsWith('Agent Warning:')) {
             const warningText = message.split("Agent Warning:", 1)[1].trim();
             appendMessage(agentActivity, `Warning: ${warningText}`, 'agent-warning');
        } else if (message.startsWith('Agent: ')) { // General activity
             const activityText = message.split("Agent:", 1)[1].trim();
             if (agentActivity.children.length === 1 && agentActivity.firstElementChild.textContent.includes("Connected to agent")) {
                 agentActivity.innerHTML = ''; // Clear initial connect message
             }
             // Prevent duplicate "Workflow complete" logs
             if (activityText !== "Workflow complete." || !agentActivity.lastElementChild || !agentActivity.lastElementChild.textContent.includes("Workflow complete.")) {
                 appendMessage(agentActivity, activityText, 'agent-activity');
             }
         } else { // Default: treat as activity
             if (agentActivity.children.length === 1 && agentActivity.firstElementChild.textContent.includes("Connected to agent")) {
                 agentActivity.innerHTML = '';
             }
             appendMessage(agentActivity, message, 'agent-activity');
         }
    };

    socket.onclose = (event) => {
        console.log(`WebSocket closed: Code=${event.code}, Reason='${event.reason}', Clean=${event.wasClean}`);
        if (!event.wasClean && event.code !== 1000 && event.code !== 1001 && reconnectAttempts < maxReconnectAttempts) {
            reconnectAttempts++;
            const reconnectMsg = `Connection closed. Reconnecting... (${reconnectAttempts}/${maxReconnectAttempts})`;
            appendMessage(agentActivity, reconnectMsg, 'agent-error');
            setTimeout(connectWebSocket, reconnectInterval);
        } else if (reconnectAttempts >= maxReconnectAttempts) {
             appendMessage(agentActivity, 'Connection lost. Max reconnection attempts reached.', 'agent-error');
        } else {
             appendMessage(agentActivity, 'Connection closed.', 'agent-activity');
        }
    };

    socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        appendMessage(agentActivity, 'WebSocket error occurred. Check console.', 'agent-error');
    };
}

// --- Message Handling ---
function sendMessage() {
    const messageText = userInput.value.trim();
    const selectedModel = modelSelect.value; // Get selected model

    if (messageText && socket && socket.readyState === WebSocket.OPEN) {
        console.log(`Sending message: '${messageText}' using model: ${selectedModel}`);

        // Clear initial "Welcome" message
        if (chatHistory.children.length === 1 && chatHistory.firstElementChild.textContent.includes("Welcome")) {
             chatHistory.innerHTML = '';
        }
        appendMessage(chatHistory, `You (${modelSelect.options[modelSelect.selectedIndex].text}): ${messageText}`, 'user');

        // Send as JSON object
        const messagePayload = JSON.stringify({
            query: messageText,
            model: selectedModel
        });
        socket.send(messagePayload);

        userInput.value = ''; // Clear input
        userInput.rows = 3;   // Reset textarea size

        // Clear previous results/activity
        agentActivity.innerHTML = '<p class="message agent-activity">Processing request...</p>';
        finalResults.innerHTML = '<p class="message agent-activity">Waiting for results...</p>';

    } else if (!socket || socket.readyState !== WebSocket.OPEN) {
        console.error('WebSocket is not connected.');
        appendMessage(agentActivity, 'Error: Not connected to agent.', 'agent-error');
    } else if (!messageText) {
         console.log('No message to send.');
    }
}

// --- Utility to Append Messages ---
function appendMessage(container, text, type) {
     // Clear specific initial messages if they exist
     const initialMessages = ["Connecting to agent...", "No results yet.", "Waiting for connection...", "Welcome! Select a model and enter your query."];
     if (container.children.length === 1 && initialMessages.some(msg => container.firstElementChild.textContent.includes(msg))) {
         container.innerHTML = '';
     }

    const messageElement = document.createElement('p');
    messageElement.classList.add('message', type);
    // Basic escaping + newline handling
    const escapedText = text.replace(/</g, "&lt;").replace(/>/g, "&gt;");
    messageElement.innerHTML = escapedText.replace(/\n/g, '<br>');
    container.appendChild(messageElement);
    container.scrollTop = container.scrollHeight; // Auto-scroll
}

// --- Event Listeners ---
sendButton.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
});
// Auto-resize textarea
userInput.addEventListener('input', () => {
    userInput.rows = 3;
    const lines = userInput.value.split('\n').length;
    userInput.rows = Math.max(3, Math.min(lines, 10));
});

// --- Initial Connection ---
connectWebSocket();