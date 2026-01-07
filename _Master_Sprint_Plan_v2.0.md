# EBAY OFFLINE SILVER MONITOR
## Master Sprint Plan v2.0 (Compressed Structure)

> **Purpose**  
> Incrementally evolve a trusted, stable codebase into a feature-complete system  
> **without UX drift, logic entanglement, or context collapse**.

**Version:** 2.0  
**Updated:** January 6, 2026  
**Changes from v1.0:** Compressed Sprints 06.2-08 into 3 focused sprints

---

## PHASE 0 — FOUNDATIONS (COMPLETE)

### Sprint 00 — UX & Math Contract
- **Owner:** Chat A
- **Output:** `Contract_Packet_v1.0.md`
- **Status:** ✅ Complete
- **Notes:** Immutable. Version only if explicitly changed.

---

### Sprint 01 — System Responsibility Map
- **Owner:** Chat B → Chat C → Chat D
- **Output:** `System_Responsibility_Map.md`
- **Status:** ✅ Complete
- **Notes:** Defines file ownership, boundaries, and "must never" rules.

---

## PHASE 1 — COMPATIBILITY & SKELETONS (COMPLETE)

### Sprint 02 — Compatibility Audit + Email UX Skeleton
**Goal:** Verify the stable build can support the UX contract and render a **static email skeleton** using placeholders.

- **Status:** ✅ Complete
- **Notes:** Confirms old stable build's compatibility with current UX contract.

**In Scope**
- Read-only compatibility audit
- Email output structure (spacing, ordering, labels)
- Placeholder values (`$XX.XX`, `--`)

**Out of Scope**
- Parsing
- EMA / scoring
- Classification logic

**Acceptance**
- Matches `Contract_Packet_v1.0.md` exactly
- No runtime dependency on missing data

---

### Sprint 03 — Parser + Classification Shape (No Math)
**Goal:** Define *what data exists*, not what it means.

- **Status:** ✅ Complete

**In Scope**
- Title parsing
- Quantity detection
- Filter term flags
- Numismatic term flags

**Out of Scope**
- EMA
- Prospect scoring
- HIT / MISS logic

**Acceptance**
- Deterministic extraction
- Stable output structure

---

## PHASE 2 — CORE LOGIC (COMPLETE)

### Sprint 04 — EMA Engine (Pure Math)
**Goal:** Implement EMA calculation and observer tracking in isolation.

- **Status:** ✅ Complete

**In Scope**
- EMA calculation
- Observer counts
- Silent eligibility rules

**Out of Scope**
- UX wiring
- Classification logic

**Acceptance**
- Math matches contract exactly
- No output side effects

---

### Sprint 05 — Prospect Scoring (Numismatic Only)
**Goal:** Capture numismatic upside without contaminating melt logic.

- **Status:** ✅ Complete

**In Scope**
- Prospect score calculation
- Dealer payout math
- PROS thresholds

**Out of Scope**
- EMA updates
- Email output
- HIT / MISS logic

**Acceptance**
- PROS logic isolated from EMA
- No effect on melt pipeline

---

### Sprint 05.5 (ad-hoc)
**Goal:** Create working runtime foundation that integrates Sprints 02-05 outputs into end-to-end monitor

- **Status:** ✅ Complete
- **Contract Version:** v1.2 (authoritative)

**In Scope**
- Main runtime orchestrator (`silver_monitor.py`)
- Melt calculation engine (`silver_math.py`)
- Basic HIT/MISS classification (`classifier.py`)
- Configuration (`config.py`)
- Integration with all existing modules
- End-to-end working monitor (parse → classify → email)

**Out of Scope (Deferred)**
- Diagnostic output (Sprint 06.1)
- Filter word gates (Sprint 06)
- PROS classification (Sprint 08)

---

## PHASE 3 — DIAGNOSTICS & FILTERS (CURRENT)

### Sprint 06.1 — Melt HIT / MISS Diagnostics
**Goal:** Validate core melt economics produce visible HITs on real data with diagnostic observability.

- **Status:** ✅ Complete
- **Contract Version:** v1.2 + Clarifications

**In Scope**
- QTY-aware melt calculation
- Pawn payout calculation
- Melt HIT gate (margin vs pawn, cost-basis)
- MISS fallback when Melt HIT fails
- Diagnostic output (JSON + summary text)
- DEBUG_DIAGNOSTICS flag

**Out of Scope**
- Filter words
- PROS logic
- Numismatic scoring

**Acceptance**
- Eligible listings > 0 on known-good pages
- HIT count > 0 on melt-favorable pages
- Diagnostics clearly show why listings MISS
- Diagnostic files created when DEBUG_DIAGNOSTICS = True
- UX unchanged (console + email)

---

### Sprint 06 — HIT Logic Complete + Basic Filters
**Goal:** Complete melt-based HIT path with essential safety gates and diagnostic tracking.

**In Scope**
- Hard filter gates:
  - Blocked terms: lot, roll, set, face value, damaged, accessories
  - Invalid data: missing price, missing time, QTY violations
- Filter diagnostics (rejection reasons tracked)
- INELIGIBLE vs MISS distinction
- Existing Melt HIT logic unchanged (verified stable)
- PROS placeholder (always False)

**Out of Scope**
- PROS classification logic
- Numismatic-specific filters
- UX changes (console/email remain unchanged)
- EMA modifications

**Acceptance**
- HIT count decreases relative to 06.1 (filters working)
- Diagnostics show `blocked_terms` and `invalid_data` reasons
- No false positives (valid HITs still pass)
- INELIGIBLE count > 0 (filters catching bad data)
- Console/email output unchanged

**Files to Modify**
- `classifier.py` — Add filter gate logic, track INELIGIBLE
- `diagnostics.py` — Add filter-specific rejection buckets
- `config.py` — Add filter term lists if needed

---

## PHASE 4 — UX FINALIZATION

### Sprint 07 — Email & Console UX Finalization
**Goal:** Production-ready output formatting for both melt HITs and PROS placeholders.

**In Scope**
- Email body formatting (Contract Section 2):
  - Melt entry format (complete)
  - PROS entry format (placeholders: `"--"` or `"N/A"`)
  - Subject line time calculation
  - Entry sorting (earliest end time first)
  - Field legend accuracy
- Console polish:
  - Table alignment
  - Time format consistency
  - Counts line accuracy
- Remove any temporary scaffolding/debug output

**Out of Scope**
- PROS classification (still False)
- Filter changes
- Classification logic changes

**Acceptance**
- Email matches Contract Section 2 exactly
- Console matches Contract Section 1 exactly
- PROS fields show placeholders (not empty/error)
- Subject line time accurate
- Sorting correct (earliest first)

**Files to Modify**
- `email_builder.py` — Full email formatting per Contract
- `silver_monitor.py` — Console table polish (if needed)

---

## PHASE 5 — NUMISMATIC LOGIC

### Sprint 05.6 — Price Store Key Normalization (PREREQUISITE)
**Goal:** Normalize price_store keys to enable proper EMA aggregation for PROS.

**In Scope**
- Coin metadata extraction (series, year, mint)
- Normalized key format: `"Series|Year|Mint"`
- Update price_store read/write operations
- Support 7 coin series (Morgan, Peace, Kennedy, Walking Liberty, Franklin, Barber, Seated Liberty)

**Out of Scope**
- EMA calculation changes
- Classification changes
- UX changes

**Acceptance**
- Keys format: `"Morgan Dollar|1881|CC"`
- All 7 series extract correctly
- price_store.json uses normalized keys
- No integration breakage

**Files to Modify**
- `parser_listings.py` — Add `extract_coin_metadata(title)`
- `price_store.py` — Use normalized keys

**Notes:** Must complete BEFORE Sprint 08 (PROS needs normalized EMA lookups)

---

### Sprint 08 — PROS Complete
**Goal:** Numismatic upside detection fully operational with tight thresholds.

**In Scope**
- PROS classification logic:
  - Coin name + mint required
  - Dealer/FMV floor validation (from normalized price_store)
  - QTY == 1 hard gate
  - DealerProfit > 0 validation
  - Final prospect_score threshold (tight)
- Numismatic filter tightening:
  - Grade keyword requirements
  - Slabbed/certified preferences
  - Key date detection
- PROS diagnostics:
  - Track `non_numismatic` rejections
  - Track `insufficient_prospect` rejections
  - Sample titles for PROS MISS
- Remove PROS placeholders from UX (populate real data)

**Out of Scope**
- Melt HIT logic changes (stable)
- Basic filter changes (stable from Sprint 06)
- EMA calculation changes

**Acceptance**
- PROS count > 0 on numismatic-heavy pages
- Melt HITs remain unaffected (no regression)
- Diagnostics distinguish PROS vs MISS clearly
- Email shows real PROS data (not placeholders)
- PROS never overrides Melt HIT (Contract rule)

**Files to Modify**
- `classifier.py` — Add PROS classification path
- `prospect_score.py` — Integrate with classifier (if needed)
- `email_builder.py` — Remove PROS placeholders, add real formatting
- `diagnostics.py` — Add PROS-specific rejection tracking

**Dependencies**
- Requires Sprint 05.6 complete (normalized price_store keys)

---

## PHASE 6 — HARDENING

### Sprint 09 — Regression Testing
**Goal:** Prove nothing broke across all features.

**Coverage**
- Cold start behavior (empty price_store, empty seen_hits)
- Duplicate suppression (cross-run deduplication)
- No-HIT runs (all MISS)
- PROS-only runs (no melt HITs)
- Mixed runs (both HIT and PROS)
- Filter edge cases (borderline terms)
- Diagnostic accuracy (counts sum correctly)

**Acceptance**
- PASS / FAIL only (no fixes during verification)
- All scenarios produce expected output
- No crashes or silent failures
- Diagnostics accurate across scenarios

**Test Artifacts**
- Test data sets (HTML files for each scenario)
- Expected outputs (console + email + diagnostics)
- Verification script (automated PASS/FAIL)

---

## SPRINT SEQUENCING (v2.0)

**Completed:**
1. Sprint 00 ✅
2. Sprint 01 ✅
3. Sprint 02 ✅
4. Sprint 03 ✅
5. Sprint 04 ✅
6. Sprint 05 ✅
7. Sprint 05.5 ✅
8. Sprint 06.1 ✅

**Remaining (in order):**
1. Sprint 06 (HIT + filters)
2. Sprint 07 (UX finalization)
3. Sprint 05.6 (price_store normalization)
4. Sprint 08 (PROS complete)
5. Sprint 09 (regression testing)

---

## ROLE SUMMARY

- **You**
  - Decide stability
  - Approve sprint plans
  - Run code locally

- **Chat A (Contract Vault)**
  - Contract authority only
  - Semantic rulings on requirements
  - No planning or implementation

- **Chat B (PM)**
  - Sprint planning only
  - Coordination and routing
  - No artifacts or code

- **Chat C (Build Studio)**
  - Implementation only
  - No explanations or validation

- **Chat D (Verifier)**
  - Verification only
  - PASS / FAIL judgment

---

## OPERATING PRINCIPLES

- Contracts are law
- Stable code is truth
- One sprint, one concern
- Files carry state — chats do not
- No self-validation
- Usage discipline: minimize token waste

---

## CHANGELOG: v1.0 → v2.0

**Compression:**
- Sprint 06.2 + 06.3 + 06.4 → Sprint 06 (HIT + filters) + Sprint 08 (PROS)
- Sprint 07 + 08 → Sprint 07 (UX finalization)
- Added Sprint 05.6 before Sprint 08 (price_store dependency)

**Net Result:**
- Original: 9 remaining sprints (06.2, 06.3, 06.4, 07, 08, 09)
- Compressed: 5 remaining sprints (06, 07, 05.6, 08, 09)
- **Savings:** 4 sprint cycles

**Rationale:**
- User priority: Complete melt path first, PROS second
- Reduce handoff overhead
- Enable ship after Sprint 07 (melt-only mode functional)

---

**END OF MASTER SPRINT PLAN v2.0**
