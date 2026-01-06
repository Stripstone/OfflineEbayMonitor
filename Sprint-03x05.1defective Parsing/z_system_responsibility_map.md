# System Responsibility Map (SRM)

> **Purpose:** Lock file-level responsibilities and immutable boundaries so the Console + Email product remains UX- and math-contract compliant. This document is authoritative for Phase 1+ unless revised by an explicit Contract Packet update.

---

## Dependency Direction (High Level)
**monitor → parser → classifier → math → email_builder → mailer**

- Calls flow strictly left → right.
- No reverse imports.
- Shared state (seen hits, price store) is accessed only by the owning module.

---

## File Responsibilities & Boundaries

### `silver_monitor.py` (or top-level runner)
**Owns:**
- Main loop lifecycle (never exits silently)
- Scan cycle cadence & sleep visibility
- Orchestration only (no business logic)

**Must never:**
- Parse HTML
- Compute math
- Format console tables or email bodies

---

### `core_monitor.py` (pipeline coordinator)
**Owns:**
- Per-file scan coordination
- Calling parser → classifier → email builder in order
- HIT/PROS eligibility gates (as defined in Contract Packet)

**Must never:**
- Reformat UX strings
- Recompute math formulas
- Emit raw URLs

---

### `parser_*.py` (HTML parsing)
**Owns:**
- Offline HTML extraction (auction-only)
- Identity, price, shipping, quantity, time-left parsing

**Must never:**
- Emit UX-facing strings
- Apply business rules (HIT/PROS)
- Perform math beyond raw extraction

---

### `classifier_*.py` (classification & gates)
**Owns:**
- Eligible / Ineligible
- HIT / PROS / MISS decisions (per Contract Packet)

**Must never:**
- Calculate payout math
- Format console or email output
- Override UX ordering rules

---

### `math_*.py` / `numismatic_rules.py`
**Owns:**
- All melt, pawn, dealer, margin, and recommendation math
- Rounding and display precision rules

**Must never:**
- Change formulas without Contract Packet revision
- Duplicate math in other modules
- Emit UX strings

---

### `email_builder.py` / `email_format.py`
**Owns:**
- Exact email UX contract (subject, body, ordering, dividers)
- Field labels, spacing, and ordering
- Link label rendering (never raw URLs)

**Must never:**
- Recompute math
- Reorder entries outside earliest-time-left rule
- Include fields not defined in Contract Packet

---

### `mailer.py` / `mail_config.py`
**Owns:**
- SMTP configuration
- Send / no-send decision based on new HITs only

**Must never:**
- Modify email body content
- Apply business logic

---

### `price_store.*` (EMA / observer data)
**Owns:**
- Persisted EMA values and observer counts
- Read/write hygiene

**Must never:**
- Affect HIT gates directly
- Override static defaults silently

---

### `seen_hits.*`
**Owns:**
- Deduplication across runs

**Must never:**
- Gate classification logic
- Alter math or UX

---

## "Where Do I Add X?" Guide
- **New HTML field extraction:** parser module only
- **New classification rule:** classifier module only (must cite Contract Packet)
- **Math tweak:** forbidden without Contract Packet revision
- **Email spacing/labels/dividers:** forbidden without Contract Packet revision
- **New console column:** forbidden without Contract Packet revision

---

## Non‑Negotiables (Contract Anchors)
- Console renders every cycle; loop never exits silently
- Console table columns and time-left formatting are locked
- Email subject/body format is locked and ordered by earliest time left
- Margins are cost-basis; dealer profit formula is fixed
- Rendered email never shows raw URLs

---

**Change Control:** Any violation requires an explicit Contract Packet version bump (vX.Y → vX.(Y+1)).

