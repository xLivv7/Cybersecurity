const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname, "../../static/js/captcha.js"), "utf8");

function page() {
  const events = {};
  const status = { textContent: "" };
  const root = { dataset: { siteKey: "public-site", action: "login" } };
  const retry = { addEventListener: (name, cb) => { events[name] = cb; } };
  let options, renders = 0, resets = 0;
  const window = {
    addEventListener: (name, cb) => { events[name] = cb; },
    turnstile: {
      render: (node, opts) => { assert.equal(node, root); renders++; options = opts; return 0; },
      reset: id => { assert.equal(id, 0); resets++; },
    },
  };
  const document = {
    getElementById: id => ({ "captcha-widget": root, "captcha-status": status, "captcha-retry": retry })[id],
    addEventListener: (name, cb) => { events[name] = cb; },
  };
  // No storage, request API, secret or form submission is exposed to the script.
  vm.runInNewContext(source, { window, document });
  return { window, status, events, get options() { return options; }, get renders() { return renders; }, get resets() { return resets; } };
}

test("widget uses public key and action, with explicit accessible retry", () => {
  const p = page();
  p.window.turnstileReady(); p.window.turnstileReady();
  assert.equal(p.renders, 1);
  assert.equal(p.options.sitekey, "public-site");
  assert.equal(p.options.action, "login");
  assert.equal(p.options.language, "pl");
  p.options.callback("sensitive-token");
  assert.match(p.status.textContent, /Możesz wysłać/);
  assert.ok(!p.status.textContent.includes("sensitive-token"));
  p.events.click(); assert.equal(p.resets, 1);
});

test("expiry, timeout and BFCache restore reset the challenge", () => {
  const p = page(); p.window.turnstileReady();
  p.options["expired-callback"]();
  p.options["timeout-callback"]();
  p.events.pageshow({ persisted: true });
  p.events.pageshow({ persisted: false });
  assert.equal(p.resets, 3);
});

test("provider and script errors give a visible retry message", () => {
  const p = page(); p.window.turnstileReady();
  assert.equal(p.options["error-callback"](), true);
  assert.match(p.status.textContent, /ponów weryfikację/);
  p.events.error({ target: { id: "captcha-provider" } });
  assert.match(p.status.textContent, /niedostępna/);
});

test("missing widget is harmless", () => {
  vm.runInNewContext(source, { document: { getElementById: () => null } });
});
