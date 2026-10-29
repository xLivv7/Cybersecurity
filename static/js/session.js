/* The server decides validity. Passive checks never renew the session. */
(() => {
  "use strict";
  const root = document.getElementById("session-status");
  if (!root) return;
  const countdown = document.getElementById("session-countdown");
  const notice = document.getElementById("session-notice");
  const protectedElements = [
    document.getElementById("main-content"),
    document.querySelector(".site-header"),
  ].filter(Boolean);
  const originalTitle = document.title;
  let deadline = null;
  let timer;
  let inFlight = false;
  let stopped = false;

  function lock(locked) {
    protectedElements.forEach((element) => { element.hidden = locked; });
    document.title = locked ? "Sesja wymaga weryfikacji" : originalTitle;
  }

  function leave(url) {
    stopped = true;
    clearTimeout(timer);
    lock(true);
    window.location.replace(url);
  }

  function render() {
    if (deadline === null) return;
    const seconds = Math.max(0, Math.ceil((deadline - performance.now()) / 1000));
    const minutes = Math.floor(seconds / 60);
    countdown.textContent = `Sesja wygaśnie za: ${minutes}:${String(seconds % 60).padStart(2, "0")}`;
    if (seconds === 0) {
      lock(true);
      notice.textContent = "Sprawdzanie ważności sesji…";
    }
  }

  async function check() {
    if (inFlight || stopped) return;
    clearTimeout(timer);
    inFlight = true;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);
    let nextCheck = 5000;
    try {
      const response = await fetch(root.dataset.statusUrl, {
        credentials: "same-origin",
        cache: "no-store",
        headers: { Accept: "application/json" },
        signal: controller.signal,
      });
      if (!response.ok || response.redirected) throw new Error("Invalid status response");
      const state = await response.json();
      if (state.active === false) {
        leave(root.dataset.loginUrl);
        return;
      }
      if (state.active !== true || !["full", "limited"].includes(state.scope)
          || !Number.isFinite(state.remaining_seconds) || state.remaining_seconds <= 0) {
        throw new Error("Invalid session status");
      }
      if (state.scope === "limited" && window.location.pathname !== root.dataset.requiredUrl) {
        leave(root.dataset.requiredUrl);
        return;
      }
      deadline = performance.now() + state.remaining_seconds * 1000;
      lock(false);
      notice.textContent = "";
      render();
      nextCheck = Math.min(30000, state.remaining_seconds * 1000);
    } catch {
      if (deadline === null || performance.now() >= deadline) {
        lock(true);
        notice.textContent = "Nie można potwierdzić ważności sesji. Oczekiwanie na połączenie…";
      }
    } finally {
      clearTimeout(timeout);
      inFlight = false;
      if (!stopped) timer = setTimeout(check, nextCheck);
    }
  }

  setInterval(() => { if (!stopped) render(); }, 1000);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) { render(); check(); }
  });
  window.addEventListener("online", check);
  window.addEventListener("pagehide", () => { stopped = true; clearTimeout(timer); lock(true); });
  window.addEventListener("pageshow", () => { stopped = false; check(); });
  check();
})();
