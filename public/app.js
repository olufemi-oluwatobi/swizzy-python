document.addEventListener('DOMContentLoaded', () => {
    const taskInput = document.getElementById('task-input');
    const fileInput = document.getElementById('file-input');
    const sendTaskButton = document.getElementById('send-task');
    const taskStatusArea = document.getElementById('task-status-area');
    const responseDisplayArea = document.getElementById('response-display-area');
    const memoryStateArea = document.getElementById('memory-state-area');
    const fileList = document.getElementById('file-list');

    let files = [];

    fileInput.addEventListener('change', (event) => {
        files = Array.from(event.target.files);
        updateFileList();
    });

    function updateFileList() {
        fileList.innerHTML = '';
        files.forEach(file => {
            const listItem = document.createElement('li');
            listItem.textContent = file.name;
            fileList.appendChild(listItem);
        });
    }

    sendTaskButton.addEventListener('click', async () => {
        const taskDescription = taskInput.value.trim();
        if (!taskDescription && files.length == 0) return;

        const taskId = `task-${Date.now()}`;
        addTaskStatus(taskId, taskDescription, 'Pending');

        const formData = new FormData();
        formData.append('message', taskDescription);
        files.forEach(file => formData.append('files', file));

        try {
            updateTaskStatus(taskId, 'In Progress');
            const response = await fetch('/chat', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            displayResponse(taskId, data.response);
            displayMemoryState(data.memory);
            updateTaskStatus(taskId, 'Completed');
        } catch (error) {
            console.error('Error:', error);
            displayError(taskId, "An error occurred while processing your task.");
            updateTaskStatus(taskId, 'Error');
        }
    });

    function addTaskStatus(taskId, taskDescription, status) {
        const taskEntry = document.createElement('div');
        taskEntry.id = taskId;
        taskEntry.innerHTML = `
            <p><strong>Task:</strong> ${taskDescription}</p>
            <p><strong>Status:</strong> <span id="${taskId}-status">${status}</span></p>
        `;
        taskStatusArea.appendChild(taskEntry);
    }

    function updateTaskStatus(taskId, status) {
        const statusSpan = document.getElementById(`${taskId}-status`);
        if (statusSpan) {
            statusSpan.textContent = status;
        }
    }

    function displayResponse(taskId, response) {
        const responseEntry = document.createElement('div');
        responseEntry.id = `${taskId}-response`;
        responseEntry.innerHTML = `<p><strong>Response:</strong></p><div class="agent-response">${response}</div>`;
        responseDisplayArea.appendChild(responseEntry);
    }

    function displayMemoryState(memoryState) {
        memoryStateArea.innerHTML = '';
        if (memoryState) {
            const memoryEntry = document.createElement('div');
            memoryEntry.innerHTML = `
                <p><strong>Memory State:</strong></p>
                <pre>${JSON.stringify(memoryState, null, 2)}</pre>
            `;
            memoryStateArea.appendChild(memoryEntry);
        }
    }

    function displayError(taskId, errorMessage) {
        const responseEntry = document.createElement('div');
        responseEntry.id = `${taskId}-response`;
        responseEntry.innerHTML = `<p><strong>Error:</strong> ${errorMessage}</p>`;
        responseDisplayArea.appendChild(responseEntry);
    }
});