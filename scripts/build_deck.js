const pptxgen = require("pptxgenjs");
const p = new pptxgen();
p.defineLayout({ name: "W", width: 13.333, height: 7.5 });
p.layout = "W";

const R = "/Users/gigi/hedgefund-analysis/reports";
// palette — Midnight Executive, biotech/finance
const NAVY = "1E2761", INK = "141B33", ICE = "CADCFC", MINT = "02C39A",
      RED = "C0392F", MUTED = "5B636E", LINE = "E4E6EE", WHITE = "FFFFFF",
      PAPER = "FFFFFF", FAINT = "8A919B", GOLD = "E0A458";
const HF = "Cambria", BF = "Calibri";

function pageno(s, n) {
  s.addText(String(n).padStart(2, "0"), { x: 12.5, y: 7.02, w: 0.7, h: 0.3,
    fontFace: BF, fontSize: 9, color: FAINT, align: "right" });
}
// section header with mint number chip
function head(s, num, title, sub) {
  s.addText(num, { x: 0.6, y: 0.5, w: 0.62, h: 0.62, fontFace: HF, fontSize: 20,
    bold: true, color: WHITE, align: "center", valign: "middle",
    fill: { color: MINT }, line: { color: MINT }, rectRadius: 0.08, shape: p.ShapeType.roundRect });
  s.addText(title, { x: 1.4, y: 0.46, w: 11.4, h: 0.5, fontFace: HF, fontSize: 27,
    bold: true, color: NAVY, align: "left", valign: "middle", margin: 0 });
  if (sub) s.addText(sub, { x: 1.42, y: 0.98, w: 11.3, h: 0.32, fontFace: BF,
    fontSize: 12.5, color: MUTED, align: "left", margin: 0, italic: true });
}
function statCard(s, x, y, w, big, label, col) {
  s.addText(big, { x, y, w, h: 0.72, fontFace: HF, fontSize: 34, bold: true,
    color: col || NAVY, align: "center", valign: "middle", margin: 0 });
  s.addText(label, { x, y: y + 0.72, w, h: 0.5, fontFace: BF, fontSize: 11.5,
    color: MUTED, align: "center", valign: "top", margin: 0 });
}

// ---------------------------------------------------------------- Slide 1: TITLE
let s = p.addSlide();
s.background = { color: INK };
s.addText("INVESTMENT COMMITTEE  ·  FEASIBILITY BRIEF", { x: 0.9, y: 1.5, w: 11, h: 0.4,
  fontFace: BF, fontSize: 13, color: MINT, charSpacing: 3, bold: true });
s.addText("Biotech Clinical-Catalyst Strategy", { x: 0.85, y: 2.05, w: 11.6, h: 1.2,
  fontFace: HF, fontSize: 52, bold: true, color: WHITE, margin: 0 });
s.addText("Trading the stock reaction to clinical-trial & FDA outcomes — market-neutral.",
  { x: 0.9, y: 3.35, w: 11, h: 0.5, fontFace: BF, fontSize: 18, color: ICE, margin: 0 });
s.addText([
  { text: "Perfect-foresight backtest (README Step 2)", options: { color: WHITE, bold: true } },
  { text: "  —  the payoff ceiling and its honest, deployable haircut.", options: { color: FAINT } },
], { x: 0.9, y: 4.0, w: 11, h: 0.4, fontFace: BF, fontSize: 14, margin: 0 });
// bottom stat strip
const strip = [["$10M", "starting capital"], ["2016–2019", "test window"],
  ["Small-cap", "tradeable universe"], ["Market-neutral", "beta-hedged"]];
strip.forEach((c, i) => {
  const x = 0.9 + i * 3.0;
  s.addText(c[0], { x, y: 5.55, w: 2.8, h: 0.5, fontFace: HF, fontSize: 22, bold: true, color: MINT, margin: 0 });
  s.addText(c[1], { x, y: 6.05, w: 2.8, h: 0.35, fontFace: BF, fontSize: 12, color: ICE, margin: 0 });
});
s.addText("July 2026", { x: 0.9, y: 6.75, w: 5, h: 0.3, fontFace: BF, fontSize: 12, color: FAINT, margin: 0 });
s.addNotes("Objective: establish the ceiling of a trial-outcome trading strategy assuming a perfect model, then haircut to what is actually executable. Everything here is small-molecule biotech, 2016-2019, market-neutral.");

// ---------------------------------------------------------------- Slide 2: OBJECTIVE
s = p.addSlide(); s.background = { color: PAPER };
head(s, "1", "What we set out to test", "The ceiling first, then the honest, deployable number");
s.addText([
  { text: "Assume a 100%-accurate outcome model", options: { bold: true, color: NAVY } },
  { text: " (the fantasy ceiling), backtest a $10M book over 2016–2019, then progressively haircut for the constraints that actually bind a biotech book: borrow supply, short executability, sector beta, path risk.", options: { color: "27313F" } },
], { x: 0.6, y: 1.65, w: 7.0, h: 1.6, fontFace: BF, fontSize: 16, lineSpacingMultiple: 1.25, valign: "top" });

// two-question cards on the right
const q = [["1", "What is the ceiling?", "If the model were perfect, how much could the strategy make?"],
  ["2", "What survives reality?", "After borrow limits, executability and costs — what is left to deploy?"]];
q.forEach((c, i) => {
  const y = 1.55 + i * 1.65;
  s.addShape(p.ShapeType.roundRect, { x: 8.0, y, w: 4.7, h: 1.45, fill: { color: "F4F6FC" },
    line: { color: LINE, width: 1 }, rectRadius: 0.09 });
  s.addText(c[0], { x: 8.25, y: y + 0.22, w: 0.6, h: 0.6, fontFace: HF, fontSize: 22, bold: true,
    color: WHITE, align: "center", valign: "middle", fill: { color: NAVY }, rectRadius: 0.3, shape: p.ShapeType.roundRect });
  s.addText(c[1], { x: 9.0, y: y + 0.18, w: 3.5, h: 0.4, fontFace: HF, fontSize: 16, bold: true, color: NAVY, margin: 0 });
  s.addText(c[2], { x: 9.0, y: y + 0.62, w: 3.55, h: 0.7, fontFace: BF, fontSize: 12, color: MUTED, margin: 0 });
});
s.addText([
  { text: "Bottom line.  ", options: { bold: true, color: MINT } },
  { text: "The strategy works and is market-neutral — but it is a ", options: { color: "27313F" } },
  { text: "capacity-limited sleeve", options: { bold: true, color: NAVY } },
  { text: ", not a scalable flagship.", options: { color: "27313F" } },
], { x: 0.6, y: 4.35, w: 7.0, h: 1.1, fontFace: BF, fontSize: 15, lineSpacingMultiple: 1.2, valign: "top" });
s.addShape(p.ShapeType.line, { x: 0.6, y: 5.55, w: 12.1, h: 0, line: { color: LINE, width: 1 } });
s.addText("Data: BioPharmCatalyst small-molecule Approved/CRL + parsed Phase 2/3 · market-model CAR vs XBI · sample 320 small-cap events 2016–2019 (217 successes / 103 failures).",
  { x: 0.6, y: 5.7, w: 12.1, h: 0.4, fontFace: BF, fontSize: 11.5, color: FAINT, italic: true });
pageno(s, 2);
s.addNotes("We are not claiming to have a model yet. Step 2 is the perfect-foresight ceiling. The value of this exercise is the haircut path — showing what a real, executable version keeps.");

// ---------------------------------------------------------------- Slide 3: THE FINDING
s = p.addSlide(); s.background = { color: PAPER };
head(s, "2", "The finding: only failure moves the stock", "Approvals are priced in advance — the information event is failure, and only in small-caps");
s.addShape(p.ShapeType.roundRect, { x: 0.6, y: 1.7, w: 12.1, h: 1.95, fill: { color: "F4F6FC" }, line: { color: LINE, width: 1 }, rectRadius: 0.08 });
statCard(s, 0.9, 1.95, 3.6, "~0%", "Approval-day reaction\n(priced in advance)", NAVY);
statCard(s, 4.85, 1.95, 3.6, "−11% to −18%", "Small-cap failure\n(single-day drop)", RED);
statCard(s, 8.8, 1.95, 3.6, "~0%", "Big-pharma failure\n(non-event)", NAVY);
s.addText([
  { text: "The tradeable signal lives only in small-caps.  ", options: { bold: true, color: NAVY } },
  { text: "A large-cap failure barely moves a diversified pipeline; a small-cap’s whole value is the one drug. That asymmetry is the entire edge — and it is why the universe is deliberately small-cap-only.", options: { color: "27313F" } },
], { x: 0.6, y: 4.05, w: 12.1, h: 1.4, fontFace: BF, fontSize: 16, lineSpacingMultiple: 1.25, valign: "top" });
s.addText([
  { text: "Why the crowd is there:  ", options: { bold: true, color: MINT } },
  { text: "~90% of trials fail, so shorting biotech into a catalyst is the consensus trade — which is exactly what makes the borrow rich when the model is right.", options: { color: "27313F" } },
], { x: 0.6, y: 5.55, w: 12.1, h: 1.0, fontFace: BF, fontSize: 15, lineSpacingMultiple: 1.2, valign: "top" });
pageno(s, 3);
s.addNotes("Key insight for the committee: you do not get paid for predicting approvals — the market already knows. You get paid on failures, and only small-caps actually move. This narrows the whole strategy.");

// ---------------------------------------------------------------- Slide 4: WHERE THE MONEY IS
s = p.addSlide(); s.background = { color: NAVY };
s.addText("Where the money is", { x: 0.7, y: 0.6, w: 12, h: 0.7, fontFace: HF, fontSize: 30, bold: true, color: WHITE, margin: 0 });
s.addText("The profit is on the long side — the failure signal is what makes the shorts crowded, and the lending rich.",
  { x: 0.72, y: 1.35, w: 11.8, h: 0.5, fontFace: BF, fontSize: 15, color: ICE, italic: true, margin: 0 });
const flow = [
  ["~90% of trials fail", "So the crowd systematically shorts biotech names into their catalysts."],
  ["Borrow fees spike", "Heavy short demand drives securities-lending rates sky-high on these names."],
  ["Our model picks the winners", "We go long the names that will actually succeed — against the consensus short."],
  ["We lend to the shorts", "Collecting their borrow fees as they are proven wrong, on top of the price jump."],
];
flow.forEach((c, i) => {
  const y = 2.2 + i * 1.12;
  s.addText(String(i + 1), { x: 0.7, y, w: 0.7, h: 0.7, fontFace: HF, fontSize: 22, bold: true, color: NAVY,
    align: "center", valign: "middle", fill: { color: MINT }, rectRadius: 0.35, shape: p.ShapeType.roundRect });
  s.addText(c[0], { x: 1.65, y: y - 0.02, w: 4.6, h: 0.5, fontFace: HF, fontSize: 18, bold: true, color: WHITE, valign: "middle", margin: 0 });
  s.addText(c[1], { x: 6.4, y: y - 0.02, w: 6.3, h: 0.75, fontFace: BF, fontSize: 13.5, color: ICE, valign: "middle", margin: 0 });
});
pageno(s, 4);
s.addNotes("This is the counter-consensus core: the crowd shorts because most trials fail; when our model finds the exceptions, we are long AND we rent our shares to the very shorts who are wrong. Two income streams from one position.");

// ---------------------------------------------------------------- Slide 5: THE STRATEGY (3 legs)
s = p.addSlide(); s.background = { color: PAPER };
head(s, "3", "The strategy — deployed = long + lend", "Money comes from long price + lending fees; the short leg was tested and dropped");
const legs = [
  ["Long + lend", MINT, "Buy known successes ~1 month out, hold ~3 months, and lend the shares to the crowded shorts for borrow-fee income. The engine.", "DEPLOYED — the engine"],
  ["Short / puts", RED, "Short — or buy puts on — known failures. After honest borrow limits it nets flat-to-negative; only pays in the bull regime. Not deployed.", "tested & dropped"],
  ["Hedge beta", NAVY, "Net biotech-sector exposure hedged with XBI, so returns are alpha, not market direction. Cost return this window.", "optional — mandate / tail"],
];
legs.forEach((c, i) => {
  const x = 0.6 + i * 4.05;
  s.addShape(p.ShapeType.roundRect, { x, y: 1.75, w: 3.75, h: 3.7, fill: { color: "F7F8FC" }, line: { color: LINE, width: 1 }, rectRadius: 0.09 });
  s.addShape(p.ShapeType.roundRect, { x: x + 0.35, y: 2.1, w: 0.55, h: 0.55, fill: { color: c[1] }, line: { color: c[1] }, rectRadius: 0.28 });
  s.addText(String(i + 1), { x: x + 0.35, y: 2.1, w: 0.55, h: 0.55, fontFace: HF, fontSize: 20, bold: true, color: WHITE, align: "center", valign: "middle", margin: 0 });
  s.addText(c[0], { x: x + 1.05, y: 2.12, w: 2.5, h: 0.55, fontFace: HF, fontSize: 20, bold: true, color: NAVY, valign: "middle", margin: 0 });
  s.addText(c[2], { x: x + 0.35, y: 2.95, w: 3.1, h: 1.7, fontFace: BF, fontSize: 14, color: "27313F", lineSpacingMultiple: 1.2, valign: "top", margin: 0 });
  s.addText(c[3].toUpperCase(), { x: x + 0.35, y: 4.75, w: 3.1, h: 0.4, fontFace: BF, fontSize: 11, bold: true, color: c[1], charSpacing: 1.5, margin: 0 });
});
s.addText([
  { text: "Long price + lending is the whole engine. ", options: { bold: true, color: NAVY } },
  { text: "The short leg loses money after honest borrow limits (see next slide) and isn't needed for neutrality — the XBI hedge already provides that — so it is dropped.", options: { color: MUTED } },
], { x: 0.6, y: 5.75, w: 12.1, h: 0.8, fontFace: BF, fontSize: 14, lineSpacingMultiple: 1.15, valign: "top" });
pageno(s, 5);
s.addNotes("Three legs, but do not let the symmetry mislead: the long+lend leg is the profit engine. Short and hedge are risk-control, not return generators.");

// ---------------------------------------------------------------- Slide 6: MECHANICS + FORMULA
s = p.addSlide(); s.background = { color: PAPER };
head(s, "4", "Mechanics & the lending engine", "The levers a reviewer should interrogate — with a worked example");
// left: rules
const rules = [
  ["Portfolio", "5% per position · 10% max per company · 150% gross cap → ~30 positions open; new events queue when full."],
  ["Timing (from our data)", "Long: enter T−20, hold to T+63 (~3 mo). Short: enter T−10, cover T+5 (a one-day gap)."],
  ["Executability gate", "Keep only 60% of failures as shortable — the biggest drops are the hardest to borrow. This is why the short leg barely earns."],
  ["Costs", "80 bps market impact + 5 bps commission, round trip (small caps move on your trades)."],
];
let ry = 1.7;
rules.forEach((c) => {
  s.addText(c[0], { x: 0.6, y: ry, w: 6.2, h: 0.35, fontFace: HF, fontSize: 14.5, bold: true, color: NAVY, margin: 0 });
  s.addText(c[1], { x: 0.6, y: ry + 0.36, w: 6.2, h: 0.72, fontFace: BF, fontSize: 12.5, color: "27313F", lineSpacingMultiple: 1.12, margin: 0 });
  ry += 1.18;
});
// right: formula box
s.addShape(p.ShapeType.roundRect, { x: 7.1, y: 1.7, w: 5.6, h: 4.55, fill: { color: INK }, line: { color: INK }, rectRadius: 0.09 });
s.addText("Lending income (per position)", { x: 7.4, y: 1.9, w: 5.0, h: 0.4, fontFace: HF, fontSize: 16, bold: true, color: MINT, margin: 0 });
s.addText("notional × rate × utilization × days/252 × multiplier",
  { x: 7.4, y: 2.4, w: 5.0, h: 0.6, fontFace: "Courier New", fontSize: 12.5, color: ICE, margin: 0 });
s.addText([
  { text: "pre-catalyst (20d): full rate ", options: { color: WHITE } },
  { text: "× 1.0", options: { color: MINT, bold: true } },
  { text: "\npost-catalyst (63d): collapsed ", options: { color: WHITE } },
  { text: "× 0.10", options: { color: MINT, bold: true } },
], { x: 7.4, y: 3.05, w: 5.0, h: 0.85, fontFace: BF, fontSize: 12.5, lineSpacingMultiple: 1.25, margin: 0 });
s.addShape(p.ShapeType.line, { x: 7.4, y: 4.0, w: 5.0, h: 0, line: { color: "34406B", width: 1 } });
s.addText("Worked example — one $1M position (rate 100%/yr, util 40%)",
  { x: 7.4, y: 4.1, w: 5.0, h: 0.35, fontFace: BF, fontSize: 11.5, bold: true, color: ICE, margin: 0 });
s.addText([
  { text: "pre   = 1M × 1.00 × 0.40 × 20/252 × 1.00 = $31,700\n", options: {} },
  { text: "post = 1M × 1.00 × 0.40 × 63/252 × 0.10 = $10,000", options: {} },
], { x: 7.4, y: 4.5, w: 5.0, h: 0.8, fontFace: "Courier New", fontSize: 11, color: WHITE, lineSpacingMultiple: 1.2, margin: 0 });
s.addText([
  { text: "total lending = $41,700 ", options: { color: MINT, bold: true } },
  { text: "(4.2% of the position)", options: { color: ICE } },
], { x: 7.4, y: 5.45, w: 5.0, h: 0.5, fontFace: HF, fontSize: 15, margin: 0 });
pageno(s, 6);
s.addNotes("The lending fee is a daily flow, not an upfront payment, and it collapses after the catalyst because shorts cover. That time-shape is why we model pre- and post- separately. 4.2% per position from lending alone, before the price move.");

// ---------------------------------------------------------------- Slide 7: RESULTS
s = p.addSlide(); s.background = { color: PAPER };
head(s, "5", "Results — deployed long+lend vs the market", "2016–2019, small-cap, capped pre-COVID · perfect-foresight; realistic 90% model ~$26M");
statCard(s, 0.6, 1.5, 3.0, "$28.9M", "$10M grows to", MINT);
statCard(s, 3.65, 1.5, 3.0, "29%", "CAGR", NAVY);
statCard(s, 6.7, 1.5, 3.0, "1.65", "Sharpe", NAVY);
statCard(s, 9.75, 1.5, 3.0, "−16%", "max drawdown", RED);
// benchmark table
const td = (t, o = {}) => ({ text: t, options: { fontFace: BF, fontSize: 12, color: "27313F", valign: "middle", align: o.align || "center", ...o } });
const rows = [
  [td("$10M →", { align: "left", bold: true, color: WHITE }), td("Total", { bold: true, color: WHITE }), td("CAGR", { bold: true, color: WHITE }), td("Sharpe", { bold: true, color: WHITE }), td("Max DD", { bold: true, color: WHITE })].map(c => ({ ...c, options: { ...c.options, fill: NAVY } })),
  [td("Strategy (perfect foresight)", { align: "left", bold: true, color: NAVY }), td("$28.9M", { bold: true, color: MINT }), td("29%", { bold: true }), td("1.65", { bold: true }), td("−16%", { bold: true })],
  [td("Strategy @ 90% model (fair)", { align: "left" }), td("$26.1M"), td("~27%"), td("—"), td("—")],
  [td("S&P 500 buy-and-hold", { align: "left" }), td("$16.7M"), td("13%"), td("1.11"), td("−20%")],
  [td("XBI (biotech) buy-and-hold", { align: "left" }), td("$15.1M"), td("10%"), td("0.42"), td("−36%")],
];
s.addTable(rows, { x: 0.6, y: 2.85, w: 6.5, colW: [2.7, 1.0, 0.9, 0.95, 0.95], rowH: 0.52,
  border: { type: "solid", color: LINE, pt: 1 }, fill: { color: WHITE }, align: "center", valign: "middle" });
s.addImage({ path: `${R}/backtest_equity.png`, x: 7.35, y: 2.9, w: 5.35, h: 2.41 });
s.addText([
  { text: "Not apples-to-apples at the top — the strategy line is perfect-foresight. ", options: { color: MUTED } },
  { text: "The 90%-model row ($26.1M, +161%) is the fair comparison, still well above the S&P's +67% with a smaller drawdown. ", options: { bold: true, color: NAVY } },
  { text: "Window capped 2020-02-14 so the COVID crash doesn't distort either side.", options: { color: MUTED } },
], { x: 0.6, y: 5.5, w: 12.1, h: 0.95, fontFace: BF, fontSize: 12.5, lineSpacingMultiple: 1.12, valign: "top" });
pageno(s, 7);
s.addNotes("Lead with $28.9M perfect-foresight, but be upfront it's a ceiling; the fair line is the 90% model at $26.1M / +161%, which still beats the S&P's +67% with a smaller drawdown. Benchmarks capped pre-COVID so the 2020 crash doesn't flatter us.");

// ---------------------------------------------------------------- Slide 8: P&L BY LEG
s = p.addSlide(); s.background = { color: PAPER };
head(s, "6", "P&L by leg — why we drop the short", "Universe: 320 small-cap events = 217 successes (longs) + 103 failures · short gate keeps 60% = 62 names · 100% model");
const pd = (t, o = {}) => ({ text: t, options: { fontFace: BF, fontSize: 12.5, color: "27313F", valign: "middle", align: o.align || "center", ...o } });
const prows = [
  [pd("Scenario (assumptions)", { align: "left", bold: true, color: WHITE }), pd("L-price", { bold: true, color: WHITE }), pd("L-lend", { bold: true, color: WHITE }), pd("Short net", { bold: true, color: WHITE }), pd("Frict", { bold: true, color: WHITE }), pd("Gross", { bold: true, color: WHITE })].map(c => ({ ...c, options: { ...c.options, fill: NAVY } })),
  [pd("BEAR — borrow 30%, 30% short, 150bps", { align: "left" }), pd("+$15.2M"), pd("+$0.6M"), pd("−$1.6M", { color: RED, bold: true }), pd("−$1.8M"), pd("+$12.3M")],
  [pd("BASE — borrow 100%, 60% short, 80bps", { align: "left", bold: true, color: NAVY }), pd("+$14.7M"), pd("+$4.3M"), pd("−$0.6M", { color: RED, bold: true }), pd("−$1.1M"), pd("+$17.3M", { bold: true })],
  [pd("BULL — borrow 200%, 70% short, 50bps", { align: "left" }), pd("+$14.7M"), pd("+$17.4M"), pd("+$0.1M", { color: MINT, bold: true }), pd("−$0.8M"), pd("+$31.5M")],
];
s.addTable(prows, { x: 0.6, y: 1.7, w: 12.1, colW: [4.3, 1.55, 1.55, 1.6, 1.5, 1.6], rowH: 0.6,
  border: { type: "solid", color: LINE, pt: 1 }, fill: { color: WHITE }, valign: "middle" });
// callouts
s.addShape(p.ShapeType.roundRect, { x: 0.6, y: 4.2, w: 6.0, h: 1.35, fill: { color: "FBF3F2" }, line: { color: RED, width: 1 }, rectRadius: 0.09 });
s.addText([{ text: "Short is negative except in BULL.  ", options: { bold: true, color: RED } }, { text: "Of 103 failures we can borrow only ~60% (62) — the biggest drops are un-borrowable — so what's left barely covers borrow cost. Loses in BEAR/BASE; dropped.", options: { color: "27313F" } }],
  { x: 0.85, y: 4.32, w: 5.5, h: 1.15, fontFace: BF, fontSize: 12, lineSpacingMultiple: 1.1, valign: "middle", margin: 0 });
s.addShape(p.ShapeType.roundRect, { x: 6.85, y: 4.2, w: 5.85, h: 1.35, fill: { color: "F0FAF6" }, line: { color: MINT, width: 1 }, rectRadius: 0.09 });
s.addText([{ text: "Lending is the swing factor.  ", options: { bold: true, color: MINT } }, { text: "Long price is stable (~$15M); lending income runs $0.6M → $4.3M → $17.4M across regimes. It adds +18% over price-only.", options: { color: "27313F" } }],
  { x: 7.1, y: 4.35, w: 5.35, h: 1.1, fontFace: BF, fontSize: 12.5, lineSpacingMultiple: 1.12, valign: "middle", margin: 0 });
s.addText([
  { text: "The real risk is not the short leg — it is misclassifying a failure as a winner.  ", options: { bold: true, color: NAVY } },
  { text: "A wrong long buys a landmine that gaps −15%. Failure-class precision, not raw accuracy, is the number that matters.", options: { color: MUTED } },
], { x: 0.6, y: 5.8, w: 12.1, h: 0.8, fontFace: BF, fontSize: 13.5, lineSpacingMultiple: 1.12, valign: "top" });
pageno(s, 8);
s.addNotes("Held at 100% model so the columns isolate the cost assumptions. Short is a drag everywhere except bull, and doesn't help neutrality (the XBI hedge does that) — so it's dropped. Long price is steady; lending is what swings the result.");

// ---------------------------------------------------------------- Slide 9: ROBUSTNESS / MC
s = p.addSlide(); s.background = { color: PAPER };
head(s, "7", "Robustness — Monte Carlo", "Accuracy held fixed (90% & 80%) so trade-luck vs assumption-luck is like-for-like");
const mh = (t) => ({ text: t, options: { fontFace: BF, fontSize: 11.5, bold: true, color: WHITE, fill: NAVY, valign: "middle", align: "center" } });
const mdc = (t, o = {}) => ({ text: t, options: { fontFace: BF, fontSize: 11.5, color: "27313F", valign: "middle", align: o.align || "center", ...o } });
const mrows = [
  [{ ...mh("What varies (accuracy fixed)"), options: { ...mh("").options, align: "left" } }, mh("90% model"), mh("80% model")],
  [mdc("A. Trade luck (bootstrap)", { align: "left" }), mdc("$26.6M"), mdc("$23.8M")],
  [mdc("B1. Assumptions, independent", { align: "left" }), mdc("$26.9M"), mdc("$24.5M")],
  [mdc("B2. Assumptions, correlated — hedged", { align: "left", bold: true, color: NAVY }), mdc("$26.7M", { bold: true }), mdc("$24.2M", { bold: true })],
  [mdc("B2 correlated — un-hedged", { align: "left" }), mdc("$30.4M"), mdc("$27.6M")],
  [mdc("P(lose money over 4yr)", { align: "left", italic: true }), { text: "0% in every cell", options: { fontFace: BF, fontSize: 11.5, color: MINT, bold: true, align: "center", colspan: 2, valign: "middle" } }],
];
s.addTable(mrows, { x: 0.6, y: 1.7, w: 7.0, colW: [3.7, 1.65, 1.65], rowH: 0.52,
  border: { type: "solid", color: LINE, pt: 1 }, fill: { color: WHITE }, valign: "middle" });
s.addText([
  { text: "At a fixed accuracy, trade luck ≈ assumption luck ", options: { bold: true, color: NAVY } },
  { text: "— not a few lucky deals nor lucky cost guesses. Dropping the short leg removed the downside: ", options: { color: "27313F" } },
  { text: "P(loss) is 0% everywhere. ", options: { bold: true, color: MINT } },
  { text: "Un-hedged sits ~$3–4M higher (the hedge cost return here). The lever that dominates is model accuracy.", options: { color: "27313F" } },
], { x: 0.6, y: 5.05, w: 7.0, h: 1.7, fontFace: BF, fontSize: 13, lineSpacingMultiple: 1.2, valign: "top" });
s.addImage({ path: `${R}/backtest_montecarlo.png`, x: 8.0, y: 1.7, w: 4.7, h: 3.46 });
s.addText("Density-normalized so all curves compare despite different sample counts. 90% (top) / 80% (bottom); purple = un-hedged.",
  { x: 8.0, y: 5.2, w: 4.7, h: 0.6, fontFace: BF, fontSize: 10, color: FAINT, italic: true, align: "center" });
pageno(s, 9);
s.addNotes("Accuracy pinned at a common baseline so trade-luck and assumption-luck are comparable — they land in the same place. Dropping the short leg removed the loss scenarios (P(loss)=0%). Un-hedged is higher; the hedge is a mandate choice. Borrow rate (cost of lending) is the single biggest input — the one-at-a-time MC in the brief shows that.");

// ---------------------------------------------------------------- Slide 10: WHAT COULD BREAK IT
s = p.addSlide(); s.background = { color: PAPER };
head(s, "8", "What could break it", "Honest confidence on every assumption");
const ch = (t) => ({ text: t, options: { fontFace: BF, fontSize: 13, bold: true, color: WHITE, fill: NAVY, valign: "middle", align: "center" } });
const cd = (t, o = {}) => ({ text: t, options: { fontFace: BF, fontSize: 13, color: "27313F", valign: "middle", align: o.align || "left", ...o } });
const conf = (t, col) => ({ text: t, options: { fontFace: BF, fontSize: 12.5, bold: true, color: col, valign: "middle", align: "center" } });
const crows = [
  [{ ...ch("Assumption"), options: { ...ch("").options, align: "left" } }, ch("Value"), ch("Confidence")],
  [cd("Entry / exit timing"), cd("T−20/T+63 · T−10/T+5", { align: "center" }), conf("grounded in data", MINT)],
  [cd("Costs"), cd("80 + 5 bps", { align: "center" }), conf("market convention", MINT)],
  [cd("Sizing / caps"), cd("5% / 10% / 150%", { align: "center" }), conf("reasonable, swept", NAVY)],
  [cd("Borrow rate + utilization"), cd("100%/yr · 40%", { align: "center" }), conf("assumed — no data", RED)],
  [cd("Model accuracy"), cd("100% (Step 2 ceiling)", { align: "center" }), conf("ceiling only — 90/80% in MC", GOLD)],
  [cd("XBI hedge"), cd("on", { align: "center" }), conf("optional — cost return here", GOLD)],
];
s.addTable(crows, { x: 0.6, y: 1.7, w: 12.1, colW: [4.6, 4.0, 3.5], rowH: 0.55,
  border: { type: "solid", color: LINE, pt: 1 }, fill: { color: WHITE }, valign: "middle" });
s.addShape(p.ShapeType.roundRect, { x: 0.6, y: 5.7, w: 12.1, h: 1.0, fill: { color: "FBF3F2" }, line: { color: RED, width: 1 }, rectRadius: 0.08 });
s.addText([
  { text: "The real uncertainty is borrow economics and model accuracy.  ", options: { bold: true, color: RED } },
  { text: "Both are swept in the one-at-a-time and joint Monte Carlo; neither breaks the strategy (P(loss)=0%), but the borrow rate is un-measured until we trade, and accuracy is what Step 3/4 must deliver. Window capped pre-COVID; short executability is gone (leg dropped).", options: { color: "27313F" } },
], { x: 0.85, y: 5.8, w: 11.6, h: 0.82, fontFace: BF, fontSize: 12.5, lineSpacingMultiple: 1.12, valign: "middle", margin: 0 });
pageno(s, 10);
s.addNotes("I am flagging my own weak points. Timing and costs are solid. Borrow economics and executability are assumed and could be wrong — but they are stress-tested and the strategy survives. The honest gap is a real model.");

// ---------------------------------------------------------------- Slide 11: RECOMMENDATION
s = p.addSlide(); s.background = { color: INK };
s.addText("Recommendation", { x: 0.85, y: 0.75, w: 11.6, h: 0.8, fontFace: HF, fontSize: 34, bold: true, color: WHITE, margin: 0 });
// does it add profit? comparison
s.addText("Does the strategy actually add profit?", { x: 0.85, y: 1.85, w: 11.6, h: 0.45, fontFace: HF, fontSize: 20, bold: true, color: ICE, margin: 0 });
s.addShape(p.ShapeType.roundRect, { x: 0.85, y: 2.5, w: 5.6, h: 1.7, fill: { color: "232C4D" }, line: { color: "34406B", width: 1 }, rectRadius: 0.09 });
s.addText("$24.6M", { x: 1.1, y: 2.7, w: 5.1, h: 0.7, fontFace: HF, fontSize: 32, bold: true, color: ICE, margin: 0 });
s.addText("price-trading alone", { x: 1.1, y: 3.42, w: 5.1, h: 0.4, fontFace: BF, fontSize: 14, color: FAINT, margin: 0 });
s.addShape(p.ShapeType.roundRect, { x: 6.75, y: 2.5, w: 5.7, h: 1.7, fill: { color: "0E3B32" }, line: { color: MINT, width: 1.5 }, rectRadius: 0.09 });
s.addText("$28.9M", { x: 7.0, y: 2.7, w: 5.2, h: 0.7, fontFace: HF, fontSize: 32, bold: true, color: MINT, margin: 0 });
s.addText([{ text: "with lending overlay  ", options: { color: WHITE } }, { text: "(+18%)", options: { color: MINT, bold: true } }],
  { x: 7.0, y: 3.42, w: 5.2, h: 0.4, fontFace: BF, fontSize: 14, margin: 0 });
s.addText("Yes — the deployed long+lend book; the short leg was tested and dropped. Lending is the differentiator, not decoration.",
  { x: 0.85, y: 4.35, w: 11.6, h: 0.4, fontFace: BF, fontSize: 15, color: ICE, italic: true, margin: 0 });
// next step
s.addShape(p.ShapeType.roundRect, { x: 0.85, y: 5.0, w: 11.6, h: 1.75, fill: { color: "232C4D" }, line: { color: "34406B", width: 1 }, rectRadius: 0.09 });
s.addText("Next step", { x: 1.1, y: 5.2, w: 11, h: 0.4, fontFace: BF, fontSize: 12, bold: true, color: MINT, charSpacing: 2, margin: 0 });
s.addText([
  { text: "Proceed to Steps 3 / 4 — build the real predictive model and measure its true accuracy.  ", options: { bold: true, color: WHITE } },
  { text: "We have stress-tested a 70–100% accuracy range; we have not built the model. The one number that decides everything is how well it separates winners from landmines.", options: { color: ICE } },
], { x: 1.1, y: 5.6, w: 11.1, h: 1.05, fontFace: BF, fontSize: 15, lineSpacingMultiple: 1.2, valign: "top", margin: 0 });
pageno(s, 11);
s.addNotes("Ask: approval to proceed to Step 3/4 — building and validating the model. The economics work if the model is real; everything hinges on failure-class precision. This is a capacity-limited uncorrelated sleeve, not a flagship.");

p.writeFile({ fileName: `${R}/IC_Biotech_Catalyst_Strategy.pptx` }).then(f => console.log("WROTE", f));
