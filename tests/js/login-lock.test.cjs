/* Run with: node --test tests/js/login-lock.test.cjs */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname, "../../static/js/login-lock.js"), "utf8");

function page(seconds = "900") {
  let now = 0, tick, stopped = false;
  const listeners = {};
  const root = { dataset: { remainingSeconds: seconds }, textContent: "" };
  const output = { textContent: "" };
  const document = {
    hidden: false,
    getElementById: id => id === "login-block" ? root : output,
    addEventListener: (name, callback) => { listeners[name] = callback; },
  };
  // No fetch, storage, form submit or credentials API is available in this DOM.
  vm.runInNewContext(source, {
    document, performance: { now: () => now },
    setInterval: callback => { tick = callback; return 1; },
    clearInterval: () => { stopped = true; },
    window: { addEventListener: (name, callback) => { listeners[name] = callback; } },
  });
  return {
    root, output, document, listeners,
    setTime: value => { now = value; },
    advance: value => { now += value; if (!stopped && tick) tick(); },
    get stopped() { return stopped; },
  };
}

test("initial time and exact deadline without network or submitting a password", () => {
  const p = page();
  assert.equal(p.output.textContent, "15:00");
  p.advance(899999);
  assert.equal(p.output.textContent, "0:01");
  assert.equal(p.stopped, false);
  p.advance(1);
  assert.match(p.root.textContent, /Czas blokady upłynął/);
  assert.equal(p.stopped, true);
});

test("returning to a background tab catches up instead of restarting", () => {
  const p = page();
  p.setTime(600000);
  p.listeners.visibilitychange();
  assert.equal(p.output.textContent, "5:00");
  p.setTime(950000);
  p.listeners.pageshow();
  assert.equal(p.stopped, true);
});

test("resuming before the deadline preserves remaining time", () => {
  const p = page("30");
  p.setTime(12001);
  p.listeners.pageshow();
  assert.equal(p.output.textContent, "0:18");
});

test("missing elements and invalid durations do not create a timer", () => {
  for (const seconds of ["NaN", "0", "-1", "Infinity"]) {
    const p = page(seconds);
    assert.equal(p.output.textContent, "");
  }
  vm.runInNewContext(source, { document: { getElementById: () => null } });
});
