import { chainChecks, fetchLedger, tamper } from "./ledger.js";

const VIEWS = ["overview", "run", "ledger", "receiver"];
const STEP_MS = 900;

const showTheme = (theme) => {
  document.documentElement.dataset.rdTheme = theme;
  const toggle = document.getElementById("theme-toggle");
  toggle.textContent = theme === "dark" ? "◑" : "◐";
  toggle.setAttribute(
    "aria-label",
    theme === "dark" ? "Switch to light mode" : "Switch to dark mode",
  );
};

const currentTheme = () => document.documentElement.dataset.rdTheme || "light";

const setUpTheme = () => {
  showTheme(currentTheme());
  document.getElementById("theme-toggle").addEventListener("click", () => {
    const next = currentTheme() === "dark" ? "light" : "dark";
    try {
      localStorage.setItem("rd-theme", next);
    } catch (error) {
      // a private window refuses to store the choice; the toggle still works for this page
    }
    showTheme(next);
  });
};

const showView = (view) => {
  const wanted = VIEWS.includes(view) ? view : VIEWS[0];
  for (const section of document.querySelectorAll("[data-view]")) {
    section.hidden = section.dataset.view !== wanted;
  }
  for (const link of document.querySelectorAll("[data-view-link]")) {
    if (link.dataset.viewLink === wanted) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  }
};

const explainStates = () => {
  for (const element of document.querySelectorAll("[data-help]")) {
    const help = STATE_HELP[element.dataset.help];
    if (help) element.title = help;
  }
};

const setUpRouting = () => {
  const fromHash = () => showView(location.hash.replace("#", ""));
  window.addEventListener("hashchange", fromHash);
  fromHash();
};

const activePanel = () =>
  document.querySelector("[data-scenario-panel]:not([hidden])");

const paintStep = (step) => {
  const panel = activePanel();
  if (!panel) return;
  for (const element of panel.querySelectorAll("[data-step-min],[data-step-max]")) {
    const min = Number(element.dataset.stepMin ?? 0);
    const max = Number(element.dataset.stepMax ?? Infinity);
    element.hidden = !(step >= min && step <= max);
  }
  for (const rung of panel.querySelectorAll("[data-live-from]")) {
    rung.classList.toggle("rung-live", step >= Number(rung.dataset.liveFrom));
  }
};

const setUpRun = () => {
  const button = document.getElementById("replay");
  const tabs = [...document.querySelectorAll("[data-scenario]")];
  let timer = null;

  const totalSteps = () =>
    Number(tabs.find((tab) => tab.getAttribute("aria-pressed") === "true").dataset.steps);

  const stop = () => {
    clearInterval(timer);
    timer = null;
    button.textContent = "Replay the run";
    button.disabled = false;
  };

  const replay = () => {
    clearInterval(timer);
    const total = totalSteps();
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
      paintStep(total);
      return;
    }
    let step = 0;
    paintStep(step);
    button.textContent = "Running…";
    button.disabled = true;
    timer = setInterval(() => {
      step += 1;
      paintStep(step);
      if (step >= total) stop();
    }, STEP_MS);
  };

  const select = (tab) => {
    stop();
    for (const other of tabs) {
      const selected = other === tab;
      other.setAttribute("aria-pressed", String(selected));
      document.querySelector(
        `[data-scenario-panel="${other.dataset.scenario}"]`,
      ).hidden = !selected;
    }
    paintStep(totalSteps());
    // the panels differ by up to 672px, so switching while scrolled down leaves the reader
    // adrift with the tabs off-screen above them
    if (tab.getBoundingClientRect().top < 0) tab.scrollIntoView({ block: "start" });
  };

  button.addEventListener("click", replay);

  for (const tab of tabs) {
    tab.addEventListener("click", () => select(tab));
  }
};

const STATE_HELP = {
  acknowledged:
    "The person gave their name, said they were taking it, and named a number of minutes. All three had to be quoted from what they actually said.",
  no_eta:
    "They agreed, but never named a number of minutes. Without a clock there is no commitment, so the ladder moves on.",
  no_answer: "The provider reported the call as failed, so there is no transcript to read.",
  voicemail: "Ringdown hangs up without leaving a message.",
  low_confidence:
    "The provider's own confidence in the transcription was below the policy floor, so nothing in it is trusted.",
  dialling: "The call is placed and ringing. Nothing is recorded until it settles.",
  "on the call": "The call connected and is in progress.",
};

const checkRow = (ok, label) => {
  const row = document.createElement("div");
  row.className =
    "check" + (ok === false ? " check-fail" : ok === null ? " check-unresolved" : "");
  const mark = document.createElement("span");
  mark.className = "check-mark";
  mark.textContent = ok === false ? "[!]" : ok === null ? "[?]" : "[x]";
  const text = document.createElement("span");
  text.textContent = label;
  row.append(mark, text);
  return row;
};

const FAMILIES = {
  links: {
    whole: (total) => `all ${total} records link to the one before them`,
    broken: (failed, total) => `${failed} of ${total} records do not link to the one before them`,
  },
  seals: {
    whole: (total) => `all ${total} seals match their content`,
    broken: (failed, total) => `${failed} of ${total} seals do not match their content`,
  },
  positions: {
    whole: (total) => `all ${total} records carry their position in the chain`,
    broken: (failed, total) => `${failed} of ${total} records sit somewhere they do not claim`,
  },
};

const summarise = (checks, family, wording) => {
  const group = checks.filter((check) => check.family === family);
  if (group.length === 0) return null;
  const failed = group.filter((check) => check.ok === false).length;
  return checkRow(
    failed === 0,
    failed === 0 ? wording.whole(group.length) : wording.broken(failed, group.length),
  );
};

const renderChecks = (checks) => {
  const host = document.getElementById("ledger-checks");
  host.replaceChildren();
  for (const [family, wording] of Object.entries(FAMILIES)) {
    const row = summarise(checks, family, wording);
    if (row) host.append(row);
  }
  for (const check of checks) {
    if (check.family in FAMILIES) continue;
    host.append(checkRow(check.ok, check.label));
  }

  const details = document.createElement("details");
  details.style.marginTop = "16px";
  const summary = document.createElement("summary");
  summary.style.cursor = "pointer";
  summary.style.color = "var(--color-neutral-500)";
  summary.style.fontSize = "0.8125rem";
  summary.textContent = `All ${checks.length} checks, one by one`;
  details.append(summary);
  const all = document.createElement("div");
  all.style.cssText = "display:flex;flex-direction:column;gap:9px;margin-top:12px";
  for (const check of checks) all.append(checkRow(check.ok, check.label));
  details.append(all);
  host.append(details);
};

const renderRecords = (records, changed) => {
  const host = document.getElementById("ledger-records");
  host.replaceChildren();
  for (const record of records) {
    const row = document.createElement("div");
    row.style.cssText =
      "display:flex;gap:12px;align-items:baseline;padding:10px 14px;border-radius:var(--radius-md);box-shadow:inset 0 0 0 1px var(--color-neutral-900)";
    if (changed.has(record.seq)) {
      row.style.boxShadow = "inset 0 0 0 1px var(--color-bad)";
    }
    const seq = document.createElement("span");
    seq.className = "mono";
    seq.style.color = "var(--color-neutral-600)";
    seq.textContent = String(record.seq);
    const type = document.createElement("span");
    type.style.cssText = "font-family:var(--font-heading);flex:1;min-width:0";
    type.textContent = recordLabel(record);
    const hash = document.createElement("button");
    hash.type = "button";
    hash.className = "mono hash-copy";
    hash.textContent = shortHash(record.hash);
    hash.title = `${record.hash}\n\nClick to copy.`;
    hash.setAttribute("aria-label", `Copy the full hash of record ${record.seq}`);
    hash.addEventListener("click", () => copyHash(hash, record.hash));
    row.append(seq, type);
    if (record.instructed === true) {
      const flag = document.createElement("span");
      flag.className = "mono";
      flag.style.cssText =
        "font-size:0.6875rem;color:var(--color-bad);border:1px solid var(--color-bad);" +
        "border-radius:999px;padding:1px 8px;flex:none";
      flag.textContent = "instructed";
      flag.title =
        "The transcript carried an instruction addressed to the agent. It was not followed.";
      row.append(flag);
    }
    row.append(hash);
    host.append(row);
  }
};

const HASH_PREFIX = "sha256:".length;

const shortHash = (hash) => hash.slice(0, 14) + "…";

const recordLabel = (record) =>
  record.type === "verdict" ? `verdict ${record.verdict}` : record.type;

const copyHash = async (element, value) => {
  try {
    await navigator.clipboard.writeText(value);
    element.textContent = "copied";
  } catch (error) {
    element.textContent = "copy refused";
  }
  setTimeout(() => {
    element.textContent = shortHash(value);
  }, 1200);
};

const verdictOf = (checks) => {
  if (checks.some((check) => check.ok === false)) {
    return {
      exit: "exit 40",
      summary: "the ledger does not verify",
      colour: "var(--color-bad)",
      help: "The second channel contradicted the run. Treat the incident as unowned.",
    };
  }
  if (checks.some((check) => check.ok === null)) {
    return {
      exit: "exit 45",
      summary: "unproven, not tampered with",
      colour: "var(--color-neutral-400)",
      help: "Nothing was contradicted, but nothing could be corroborated either.",
    };
  }
  return {
    exit: "exit 0",
    summary: "the ledger verifies",
    colour: "var(--color-accent-300)",
    help: "Somebody acknowledged, with an owner and an ETA, and the second channel agreed.",
  };
};

const renderHeroLedger = (records) => {
  const host = document.getElementById("hero-ledger-records");
  for (const record of records) {
    const row = document.createElement("div");
    row.className = "mono";
    row.style.cssText =
      "display:flex;gap:10px;align-items:baseline;font-size:0.75rem;color:var(--color-neutral-500)";
    const seq = document.createElement("span");
    seq.style.width = "12px";
    seq.textContent = String(record.seq);
    const type = document.createElement("span");
    type.style.cssText = "flex:1;min-width:0;color:var(--color-text)";
    type.textContent = recordLabel(record);
    const hash = document.createElement("span");
    hash.textContent = record.hash.slice(HASH_PREFIX, HASH_PREFIX + 7);
    row.append(seq, type, hash);
    host.append(row);
  }
};

const renderHeroFoot = (verdict, records) => {
  const head = records[records.length - 1];
  document.getElementById("hero-ledger-foot").textContent =
    `${verdict.exit} · ${records.length} records · head ${shortHash(head.hash)}`;
};

const setUpLedger = async () => {
  const status = document.getElementById("ledger-status");
  const body = document.getElementById("ledger-body");
  const tamperButton = document.getElementById("tamper-btn");
  const restoreButton = document.getElementById("restore-btn");

  let committed;
  try {
    committed = await fetchLedger();
  } catch (error) {
    status.textContent = `Could not fetch the ledger (${error.message}). It is committed at examples/ledger.example.jsonl.`;
    tamperButton.disabled = true;
    return;
  }

  const verdict = document.getElementById("ledger-verdict");

  const show = async (records, changed, checks) => {
    const settled = checks ?? (await chainChecks(records));
    renderRecords(records, changed);
    renderChecks(settled);
    const seen = verdictOf(settled);
    verdict.textContent = `${seen.exit} — ${seen.summary}`;
    verdict.style.color = seen.colour;
    verdict.title = seen.help;
  };

  // the hero is above the fold and needs no crypto, so it paints before the ledger
  // view, which is hidden on load and costs a SHA-256 per record to fill
  renderHeroLedger(committed);
  const checks = await chainChecks(committed);
  renderHeroFoot(verdictOf(checks), committed);

  status.hidden = true;
  body.hidden = false;
  await show(committed, new Set(), checks);

  const swap = async (records, changed, tampered) => {
    tamperButton.hidden = tampered;
    restoreButton.hidden = !tampered;
    await show(records, changed);
    verdict.scrollIntoView({ block: "center" });
    verdict.focus({ preventScroll: true });
  };

  tamperButton.addEventListener("click", async () => {
    const rewritten = await tamper(committed);
    const changed = new Set(
      rewritten
        .filter((record, index) => record.hash !== committed[index].hash)
        .map((record) => record.seq),
    );
    await swap(rewritten, changed, true);
  });

  restoreButton.addEventListener("click", () => swap(committed, new Set(), false));
};

setUpTheme();
explainStates();
setUpRouting();
setUpRun();
setUpLedger();
