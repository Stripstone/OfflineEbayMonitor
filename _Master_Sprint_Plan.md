 # EBAY OFFLINE SILVER MONITOR
## Master Sprint Plan (Authoritative Execution Order)

> **Purpose**  
> Incrementally evolve a trusted, stable codebase into a feature-complete system  
> **without UX drift, logic entanglement, or context collapse**.

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
            - **Notes:** Defines file ownership, boundaries, and “must never” rules.

---

## PHASE 1 — COMPATIBILITY & SKELETONS (LOW RISK)

            ### Sprint 02 — Compatibility Audit + Email UX Skeleton
            **Goal:**  
            Verify the stable build can support the UX contract and render a **static email skeleton** using placeholders.
            - **Status:** ✅ Complete
            - **Notes:** Confirms old stable build's compatability with current UX contract.

            **In Scope**
            - Read-only compatibility audit
            - Email output structure (spacing, ordering, labels)
            - Placeholder values (`$XX.XX`, `--`)

            **Out of Scope**
            - Parsing
            - EMA / scoring
            - Classification logic

            **Files Allowed**
            - Email builder module only (per SRM)

            **Acceptance**
            - Matches `Contract_Packet_v1.0.md` exactly
            - No runtime dependency on missing data

---

            ### Sprint 03 — Parser + Classification Shape (No Math)
            **Goal:**  
            Define *what data exists*, not what it means.
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

## PHASE 2 — CORE LOGIC (ISOLATED, TESTABLE)

            ### Sprint 04 — EMA Engine (Pure Math)
            **Goal:**  
            Implement EMA calculation and observer tracking in isolation.
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
            **Goal:**  
            Capture numismatic upside without contaminating melt logic.
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
            # Sprint_05.5 (ad-hoc)
            **Goal:** 
            Create working runtime foundation that integrates Sprints 02-05 outputs into end-to-end monitor
            - **Status:** ✅ Complete

            **Contract Version:** v1.2 (authoritative)

            **Master Sprint Plan Reference:** Foundation sprint (bridges Phase 2 → Sprint 06)
            ## In Scope

            - Main runtime orchestrator (`silver_monitor.py`)
            - Melt calculation engine (`silver_math.py`)
            - Basic HIT/MISS classification (`classifier.py`)
            - Configuration (`config.py`)
            - Integration with all existing modules
            - End-to-end working monitor (parse → classify → email)

            ## Out of Scope (Deferred to Sprint 06.x)

            - ❌ Diagnostic output (Sprint 06.1)
            - ❌ Filter word gates (Sprint 06.2)
            - ❌ PROS classification (Sprint 06.3)
            - ❌ Prospect scoring integration in classifier (Sprint 06.3)

            ---

            ## Files to CREATE

            ### **`silver_monitor.py`** — Runtime Orchestrator
            ---


### Sprint 06 — HIT / MISS / PROS Gating (Ladder Sprint, LOCKED)

**Goal:**  
Decide classification outcomes incrementally (HIT / PROS / MISS) **without presentation logic**,  
while producing a single, human-readable diagnostic snapshot per run that explains *why* listings were accepted or rejected.

---

## Global Rules (Apply to All 06.x Stages)

- Product UX (email + console) MUST remain unchanged
- No additional user-facing output
- Diagnostics are written to disk only
- EMA logic must not be altered
- PROS must never override a Melt HIT
- silver_monitor.py is the runtime entrypoint and orchestrator only

---

## Diagnostic Mode (Option 1 — LOCKED)

Diagnostics are enabled **only** when:

config.DEBUG_DIAGNOSTICS == True

yaml
Copy code

### Recapture / Reset Semantics (LOCKED)

1. When `silver_monitor.py` starts:
   - Ensure `./diagnostics/` exists
   - **RESET (overwrite)** the following files immediately:
     - `./diagnostics/run_diagnostics.json`
     - `./diagnostics/run_diagnostics_summary.txt`

2. During runtime:
   - Diagnostics accumulate **persistently across scan cycles within the same run**
   - No additional diagnostic files are created

3. After each scan cycle (or at least once per run):
   - The same two files are **overwritten in place** with updated data

4. On the next program start:
   - Step (1) occurs again
   - Previous run data is discarded

**Invariant:**  
There is always **exactly one current-run diagnostics snapshot**.

---

## Definitions (LOCKED)

- **INELIGIBLE**  
  Listing cannot be evaluated safely or violates eligibility rules  
  (e.g. blocked terms, invalid QTY, missing end-clock, accessories, damaged).  
  Dropped silently from HIT / PROS / MISS consideration.

- **MISS**  
  Listing is eligible, evaluated, but fails both HIT and PROS gates.

---

## Diagnostic Output — JSON (`run_diagnostics.json`)

### Contents (minimum, LOCKED)

- total_listings_seen
- ineligible_count
- eligible_count
- hit_count
- pros_count
- miss_count

- rejection_buckets (counts, top 5 reasons only):
  - blocked_terms
  - qty_invalid
  - non_numismatic
  - insufficient_margin
  - insufficient_prospect
  - other

- samples_by_reason (max 3 per reason):
  - Each sample includes:
    - title
    - short reason_detail (human readable, no stack traces)

---

## Diagnostic Output — Summary (`run_diagnostics_summary.txt`)

Human-readable snapshot intended for quick inspection after each run.

Must include:
- Run timestamp
- Aggregate counts (seen / eligible / HIT / PROS / MISS / ineligible)
- Top 5 rejection reasons (ranked by count)
- Up to 3 sample titles per reason with short explanation

This file:
- Is never printed to console
- Is never emailed
- Exists only for developer inspection

---

## Sprint 06.x Ladder Execution

## Sprint 06.1 — Melt HIT / MISS Only

**Goal:**  
Validate core melt economics produce visible HITs on real data.

**In Scope**
- QTY-aware melt calculation
- Pawn payout calculation
- Melt HIT gate (margin vs pawn, cost-basis)
- MISS fallback when Melt HIT fails

**Out of Scope**
- Filter words
- PROS logic
- Numismatic scoring

**Acceptance**
- Eligible listings > 0 on known-good pages
- HIT count > 0 on melt-favorable pages
- Diagnostics clearly show why listings MISS

---

## Sprint 06.2 — Add Hard Filter Gates

**Goal:**  
Apply strict exclusion rules and confirm they reduce results in a controlled, explainable way.

**In Scope**
- Blocked filter words (lot, roll, set, face value, damaged, etc.)
- Existing Melt HIT logic unchanged

**Out of Scope**
- PROS logic
- Prospect score

**Acceptance**
- HIT count decreases relative to 06.1
- Diagnostics show blocked_terms as primary rejection cause
- No false positives introduced

---

## Sprint 06.3 — PROS (Loose, Conservative)

**Goal:**  
Introduce numismatic upside with maximum visibility and minimum risk.

**In Scope**
- PROS path enabled
- Coin name required
- Mint mark preferred but not required
- Dealer/FMV floor must exist
- DealerProfit > 0
- QTY == 1 only (hard gate)
- Low / permissive prospect_score threshold

**Out of Scope**
- Tight scoring
- EMA updates
- UX changes

**Acceptance**
- PROS count > 0 on numismatic-heavy pages
- Melt HITs remain unaffected
- Diagnostics distinguish PROS vs MISS clearly

---

## Sprint 06.4 — PROS Tightening (Final Contract Behavior)

**Goal:**  
Reach full PROS contract compliance through incremental tightening.

**In Scope**
- Raise prospect_score threshold
- Enforce mint requirements (if contract-defined)
- Strengthen numismatic keyword rules
- Maintain QTY == 1 gate

**Out of Scope**
- Presentation logic
- Sorting / display
- EMA write behavior

**Acceptance**
- PROS count decreases in plausible steps
- Diagnostics show clear rejection reasons
- Final behavior matches contract intent

---

## Final Sprint 06 Acceptance (Overall)

- HIT / PROS / MISS outcomes are deterministic
- No UX or output changes occurred
- Diagnostic report explains every reduction in results
- System produces signal, not silence
- Ready for Sprint 07 integration


## PHASE 3 — INTEGRATION & USER EXPERIENCE

### Sprint 07 — Wire Logic → Email UX
**Goal:**  
Populate the verified email skeleton with real data.

**In Scope**
- Parser → Math → Classification → Email wiring

**Notes**
- Only sprint allowed to touch all layers

**Acceptance**
- Field ordering correct
- Formatting exact
- Subject time derived correctly

---

### Sprint 08 — Console UX Finalization
**Goal:**  
Lock the live-running console experience.

**In Scope**
- Continuous scan loop
- Table rendering
- Status and sleep cadence output

**Acceptance**
- No silent exits
- Console UX matches contract

---

## PHASE 4 — HARDENING

### Sprint 09 — Regression Testing
**Goal:**  
Prove nothing broke.

**Coverage**
- Cold start behavior
- Duplicate suppression
- No-HIT runs
- PROS-only runs
- Mixed runs

**Acceptance**
- PASS / FAIL only
- No fixes during verification

---

## ROLE SUMMARY

- **You**
  - Decide stability
  - Approve sprint plans
  - Run code locally

- **Chat A**
  - Contract authority only
  - No planning or implementation

- **Chat B**
  - Sprint planning only
  - No artifacts or code

- **Chat C**
  - Implementation only
  - No explanations or validation

- **Chat D**
  - Verification only
  - PASS / FAIL judgment

---

## OPERATING PRINCIPLES

- Contracts are law
- Stable code is truth
- One sprint, one concern
- Files carry state — chats do not
- No self-validation
