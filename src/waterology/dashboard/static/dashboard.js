const root = document.documentElement;
const themeButton = document.querySelector("[data-theme-toggle]");
const themes = ["system", "light", "dark"];

function applyTheme(theme) {
  root.dataset.theme = theme;
  if (themeButton) themeButton.textContent = `Theme: ${theme}`;
  localStorage.setItem("waterology-theme", theme);
}

applyTheme(localStorage.getItem("waterology-theme") || "system");
themeButton?.addEventListener("click", () => {
  const index = themes.indexOf(root.dataset.theme || "system");
  applyTheme(themes[(index + 1) % themes.length]);
});

const events = new EventSource("/events");
events.addEventListener("summary", (event) => {
  const counts = JSON.parse(event.data);
  for (const [name, value] of Object.entries(counts)) {
    const target = document.querySelector(`[data-count="${name}"]`);
    if (target) target.textContent = String(value);
  }
  const updated = document.querySelector("[data-updated]");
  if (updated) updated.textContent = new Date().toLocaleTimeString();
});
