# Sprint 06 Plan — HIT Logic Complete + Basic Filters

**Goal:** Complete melt-based HIT path with essential safety gates and diagnostic tracking.

**Contract Version:** v1.3.1  
**Master Sprint Plan Reference:** v2.0, Phase 3

---

## In Scope

- Hard filter gates:
  - Blocked terms: lot, roll, set, face value, damaged, accessories
  - Invalid data: missing price, missing time, QTY violations
- Filter diagnostics (rejection reasons tracked)
- INELIGIBLE vs MISS distinction
- Existing Melt HIT logic unchanged (verified stable)
- PROS placeholder (always False)

## Out of Scope

- PROS classification logic
- Numismatic-specific filters
- UX changes (console/email remain unchanged)
- EMA modifications

## Acceptance

- HIT count decreases relative to 06.1 (filters working)
- Diagnostics show `blocked_terms` and `invalid_data` reasons
- No false positives (valid HITs still pass)
- INELIGIBLE count > 0 (filters catching bad data)
- Console/email output unchanged

## Files to Modify

- `classifier.py` — Add filter gate logic, track INELIGIBLE
- `diagnostics.py` — Add filter-specific rejection buckets
- `config.py` — Add filter term lists if needed

---

## Handoff Package

**Files:**
- /mnt/project/Sprint_06_Plan.md (this file)
- /mnt/project/Contract_Packet_v1.3.1.md
- /mnt/user-data/uploads/_system_responsibility_map_v_1_4.md
- /mnt/user-data/uploads/classifier.py
- /mnt/user-data/uploads/diagnostics.py
- /mnt/user-data/uploads/config.py

**Expected Deliverables:**
- classifier.py (modified)
- diagnostics.py (modified)
- config.py (modified)

---

## Success Criteria

**Sprint 06 PASSES if:**
✅ HIT count < Sprint 06.1 baseline  
✅ INELIGIBLE count > 0  
✅ blocked_terms in rejection_buckets  
✅ No valid listings wrongly blocked  
✅ Console/email format unchanged

**Sprint 06 FAILS if:**
❌ HIT count unchanged or increases  
❌ INELIGIBLE = 0 (filters not working)  
❌ Valid HITs blocked (false positives)  
❌ UX formatting changed

---

**END OF SPRINT 06 PLAN**
