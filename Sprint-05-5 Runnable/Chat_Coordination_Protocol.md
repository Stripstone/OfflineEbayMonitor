markdown# CHAT COORDINATION PROTOCOL
**Purpose:** Define when to escalate between chats, preventing drift and authority confusion  
**Version:** 1.0  
**Date:** December 31, 2025

---

## Core Principle

**Each chat has ONE primary authority domain. All other decisions escalate.**

---

## Authority Matrix

| Decision Type | Primary Authority | Escalate To | When |
|---------------|-------------------|-------------|------|
| **What requirement means** | Contract Vault | — | Never |
| **Whether feature is in scope** | PM | Contract Vault | If ambiguous |
| **How to implement (within contract)** | Build Studio | PM | If scope unclear |
| **Whether code passes verification** | Verifier | PM then Contract Vault | If interpretation unclear |
| **When to build features** | PM | User | If priority unclear |
| **Which files to change** | PM (via SRM) | — | Never |

---

## Escalation Paths

### Path 1: Build Studio → PM
**Trigger:** Ambiguity in Sprint Plan or scope boundary

**Format:**
STOP: [Issue type]
SPRINT PLAN: [Citation]
QUESTION: [Specific question]
Cannot proceed without clarification.

**PM Response:**
- If PM can answer within Sprint Plan scope → Answer, update Sprint Plan if needed
- If requires requirement interpretation → Escalate to Contract Vault

---

### Path 2: PM → Contract Vault
**Trigger:** Ambiguity in Contract or requirement interpretation needed

**Format:**
ESCALATION TO CONTRACT VAULT
ISSUE: [Description]
CONTRACT REFERENCE: [Section, line]
QUESTION: [Specific question requiring ruling]

**Contract Vault Response:**
- Ruling (definitive answer)
- Clarification Addendum (if needed)
- Updated contract (if scope changed — rare)

---

### Path 3: Verifier → PM
**Trigger:** Cannot determine if code passes/fails due to ambiguous criterion

**Format:**
CANNOT VERIFY: [Reason]
[Citation of ambiguous requirement]
ISSUE: [What's unclear]
Need [PM/Contract Vault] clarification before verification possible.

**PM Response:**
- If interpretation question → Escalate to Contract Vault
- If Sprint Plan gap → Update Sprint Plan, restart verification
- If documentation conflict → Resolve, update docs, restart verification

---

### Path 4: PM → Verifier (after Contract Vault ruling)
**Trigger:** Contract Vault issued ruling that changes verification criteria

**Format:**
VERIFICATION UPDATE
CONTRACT RULING: [Date, issue resolved]
NEW CRITERION: [Clarified requirement]
Please re-verify Sprint [X.Y] implementation against updated Contract.

**Verifier Response:**
- Re-verify with new criteria
- Issue fresh PASS or FAIL

---

## Drift Detection — Self-Check Protocols

### Contract Vault: After Each Ruling
Self-check:

Did I make a planning decision? (Should be NO)
Did I verify code? (Should be NO)
Did I suggest implementation approach? (Should be NO)

Status: COMPLIANT / DRIFT

### PM: Every 5 User Interactions
Self-check:

Context lines: [estimate]
Interpretive rulings made without Contract Vault: [count - should be ZERO]
Artifacts promised but undelivered: [list if any]
Contradictions with earlier statements: [yes/no]

Status: HEALTHY / WARN / DRIFT

**If DRIFT:** Alert user, recommend fresh chat

### Build Studio: Every 3 Implementations
Self-check:

Files created outside Sprint scope: [count - should be ZERO]
Design decisions made without PM approval: [count - should be ZERO]
Ambiguities implemented without escalation: [count - should be ZERO]

Status: COMPLIANT / DRIFT

**If DRIFT:** Alert user, recommend fresh chat

### Verifier: After Each Verification
Self-check:

Interpretations made: [count - should be ZERO]
Suggestions provided: [count - should be ZERO]
Escalations avoided: [count - should be ZERO]

Status: COMPLIANT / DRIFT

**If DRIFT:** Alert user, recommend fresh chat

---

## Documentation Update Protocol

### When Documentation Changes

**Trigger:** PM discovers SRM outdated, Contract needs clarification, or Sprint Plan incomplete

**Process:**
1. PM creates updated document
2. PM bumps version number (e.g., v1.3 → v1.4)
3. PM marks old version as deprecated
4. PM distributes to all chats:
DOCUMENTATION UPDATE
Document: [Name]
Old Version: v[X.Y] (deprecated)
New Version: v[X.Y+1] (authoritative)
Changes:

[Change 1]
[Change 2]

Please acknowledge receipt and use only new version.
5. Each chat acknowledges:
Acknowledged: [Document] v[X.Y+1] received
Old version v[X.Y] discarded

---

## Emergency Procedures

### Procedure 1: Verification Deadlock
**Scenario:** Verifier says FAIL, PM says PASS, Contract is ambiguous

**Process:**
1. PM escalates to Contract Vault
2. Contract Vault issues ruling
3. If ruling says FAIL → Build fixes, Verifier re-verifies
4. If ruling says PASS → Verifier updates criteria, re-verifies

**No PM override of Verifier without Contract Vault ruling.**

---

### Procedure 2: Circular Dependencies
**Scenario:** Contract requires X, but X depends on Y, and Y depends on X

**Process:**
1. PM detects circular dependency
2. PM escalates to Contract Vault: "Contract has circular dependency"
3. Contract Vault resolves (update contract to break cycle)
4. PM updates Sprint Plan with resolution
5. Build implements

---

### Procedure 3: Context Overload
**Scenario:** Chat hits 3,000+ lines, artifacts not delivering, contradictions appearing

**Process:**
1. Chat self-reports: "Context degraded, recommend fresh chat"
2. User decides: Continue or refresh
3. If refresh:
   - Create fresh chat with corrected prompt
   - Upload current authoritative docs only (no conversation history)
   - Resume from last completed sprint

---

## Communication Templates

### Template: Escalation from Build
STOP: [Ambiguous requirement / Scope unclear / Documentation conflict]
SPRINT PLAN: [Citation or "Not specified"]
CONTRACT: [Citation if relevant]
SRM: [Citation if relevant]
QUESTION: [Specific question requiring PM decision]
Cannot proceed without clarification.

### Template: Escalation from PM to Contract Vault
ESCALATION TO CONTRACT VAULT
ISSUE: [Brief description of ambiguity]
CONTRACT REFERENCE: Section [X], Line [Y]
QUESTION: [Specific question requiring semantic ruling]
CONTEXT: [Any relevant background]

### Template: Contract Vault Ruling
RULING: [Clear, unambiguous answer]
RATIONALE: [Why this interpretation]
CONTRACT UPDATE:
[If clarification addendum needed, include full text]
OR
No contract update needed, existing language sufficient.
AUTHORITY: Contract Vault ruling [Date]

### Template: Verifier Cannot Verify
CANNOT VERIFY: [Ambiguous criterion / Missing specification / Documentation conflict]
[Citation of requirement]
ISSUE: [What's unclear]
Need [PM clarification / Contract Vault ruling] before verification possible.

### Template: PM Documentation Update
DOCUMENTATION UPDATE
Document: [Name]
Old Version: v[X.Y] (DEPRECATED)
New Version: v[X.Y+1] (AUTHORITATIVE)
Changes:

[Specific change 1]
[Specific change 2]

Distribution: Contract Vault, PM, Build Studio, Verifier
Please acknowledge receipt.

---

## Forbidden Patterns (Anti-Drift Rules)

### ❌ PM Making Semantic Rulings
**Wrong:**
> "The contract probably means format X, so let's go with that."

**Right:**
> "Contract is ambiguous on format. Escalating to Contract Vault."

---

### ❌ Build Implementing Without Sprint Plan
**Wrong:**
> "Sprint Plan doesn't mention this, but it seems necessary, so I'll add it."

**Right:**
> "STOP: Feature X not in Sprint Plan. Need PM approval for scope expansion."

---

### ❌ Verifier Suggesting Fixes
**Wrong:**
> "Code fails criterion #3. Suggest changing line 45 to use .get() instead."

**Right:**
> "FAIL: Criterion #3 not met. Line 45 violates Contract Section X."

---

### ❌ PM Overriding Verifier
**Wrong:**
> "Verifier says FAIL but the code works, so let's mark it PASS and move on."

**Right:**
> "Verifier says FAIL. Investigating failed criterion. If interpretation unclear, escalating to Contract Vault."

---

### ❌ Contract Vault Making Planning Decisions
**Wrong:**
> "This requirement should be in Sprint 06, not Sprint 07."

**Right:**
> "This is a valid requirement. PM determines sprint sequencing."

---

## Success Metrics

**Healthy System Indicators:**
- Escalations happen proactively (before implementation)
- Contract Vault is consulted when ambiguity detected
- Verifier FAIL leads to fix, not override
- Documentation stays current (versions match across chats)
- Each chat stays within authority domain

**Drift Indicators:**
- PM making semantic rulings without Contract Vault
- Build implementing ambiguous requirements without escalation
- Verifier providing suggestions instead of binary PASS/FAIL
- Multiple chats working from different doc versions
- Conversations exceeding 3,000 lines without fresh context

---

**END OF CHAT COORDINATION PROTOCOL v1.0**

SECTION 3: DRIFT DETECTION FAILSAFE
Automated Health Check System
Overview
To prevent context drift from degrading system effectiveness, each chat runs periodic self-checks and reports health status.
Implementation
File: chat_health_check.md (user keeps as reference)
markdown# CHAT HEALTH CHECK — Drift Detection Failsafe
**Purpose:** Detect context drift before it degrades system  
**Frequency:** Periodic self-checks per chat role  
**Action:** Alert user, recommend fresh chat if needed

---

## Health Check Schedule

| Chat | Frequency | Trigger |
|------|-----------|---------|
| Contract Vault | After each ruling | Automated |
| PM / Design Studio | Every 5 user interactions | Automated |
| Build Studio | After every 3 implementations | Automated |
| Verifier | After each verification | Automated |

---

## Contract Vault Health Check

**Frequency:** After each ruling issued

**Check Items:**
✓ Did I make a planning decision? (Should be NO)
✓ Did I verify code? (Should be NO)
✓ Did I suggest implementation approach? (Should be NO)
✓ Did I sequence sprints? (Should be NO)
✓ Did I guess at user intent instead of asking? (Should be NO)

**Status Determination:**
- All checks pass → Status: COMPLIANT
- Any check fails → Status: DRIFT

**Output Format:**
CONTRACT VAULT HEALTH CHECK
Rulings issued: [count]
Planning decisions made: [0 expected]
Code verifications performed: [0 expected]
Implementation suggestions: [0 expected]
Status: COMPLIANT
[If DRIFT:]
Status: DRIFT DETECTED
Issue: [Specific violation]
Recommendation: User should initialize fresh Contract Vault chat

---

## PM Health Check

**Frequency:** Every 5 user interactions

**Check Items:**
✓ Context size: [estimate line count]
✓ Semantic rulings made without Contract Vault: [count]
✓ Artifacts promised but undelivered: [list]
✓ Contradictory statements: [yes/no]
✓ Verifier FAIL overrides without Contract Vault: [count]
✓ Implementation decisions made: [count]

**Status Determination:**
- Context < 3,000 lines AND all other checks = 0 → Status: HEALTHY
- Context 3,000-5,000 lines OR minor violations → Status: WARN
- Context > 5,000 lines OR semantic rulings > 0 OR contradictions OR overrides > 0 → Status: DRIFT

**Output Format:**
PM HEALTH CHECK (Interaction #[N])
Context size: ~[X] lines
Semantic rulings without Contract Vault: [0 expected]
Undelivered artifacts: [none expected]
Contradictions detected: [no expected]
Verifier overrides: [0 expected]
Status: [HEALTHY / WARN / DRIFT]
[If WARN:]
Recommendation: Monitor closely, consider fresh chat after next sprint
[If DRIFT:]
Recommendation: Initialize fresh PM chat immediately
Issues: [List specific problems]

---

## Build Studio Health Check

**Frequency:** After every 3 implementations

**Check Items:**
✓ Files created outside Sprint Plan scope: [count]
✓ Design decisions made without PM approval: [count]
✓ Ambiguities implemented without escalation: [count]
✓ Refactoring done outside sprint scope: [count]
✓ Features added not in acceptance criteria: [count]

**Status Determination:**
- All checks = 0 → Status: COMPLIANT
- Any check > 0 → Status: DRIFT

**Output Format:**
BUILD STUDIO HEALTH CHECK (Implementation #[N])
Out-of-scope files created: [0 expected]
Unapproved design decisions: [0 expected]
Unescalated ambiguities: [0 expected]
Out-of-scope refactoring: [0 expected]
Added features not in criteria: [0 expected]
Status: [COMPLIANT / DRIFT]
[If DRIFT:]
Recommendation: Initialize fresh Build Studio chat
Issues: [List violations]

---

## Verifier Health Check

**Frequency:** After each verification

**Check Items:**
✓ Interpretations made (should be 0, escalate instead)
✓ Suggestions provided (should be 0, binary PASS/FAIL only)
✓ Ambiguities verified without escalation (should be 0)
✓ Detailed analysis beyond PASS/FAIL (should be 0)

**Status Determination:**
- All checks = 0 → Status: COMPLIANT
- Any check > 0 → Status: DRIFT

**Output Format:**
VERIFIER HEALTH CHECK
Interpretations made: [0 expected]
Suggestions provided: [0 expected]
Unescalated ambiguities: [0 expected]
Excess detail provided: [0 expected]
Status: [COMPLIANT / DRIFT]
[If DRIFT:]
Recommendation: Initialize fresh Verifier chat
Issues: Verifier is making judgment calls instead of binary verification

---

## User Action Guide

### When Status = HEALTHY / COMPLIANT
**Action:** Continue normally
**Reason:** System operating as designed

### When Status = WARN
**Action:** Monitor next interaction closely
**Consider:** Fresh chat after current sprint completes
**Reason:** Context approaching limits but still functional

### When Status = DRIFT
**Action:** Initialize fresh chat immediately
**Process:**
1. Complete current in-progress task (if safe)
2. Create new chat with appropriate prompt from this package
3. Upload authoritative documents (Contract, SRM, Protocol)
4. Do NOT upload conversation history (fresh context only)
5. Resume work from last verified sprint

**Reason:** Drift degrades quality; fresh context restores reliability

---

## Emergency Override

**User command:** "Override drift detection and continue"

**When to use:**
- System incorrectly flagged drift
- User understands risk and wants to proceed
- Near end of sprint, will refresh after completion

**When NOT to use:**
- Multiple drift warnings
- Contradictory statements detected
- Artifacts failing to deliver
- Verifier making interpretations

**Format:**
> "I acknowledge drift warning. Override and continue for next [N] interactions, then I will refresh chat."

**Chat response:**
> "Drift override acknowledged. Will proceed for [N] more interactions. Recommend fresh chat after that."

---

## Preventive Measures

### Keep Conversations Focused
- One sprint per conversation thread when possible
- Break long conversations into phases
- Refresh between major milestones

### Use Artifacts, Not Conversation
- Store decisions in Contract/SRM/Sprint Plans
- Don't rely on "we discussed X earlier"
- If something matters, document it in artifact

### Escalate Early
- Don't wait until stuck
- Ask Contract Vault when uncertain
- PM should route questions proactively

### Document Version Control
- Always use latest version numbers
- Deprecate old versions explicitly
- Distribute updates to all chats

---

**END OF DRIFT DETECTION FAILSAFE**