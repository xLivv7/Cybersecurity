/* Tokens stay in the provider's form field; never copy them to storage or URLs. */
(() => {
  "use strict";
  const root = document.getElementById("captcha-widget");
  const status = document.getElementById("captcha-status");
  const retry = document.getElementById("captcha-retry");
  if (!root || !status || !retry) return;
  let widget;
  function reset() {
    if (widget !== undefined && window.turnstile) window.turnstile.reset(widget);
    status.textContent = "Wykonaj nowe wyzwanie CAPTCHA.";
  }
  window.turnstileReady = () => {
    if (widget !== undefined) return;
    widget = window.turnstile.render(root, {
      sitekey: root.dataset.siteKey,
      action: root.dataset.action,
      language: "pl",
      callback: () => { status.textContent = "Weryfikacja CAPTCHA zakończona. Możesz wysłać formularz."; },
      "expired-callback": reset,
      "timeout-callback": reset,
      "error-callback": () => {
        status.textContent = "Nie udało się wczytać CAPTCHA. Sprawdź połączenie i ponów weryfikację.";
        return true;
      },
    });
  };
  retry.addEventListener("click", reset);
  window.addEventListener("pageshow", event => { if (event.persisted) reset(); });
  document.addEventListener("error", event => {
    if (event.target.id === "captcha-provider") status.textContent = "Usługa CAPTCHA jest niedostępna. Odśwież stronę po przywróceniu połączenia.";
  }, true);
})();
