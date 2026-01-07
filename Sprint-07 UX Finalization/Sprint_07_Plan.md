# SPRINT 07 PLAN
**Email & Console UX Finalization**

**Version:** 1.0  
**Date:** January 7, 2026  
**Status:** ACTIVE  
**Phase:** 4 (UX Finalization)

---

## GOAL

Production-ready output formatting for email alerts and console display, matching Contract v1.3.1 specifications exactly. Implement complete melt entry format with PROS placeholders.

---

## CONTRACT AUTHORITY

**Primary References:**
- Contract v1.3.1 Section 1 (Console UX Contract)
- Contract v1.3.1 Section 2 (Email UX Contract - Complete Specification)
- Contract v1.3.1 Section 4 (Link Contract)
- Contract v1.3.1 Clarification #1 (Counts line format)
- Contract v1.3.1 Clarification #2 (Target column definition)

---

## FILES IN SCOPE

### Primary Modifications
1. **`email_builder.py`** (major rewrite)
   - Implement complete Section 2 email format
   - Subject line with earliest time + new count
   - Header section (spot, pawn, margins, time filter, total HITs)
   - Melt entry format (complete multi-line breakdown)
   - PROS entry format (with placeholders)
   - Footer (generated timestamp)
   - Link construction (eBay listing, eBay sales, CoinBook)
   - Entry sorting (earliest end time first)
   - Entry numbering (sequential from #1)

2. **`silver_monitor.py`** (console polish)
   - Table column alignment verification
   - Time format consistency check
   - Counts line format verification (per Clarification #1)
   - Remove any debug/scaffolding output

### Reference Only (Read, Do Not Modify)
- `classifier.py` (provides Evaluated objects with is_hit/is_prospect flags)
- `silver_math.py` (provides calculation results)
- `config.py` (provides constants for header section)
- `Contract_Packet_v1.3.1.md` (specification authority)
- `_system_responsibility_map_v_1_4.md` (component boundaries)

---

## CURRENT STATE ANALYSIS

**What Works (Don't Break):**
- Classification logic (HIT/MISS via melt economics)
- Filter gates (time, qty, blacklist, blocked terms)
- Diagnostic output (DEBUG_DIAGNOSTICS mode)
- Deduplication (seen_hits.json)
- Parser integration (ListingAdapter bridge)

**What Needs Implementation:**
- Complete email body formatting (currently minimal)
- PROS entry format with placeholders
- Subject line calculation (earliest time)
- Entry sorting (by end time)
- Link construction (3 types)
- Console table polish (if needed)

---

## ACCEPTANCE CRITERIA

### AC1: Email Subject Line (Contract Section 2)
**Format:** `[A1] Offline eBay Silver HITS ([A6] new)`
- ✅ `[A1]` = Earliest listing time (h:mm AM/PM format, e.g., "3:45 PM")
- ✅ `[A6]` = Total new HIT count (integer)
- ✅ Example: `3:45 PM Offline eBay Silver HITS (3 new)`

**Contract Citation:** Section 2, Subject Line Format

---

### AC2: Email Header Section (Contract Section 2)
**Format:**
```
Spot: [A2] | Pawn: [A3]%
Bid offset: [A4]
Target margin: [A5-min]%—[A5-max]%
Max time left: [A7] hours
Total HITs: [A6]
```

**Requirements:**
- ✅ All values pulled from `config.py` constants
- ✅ Dollar amounts formatted as `$X.XX`
- ✅ Percentages as integers (no decimal unless needed)
- ✅ Em dash (—) between margin range
- ✅ Exact spacing and line breaks as shown

**Contract Citation:** Section 2, Header Section

---

### AC3: Melt Entry Format (Contract Section 2)
**Format:**
```
----------------------------------------
#[N] [F1]
Title: [F2]

Current Total: [B3] (item [B1] + ship [B2])
Current Profit (pawn): [D1] ([D2] margin vs pawn)
RecMaxBid: [D4] ([D3] incl. ship) | [D5$] ([D5%] margin vs pawn)

Qty: [C1] | oz/coin: [C2] | Total oz: [C3]
Melt: [C4] | Pawn payout: [C5]
Time left: [T1] ([T2])

Links: Link to Listing | Link to Ebay Sales
----------------------------------------
```

**Requirements:**
- ✅ 40-dash dividers (before and after each entry)
- ✅ Sequential numbering (#1, #2, ...)
- ✅ Full title (no truncation)
- ✅ All field values from silver_math calculations
- ✅ Dollar amounts: `$X.XX` format (2 decimals)
- ✅ Percentages: Integer (1 decimal if needed)
- ✅ Time left: `Xh Ym` format + absolute time
- ✅ Links: Clickable URLs (constructed per Section 4)

**Field Mapping:**
- `[N]` = Entry number (sequential)
- `[F1]` = listing.item_id
- `[F2]` = listing.title (full text)
- `[B1]` = listing.total_price (or item_price if separate)
- `[B2]` = listing.shipping (default 0)
- `[B3]` = B1 + B2
- `[C1]` = listing.qty
- `[C2]` = silver_calc["oz"] / qty (oz per coin)
- `[C3]` = silver_calc["oz"]
- `[C4]` = silver_calc["melt_value"]
- `[C5]` = silver_calc["pawn_exit"]
- `[D1]` = C5 - B3 (current profit)
- `[D2]` = (D1 / B3) * 100 (current margin)
- `[D3]` = silver_calc["rec_max_total"]
- `[D4]` = D3 - B2 - bid_offset (rec max bid)
- `[D5$]` = C5 - D3 (profit at max)
- `[D5%]` = (D5$ / D3) * 100 (margin at max)
- `[T1]` = listing.time_left
- `[T2]` = listing.end_clock (absolute time)

**Contract Citation:** Section 2, Melt Entry Format

---

### AC4: PROS Entry Format with Placeholders (Contract Section 2)
**Format:**
```
----------------------------------------
#[N] [F1]
Title: [F2]
<<<< Numismatic override: [F3] >>>>

Est. dealer payout (@[E-dealer-%]%): [E2] (est. profit: [E3$], [E3-margin]% margin vs current)
FMV floor (G—VG): [E1] | Source: Offline EMA [E-source-version]
Current Total: [B3] (item [B1] + ship [B2])
Current Profit: [D1] ([D2] margin)
RecMaxTotal (incl. ship): [D3]
RecMaxBid (item only): [D4]

Qty: [C1] | oz/coin: [C2] | Total oz: [C3]
Melt: [C4] | Pawn payout: [C5]
Time left: [T1] ([T2])

Links: Link to Listing | Link to Ebay Sales | Link to CoinBook
----------------------------------------
```

**Requirements:**
- ✅ PROS entry format used when `evaluated.is_prospect = True`
- ✅ Melt entry format used when `evaluated.is_prospect = False`
- ✅ PROS-specific fields show placeholders: `"--"` or `"N/A"`
  - `[F3]` = `"N/A"` (numismatic override)
  - `[E1]` = `"--"` (FMV floor)
  - `[E2]` = `"--"` (dealer payout)
  - `[E3$]` = `"--"` (est profit)
  - `[E3-margin]` = `"--"` (margin)
  - `[E-dealer-%]` = `"--"` (dealer %)
  - `[E-source-version]` = `"--"` (source)
- ✅ All melt fields (B/C/D/T) populated normally
- ✅ CoinBook link shows placeholder URL or `"[Placeholder]"`

**Note:** Sprint 08 will populate real PROS data. This sprint establishes the format structure.

**Contract Citation:** Section 2, Numismatic Entry Format

---

### AC5: Entry Sorting and Numbering (Contract Section 2)
**Requirements:**
- ✅ Entries sorted by earliest end time (ascending)
- ✅ Sequential numbering from #1
- ✅ Numbering applies to all entries (melt + PROS combined)
- ✅ Earliest listing appears first in email body

**Contract Citation:** Section 2, Entry Rules

---

### AC6: Link Construction (Contract Section 4)
**eBay Listing URL:**
```
https://www.ebay.com/itm/<item_id>
```
- ✅ Use listing.item_id
- ✅ No query parameters
- ✅ No trailing slashes

**eBay Sales Search URL:**
```
https://www.ebay.com/sch/i.html?_nkw=<series>+<year>+<mint>&LH_Sold=1&LH_Complete=1
```
- ✅ Extract series, year, mint from title (best effort)
- ✅ If extraction fails, use generic title search
- ✅ Include LH_Sold=1 and LH_Complete=1 parameters

**CoinBook URL (PROS only):**
```
https://www.pcgs.com/coinfacts/<series-slug>
```
- ✅ Series-level directory only
- ✅ For Sprint 07: Use placeholder `"[Placeholder - CoinBook]"`
- ✅ Sprint 08 will implement real links

**Contract Citation:** Section 2 (Link construction rules), Section 4 (Link Contract)

---

### AC7: Email Footer (Contract Section 2)
**Format:**
```
Generated at: [A8]
```
- ✅ `[A8]` = Timestamp of email generation
- ✅ Format: `YYYY-MM-DD HH:MM:SS`
- ✅ Use local system time

**Contract Citation:** Section 2, Footer

---

### AC8: Console Output Verification (Contract Section 1)
**Requirements:**
- ✅ Counts line format: `Found: X | Eligible: Y | HITs: Z | New: W`
  - Per Clarification #1 (exact format with pipe separators)
- ✅ Table columns (fixed order): `Target | Found | Hit? | Price | QTY | Time Left | Title`
- ✅ Target column: Always "Silver" (per Clarification #2)
- ✅ Time format consistency:
  - Console timestamps: `[HH:MM:SS]` (24-hour)
  - Listing end times: `3:45p` / `11:30a` (12-hour, lowercase)
  - Time remaining: `2h 15m` (no leading zeros on hours)
- ✅ No debug output (unless DEBUG_DIAGNOSTICS = True)

**Contract Citation:** Section 1 (Console UX Contract), Clarifications #1-2

---

### AC9: No Logic Changes (Sprint Boundary)
**Requirements:**
- ✅ Classification logic unchanged (HIT/MISS via melt economics)
- ✅ Filter gates unchanged (time, qty, blacklist, blocked terms)
- ✅ PROS classification remains False (Sprint 08 will implement)
- ✅ Diagnostic output unchanged (Sprint 06 implementation stable)

**Rationale:** This sprint is UX-only. All logic changes are out of scope.

---

## OUT OF SCOPE

**Explicitly NOT Included:**
- ❌ PROS classification logic (Sprint 08)
- ❌ Filter word changes (Sprint 06 complete)
- ❌ Classification threshold changes (Sprint 06 complete)
- ❌ Diagnostic logic changes (Sprint 06 complete)
- ❌ Price store normalization (Sprint 05.6, before Sprint 08)
- ❌ EMA calculation changes (stable from Sprint 04)
- ❌ Parser changes (stable from Sprint 03)

**Why Out of Scope:**
- This sprint focuses solely on presenting existing data in production format
- All backend logic is stable and verified
- PROS placeholders establish format structure for Sprint 08

---

## IMPLEMENTATION APPROACH

### Phase 1: Email Builder Rewrite
1. Create helper functions:
   - `format_melt_entry(evaluated) -> str`
   - `format_pros_entry(evaluated) -> str`
   - `construct_ebay_listing_url(item_id) -> str`
   - `construct_ebay_sales_url(title) -> str`
   - `construct_coinbook_url() -> str` (placeholder)
   - `extract_earliest_time(hits) -> str`
   - `format_header_section() -> str`
   - `format_footer() -> str`

2. Rewrite `build_email_body_simple()`:
   - Sort entries by end time
   - Number entries sequentially
   - Apply correct format (melt vs PROS)
   - Assemble complete email body

3. Update `send_email()`:
   - Use new subject line format
   - Include new body format

### Phase 2: Console Polish
1. Verify counts line format matches Clarification #1
2. Verify table column order and alignment
3. Remove any debug output (unless DEBUG_DIAGNOSTICS flag set)
4. Verify time format consistency

### Phase 3: Testing Checklist
- Email with 1 HIT (melt entry format)
- Email with multiple HITs (sorting, numbering)
- Email with PROS placeholder (format verification)
- Console output (counts line, table format)
- Link construction (eBay listing, eBay sales)

---

## TESTING SCENARIOS

### Test 1: Single Melt HIT
**Input:** 1 listing passes melt HIT gate  
**Expected Output:**
- Email subject: `[time] Offline eBay Silver HITS (1 new)`
- Email body: Header + 1 melt entry + footer
- Entry #1 with all melt fields populated
- Links: eBay listing + eBay sales

### Test 2: Multiple HITs with Sorting
**Input:** 3 listings pass melt HIT gate with different end times  
**Expected Output:**
- Email subject: `[earliest_time] Offline eBay Silver HITS (3 new)`
- Email body: Header + 3 entries (sorted earliest first) + footer
- Entry numbering: #1, #2, #3
- Earliest end time appears first

### Test 3: PROS Placeholder Format
**Input:** 1 listing with `is_prospect = True` (manually set for testing)  
**Expected Output:**
- PROS entry format used (not melt format)
- Numismatic fields show placeholders (`"--"` or `"N/A"`)
- CoinBook link shows placeholder
- All melt fields (B/C/D/T) still populated

### Test 4: Console Output Verification
**Input:** Run with mixed results (some HITs, some MISS)  
**Expected Output:**
- Counts line: `Found: X | Eligible: Y | HITs: Z | New: W`
- Table columns in correct order
- Target column = "Silver"
- Time formats consistent

---

## DELIVERABLES

1. **`email_builder.py`** (rewritten)
   - Complete Section 2 implementation
   - All helper functions documented
   - Link construction logic
   - Sorting and numbering logic

2. **`silver_monitor.py`** (console polish)
   - Verified counts line format
   - Verified table format
   - No debug output (unless flag set)

3. **Testing Notes**
   - Which test scenarios were run
   - Any edge cases discovered
   - Any format deviations from Contract (should be zero)

---

## HANDOFF PACKAGE

### Files for Chat C (Build Studio)
- `/mnt/project/Sprint_07_Plan.md` (this file)
- `/mnt/project/Contract_Packet_v1_3_1.md` (specification authority)
- `/mnt/project/_system_responsibility_map_v_1_4.md` (component boundaries)
- `/mnt/user-data/uploads/email_builder.py` (current version)
- `/mnt/user-data/uploads/silver_monitor.py` (current version)
- `/mnt/user-data/uploads/classifier.py` (reference only)
- `/mnt/user-data/uploads/silver_math.py` (reference only)
- `/mnt/user-data/uploads/config.py` (reference only)

### Expected Deliverables
- `email_builder.py` (modified)
- `silver_monitor.py` (modified if needed)
- Implementation notes (brief summary of changes)

---

## CHAT C MESSAGE (Build Studio)

```
SPRINT 07 HANDOFF — EMAIL & CONSOLE UX FINALIZATION

INPUT FILES:
- Sprint_07_Plan.md (this plan)
- Contract_Packet_v1_3_1.md (Sections 1, 2, 4)
- email_builder.py (primary modification)
- silver_monitor.py (console polish)
- classifier.py, silver_math.py, config.py (reference only)

TASK:
Implement production-ready email and console formatting per Contract v1.3.1.

SCOPE:
- Complete Section 2 email format (melt entries + PROS placeholders)
- Subject line with earliest time + new count
- Entry sorting (earliest first) + sequential numbering
- Link construction (eBay listing, eBay sales, CoinBook placeholder)
- Console counts line verification (Clarification #1)
- Console table format verification (Section 1)

OUT OF SCOPE:
- Classification logic (stable)
- Filter gates (stable)
- PROS classification (Sprint 08)
- Diagnostic output (Sprint 06)

DELIVERABLES:
- email_builder.py (modified)
- silver_monitor.py (modified if needed)

Begin implementation. No explanations needed.
```

---

## CHAT D MESSAGE (Verifier)

```
VERIFICATION — SPRINT 07

INPUT FILES:
- Sprint_07_Plan.md (acceptance criteria)
- Contract_Packet_v1_3_1.md (Sections 1, 2, 4)
- email_builder.py (modified by Chat C)
- silver_monitor.py (modified by Chat C)

VERIFICATION CRITERIA:
1. Email subject matches Section 2 format exactly
2. Email header matches Section 2 format exactly
3. Melt entry format matches Section 2 exactly (all fields)
4. PROS entry format with placeholders matches Section 2
5. Entry sorting correct (earliest time first)
6. Entry numbering sequential (#1, #2, ...)
7. Links constructed per Section 4
8. Email footer matches Section 2
9. Console counts line matches Clarification #1
10. Console table matches Section 1
11. No logic changes (HIT/MISS classification unchanged)
12. No scope creep (PROS classification still False)

PASS CONDITIONS:
- All 12 criteria met
- Email format matches Contract exactly
- Console format matches Contract exactly
- No regression in classification logic

FAIL CONDITIONS:
- Any format deviation from Contract
- Classification logic changed
- PROS classification implemented (out of scope)
- Missing required fields

Output: PASS or FAIL with specific criteria violations.
```

---

**END OF SPRINT 07 PLAN**
