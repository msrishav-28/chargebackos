import { CATEGORY_LABELS, STATE_LABELS } from "./constants";
import type { DisputeCategory } from "./types";

function groupIN(n: number) {
  const s = String(Math.round(Math.abs(n)));
  if (s.length <= 3) return s;
  const last3 = s.slice(-3);
  const rest = s.slice(0, -3);
  return rest.replace(/\B(?=(\d{2})+(?!\d))/g, ",") + "," + last3;
}

export function formatINR(n: number, compact = false) {
  if (!Number.isFinite(n)) return "—";
  const sign = n < 0 ? "−" : "";
  const abs = Math.abs(n);
  if (compact && abs >= 100000) {
    if (abs >= 10000000) return `${sign}₹${(abs / 10000000).toFixed(1)}Cr`;
    return `${sign}₹${(abs / 100000).toFixed(1)}L`;
  }
  return `${sign}₹${groupIN(abs)}`;
}

export function formatINRExact(n: number) {
  if (!Number.isFinite(n)) return "—";
  const sign = n < 0 ? "−" : "";
  const abs = Math.abs(n);
  const [r, f] = abs.toFixed(2).split(".");
  return `${sign}₹${groupIN(Number(r))}.${f}`;
}

export function formatNumber(n: number) {
  if (!Number.isFinite(n)) return "—";
  return groupIN(n);
}

export function formatPct(n: number, digits = 1) {
  if (!Number.isFinite(n)) return "—";
  return `${(n * 100).toFixed(digits)}%`;
}

export function formatScore(n: number, digits = 2) {
  if (!Number.isFinite(n)) return "—";
  return n.toFixed(digits);
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function pad(n: number) {
  return n < 10 ? `0${n}` : String(n);
}

/** IST (UTC+5:30), hydration-safe. */
export function formatDate(iso: string) {
  const d = new Date(iso);
  const ist = new Date(d.getTime() + 5.5 * 3600 * 1000);
  return `${pad(ist.getUTCDate())} ${MONTHS[ist.getUTCMonth()]} ${ist.getUTCFullYear()}, ${pad(ist.getUTCHours())}:${pad(ist.getUTCMinutes())} IST`;
}

export function formatDateShort(iso: string) {
  const d = new Date(iso);
  const ist = new Date(d.getTime() + 5.5 * 3600 * 1000);
  return `${pad(ist.getUTCDate())} ${MONTHS[ist.getUTCMonth()]}`;
}

export function categoryLabel(c: DisputeCategory) {
  return CATEGORY_LABELS[c];
}

export function stateLabel(s: string) {
  return STATE_LABELS[s] ?? s;
}

export function signedINR(n: number) {
  const abs = formatINR(Math.abs(n));
  if (n > 0) return `+${abs}`;
  if (n < 0) return `−${abs.replace("₹", "₹")}`;
  return abs;
}
