const documentsList = document.querySelector(".documents");

function formatDate(date) {
  return new Date(date).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function updateDocumentItem(detailsEl, data) {
  const { status, results } = data;

  detailsEl.querySelector(".item__counter-value").textContent = results.files_processed.length;
  detailsEl.querySelector(".item__status-value").textContent = status;

  const statusEl = detailsEl.querySelector(".item__status");
  statusEl.className = "item__status " + status.toLowerCase();

  detailsEl.querySelector(".item__results-total-words-label .item__results-item-value").textContent = results.total_words;
  detailsEl.querySelector(".item__results-total-lines-label .item__results-item-value").textContent = results.total_lines;
  detailsEl.querySelector(".item__results-total-chars-label .item__results-item-value").textContent = results.total_chars;
  detailsEl.querySelector(".item__results-frequent-words-label .item__results-item-value").textContent = results.most_frequent_words.join(", ");

  const filesContainer = detailsEl.querySelector(".item__results-files-label .item__results-item-value");
  filesContainer.innerHTML = "";
  results.files_processed.forEach(file => {
    const fileItem = document.createElement("div");
    fileItem.classList.add("file");
    fileItem.textContent = file;
    filesContainer.appendChild(fileItem);
  });
}

function lockDetails(detailsEl) {
  detailsEl.open = true;
  detailsEl.classList.add("item--locked");
  detailsEl.querySelector("summary").addEventListener("click", preventCollapse);
}

function unlockDetails(detailsEl) {
  detailsEl.classList.remove("item--locked");
  detailsEl.querySelector("summary").removeEventListener("click", preventCollapse);
}

function preventCollapse(e) {
  e.preventDefault();
}

function connectWebSocket(processId, detailsEl) {
  const ws = new WebSocket(`ws://${location.host}/process/ws/${processId}`);

  ws.onopen = () => {
    lockDetails(detailsEl);
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    updateDocumentItem(detailsEl, data);
  };

  ws.onclose = () => {
    unlockDetails(detailsEl);
  };

  ws.onerror = () => {
    unlockDetails(detailsEl);
  };
}

function createDocumentItem(data) {
  const { process_id, status, started_at, results } = data;
  const templateItem = document.querySelector("#document-item-template");
  const clone = templateItem.content.cloneNode(true);
  const detailsEl = clone.querySelector(".item");

  clone.querySelector(".item__created-at-value").textContent = formatDate(started_at);
  updateDocumentItem(detailsEl, data);

  // If it is still running, open and connect the WebSocket.
  if (status === "RUNNING" || status === "PENDING") {
    connectWebSocket(process_id, detailsEl);
  }

  return clone;
}

function fillDocumentsList(documents = []) {
  if (documents.length === 0) {
    documentsList.classList.add("empty");
    documentsList.classList.remove("loading");
    return;
  }

  documents.forEach(doc => {
    documentsList.appendChild(createDocumentItem(doc));
  });

  documentsList.classList.remove("loading");
  lucide.createIcons();
}

function fetchDocuments() {
  fetch("/process/list")
    .then(response => response.json())
    .then(data => fillDocumentsList(data))
    .catch(error => console.error("Error fetching documents:", error));
}

// On upload, start the process and connect the WebSocket immediately.
document.querySelector("#documents").addEventListener("change", async (e) => {
  const files = e.target.files;
  if (!files.length) return;

  const formData = new FormData();
  Array.from(files).forEach(file => formData.append("documents", file));

  const response = await fetch("/process/start", { method: "POST", body: formData });
  if (!response.ok) return console.error("Failed to start process.");

  const { process_id } = await response.json();

  // Create a placeholder item while the process is not yet in the list.
  const placeholderData = {
    process_id,
    status: "RUNNING",
    started_at: new Date().toISOString(),
    results: {
      total_words: 0,
      total_lines: 0,
      total_chars: 0,
      most_frequent_words: [],
      files_processed: [],
    },
  };

  const item = createDocumentItem(placeholderData);
  documentsList.prepend(item);
  documentsList.classList.remove("loading", "empty");
  lucide.createIcons();

  // Clear the input to allow a new upload.
  e.target.value = "";
});

fetchDocuments();