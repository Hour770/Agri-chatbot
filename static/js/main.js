/**
 * Creates and returns a complete HTML element for a chat history item.
 * @param {object} chatData - An object with chat_id and title.
 * @returns {HTMLElement} The fully constructed div element for the chat item.
 */
function createChatItemComponent(chatData) {
  const item = document.createElement("div");
  item.className = "chat-item";
  item.dataset.chatId = chatData.chat_id;
  item.onclick = () => loadChat(chatData.chat_id);

  const titleWrapper = document.createElement("div");
  titleWrapper.className = "title-wrapper";

  const titleSpan = document.createElement("span");
  titleSpan.className = "chat-title-text";
  titleSpan.innerText = chatData.title;

  titleWrapper.appendChild(titleSpan);

  const editBtn = document.createElement("button");
  editBtn.className = "edit-chat-btn";
  editBtn.innerHTML = "✏️";
  editBtn.onclick = (event) => editChatTitle(event, chatData.chat_id);

  item.appendChild(titleWrapper);
  item.appendChild(editBtn);

  return item;
}

/**
 * Appends a message to the chat box.
 */
function appendMessage(sender, text) {
  const box = document.getElementById("chat-box");
  const msg = document.createElement("div");
  msg.className = sender;

  const msgText = document.createElement("span");
  msgText.innerText = text;
  msg.appendChild(msgText);

  box.appendChild(msg);
  box.scrollTop = box.scrollHeight;
}

/**
 * Starts a new chat session.
 */
async function newChat() {
  try {
    await fetch("/new-chat", { method: "POST" });
    document.getElementById("chat-box").innerHTML =
      '<div class="bot-message initial-message"><span>Welcome to Agri-Chatbot! How can I help you with your farming today?</span></div>';
    document.getElementById("user-input").value = "";
    document
      .querySelectorAll(".chat-item.active")
      .forEach((item) => item.classList.remove("active"));
  } catch (err) {
    console.error("Error starting new chat:", err);
  }
}

/**
 * Sends the user's message to the backend and displays the response.
 */
async function sendMessage() {
  const input = document.getElementById("user-input");
  const message = input.value.trim();
  if (!message) return;

  appendMessage("user-message", message);
  input.value = "";

  try {
    const res = await fetch("/get-response", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: message }),
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    if (data.new_chat) {
      const hist = document.querySelector(".chat-history");
      const noChatsMsg = hist.querySelector(".no-chats-message");
      if (noChatsMsg) noChatsMsg.remove();

      const item = createChatItemComponent(data.new_chat);
      hist.prepend(item);
    }
    appendMessage("bot-message", data.response);
  } catch (err) {
    console.error("Error sending message:", err);
    appendMessage(
      "bot-message",
      "Error: Could not reach Agri-Chatbot. Please try again."
    );
  }
}

/**
 * Loads a previous chat's history from the server.
 */
async function loadChat(chatId) {
  try {
    document
      .querySelectorAll(".chat-item.active")
      .forEach((item) => item.classList.remove("active"));
    document
      .querySelector(`.chat-item[data-chat-id='${chatId}']`)
      .classList.add("active");

    const res = await fetch(`/load-chat/${chatId}`);
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    const box = document.getElementById("chat-box");
    box.innerHTML = "";
    data.messages.forEach((m) => {
      appendMessage(
        m.sender === "user" ? "user-message" : "bot-message",
        m.message
      );
    });

    await fetch("/set-active-chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: chatId }),
    });
  } catch (err) {
    console.error("Error loading chat:", err);
    appendMessage("bot-message", "Error: Could not load chat history.");
  }
}

/**
 * Handles the entire chat title editing process with a cleaner UI.
 */
/**
 * Handles the entire chat title editing process with a cleaner UI.
 */
/**
 * Handles the chat title editing process using only the keyboard (Enter/Escape).
 */
function editChatTitle(event, chatId) {
  event.stopPropagation();

  const chatItem = document.querySelector(
    `.chat-item[data-chat-id='${chatId}']`
  );
  const titleWrapper = chatItem.querySelector(".title-wrapper");
  const titleSpan = titleWrapper.querySelector(".chat-title-text");
  if (!titleSpan) return;

  const originalTitle = titleSpan.innerText;

  const editContainer = document.createElement("div");
  editContainer.className = "edit-container";

  const input = document.createElement("input");
  input.type = "text";
  input.value = originalTitle;
  input.className = "chat-title-input";

  // The save and cancel buttons have been completely removed.

  const restoreTitle = () => {
    titleWrapper.innerHTML = "";
    titleWrapper.appendChild(titleSpan);
  };

  const saveEdit = async () => {
    const newTitle = input.value.trim();

    // If the title is empty or unchanged, just cancel the edit.
    if (!newTitle || newTitle === originalTitle) {
      restoreTitle();
      return;
    }

    titleSpan.innerText = newTitle;
    restoreTitle();

    try {
      const res = await fetch("/rename-chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: chatId, new_title: newTitle }),
      });
      if (!res.ok) throw new Error("Failed to save title.");
    } catch (err) {
      console.error("Error renaming chat:", err);
      titleSpan.innerText = originalTitle; // Revert on API error
      alert("Could not rename chat.");
    }
  };

  // Keyboard controls for saving and canceling
  input.onkeydown = (e) => {
    if (e.key === "Enter") {
      e.preventDefault(); // Prevents form submission if it's inside a form
      saveEdit();
    }
    if (e.key === "Escape") {
      restoreTitle();
    }
  };

  // Optional: Also save when the user clicks away from the input
  input.onblur = saveEdit;

  editContainer.appendChild(input);
  titleWrapper.innerHTML = "";
  titleWrapper.appendChild(editContainer);

  input.focus();
  input.select();
}
// --- Event Listeners ---
// Use DOMContentLoaded to make sure the HTML is fully loaded before attaching listeners
document.addEventListener("DOMContentLoaded", (event) => {
  document.getElementById("new-chat-btn").addEventListener("click", newChat);

  document
    .getElementById("user-input")
    .addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
});

const saveEdit = async () => {
  const newTitle = input.value.trim();

  if (!newTitle || newTitle === originalTitle) {
    restoreTitle();
    return;
  }

  titleSpan.innerText = newTitle;
  restoreTitle();

  try {
    // Confirm the URL is '/rename-chat'
    const res = await fetch("/rename-chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      // Confirm the body has 'chat_id' and 'new_title'
      body: JSON.stringify({ chat_id: chatId, new_title: newTitle }),
    });
    if (!res.ok) throw new Error("Failed to save title.");
  } catch (err) {
    console.error("Error renaming chat:", err);
    titleSpan.innerText = originalTitle; // Revert on API error
    alert("Could not rename chat."); // This is the alert you are seeing
  }
};
