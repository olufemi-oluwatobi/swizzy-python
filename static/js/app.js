document.addEventListener("DOMContentLoaded", () => {
    const messageTextInput = document.getElementById("message-text-input"); 
    const fileInput = document.getElementById("file-input"); 
    const sendButton = document.getElementById("send-message"); 
    const messagesContainer = document.getElementById("messages");

    function addMessage(content, isUser) {
        const messageDiv = document.createElement("div");
        messageDiv.className = isUser ? "user-message" : "agent-message";
        messageDiv.textContent = content;
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    async function sendMessage() { 
        const message = messageTextInput.value.trim();
        const files = fileInput.files;

        if (!message && files.length === 0) {
             addMessage("Please enter a message or select a file.", false); 
             return; 
        }

        addMessage(message || "(File(s) sent)", true); 

        const formData = new FormData();
        formData.append('message', message);

        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }

        messageTextInput.value = "";
        fileInput.value = ""; 

        try {
            const response = await fetch("/send_message", {
                method: "POST",
                body: formData, 
            });

            const data = await response.json();
            if (data.error) {
                addMessage("Error: " + data.error, false);
            } else {
                addMessage(data.response, false);
            }
        } catch (error) {
            addMessage("Error: Could not send message", false);
            console.error("Error:", error);
        }
    }

    sendButton.addEventListener("click", sendMessage);

    messageTextInput.addEventListener("keypress", (event) => {
        if (event.key === "Enter") {
            sendButton.click(); 
            event.preventDefault(); 
        }
    });
});
