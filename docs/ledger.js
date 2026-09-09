export const GENESIS = "sha256:" + "0".repeat(64);
export const LEDGER_URL = "./ledger.example.jsonl";

const SUPPORTED_SCHEMA = 1;

const sortDeep = (value) => {
  if (Array.isArray(value)) return value.map(sortDeep);
  if (value === null || typeof value !== "object") return value;
  return Object.fromEntries(
    Object.keys(value)
      .sort()
      .map((key) => [key, sortDeep(value[key])]),
  );
};

const NON_ASCII = new RegExp("[^\\u0000-\\u007e]", "g");

const escapeNonAscii = (text) =>
  text.replace(NON_ASCII, (char) =>
    "\\u" + char.charCodeAt(0).toString(16).padStart(4, "0"),
  );

export const canonicalJson = (value) => escapeNonAscii(JSON.stringify(sortDeep(value)));

const hex = (buffer) =>
  [...new Uint8Array(buffer)].map((byte) => byte.toString(16).padStart(2, "0")).join("");

export const digest = async (value) => {
  const bytes = new TextEncoder().encode(canonicalJson(value));
  return "sha256:" + hex(await crypto.subtle.digest("SHA-256", bytes));
};

export const sealed = async (record) => {
  const { hash, ...body } = record;
  return { ...body, hash: await digest(body) };
};

export const parseLedger = (text) =>
  text
    .split("\n")
    .filter((line) => line.trim() !== "")
    .map((line) => JSON.parse(line));

export const fetchLedger = async () => {
  const response = await fetch(LEDGER_URL, { cache: "no-store" });
  if (!response.ok) throw new Error(`the server answered ${response.status}`);
  return parseLedger(await response.text());
};

const incidentOf = (record) =>
  record.incident != null
    ? String(record.incident)
    : String(record.attempt_id ?? "").split("/").slice(0, -2).join("/");

const verdictV1 = (verdicts) =>
  verdicts.find((verdict) => verdict !== "not_acknowledged") ?? "unacknowledged";

const VERDICT_RULES = { 1: verdictV1 };

const corroborationCheck = (number, record) => {
  const where = `record ${number} reports the verdict was`;
  if (record.verified === true) {
    return { ok: true, label: `${where} corroborated on the second channel`, family: "verification" };
  }
  const contradicted = (record.total ?? 0) - (record.passed ?? 0) - (record.unresolved ?? 0);
  if (contradicted > 0) {
    return { ok: false, label: `${where} contradicted on the second channel`, family: "verification" };
  }
  return { ok: null, label: `${where} never confirmed on the second channel`, family: "verification" };
};

const linkChecks = (records) => {
  let prev = GENESIS;
  return records.map((record, index) => {
    const number = index + 1;
    const target = number === 1 ? "the genesis hash" : `record ${number - 1}`;
    const check = { ok: record.prev === prev, label: `record ${number} links to ${target}`, family: "links" };
    prev = record.hash ?? "";
    return check;
  });
};

const sealChecks = (records) =>
  Promise.all(
    records.map(async (record, index) => ({
      ok: record.hash === (await sealed(record)).hash,
      label: `record ${index + 1} hash matches its content`,
      family: "seals",
    })),
  );

const numbered = (records) => records.map((record, index) => ({ record, number: index + 1 }));

const positionChecks = (records) =>
  numbered(records)
    .filter(({ record }) => "seq" in record)
    .map(({ record, number }) => ({
      ok: record.seq === number,
      label: `record ${number} carries its position in the chain`,
      family: "positions",
    }));

const orphanChecks = (records) => {
  const placed = new Set(
    records.filter((record) => record.type === "attempt").map((record) => record.attempt_id),
  );
  return numbered(records)
    .filter(({ record }) => record.type === "intent" && !placed.has(record.attempt_id))
    .map(({ record, number }) => ({
      ok: null,
      label: `record ${number} announced ${record.key} and has no attempt`,
      family: "orphans",
    }));
};

const verificationChecks = (records) =>
  numbered(records)
    .filter(({ record }) => record.type === "verification")
    .map(({ record, number }) => corroborationCheck(number, record));

const verdictChecks = (records) => {
  const checks = [];
  const verdicts = new Map();
  for (const { record, number } of numbered(records)) {
    const incident = incidentOf(record);
    if (record.type === "attempt") {
      verdicts.set(incident, [...(verdicts.get(incident) ?? []), String(record.verdict)]);
    }
    if (record.type !== "verdict") continue;
    const recorded = String(record.verdict);
    const schema = record.schema ?? SUPPORTED_SCHEMA;
    const rule = Number.isInteger(schema) ? VERDICT_RULES[schema] : undefined;
    if (rule === undefined) {
      verdicts.delete(incident);
      checks.push({
        ok: null,
        label: `record ${number} was written by schema ${schema}, which this page cannot read`,
        family: "verdict",
      });
      continue;
    }
    const derived = rule(verdicts.get(incident) ?? []);
    verdicts.delete(incident);
    const tail =
      recorded === derived
        ? "follows from the recorded attempts"
        : `does not follow from the recorded attempts (${derived})`;
    checks.push({
      ok: recorded === derived,
      label: `record ${number} verdict ${recorded} ${tail}`,
      family: "verdict",
    });
  }
  return checks;
};

export const chainChecks = async (records) => [
  ...linkChecks(records),
  ...(await sealChecks(records)),
  ...positionChecks(records),
  ...orphanChecks(records),
  ...verificationChecks(records),
  ...verdictChecks(records),
];

export const tamper = async (records) => {
  const rewritten = records.map((record) =>
    record.type === "verdict" ? { ...record, verdict: "acknowledged" } : { ...record },
  );
  const relinked = [];
  let prev = GENESIS;
  for (const record of rewritten) {
    const resealed = await sealed({ ...record, prev });
    relinked.push(resealed);
    prev = resealed.hash;
  }
  return relinked;
};
