// Emotional state mapping
const emotionEmojis = {
  nervous: "😰",
  sad: "😢",
  happy: "😊",
  calm: "😌",
  excited: "🤩",
  angry: "😠",
  relaxed: "😌",
  fearful: "😨",
  enthusiastic: "🤗",
  satisfied: "☺️",
  bored: "😑",
  lonely: "🥺",
};

// Emotion artwork URLs
const emotionArtwork = {
  nervous:
    "https://dgcfnvaratrfzwofqohg.supabase.co/storage/v1/object/public/GalleryArt/website/affects/nervous.png",
  sad: "https://dgcfnvaratrfzwofqohg.supabase.co/storage/v1/object/public/GalleryArt/website/affects/sad.PNG",
  happy:
    "https://dgcfnvaratrfzwofqohg.supabase.co/storage/v1/object/public/GalleryArt/website/affects/happy.png",
  calm: "https://dgcfnvaratrfzwofqohg.supabase.co/storage/v1/object/public/GalleryArt/website/affects/calm.PNG",
  excited:
    "https://dgcfnvaratrfzwofqohg.supabase.co/storage/v1/object/public/GalleryArt/website/affects/excited.PNG",
  angry:
    "https://dgcfnvaratrfzwofqohg.supabase.co/storage/v1/object/public/GalleryArt/website/affects/angry.PNG",
  relaxed:
    "https://dgcfnvaratrfzwofqohg.supabase.co/storage/v1/object/public/GalleryArt/website/affects/relaxed.PNG",
  fearful:
    "https://dgcfnvaratrfzwofqohg.supabase.co/storage/v1/object/public/GalleryArt/website/affects/fearful.PNG",
  enthusiastic:
    "https://dgcfnvaratrfzwofqohg.supabase.co/storage/v1/object/public/GalleryArt/website/affects/enthusiastic.PNG",
  satisfied:
    "https://dgcfnvaratrfzwofqohg.supabase.co/storage/v1/object/public/GalleryArt/website/affects/satisfied.PNG",
  bored:
    "https://dgcfnvaratrfzwofqohg.supabase.co/storage/v1/object/public/GalleryArt/website/affects/bored.PNG",
  lonely:
    "https://dgcfnvaratrfzwofqohg.supabase.co/storage/v1/object/public/GalleryArt/website/affects/lonely.PNG",
};

// Feature flag: Set to false to allow unauthenticated chat
const REQUIRE_AUTH_TO_CHAT = true;  // EASY TOGGLE: Change to false to disable auth requirement

// Mapping of old emotions to new emotions for backwards compatibility
const emotionMapping = {
  content: "satisfied",
  focused: "calm",
  thoughtful: "calm",
  concerned: "nervous",
  worried: "fearful",
  frustrated: "angry",
  surprised: "excited",
  curious: "enthusiastic",
  empathetic: "calm",
  neutral: "calm",
};

// Comprehensive emotional trajectory mappings
const emotionalTrajectories = {
  // Escalation patterns
  escalation: {
    calm: ["nervous", "fearful"],
    nervous: ["fearful", "angry"],
    happy: ["excited", "enthusiastic"],
    bored: ["nervous", "angry"],
    satisfied: ["happy", "enthusiastic"],
  },

  // De-escalation patterns
  deescalation: {
    angry: ["nervous", "calm"],
    fearful: ["nervous", "calm"],
    excited: ["happy", "satisfied"],
    enthusiastic: ["happy", "satisfied"],
    nervous: ["calm", "relaxed"],
  },

  // Emotional cycles
  cycles: {
    lonely: ["sad", "bored", "nervous"],
    bored: ["lonely", "sad", "nervous"],
    sad: ["lonely", "nervous", "fearful"],
  },

  // Positive progressions
  positiveProgress: {
    nervous: ["calm", "relaxed", "satisfied"],
    sad: ["calm", "happy", "enthusiastic"],
    fearful: ["calm", "satisfied", "happy"],
    lonely: ["calm", "happy", "enthusiastic"],
    bored: ["calm", "satisfied", "excited"],
  },

  // Negative progressions
  negativeProgress: {
    happy: ["calm", "bored", "sad"],
    excited: ["nervous", "fearful", "angry"],
    satisfied: ["bored", "sad", "lonely"],
  },

  // Common pairings (emotions that often occur together)
  commonPairings: {
    nervous: ["fearful", "sad"],
    happy: ["excited", "enthusiastic"],
    calm: ["relaxed", "satisfied"],
    lonely: ["sad", "bored"],
    angry: ["fearful", "nervous"],
  },

  // Intensity levels (low to high)
  intensityLevels: {
    low: ["calm", "relaxed", "bored"],
    medium: ["happy", "sad", "nervous", "lonely"],
    high: ["excited", "angry", "fearful", "enthusiastic"],
  },

  // Emotional opposites
  opposites: {
    happy: "sad",
    excited: "bored",
    calm: "angry",
    fearful: "confident",
    nervous: "relaxed",
    lonely: "satisfied",
    enthusiastic: "bored",
  },

  // Recovery paths (from negative states)
  recoveryPaths: {
    angry: ["calm", "relaxed", "satisfied"],
    fearful: ["calm", "satisfied", "happy"],
    sad: ["calm", "happy", "enthusiastic"],
    lonely: ["calm", "satisfied", "happy"],
    nervous: ["calm", "relaxed", "satisfied"],
  },

  // Motivation trajectories
  motivationTrajectories: {
    bored: ["curious", "interested", "enthusiastic"],
    sad: ["accepting", "hopeful", "happy"],
    nervous: ["focused", "confident", "satisfied"],
  },

  // Social interaction impacts
  socialImpacts: {
    lonely: {
      positive: ["happy", "enthusiastic", "satisfied"],
      negative: ["sad", "nervous", "fearful"],
    },
    nervous: {
      positive: ["calm", "happy", "satisfied"],
      negative: ["fearful", "lonely", "sad"],
    },
    enthusiastic: {
      positive: ["happy", "excited", "satisfied"],
      negative: ["nervous", "bored", "sad"],
    },
  },

  // Time-based patterns
  temporalPatterns: {
    morning: ["calm", "enthusiastic", "excited"],
    afternoon: ["satisfied", "happy", "bored"],
    evening: ["relaxed", "calm", "lonely"],
  },

  // Emotional contagion (how emotions spread in groups)
  emotionalContagion: {
    happy: ["enthusiastic", "excited"],
    sad: ["lonely", "nervous"],
    angry: ["nervous", "fearful"],
    enthusiastic: ["excited", "happy"],
    nervous: ["fearful", "sad"],
  },
};

// Function to convert old emotion to new emotion
function mapOldEmotionToNew(emotion) {
  const lowerEmotion = emotion.toLowerCase();
  return emotionMapping[lowerEmotion] || lowerEmotion;
}

// Load initial emotional state and chat history when page loads
document.addEventListener("DOMContentLoaded", function () {
  loadCurrentEmotion();
  loadChatHistory();  // Load chat history for authenticated users
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

function loadChatHistory() {
  // Only load history if user is authenticated
  if (!isAuthenticated) {
    console.log("User not authenticated, skipping chat history load");
    return;
  }

  fetch("/chat-history?limit=50")
    .then((response) => response.json())
    .then((data) => {
      if (data.success && data.messages && data.messages.length > 0) {
        console.log(`Loading ${data.messages.length} historical messages`);

        // Add each message to the chat interface (historical messages - no typing effect)
        data.messages.forEach((msg) => {
          addMessage(msg.text, msg.sender, msg.timestamp, true);
        });

        console.log(`✓ Loaded ${data.count} messages from history`);
      } else {
        console.log("No chat history found for this user");
      }
    })
    .catch((error) => {
      console.error("Error loading chat history:", error);
    });
}

function updateEmotionalState(emotion, intensity) {
  console.log("=== DEBUG: UPDATING EMOTIONAL STATE ===");
  console.log("Emotion:", emotion);
  console.log("Intensity:", intensity);
  console.log("Valid emotions:", Object.keys(emotionEmojis));

  const emotionElement = document.getElementById("currentEmotion");
  const intensityFill = document.getElementById("intensityFill");
  const intensityValue = document.getElementById("intensityValue");
  const emotionArtworkImg = document.getElementById("emotionArtwork");

  console.log("Found elements:", {
    emotionElement: !!emotionElement,
    intensityFill: !!intensityFill,
    intensityValue: !!intensityValue,
    emotionArtworkImg: !!emotionArtworkImg,
  });

  if (
    !emotionElement ||
    !intensityFill ||
    !intensityValue ||
    !emotionArtworkImg
  ) {
    console.error("Missing required DOM elements for emotion update");
    return;
  }

  // Map old emotions to new ones if necessary
  emotion = mapOldEmotionToNew(emotion);
  console.log("Mapped emotion:", emotion);

  if (emotionElement) {
    const emoji = emotionEmojis[emotion] || "😐";
    emotionElement.textContent = `${emotion} ${emoji}`;
    console.log("Updated emotion text to:", emotionElement.textContent);
  }

  if (intensityFill) {
    intensityFill.style.width = `${intensity * 100}%`;
    console.log("Updated intensity fill to:", intensityFill.style.width);
  }

  if (intensityValue) {
    intensityValue.textContent = intensity.toFixed(1);
    console.log("Updated intensity value to:", intensityValue.textContent);
  }

  if (emotionArtworkImg) {
    const artworkUrl = emotionArtwork[emotion] || emotionArtwork["calm"];
    emotionArtworkImg.src = artworkUrl;
    emotionArtworkImg.alt = `${emotion} artwork`;
    console.log("Updated artwork to:", artworkUrl);
  }
}

function formatTimestamp(timestamp) {
  const date = new Date(timestamp);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const messageDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());

  // Format time (HH:MM AM/PM)
  const timeStr = date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true
  });

  // If today, show just time
  if (messageDate.getTime() === today.getTime()) {
    return timeStr;
  }

  // If yesterday
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  if (messageDate.getTime() === yesterday.getTime()) {
    return `Yesterday ${timeStr}`;
  }

  // Otherwise show date and time
  return `${date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} ${timeStr}`;
}

function addMessage(text, sender, timestamp = null, isHistorical = false) {
  const chatDiv = document.getElementById("chat");

  // create outer container for alignment
  const container = document.createElement("div");
  container.className = `message-container ${sender}-container`;

  // Add timestamp if provided
  if (timestamp) {
    const timestampDiv = document.createElement("div");
    timestampDiv.className = "message-timestamp";
    timestampDiv.textContent = formatTimestamp(timestamp);
    container.appendChild(timestampDiv);
  }

  if (isDev === true || isDev === "true") {
    const msgTextarea = document.createElement("textarea");
    msgTextarea.className = "message-textarea";
    msgTextarea.value = text;
    msgTextarea.oninput = () => autoResize(msgTextarea);
    autoResize(msgTextarea);
    container.appendChild(msgTextarea);
  } else {
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${sender}`;
    if (sender === "bot") {
      container.appendChild(msgDiv);
      chatDiv.appendChild(container);

      if (isHistorical) {
        // Historical messages: show immediately (no typing effect)
        msgDiv.innerText = text;
        chatDiv.scrollTop = chatDiv.scrollHeight;
      } else {
        // Live messages: gradual typing effect
        msgDiv.innerText = "";
        chatDiv.scrollTop = chatDiv.scrollHeight;
        printMessageGradually(text, msgDiv);
      }
    } else {
      // For user messages, show immediately
      msgDiv.innerText = text;
      container.appendChild(msgDiv);
      chatDiv.appendChild(container);
      chatDiv.scrollTop = chatDiv.scrollHeight;
    }
  }
}

function addLoadingMessage() {
  const chatDiv = document.getElementById("chat");
  const container = document.createElement("div");
  container.className = "message-container bot-container loading-container";

  const loadingDiv = document.createElement("div");
  loadingDiv.className = "message bot loading";
  loadingDiv.innerHTML =
    '<div class="typing-indicator"><span></span><span></span><span></span></div>';

  container.appendChild(loadingDiv);
  chatDiv.appendChild(container);
  chatDiv.scrollTop = chatDiv.scrollHeight;

  return container; // Return the container so we can remove it later
}

function removeLoadingMessage(loadingContainer) {
  if (loadingContainer && loadingContainer.parentNode) {
    loadingContainer.parentNode.removeChild(loadingContainer);
  }
}

function printMessageGradually(text, element, speed = 30) {
  let index = 0;

  // Split into characters but preserve spaces
  const characters = Array.from(text);

  function printNextChar() {
    if (index < characters.length) {
      // Add the character as is, whether it's a space or not
      element.textContent += characters[index];
      index++;
      element.parentElement.parentElement.scrollTop =
        element.parentElement.parentElement.scrollHeight;

      // Adjust delay based on punctuation
      let delay = speed;
      if (index < characters.length) {
        if (".!?".includes(characters[index - 1])) {
          delay = speed * 8; // Longer pause after sentences
        } else if (",;:".includes(characters[index - 1])) {
          delay = speed * 4; // Medium pause after clauses
        }
      }

      setTimeout(printNextChar, delay);
    }
  }

  printNextChar();
}

function sendMessage() {
  console.log("Sending message...");

  // AUTHENTICATION CHECK: Require login to send messages
  if (REQUIRE_AUTH_TO_CHAT && !isAuthenticated) {
    showLoginModal();
    return; // Stop here - don't send message
  }

  const input = document.getElementById("messageInput");
  const promptInput = document.getElementById("promptInput");
  const msg = input.value.trim();
  const prompt = promptInput ? promptInput.value.trim() : "";

  if (!msg) return; // Don't send empty messages

  addMessage(msg, "user", new Date().toISOString());

  // Add loading animation
  const loadingContainer = addLoadingMessage();

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
      console.log("=== DEBUG: RECEIVED RESPONSE ===");
      console.log("Full response data:", data);

      // Remove loading animation
      removeLoadingMessage(loadingContainer);

      if (data.error) {
        console.error("Error:", data.error);
        addMessage("Error: " + data.error, "bot", new Date().toISOString(), false);
      } else {
        addMessage(data.reply, "bot", new Date().toISOString(), false);

        // Update emotional state if provided
        if (data.emotion && data.intensity !== undefined) {
          console.log("=== DEBUG: UPDATING EMOTION STATE ===");
          console.log("Emotion:", data.emotion);
          console.log("Intensity:", data.intensity);
          console.log("Valid emotions:", Object.keys(emotionEmojis));

          // Check if emotion is valid
          if (!Object.keys(emotionEmojis).includes(data.emotion)) {
            console.warn("Invalid emotion received:", data.emotion);
            data.emotion = "calm"; // Default to calm for invalid emotions
          }

          updateEmotionalState(data.emotion, data.intensity);
        } else {
          console.warn("No emotion data in response:", data);
        }
      }
    })
    .catch((error) => {
      // Remove loading animation
      removeLoadingMessage(loadingContainer);

      console.error("Fetch error:", error);
      addMessage("Error: Failed to send message", "bot", new Date().toISOString(), false);
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

// =============================================================================
// Authentication Functions
// =============================================================================

function showLoginModal() {
  const modal = document.createElement("div");
  modal.className = "modal";
  modal.style.display = "block";

  modal.innerHTML = `
    <div class="modal-content">
      <span class="close" onclick="closeLoginModal()">&times;</span>
      <h4>Sign In to Chat with Charlotte</h4>
      <div class="save-form">
        <div class="form-group">
          <label for="loginEmail">Email:</label>
          <input type="email" id="loginEmail" placeholder="Enter your email..." autocomplete="email">
        </div>
        <div class="form-group">
          <label for="loginPassword">Password:</label>
          <input type="password" id="loginPassword" placeholder="Enter your password..." autocomplete="current-password">
        </div>
        <div id="loginError" class="error-message" style="display: none;"></div>
        <div class="save-actions">
          <button onclick="closeLoginModal()" class="secondary-btn">Cancel</button>
          <button onclick="confirmLogin()" class="primary-btn">Sign In</button>
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  // Focus on email field
  setTimeout(() => {
    document.getElementById("loginEmail").focus();
  }, 100);

  // Allow Enter key to submit
  document.getElementById("loginPassword").addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      confirmLogin();
    }
  });
}

function closeLoginModal() {
  const modal = document.querySelector(".modal");
  if (modal) {
    modal.remove();
  }
}

function confirmLogin() {
  const email = document.getElementById("loginEmail").value.trim();
  const password = document.getElementById("loginPassword").value;
  const errorDiv = document.getElementById("loginError");

  if (!email || !password) {
    errorDiv.textContent = "Please enter both email and password.";
    errorDiv.style.display = "block";
    return;
  }

  // Hide previous error
  errorDiv.style.display = "none";

  // Disable button during login
  const loginBtn = document.querySelector(".modal-content .primary-btn");
  const originalText = loginBtn.textContent;
  loginBtn.textContent = "Signing in...";
  loginBtn.disabled = true;

  fetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: email,
      password: password,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.error) {
        errorDiv.textContent = data.error;
        errorDiv.style.display = "block";
        loginBtn.textContent = originalText;
        loginBtn.disabled = false;
      } else {
        // Login successful - reload page to refresh UI
        console.log("✓ Login successful:", data.user.username);
        window.location.reload();
      }
    })
    .catch((error) => {
      console.error("Login error:", error);
      errorDiv.textContent = "Failed to connect to server. Please try again.";
      errorDiv.style.display = "block";
      loginBtn.textContent = originalText;
      loginBtn.disabled = false;
    });
}

function logout() {
  if (!confirm("Are you sure you want to logout?")) {
    return;
  }

  fetch("/auth/logout", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        console.log("✓ Logout successful");
        window.location.reload();
      } else {
        alert("Logout failed: " + (data.error || "Unknown error"));
      }
    })
    .catch((error) => {
      console.error("Logout error:", error);
      alert("Failed to logout. Please try again.");
    });
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
