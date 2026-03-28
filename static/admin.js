const settingsForm = document.getElementById("settings-form");
const settingsStatus = document.getElementById("settings-status");

function setSettingsStatus(message, isError = false) {
  settingsStatus.textContent = message;
  settingsStatus.style.color = isError ? "#b42318" : "";
}

settingsForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const formData = new FormData(settingsForm);
  const payload = {
    default_days: Number(formData.get("default_days") || 30),
  };

  setSettingsStatus("Сохраняю настройки...");

  try {
    const response = await fetch("/api/settings", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Не удалось сохранить настройки.");
    }

    setSettingsStatus("Настройки сохранены.");
  } catch (error) {
    setSettingsStatus(error.message || "Ошибка сохранения.", true);
  }
});
