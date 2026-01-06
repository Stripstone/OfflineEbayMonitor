# Sprint_05_1_Plan.md — Schema Integration (Post-Pricing Listing Shape / Adapter)

## Goal (1 sentence)
Define and implement a **canonical post-pricing listing shape** (or a thin adapter) so `prospect_score.score_prospect()` can consume `total_price` and `bids` without changing UX, EMA math, or scoring logic.

---

## Context / Problem Statement (confirmed)
- `score_prospect()` expects at least:
  - `listing.title`
  - `listing.total_price`
  - `listing.bids`
  - optional `listing.time_left` / `end_time_ts`  
  and returns score + reasons. 
- Sprint 03 parser output currently includes:
  - `title`, `qty`, `filter_flags`, `numismatic_flags` (and optional `item_id`, `url`)  
  but **does not include pricing fields** needed by `score_prospect()`. :contentReference[oaicite:1]{index=1}
- This is an **infrastructure/schema gap**, not a scoring issue.

---

## Authoritative Inputs
- SRM boundaries (parser owns extraction; scoring must be pure; no UX drift) 
- Contract Packet (process + no UX/math drift) 
- Current `parser_listings.py` (Sprint 03 shape) :contentReference[oaicite:4]{index=4}
- Current `prospect_score.py` expectations 
- User-provided “Sprint_05.1_Plan.md” (planning seed / acceptance requirement) :contentReference[oaicite:6]{index=6}

---

## Files allowed to change (per SRM + sprint constraint)
- **Option A (Preferred, per uploaded Sprint_05.1 seed):** `parser_listings.py` only 
- **Option B (Adapter-only alternative):** a single new adapter module (ONLY if SRM explicitly allows adding one; otherwise not used)

**Planner decision:** Use **Option A** unless you explicitly approve a new adapter file.  
Rationale: SRM assigns **price/shipping/bids/time-left extraction** to the parser module. 

---

## In-scope behavior
### 1) Canonical post-pricing listing shape (additive, stable)
Extend each parsed listing dict to include these keys (additive; existing Sprint 03 keys unchanged):
- `item_price: float | None`
- `ship_price: float | None` (0.0 for “Free”, None for unknown/non-numeric)
- `total_price: float | None` (derived **in-parser** as `item_price + ship_price` only when both numeric; otherwise None)
- `bids: int` (default 0 when missing)
- `time_left: str` (raw “Xm left / Xh Ym left” text when present)
- `end_clock: str` (raw “(Today 8:42 PM)” text when present)
- `url: str | None` (canonical `/itm/<id>` link when found)
- `item_id: str | None` (from `/itm/<id>` when found)

> This creates a **post-pricing** shape that downstream logic can consume without inventing fields later.

### 2) Determinism + defensive parsing
- Same HTML → same extracted values.
- No randomness, no reliance on DOM order beyond explicit selectors.
- Missing / non-numeric values become `None` (or default `bids=0`).

### 3) Field presence report (acceptance requirement)
Add a tiny function (or CLI flag) in `parser_listings.py` that:
- Loads 1–3 offline HTML files
- Runs parsing
- Produces a **field presence report** (counts of non-null):
  - `item_price`, `ship_price`, `total_price`, `bids`, `time_left`, `end_clock`, `item_id`

This is explicitly called out in the user-provided seed plan. :contentReference[oaicite:9]{index=9}

---

## Explicit out-of-scope list
- UX changes (email/console formatting, subject logic, ordering) 
- EMA updates, observer updates, price_store changes 
- Prospect scoring logic changes (`prospect_score.py` must remain unchanged) 
- HIT/MISS/PROS decisions or gating
- Any math beyond `total_price = item_price + ship_price` when both numeric (no margins, no dealer math, no melt)

---

## Checklist: Requirement → Where enforced now → What to change (if needed)

### A) “prospect_score() expects total_price and bids”
- **Where enforced now:** `prospect_score.score_prospect()` reads `listing.total_price` and `listing.bids`. 
- **Change needed:** Ensure parsed record includes `total_price` and `bids` with stable types.

### B) “Parser output stable + additive”
- **Where enforced now:** Sprint 03 parser returns dicts with fixed keys. :contentReference[oaicite:14]{index=14}
- **Change needed:** Add new keys **without changing** existing keys or meanings.

### C) “No scoring logic changes”
- **Where enforced now:** Scoring module is independent. 
- **Change needed:** None; integration is purely schema.

### D) “No UX / EMA / melt pipeline changes”
- **Where enforced now:** SRM boundaries + sprint scope. 
- **Change needed:** Ensure parser changes do not introduce imports or wiring into monitor/email/price_store.

---

## Acceptance checks (local)
### 1) Compile gate
- `py -m py_compile parser_listings.py` :contentReference[oaicite:17]{index=17}

### 2) Smoke import gate
- `py -c "import parser_listings; print('ok')"` :contentReference[oaicite:18]{index=18}

### 3) Field presence report gate (1–3 offline HTML files)
Run the new report helper against 1–3 files:
- Expect:
  - Non-null counts for `item_price`, `ship_price`, `bids`, `time_left`, `end_clock`, `item_id` are **>0** for at least one file.
  - `total_price` count is consistent with `item_price`+`ship_price` availability.

### 4) Schema compatibility gate (no scoring changes)
Create a minimal adapter object (REPL stub) by mapping a parsed dict into an object-like view (or simply confirm downstream will do so later). Verify:
- `total_price` is present and numeric when possible
- `bids` is int (default 0)
- Title unchanged

---

## Test inputs (HTML pages, 1–3 max)
Use up to three existing offline pages:
1. Modern `li.s-card` page (expected to populate most fields)
2. Legacy `li.s-item` page (ensure fallbacks still work)
3. A page with at least one “Free delivery” shipping example (validate `ship_price=0.0`)

(Exact filenames are selected from your local dataset at run time.)

---

## Expected handoff type
- **Full file(s): `parser_listings.py` only** :contentReference[oaicite:19]{index=19}  
Reason: adding multiple extracted fields + a report helper touches multiple functions/blocks, exceeding “small snippet”.

