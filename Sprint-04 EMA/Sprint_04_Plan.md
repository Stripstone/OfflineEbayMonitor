# Sprint_04_Plan.md — EMA Engine (Pure Math)

## Goal (1 sentence)
Implement an isolated, callable EMA update function in the **price/EMA storage module** that updates `price_store` (EMA + observer totals) **only when strictly eligible**, with **no UX side effects** and full compile/smoke-import pass.

---

## Allowed Inputs (authoritative references)
- Contract Packet (math + eligibility non-negotiables) :contentReference[oaicite:0]{index=0}
- System Responsibility Map (module boundaries) :contentReference[oaicite:1]{index=1}
- Current EMA storage module: `price_store.py` :contentReference[oaicite:2]{index=2}

---

## Files allowed to change (per SRM)
- **`price_store.py` only** :contentReference[oaicite:3]{index=3}  
  *Do not touch monitor, parser, classifier, email builder, mailer, config UX, or console/email formatting.*

---

## In-scope behavior
- EMA calculation (per Contract Packet)
- Observer tracking and `o.<count>` support via stored observer totals
- Silent strict eligibility (ineligible inputs produce **no-op** with **no side effects**)
- Callable function interface: `(normalized_key, numeric_price, bid_count) -> updated? / no-op`

---

## Out of scope
- Any UX wiring (console/email formatting, subject logic, link logic)
- Classification decisions (HIT/MISS/PROS, filter rules)
- Parsing changes (HTML extraction)
- Any logging/printing/debug output

---

## Checklist: Rule → Where enforced now → What to change (if needed)

### 1) “Callable EMA update function takes normalized key + numeric price + bid_count”
- **Where enforced now:** `update_price(store, key, total_price, bid_count) -> bool` exists. :contentReference[oaicite:4]{index=4}
- **Change needed:** Ensure the function’s contract is aligned to Sprint 04:
  - Accept **normalized key** (already `key: str`)
  - Accept **numeric price input** (currently `total_price: float`)
  - Accept **bid_count** (currently `bid_count: int`)
  - Return **True only when update occurs**, else False (already true)

### 2) “Updates price_store only when eligible; otherwise no-op without side effects”
- **Where enforced now:** `update_price()` performs early returns:
  - no key → False
  - `PRICE_CAPTURE_ONLY_IF_BIDS` and `bid_count < 1` → False
  - `total_price <= 0` → False :contentReference[oaicite:5]{index=5}
- **Change needed:** Map eligibility to the Contract Packet’s strict/silent rule set:
  - Confirm “eligible price” is **numeric > 0**
  - Confirm bid gating is **strict** when enabled
  - Ensure **no store mutation** occurs for ineligible cases (already true due to early returns)
  - Ensure **no logging/printing** occurs (verify none added)

### 3) “EMA calculation matches Contract Packet exactly”
- **Where enforced now:** `update_ema_entry(existing, new_total_price, bid_count, alpha)` uses:
  - `ema = alpha*new + (1-alpha)*old`
  - rounds EMA and last_total_price to 2dp
  - increments samples by 1 :contentReference[oaicite:6]{index=6}
- **Change needed:** Validate against Contract Packet expectations (Planner requirement):
  - If Contract Packet mandates different rounding (e.g., round only at display), adjust **inside this module only**
  - If Contract Packet expects shipping exclusion/inclusion, confirm the EMA input is the specified numeric price (this sprint treats input as already normalized per scope)

### 4) “Observer counts (o.<count>) source string support”
- **Where enforced now:** `OBSERVERS_TOTAL` field exists and accumulates `bid_count` each update; `lookup_observers()` and `get_ema_value_and_observers()` exist. :contentReference[oaicite:7]{index=7}
- **Change needed:** None, unless Contract Packet defines `o.<count>` as:
  - cumulative `bid_count` totals (current) vs
  - number of observing listings (could be `SAMPLES`)  
  If mismatch, adjust `OBSERVERS_TOTAL` update to match Contract Packet—still within `price_store.py` only.

### 5) “Silent eligibility rules (no logging/printing; ineligible does not update EMA)”
- **Where enforced now:** no `print()` present; early returns prevent mutation. :contentReference[oaicite:8]{index=8}
- **Change needed:** Ensure any new callable wrapper added remains silent and does not call console/email modules.

### 6) “Compiles and smoke-imports cleanly”
- **Where enforced now:** Module imports `config` and `utils.now_ts`. :contentReference[oaicite:9]{index=9}
- **Change needed:** If Sprint 04 requires isolation beyond current imports, keep within file:
  - Avoid adding new dependencies
  - Keep typing/imports explicit and py_compile safe

---

## Acceptance checks (run locally)

### A) Compile gate
Run from project root:
- `py -m py_compile price_store.py`

### B) Smoke import gate
In a clean shell:
- `py -c "import price_store; print('ok')"`

### C) Minimal harness calls (no side effects beyond in-memory store)
In a Python REPL or one-liner:
1) **Eligible update applies**
- Create `store = {}`
- Call EMA update with: `key='Test|1|A'`, `price=100.0`, `bid_count=2`
- Expect: returns `True`, store now has key with `[ema, samples, last_price, ts, observers_total]`

2) **Ineligible bid no-op when bid-gate enabled**
- Ensure `config.PRICE_CAPTURE_ONLY_IF_BIDS=True`
- Call with `bid_count=0`
- Expect: returns `False`, store unchanged

3) **Ineligible price no-op**
- Call with `price=0` or `price=-5`
- Expect: returns `False`, store unchanged

4) **Observer accumulation**
- Apply two eligible updates with bid_count 2 then 3
- Expect: `OBSERVERS_TOTAL` increases by 5 total (or per Contract Packet definition)

> Note: This sprint does not require writing to disk. File IO (`load_store/save_store`) remains unchanged unless Contract Packet demands formatting guarantees.

---

## Test inputs (HTML pages, scenarios)
- **No HTML pages required** (pure math + storage).

---

## Expected handoff type
- **Full file(s)** (`price_store.py` only)  
  Rationale: implementing/standardizing a callable EMA update API and aligning eligibility/observer semantics may touch multiple functions and constants.

