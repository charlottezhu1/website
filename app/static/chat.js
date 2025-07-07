// Emotional state mapping
const emotionEmojis = {
  happy: "😊",
  excited: "🤩",
  content: "😌",
  calm: "😐",
  focused: "🤔",
  thoughtful: "🤔",
  concerned: "😟",
  worried: "😰",
  sad: "😢",
  frustrated: "😤",
  angry: "😠",
  surprised: "😲",
  curious: "🤨",
  enthusiastic: "🤗",
  empathetic: "🥰",
  neutral: "😐",
};

// Load initial emotional state when page loads
document.addEventListener("DOMContentLoaded", function () {
  loadCurrentEmotion();
});

function loadCurrentEmotion() {
  fetch("/current-emotion")
    .then((response) => response.json())
    .then((data) => {
      updateEmotionalState(data.emotion, data.intensity);
    })
    .catch((error) => {
      console.error("Error loading emotional state:", error);
      updateEmotionalState("happy", 0.7); // Default fallback
    });
}

function updateEmotionalState(emotion, intensity) {
  const emotionElement = document.getElementById("currentEmotion");
  const intensityFill = document.getElementById("intensityFill");
  const intensityValue = document.getElementById("intensityValue");
  const emotionEmoji = document.getElementById("emotionEmoji");

  if (emotionElement) emotionElement.textContent = emotion;
  if (intensityFill) intensityFill.style.width = `${intensity * 100}%`;
  if (intensityValue) intensityValue.textContent = intensity.toFixed(1);
  if (emotionEmoji) emotionEmoji.textContent = emotionEmojis[emotion] || "😐";
}

function addMessage(text, sender) {
  const chatDiv = document.getElementById("chat");

  // create outer container for alignment
  const container = document.createElement("div");
  container.className = `message-container ${sender}-container`;

  if (isDev === true || isDev === "true") {
    const msgTextarea = document.createElement("textarea");
    msgTextarea.className = "message-textarea"; // use a dedicated class for textarea
    msgTextarea.value = text;
    msgTextarea.oninput = () => autoResize(msgTextarea);
    autoResize(msgTextarea);
    container.appendChild(msgTextarea);
  } else {
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${sender}`;
    msgDiv.innerText = text;
    container.appendChild(msgDiv);
  }

  chatDiv.appendChild(container);
  chatDiv.scrollTop = chatDiv.scrollHeight;
}

function sendMessage() {
  console.log("Sending message...");
  const input = document.getElementById("messageInput");
  const promptInput = document.getElementById("promptInput");
  const msg = input.value.trim();
  const prompt = promptInput ? promptInput.value.trim() : "";

  if (!msg) return; // Don't send empty messages

  addMessage(msg, "user");

  fetch("/send", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message: msg,
      prompt: prompt,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.error) {
        console.error("Error:", data.error);
        addMessage("Error: " + data.error, "bot");
      } else {
        addMessage(data.reply, "bot");

        // Update emotional state if provided
        if (data.emotion && data.intensity !== undefined) {
          updateEmotionalState(data.emotion, data.intensity);
        }
      }
    })
    .catch((error) => {
      console.error("Fetch error:", error);
      addMessage("Error: Failed to send message", "bot");
    });

  input.value = "";
  autoResize(input);
}

function saveConversation() {
  const chatDiv = document.getElementById("chat");
  const messages = [];

  // Each message container holds one message textarea/div
  const containers = chatDiv.getElementsByClassName("message-container");

  for (const container of containers) {
    // Determine sender by class (user-container or bot-container)
    const sender = container.classList.contains("user-container")
      ? "user"
      : "bot";

    // In dev mode, message is in a textarea inside container
    const textarea = container.querySelector("textarea.message-textarea");
    const text = textarea ? textarea.value.trim() : "";

    if (text) {
      messages.push({ sender, text });
    }
  }

  if (messages.length === 0) {
    alert("No messages to save!");
    return;
  }

  // Show save dialog
  showSaveDialog(messages);
}

function showSaveDialog(messages) {
  // First, analyze the conversation to get auto-generated values
  fetch("/analyze-conversation", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conversation: messages }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        const analysis = data.analysis;
        createSaveDialog(messages, analysis);
      } else {
        // Fallback if analysis fails
        createSaveDialog(messages, {
          title: `Conversation ${new Date().toLocaleString()}`,
          description: "Conversation analysis failed",
          quality_score: 0.5,
        });
      }
    })
    .catch((error) => {
      console.error("Error analyzing conversation:", error);
      // Fallback if analysis fails
      createSaveDialog(messages, {
        title: `Conversation ${new Date().toLocaleString()}`,
        description: "Conversation analysis failed",
        quality_score: 0.5,
      });
    });
}

function createSaveDialog(messages, analysis) {
  // Create modal
  const modal = document.createElement("div");
  modal.className = "modal";
  modal.style.display = "block";

  modal.innerHTML = `
    <div class="modal-content">
      <span class="close" onclick="closeSaveDialog()">&times;</span>
      <h4>Save Conversation</h4>
      <div class="save-form">
        <div class="form-group">
          <label for="conversationTitle">Title:</label>
          <input type="text" id="conversationTitle" placeholder="Enter conversation title..." value="${
            analysis.title || ""
          }">
        </div>
        <div class="form-group">
          <label for="conversationDescription">Description:</label>
          <textarea id="conversationDescription" placeholder="Enter description (optional)..." rows="2">${
            analysis.description || ""
          }</textarea>
        </div>
        <div class="form-group">
          <label for="qualityScore">Quality Score (0.0-1.0):</label>
          <input type="number" id="qualityScore" min="0" max="1" step="0.1" value="${
            analysis.quality_score || 0.5
          }">
        </div>
        <div class="analysis-info">
          <p><strong>Auto-Analysis:</strong></p>
          <ul>
            <li><strong>Type:</strong> ${
              analysis.conversation_type || "Unknown"
            }</li>
            <li><strong>Topics:</strong> ${
              (analysis.topics || []).join(", ") || "None detected"
            }</li>
            <li><strong>Tone:</strong> ${
              analysis.emotional_tone || "Unknown"
            }</li>
            <li><strong>Depth:</strong> ${
              analysis.conversation_depth || "Unknown"
            }</li>
          </ul>
        </div>
        <div class="save-actions">
          <button onclick="closeSaveDialog()" class="secondary-btn">Cancel</button>
          <button onclick="confirmSaveConversation()" class="primary-btn">Save</button>
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  // Store messages for later use
  window.currentSaveMessages = messages;
}

function closeSaveDialog() {
  const modal = document.querySelector(".modal");
  if (modal) {
    modal.remove();
  }
  window.currentSaveMessages = null;
}

function confirmSaveConversation() {
  const title = document.getElementById("conversationTitle").value.trim();
  const description = document
    .getElementById("conversationDescription")
    .value.trim();
  const qualityScore = parseFloat(
    document.getElementById("qualityScore").value
  );

  if (!title) {
    alert("Please enter a title for the conversation.");
    return;
  }

  if (qualityScore < 0 || qualityScore > 1) {
    alert("Quality score must be between 0.0 and 1.0.");
    return;
  }

  // Send messages JSON to backend
  fetch("/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      conversation: window.currentSaveMessages,
      title: title,
      description: description,
      quality_score: qualityScore,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        alert("Conversation saved successfully!");
        closeSaveDialog();
      } else {
        alert(
          "Failed to save conversation: " + (data.error || "Unknown error")
        );
      }
    })
    .catch((err) => {
      alert("Error saving conversation: " + err.message);
    });
}

function handleKeyPress(event) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
}

function autoResize(textarea) {
  textarea.style.height = "auto";
  textarea.style.height = textarea.scrollHeight + "px";
}

function populateInitialData() {
  if (
    confirm(
      "This will populate the database with initial memory stream data based on Charlotte's background. Continue?"
    )
  ) {
    fetch("/populate-initial-data", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          alert("Initial data populated successfully!");
        } else {
          alert("Failed to populate data: " + (data.error || "Unknown error"));
        }
      })
      .catch((err) => {
        alert("Error populating data: " + err.message);
      });
  }
}
