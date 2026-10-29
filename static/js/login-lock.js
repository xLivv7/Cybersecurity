/* Display only: the server enforces the deadline on every submitted login. */
(() => {
  "use strict";
  const root = document.getElementById("login-block");
  const countdown = document.getElementById("login-block-countdown");
  if (!root || !countdown) return;
  const seconds = Number(root.dataset.remainingSeconds);
  if (!Number.isFinite(seconds) || seconds <= 0) return;
  const deadline = performance.now() + seconds * 1000;
  const timer = setInterval(render, 1000);
  function render() {
    const remaining = Math.max(0, Math.ceil((deadline - performance.now()) / 1000));
    if (remaining === 0) {
      clearInterval(timer);
      root.textContent = "Czas blokady upłynął. Możesz ponowić logowanie.";
      return;
    }
    countdown.textContent = `${Math.floor(remaining / 60)}:${String(remaining % 60).padStart(2, "0")}`;
  }
  render();
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) render();
  });
  window.addEventListener("pageshow", render);
})();
