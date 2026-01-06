# Sprint_03_Plan.md — Parser + Classification Shape (No Math)

## Goal (1 sentence)
Define a deterministic, stable extraction shape for offline eBay listings that captures **what data exists** (title, qty, filter flags, numismatic flags) without performing math or HIT/MISS logic.

---

## Inputs (authoritative references)
- Contract Packet (UX + process non-negotiables) :contentReference[oaicite:0]{index=0}
- System Responsibility Map (module boundaries) :contentReference[oaicite:1]{index=1}
- Offline HTML Parsing Contract v1.1 (HTML structures to support) :contentReference[oaicite:2]{index=2}

---

## Files allowed to change
- **Parser module(s) only**: `parser_*.py` responsible for offline HTML extraction (per SRM)
- **Classification-shape module only** (if separate): a single module/function that constructs the extracted record and computes flags (still “shape only”, no gates)

> Note: Console/email UX modules and any math modules are **read-only** this sprint.

---

## In-scope behavior
### 1) Title parsing (deterministic)
- Extract listing title from:
  - `.s-card__title` (modern card) and/or
  - legacy `.s-item__title` (legacy pages)
- Normalize title text (trim, collapse whitespace) but **do not** rewrite meaning.

### 2) Quantity detection (deterministic)
- Derive `qty` using only deterministic rules (no probabilistic scoring):
  - Prefer explicit patterns in title (e.g., `lot of 3`, `x3`, `3x`, `qty 3`, `3 pcs`, `3 coins`)
  - If multiple candidates exist, apply a fixed precedence order (documented in code comments later by Chat C; Planner only specifies the precedence requirement).
  - Default `qty = 1` when no signal exists.

### 3) Filter term flags (shape only)
- Produce boolean flags indicating presence of configured **filter terms** in the title (e.g., “copy”, “replica”, “plated”, etc. — whatever the stable build already uses).
- Flags are **purely descriptive** this sprint (do not exclude listings).

### 4) Numismatic term flags (shape only)
- Produce boolean flags indicating presence of **numismatic high-grade / key term** signals in title (e.g., “MS”, “Proof”, “DMPL”, “PCGS”, “NGC”, “AU”, etc. — whatever the stable build already uses).
- Flags are **purely descriptive** this sprint (do not drive PROS/HIT).

### 5) Stable output record structure (new or confirmed)
Each parsed listing must produce a stable dict/object with at least:
- `title: str`
- `qty: int`
- `filter_flags: { <flag_name>: bool, ... }`
- `numismatic_flags: { <flag_name>: bool, ... }`

Optional (allowed if already trivially available in current parser without branching):
- `listing_id` or `item_id` (from `/itm/<id>`) for identity only
- `url` (canonical listing URL) for identity only

---

## Explicit out-of-scope list
- EMA, observer counts, price_store access
- Prospect scoring of any kind
- HIT / MISS / PROS classification gates
- Any melt/pawn/dealer math
- Console UX changes (table columns, time-left formatting, loop cadence) :contentReference[oaicite:3]{index=3}
- Email UX changes (subject/body/ordering/dividers) :contentReference[oaicite:4]{index=4}

---

## Acceptance checks (user-visible)
1. **Deterministic extraction**
   - Running the parser twice over the same HTML produces identical `title/qty/flags` outputs.
2. **Stable output structure**
   - Every listing yields the same keys, with correct types:
     - `title` is always a string (non-empty if title exists in HTML)
     - `qty` is always an integer ≥ 1
     - flags are always dictionaries of booleans
3. **No hidden coupling**
   - The extraction path does not import or call:
     - math modules
     - email builder
     - mailer
     - EMA / scoring logic
4. **Modern + legacy compatibility**
   - Title extraction works for both:
     - modern `.s-card__title` cards
     - legacy `.s-item__title` cards (as described in parsing contract) :contentReference[oaicite:5]{index=5}

---

## Test inputs (HTML pages, scenarios) — 1 to 3 max
Use **exactly three** offline pages from the user’s existing dataset (no new scraping required):

1. **Modern s-card page**  
   - Contains `li` listing cards with `.s-card__title` and `.s-card__price` (per parsing contract v1.1). :contentReference[oaicite:6]{index=6}
2. **Legacy s-item page**  
   - Contains `li.s-item` listings with `.s-item__title`. :contentReference[oaicite:7]{index=7}
3. **Quantity edge-case page**  
   - At least 1 listing with a title expressing quantity (“lot of N”, “N coins”, “N pcs”, “Nx”, etc.) to validate deterministic qty precedence.

---

## Expected handoff type
- **Full file(s)**  
  Rationale: parser + flag shape work typically touches multiple functions/blocks (title extraction, qty extraction, flag extraction, record assembly), exceeding “single contiguous edit”.

