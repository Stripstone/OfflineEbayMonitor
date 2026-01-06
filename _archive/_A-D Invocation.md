# Four-Chat Invocation Prompts (Operator Guide)

> Purpose:  
> This file is an **operator ceremony guide**.  
> It tells *me* how to invoke each chat correctly.  
>  
> Authority hierarchy:
> 1. Contract Packet (Chat A output) — highest
> 2. `_A-D chat Do’s and Don’ts.md` — behavioral law
> 3. This file — invocation & reminders only

This file does **not** define roles, rules, or contracts.  
It exists to prevent misuse.

---

## CHAT A — CONTRACT VAULT (READ-ONLY)

### Invoke when:
- Establishing or revising a **Contract Packet**
- Freezing UX, math, link rules, or non-negotiables
- Versioning truth (v1.0 → v1.1)

### How to invoke:
- Provide **exact requirements**
- Request a **single immutable Contract Packet**
- Specify version number

### Hard reminders (for me):
- No code
- No planning
- No debugging
- No interpretation
- No edits after approval (new version only)

If I want opinions, planning, or fixes — **this is the wrong chat**.

---

## CHAT B — SPRINT PLANNER

### Invoke when:
- Translating ONE concern into ONE sprint plan
- Deciding scope, files allowed to change, acceptance checks

### How to invoke:
- Provide Contract Packet version
- Provide current concern
- Provide constraints (timebox, market, limits)

### Hard reminders (for me):
- Planning only
- One sprint only
- No code
- No artifacts
- No refactors for cleanliness
- No future sprint thinking

If output contains code or final files — **it failed**.

---

## CHAT C — IMPLEMENTER

### Invoke when:
- A sprint plan is approved
- I want **code changes only**

### How to invoke:
- Provide Sprint Plan
- Provide current project files
- State expectation: snippet OR full file(s)

### Hard reminders (for me):
- Code only
- One artifact only
- Preserve UX + math verbatim
- No explanations
- No justifications
- No redesign
- No self-validation

Output must end with:
- `Handoff: small snippet` **or**
- `Handoff: full file(s)`

Anything else is a failure.

---

## CHAT D — VERIFIER

### Invoke when:
- Code has been produced
- I need a **hard gate**

### How to invoke:
- Provide code output
- Provide Contract Packet
- Provide Sprint acceptance checks
- Provide console/email output if available

### Hard reminders (for me):
- PASS / FAIL only
- Bullet list only
- No fixes
- No suggestions
- No trust in prior context
- Must identify fix size (snippet vs full file)

If Chat D explains or improves — **it failed**.

---

## Operator Rule (Final)

- **Contracts are law**
- **Files carry state**
- **Chats do not**
- **Wrong chat = restart**
