const form = document.getElementById("scan-form");
const statusNode = document.getElementById("status");
const resultsCard = document.getElementById("results-card");
const summaryNode = document.getElementById("summary");
const tbody = document.querySelector("#results-table tbody");
const submitButton = document.getElementById("submit-button");

function setStatus(message, isError = false) {
  statusNode.textContent = message;
  statusNode.style.color = isError ? "#b42318" : "";
}

function renderResults(items) {
  tbody.innerHTML = "";

  for (const item of items) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${item.name}</td>
      <td>${item.shortest_service_duration_min} мин</td>
      <td>${item.total_slots}</td>
      <td>${item.total_free_minutes}</td>
    `;
    tbody.appendChild(row);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  console.log("submit:start");

  const formData = new FormData(form);
  const payload = {
    url: String(formData.get("url") || "").trim(),
    days: Number(formData.get("days") || 30),
  };
  console.log("submit:payload", payload);

  submitButton.disabled = true;
  resultsCard.classList.add("hidden");
  setStatus("Парсинг запущен. Это может занять некоторое время.");

  try {
    const response = await fetch("/api/scan", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
    });
    console.log("submit:response", response.status);

    const data = await response.json();
    console.log("submit:data", data);
    if (!response.ok) {
      throw new Error(data.detail || "Ошибка при запуске парсинга.");
    }

    const sortedItems = [...data.items].sort(
      (left, right) => right.total_free_minutes - left.total_free_minutes,
    );

    renderResults(sortedItems);
    summaryNode.textContent = `Найдено мастеров: ${data.total_masters}. Глубина: ${data.days} дней.`;
    resultsCard.classList.remove("hidden");
    setStatus("Парсинг завершен.");
  } catch (error) {
    console.error("submit:error", error);
    setStatus(error.message || "Не удалось выполнить парсинг.", true);
  } finally {
    submitButton.disabled = false;
  }
});
