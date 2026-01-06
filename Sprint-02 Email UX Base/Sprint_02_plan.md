# Sprint_02_Plan.md — Compatibility Audit + Email UX Skeleton

## Goal (1 sentence)
Verify the stable build can support **Contract_Packet_v1.0** email UX by planning a **static email skeleton** render (placeholders only) with no dependency on parsing, classification, or EMA data.

---

## Files allowed to change
- **Email builder module only** (per SRM)
  - Single module responsible for email subject/body rendering.
  - All other files are read-only and treated as stable.

---

## In-scope behavior
1. **Read-only compatibility audit (planning-level):**
   - Confirm existing email builder responsibilities can express the full Contract_Packet_v1.0 email structure without upstream data.
2. **Email UX skeleton plan:**
   - Subject format:
     - `<earliest_time> Offline eBay Silver HITS (<N> new)`
   - Body structure (exact order, whitespace significant):
     1. Header title
     2. Separator line
     3. Summary block:
        - `Spot | Pawn`
        - `Bid offset`
        - `Target margin`
        - `Max time left`
     4. Blank line
     5. `Total HITs: <N>`
     6. Divider
     7. One or more **placeholder entry blocks**
     8. Divider
     9. `Generated at: YYYY-MM-DD HH:MM:SS`
3. **Placeholders only (no live data):**
   - Currency: `$XX.XX`
   - Percent: `--.-%`
   - Counts / time: `--`
4. **Whitespace-preserving, monospaced intent** consistent with Contract_Packet_v1.0.

---

## Explicit out-of-scope list
- Parsing logic (HTML extraction, selectors, time-left parsing)
- EMA, observer counts, scoring, or price_store access
- Classification logic (Eligible / HIT / PROS / MISS)
- Console UX changes
- Link destination logic or new link rules

---

## Acceptance checks (user-visible)
1. Subject string matches **Contract_Packet_v1.0** exactly.
2. Email body renders in the **exact structural order** defined by the contract.
3. Skeleton render path has **no runtime dependency** on parsed listings or classification output.
4. Output preserves spacing and divider placement (whitespace significant).
5. No raw URLs appear in the rendered skeleton.

---

## Test inputs (HTML pages, scenarios)
- **No HTML files required** (by scope).
- Scenarios:
  1. Skeleton render with no hits provided → valid subject + body produced.
  2. Skeleton render with empty hits list → full structure still renders.
  3. Skeleton render with exactly one placeholder entry block → dividers and spacing match contract.

---

## Expected handoff type
- **Full file(s)** (email builder module only)
  - Justification: implementing a skeleton render path typically touches subject build + body build + entry stub, exceeding a single small snippet.
