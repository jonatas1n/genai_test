const documentsList = document.querySelector(".documents");

function createDocumentItem(data) {
  const templateItem = document.querySelector("#document-item-template");
  const item = templateItem.content.cloneNode(true);
  item.querySelector(".item__counter-value").textContent = data.completed_files;
  item.querySelector(".item__created-at-value").textContent = data.created_at;
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