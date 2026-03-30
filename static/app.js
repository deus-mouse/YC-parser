const form = document.getElementById("scan-form");
const statusNode = document.getElementById("status");
const resultsCard = document.getElementById("results-card");
const summaryNode = document.getElementById("summary");
const occupancyNode = document.getElementById("occupancy");
const tbody = document.querySelector("#results-table tbody");
const submitButton = document.getElementById("submit-button");

function setStatus(message, isError = false) {
  statusNode.textContent = message;
  statusNode.style.color = isError ? "#b42318" : "";
}

function formatMinutesToHours(minutes) {
  const hours = Number(minutes || 0) / 60;
  if (Number.isInteger(hours)) {
    return `${hours} ч`;
  }
  return `${hours.toFixed(1).replace(".0", "")} ч`;
}

function renderResults(items) {
  tbody.innerHTML = "";

  for (const item of items) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${item.name}</td>
      <td>${item.shortest_service_duration_min} мин</td>
      <td>${item.total_slots}</td>
      <td>${formatMinutesToHours(item.total_free_minutes)}</td>
    `;
    tbody.appendChild(row);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  console.log("submit:start");

  const formData = new FormData(form);
  const workingHoursStart = String(formData.get("working_hours_start") || "").trim();
  const workingHoursEnd = String(formData.get("working_hours_end") || "").trim();
  if ((workingHoursStart && !workingHoursEnd) || (!workingHoursStart && workingHoursEnd)) {
    setStatus("Для режима работы нужно заполнить и начало, и конец.", true);
    return;
  }

  const workingHours = workingHoursStart && workingHoursEnd
    ? `${workingHoursStart}-${workingHoursEnd}`
    : "";

  const payload = {
    url: String(formData.get("url") || "").trim(),
    days: Number(formData.get("days") || 30),
    working_hours: workingHours,
  };
  console.log("submit:payload", payload);

  submitButton.disabled = true;
  resultsCard.classList.add("hidden");
  occupancyNode.classList.add("hidden");
  occupancyNode.textContent = "";
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
    summaryNode.innerHTML = `Найдено мастеров: ${data.total_masters}.<br>Глубина: ${data.days} дней.`;
    if (payload.working_hours) {
      if (data.occupancy_percent !== null && data.occupancy_percent !== undefined) {
        occupancyNode.textContent = `Загруженность филиала: ${data.occupancy_percent}%. Свободно: ${formatMinutesToHours(data.total_free_minutes)} из ${formatMinutesToHours(data.total_working_minutes)}.`;
      } else {
        occupancyNode.textContent = "Загруженность филиала не была рассчитана. Проверь формат режима работы.";
      }
      occupancyNode.classList.remove("hidden");
    }
    resultsCard.classList.remove("hidden");
    setStatus("Парсинг завершен.");
  } catch (error) {
    console.error("submit:error", error);
    setStatus(error.message || "Не удалось выполнить парсинг.", true);
  } finally {
    submitButton.disabled = false;
  }
});
