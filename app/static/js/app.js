const documentsList = document.querySelector(".documents");

function formatDate(date) {
  return new Date(date).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function createDocumentItem(data) {
  const { status, started_at, results } = data;
  const templateItem = document.querySelector("#document-item-template");
  const item = templateItem.content.cloneNode(true);
  item.querySelector(".item__counter-value").textContent = results.files_processed.length;
  item.querySelector(".item__created-at-value").textContent = formatDate(started_at);
  item.querySelector(".item__status-value").textContent = status;
  item.querySelector(".item__status").classList.add(status.toLowerCase());
  item.querySelector(".item__results-total-words-label .item__results-item-value").textContent = results.total_words;
  item.querySelector(".item__results-total-lines-label .item__results-item-value").textContent = results.total_lines;
  item.querySelector(".item__results-total-chars-label .item__results-item-value").textContent = results.total_chars;
  item.querySelector(".item__results-frequent-words-label .item__results-item-value").textContent = results.most_frequent_words;
  results.files_processed.forEach(file => {
    const fileItem = document.createElement("div");
    fileItem.classList.add("file");
    fileItem.textContent = file;
    item.querySelector(".item__results-files-label .item__results-item-value").appendChild(fileItem);
  });
  return item;
}

function fillDocumentsList(documents=[]) {
  if (documents.length === 0) {
    documentsList.classList.add("empty");
    documentsList.classList.remove("loading");
    return;
  }

  documents.forEach(document => {
    documentsList.appendChild(createDocumentItem(document));
  });
  documentsList.classList.remove("loading");
  lucide.createIcons();
}

function fetchDocuments() {
  fetch("/process/list")
    .then(response => response.json())
    .then(data => {
      fillDocumentsList(data);
    })
    .catch(error => {
      console.error("Error fetching documents:", error);
    });
}

fetchDocuments();