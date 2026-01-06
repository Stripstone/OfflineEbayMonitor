# Sprint_01_Plan.md

## Goal (1 sentence)
Create an authoritative System Responsibility Map (SRM) that locks file-level responsibilities and “must never” boundaries so future sprints don’t drift the UX, math, or link contracts.

## Files allowed to change
- System_Responsibility_Map.md (NEW or REPLACE if it already exists)

## In-scope behavior
- Produce a one-page SRM that:
  - Lists each runtime-critical file/module and its single responsibility (console loop/UX, parsing, classification, math, email rendering, email send gate, seen_hits storage, price_store/EMA storage).
  - Declares explicit “must never” boundaries per file (e.g., email formatting logic must never live in the parser; math formulas must never be duplicated; link formatting must never output raw URLs).
  - States allowed dependency direction at a high level (monitor → parser → classifier → email builder → mailer; never reversed).
  - Includes a short “where to add X” guide (e.g., new parsing heuristic, new email field requiring contract revision, etc.).

## Explicit out-of-scope list
- Any Python code changes (no refactors, no cleanup, no helpers).
- Any UX changes to console or email (formatting, labels, ordering, spacing, dividers).
- Any math changes (margins, payout formulas, rounding rules, HIT/PROS gates).
- Any link behavior changes (raw URL handling, destinations, ordering).
- Any pipeline tuning, config changes, or feature additions.

## Acceptance checks (user-visible)
1. SRM exists as a single markdown document and fits on one screen/page.
2. SRM explicitly references non-negotiables from the Contract Packet:
   - Console loop never exits silently; per-cycle output always renders.
   - Console table columns and time-left formatting are locked.
   - Email subject/body structure is locked and ordered by earliest time left.
   - Math contract is frozen (cost-basis margins; corrected dealer profit formula).
   - Link contract is frozen; no raw URLs in rendered email.
3. SRM contains a “must never” section that prevents:
   - Duplicate math across modules.
   - Email formatting logic outside the email builder.
   - Parser emitting UX strings.
4. SRM includes a clear dependency direction sketch (text-only).

## Test inputs (HTML pages, scenarios)
- No HTML files required (documentation-only sprint).
- Review scenarios:
  1) Where to implement a new QTY heuristic → exactly one file named.
  2) Where to change email spacing/dividers → explicitly forbidden without Contract Packet revision.
  3) Where raw URL suppression is enforced → exactly one responsible module named.

## Expected handoff type
- Full file(s) (System_Responsibility_Map.md only)
