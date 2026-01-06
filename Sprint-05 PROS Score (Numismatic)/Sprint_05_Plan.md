# Sprint_05_Plan.md — Prospect Scoring (Numismatic Only)

## Goal (1 sentence)
Implement a deterministic `score_prospect()` that outputs `prospect_score` and `prospect_reasons[]` from **title-driven signals only**, capturing numismatic upside **without affecting melt logic or EMA**.

---

## Interpretation rules
- Score is **linear and additive** (sum of signals).
- **Soft negative signals subtract points but continue scoring**.
- **Hard disqualifiers short-circuit**:
  - Return `score = 0`
  - Emit applicable disqualifier reason(s)
  - Do **not** evaluate remaining signals.

## Authoritative Inputs
- Contract_Packet_v1.1 (math + “PROS are numismatic only; must not feed EMA”) :contentReference[oaicite:0]{index=0}
- System_Responsibility_Map (module boundaries; no UX drift) :contentReference[oaicite:1]{index=1}
- Existing scoring module target: `prospect_score.py` :contentReference[oaicite:2]{index=2}

---

## Files allowed to change (per SRM)
- **`prospect_score.py` only** :contentReference[oaicite:3]{index=3}

No changes to:
- `price_store.*` (no EMA writes, no observers) :contentReference[oaicite:4]{index=4}
- email builder / mailer / console UX :contentReference[oaicite:5]{index=5}
- parsing modules
- HIT/MISS logic modules

---

## In-scope behavior
### 1) Deterministic scoring function
Provide/standardize:
- `score_prospect(listing, *, fmv_floor, dealer_value) -> ProspectScore`
- Output:
  - `ProspectScore.score: int (0..100)`
  - `ProspectScore.reasons: List[str]` (stable, ordered deterministically)

### 2) Dealer payout math (within prospect-only context)
- Dealer anchor is passed in as `dealer_value` (documented as `fmv_floor * NUMISMATIC_PAYOUT_PCT`).
- This sprint may **compute** dealer-derived margins used for scoring (e.g., dealer margin %), but must not modify global dealer math rules elsewhere.

### 3) PROS thresholds (score classification inputs)
- Define deterministic threshold(s) (config-driven) to support later “PROS decision” wiring:
  - e.g., `PROS_MIN_SCORE` and/or tier thresholds
- Sprint 05 does **not** make the PROS decision; it only computes score + reasons (but may include a helper `is_prospect(score)` if already in-module).

### 4) Title-driven signals only
- Signals must be derived from `listing.title` and static config lists/regex only.
- No network calls, no photo analysis, no dependence on parsing beyond the title string already provided.

---

## Explicit out-of-scope list
- EMA updates, price_store writes, observer updates :contentReference[oaicite:6]{index=6}
- Email output (subject/body), console output, link rendering :contentReference[oaicite:7]{index=7}
- HIT/MISS logic and melt pipeline gates
- Parsing changes (HTML extraction, qty parsing, time-left parsing rules beyond best-effort already present)

---

## Checklist: Requirement → Where enforced (per SRM) → What to change (if needed)

### A) “PROS logic isolated from EMA”
- **Where enforced:** `prospect_score.py` must not import or call `price_store.*` and must not mutate shared state. :contentReference[oaicite:8]{index=8}
- **What to change:** Ensure `prospect_score.py` remains pure-function style (already designed that way). :contentReference[oaicite:9]{index=9}

### B) “No effect on melt pipeline”
- **Where enforced:** module boundary + return-only API; no side effects, no global writes. :contentReference[oaicite:10]{index=10}
- **What to change:** Keep scoring output as data (`score`, `reasons`) only; do not gate listings here. :contentReference[oaicite:11]{index=11}

### C) “Deterministic score + reasons”
- **Where enforced:** `score_prospect()` behavior; stable ordering of reasons; clamp score 0..100. :contentReference[oaicite:12]{index=12}
- **What to change:** If any nondeterminism exists (unordered sets, exception-driven reason ordering), replace with deterministic ordering.

### D) “Dealer payout math included”
- **Where enforced:** within `score_prospect()` using passed anchors (`fmv_floor`, `dealer_value`) and current total. :contentReference[oaicite:13]{index=13}
- **What to change:** If the stable build computes dealer_value elsewhere, this module must not re-derive payout pct from globals unless already contractual via config.

### E) “PROS thresholds supported”
- **Where enforced:** config-driven constants read by `prospect_score.py` only; no pipeline wiring. 
- **What to change:** Add/standardize threshold keys and ensure defaults are safe (score-only output still produced even if thresholds missing).

---

## Acceptance checks (local, user-runnable)
### 1) Compile gate
- `py -m py_compile prospect_score.py` :contentReference[oaicite:15]{index=15}

### 2) Smoke-import gate
- `py -c "import prospect_score; print('ok')"` :contentReference[oaicite:16]{index=16}

### 3) Micro-harness (no other modules)
In a REPL:

- Create a tiny listing stub with:
  - `title`
  - `total_price`
  - `bids`
  - `time_left` (optional)

Run:
- `score_prospect(stub, fmv_floor=100.0, dealer_value=80.0)`  
Expect:
- `ProspectScore.score` is int 0..100
- `ProspectScore.reasons` is a stable ordered list (same output across runs)

Test cases:
1. “under-described” style title → score increases, includes reason `under-described`
2. hype/grade-pump title → score decreases, includes reason `hype-language`
3. high-grade terms + priced at/below fmv floor within tolerance → includes `premium-terms-priced-like-raw` (if configured) :contentReference[oaicite:17]{index=17}
4. missing anchors (`fmv_floor=None`) → returns score=0 with reason `missing-anchors` :contentReference[oaicite:18]{index=18}

### 4) Isolation check
- Grep/inspect: `prospect_score.py` contains **no imports** of `price_store`, no file IO, no prints/logging.

---

## Test inputs (HTML pages, scenarios) — 1 to 3 max
- **No HTML required** (title-driven + anchors passed in).  
Use 3 title strings as scenarios:
1. High-grade + certification language (PCGS/NGC/MS/Proof)
2. Under-described/estate/“found” language
3. Disqualify keyword present (to confirm score=0 reasons include hard disqualifier)

---

## Expected handoff type
- **Full file(s): `prospect_score.py` only** :contentReference[oaicite:19]{index=19}  
Reason: threshold support + deterministic reasons + isolation constraints usually touch multiple blocks, exceeding a single small snippet.
