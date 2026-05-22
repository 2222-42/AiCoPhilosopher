# Contract: REPL Rendering — Progressive Disclosure Format

**Date**: 2026-05-18
**Feature**: 002-console-agent
**Interface**: Console REPL Response Renderer

---

## 1. Overview

All coordinator responses in the REPL follow a progressive disclosure format per FR-007. The response is divided into five sections, with the first three always visible and the last two togglable via `/details` and `/suggestions` commands.

**Design principle**: Give the user the essential information immediately. Let them drill deeper on demand. Never bury critical information in collapsed sections.

---

## 2. Section Definitions

### 2.1 Summary (ALWAYS VISIBLE)

- **Anchor**: `**Summary**`
- **Purpose**: Concise answer to user's query or state update
- **Max length**: ≤5 lines (SC-007)
- **Content**: Plain text or simple inline formatting (bold, italic)
- **Never contains**: Technical details, workstream IDs, data dumps

### 2.2 Epistemic Status (ALWAYS VISIBLE)

- **Anchor**: `**Epistemic Status**`
- **Purpose**: Confidence, counter-argument strength, tradition context
- **Content**: Key-value pairs: `Confidence: 0.85 | Tradition: Philosophy of Technology | Review: Under Review`
- **Optional fields**: `Counter-Argument Strength`, `Open Questions`, `Methodology Note`

### 2.3 Active Workstreams (ALWAYS VISIBLE)

- **Anchor**: `**Active Workstreams**`
- **Purpose**: Real-time workstream status overview
- **Content**: One line per workstream: `WS-XXX: <type> — <status> [(<progress>)]`
- **Progress indicators**: `running (60%)`, `completed (23 papers)`, `paused`, `failed (reason)`
- **Hidden when**: No workstreams exist in the project

### 2.4 [Details] (COLLAPSED BY DEFAULT)

- **Anchor**: `[Details]`
- **Purpose**: Full response content — argument maps, citation lists, methodology notes
- **Toggle**: `/details` (show), `/hide-details` (hide). State persisted in FocusContext.
- **Content**: Free-form, can be multi-paragraph. May include nested sections.
- **Typical contents**:
  - Hypothesis lists with confidence scores
  - Argument summaries
  - Recent claims
  - Review round status
  - Inline Markdown with annotation links

### 2.5 [Suggestions] (COLLAPSED BY DEFAULT)

- **Anchor**: `[Suggestions]`
- **Purpose**: Proactive next-step suggestions from the coordinator
- **Toggle**: `/suggestions` (show), `/hide-suggestions` (hide). State persisted in FocusContext.
- **Max items**: 3-5 suggestions
- **Content**: One suggestion per line, actionable and specific
- **Never contains**: Generic advice ("think about it more"), passive language

---

## 3. Full Response Template

```
┌─ Summary ────────────────────────────────────────────────────────────┐
│ [Concise 1-5 line summary of the coordinator's response]             │
└───────────────────────────────────────────────────────────────────────┘

┌─ Epistemic Status ───────────────────────────────────────────────────┐
│ Confidence: 0.XX | Tradition: <name> | Review: <status>              │
│ [Optional: Counter-Argument Strength, Open Questions, Note]          │
└───────────────────────────────────────────────────────────────────────┘

┌─ Active Workstreams ─────────────────────────────────────────────────┐
│ WS-001: Literature Search — completed (23 papers)                     │
│ WS-002: Concept Analysis — running (60%)                              │
│ WS-003: Cross-Traditional Comparison — running (30%)                  │
└───────────────────────────────────────────────────────────────────────┘

[Details]                        ← Label shown when collapsed
┌─ [Details] ──────────────────────────────────────────────────────────┐
│ [Full response content — hypotheses, arguments, citations, etc.]      │
│                                                                       │
│ Hypotheses:                                                           │
│   H1: Software abstractions have ontological status... (Conf: 0.72)  │
│   H2: Abstraction is purely instrumental... (Conf: 0.45, Refuted)    │
│                                                                       │
│ Recent Claims:                                                        │
│   C1: "Mathematical abstraction differs from software abstraction     │
│        in normative commitments" (Conf: 0.85, Under Review)           │
│                                                                       │
│ Review Round 1/5:                                                     │
│   Reviewer A (Analytic): Approved with reservations                   │
│   Reviewer B (Phenomenological): Requested revisions                  │
└───────────────────────────────────────────────────────────────────────┘

[Suggestions]                    ← Label shown when collapsed
┌─ [Suggestions] ──────────────────────────────────────────────────────┐
│ • WS-001 is complete. Start Argumentation workstream?                  │
│ • WS-002 will finish in ~2 minutes.                                    │
│ • Consider adding Pragmatist tradition to the comparison.              │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 4. Rendering Rules

### 4.1 Content Allocation

| Type of Information | Goes In | Rationale |
|--------------------|---------|-----------|
| Direct answer to user's question | Summary | Primary value; always visible |
| Confidence, tradition, review status | Epistemic Status | Constitution Principle II — intellectual honesty |
| Workstream progress | Active Workstreams | User needs real-time awareness |
| Hypothesis details, citations, argument maps | [Details] | Deep content; on-demand |
| Next-step suggestions | [Suggestions] | Non-essential; opt-in |
| Warnings, errors, escalations | Summary (prepended with ⚠️) | Critical info must never be collapsed |
| Approval requests | Summary (inline, highlighted) | Blocking requests must be immediately visible |

### 4.2 Formatting Rules

- **Summary**: Plain text, max 5 lines. Use bold for key terms only.
- **Epistemic Status**: Key-value pairs separated by ` | `. Always on one line.
- **Active Workstreams**: One line per workstream (ideally). Abbreviate descriptions when necessary to keep each workstream on a single line; at narrow terminal widths lines may wrap.
- **[Details]**: Full Markdown with headings, lists, code blocks. Rich renders as styled text.
- **[Suggestions]**: Bulleted list. Each suggestion is a complete sentence with clear action.

### 4.3 Toggle State Persistence

- Toggle state (`show_details`, `show_suggestions`) is stored in `FocusContext.toggle_state`
- Persisted across turns within a session
- Persisted across session resumptions (loaded from session state)
- Default on new session: both collapsed (`show_details=False`, `show_suggestions=False`)

### 4.4 System Messages (Non-Coordinator)

System-generated messages (workstream completion notifications, connection errors) use a distinct visual style:

```
[System] 17:42 — Workstream WS-001 (Literature Search) completed: 23 papers found.
[System] 17:45 — ⚠️ Workstream WS-003 (Cross-Traditional Comparison) failed: LLM backend timeout. Retry?
```

These appear inline between coordinator responses, not inside the progressive disclosure panels.

---

## 5. Edge Cases

### 5.1 Very Long Summary

If the coordinator's response would naturally exceed 5 summary lines:
- Truncate at line 5 with `[...]` indicator
- Full text available in [Details] section
- User can type `/details` to see complete response

### 5.2 Empty Sections

- **Active Workstreams**: If no workstreams exist, omit the section entirely
- **[Details]**: If no details to show, show placeholder: `No additional details available.`
- **[Suggestions]**: If no suggestions, show placeholder: `No suggestions at this time.`
- **Epistemic Status**: Always present (even if confidence is low — that IS the status)

### 5.3 Terminal Width Constraints

- Minimum supported width: 80 columns
- Below 80 columns: Panels stack vertically; Rich auto-wraps content
- Active Workstreams may wrap if workstream descriptions are long — use abbreviated forms at narrow widths

### 5.4 Approval Requests in Response

When a coordinator response includes a blocking approval request, it is surfaced IN the Summary section with a highlighted prompt:

```
┌─ Summary ────────────────────────────────────────────────────────────┐
│ I've completed the literature review and found three competing       │
│ frameworks for understanding software abstraction.                    │
│                                                                       │
│ ⚠️ DECISION REQUIRED: Which framework should we prioritize?           │
│   1. Mathematical structuralism (analytic tradition)                  │
│   2. Post-phenomenological mediation (philosophy of technology)       │
│   3. Pragmatic naturalism (pragmatist tradition)                      │
│                                                                       │
│ [Type 1, 2, or 3 to select, or explain your preference]              │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 6. Implementation Notes

### 6.1 Rich Components Used

- `rich.panel.Panel`: Each section rendered as a bordered panel
- `rich.markdown.Markdown`: [Details] content rendered with full Markdown support
- `rich.text.Text`: Plain text sections (Summary, Workstream status lines)
- `rich.style.Style`: Color coding for confidence (green ≥0.8, yellow ≥0.5, red <0.5)

### 6.2 Rendering Pipeline

```python
def render_response(response: CoordinatorResponse, focus: FocusContext) -> None:
    """Render coordinator response with progressive disclosure."""
    console = Console()

    # Always-visible sections
    _render_summary(console, response.summary)
    _render_epistemic_status(console, response.epistemic)
    if response.active_workstreams:
        _render_workstreams(console, response.active_workstreams)

    # Togglable sections (state stored in FocusContext.toggle_state)
    if focus.toggle_state.show_details:
        _render_details(console, response.details)
    else:
        console.print("[Details]")  # Collapsed indicator

    if focus.toggle_state.show_suggestions:
        _render_suggestions(console, response.suggestions)
    else:
        console.print("[Suggestions]")  # Collapsed indicator
```

### 6.3 Toggle Commands

- `/details` → Set `FocusContext.toggle_state.show_details = True`, re-render last response
- `/hide-details` → Set `FocusContext.toggle_state.show_details = False`
- `/suggestions` → Set `FocusContext.toggle_state.show_suggestions = True`, re-render last response
- `/hide-suggestions` → Set `FocusContext.toggle_state.show_suggestions = False`

Toggle state is applied to ALL subsequent responses until toggled again.

---

**Contract Version**: 1.0.0 | **Last Updated**: 2026-05-18
