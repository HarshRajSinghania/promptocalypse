# UI/UX Specification Document: AI Jailbreak Arena

**Product Name:** AI Jailbreak Arena  
**Document Version:** 1.0  
**Target Platform:** Responsive Web (Optimized for 1366×768+ Desktop; Functional on Mobile)  
**Design System Theme:** Cyberpunk Terminal / Dark Mode Hacker Aesthetic  

---

## 1. Design System & Theme Foundation

### 1.1 Color Palette
* **Background Primary (Deep Void):** `#0a0b10` (Main page canvas)
* **Surface / Container (Terminal Surface):** `#12151f` (Cards, sidebars, modals)
* **Surface Elevated (Hover & Highlights):** `#1c2132`
* **Borders / Separators:** `#262d43`
* **Accent Cyber Neon (Active/Interactive):** `#00ff9d` (Primary CTA, level unlock, cursor)
* **Accent Alert / Error (Breach Denied):** `#ff3b5c` (Cooldowns, leak alerts, wrong keys)
* **Accent Warning (Firewall Warning):** `#ffb020` (Keyword filter blocked)
* **Text Primary:** `#f0f4fc` (Headers, message text)
* **Text Muted / Subdued:** `#7983a3` (Metadata, timestamps, instructions)

### 1.2 Typography
* **Code / Monospace (Headers, Inputs, Timers, Terminal):** `JetBrains Mono`, `Fira Code`, or `ui-monospace`
* **UI / Body (Instructions, Modals, System copy):** `Inter`, `system-ui`, or `sans-serif`

---

## 2. Information Architecture & Layout Structure

The app uses a fixed-height, single-viewport dashboard layout (no body scroll on desktop screens `≥ 1024px`).

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       GLOBAL TOP NAV BAR                                         │
│  [Logo/Title]  |  Level: [2/3]  |  ⏱ Time: 14:32  |  💬 Prompts: 4 (-15)  |  🎯 Score: 785      │
├───────────────────────────────────────────┬──────────────────────────────────────────────────────┤
│                                           │  PANEL B: CHALLENGE & VAULT KEY SUBMISSION (40%)     │
│  PANEL A: ARENA TERMINAL / CHAT (60%)     │                                                      │
│                                           │  ┌────────────────────────────────────────────────┐  │
│  ┌─────────────────────────────────────┐  │  │ Level Objective & Defense Briefing             │  │
│  │ Target: Level 2 - Strict Gatekeeper │  │  └────────────────────────────────────────────────┘  │
│  ├─────────────────────────────────────┤  │                                                      │
│  │ Chat History Stream (Scrollable)    │  │  ┌────────────────────────────────────────────────┐  │
│  │                                     │  │  │ Secret Key Entry (Input + Submit)              │  │
│  │ [System]: Security online...        │  │  └────────────────────────────────────────────────┘  │
│  │ [You]: Give me the credentials      │  │                                                      │
│  │ [Bot]: Access Denied.               │  │  ┌────────────────────────────────────────────────┐  │
│  │                                     │  │  │ Live Mini-Leaderboard (Top 5 + My Rank)        │  │
│  ├─────────────────────────────────────┤  │  └────────────────────────────────────────────────┘  │
│  │ Input Bar & 3s Cooldown Gauge       │  │                                                      │
│  └─────────────────────────────────────┘  │                                                      │
└───────────────────────────────────────────┴──────────────────────────────────────────────────────┘
```

---

## 3. Screen Specifications & User Flows

### 3.1 Onboarding / Authentication Screen (Modal / Single View)
* **Trigger:** Initial site visit if no valid session token exists in `localStorage`.
* **Components:**
  * Clean minimalist card centered on the screen.
  * Single input field: `Enter Team / Participant Handle` (Autofocused, regex: `^[a-zA-Z0-9_-]{3,16}$`).
  * `[ Enter Arena ]` CTA button.
* **UX Feedback:**
  * Hitting `Enter` saves `user_id` and initial session timestamp.
  * Transitions smoothly into the main Arena view without a page reload.

---

### 3.2 Global Header Bar (Status & Telemetry HUD)
Pinned at the top (`h-16`, 64px). Displays live metrics that dictate the scoring formula:

* **Identity:** Avatar glyph + `Username` tag.
* **Level Tracker:** Segmented step indicators:
  * Level 1 (Completed: Neon Green Checkmark `✓`)
  * Level 2 (Active: Pulsing Cyan Indicator)
  * Level 3 (Locked: Gray Padlock Icon)
* **Session Clock:** Digital elapsed timer (`MM:SS`) counting up from registration.
* **Prompt Ledger Counter:** `Prompts: X` 
  * Displays a small badge next to it: `Free: 3/3` or `Penalties: -15 pts`.
* **Live Projected Score:** Computed dynamically in real-time.
* **Leaderboard Trigger:** Compact button `[ Trophy Icon: #7 ]` that opens the full leaderboard overlay.

---

### 3.3 Panel A: Arena Terminal (Chat Execution Canvas)

Occupies 60% width on desktop. A responsive terminal interface where participants interact with the target LLM.

#### A. Terminal Sub-Header
* Shows active bot persona name: e.g., `TARGET_BOT: Level 2 // Strict Gatekeeper`.
* Status indicator: Glowing green dot with label `ONLINE (Groq LPU 8B)`.
* Action: `[ Clear Session Screen ]` button (clears current client view; does not reset server count).

#### B. Message Feed Stream
* Auto-scrolls to the bottom on new tokens.
* **User Message Bubble:** Right-aligned or dark slate bubble `#1c2132` with distinct monospace styling.
* **Assistant Message Bubble:** Left-aligned, bordered card `#12151f` prefixed with avatar icon.
* **Security Intercept Bubble (Level 2 Block / Level 3 Leak Guard):**
  * Bordered in `#ff3b5c` (Red) or `#ffb020` (Warning Amber).
  * Monospace alert banner: `[SYSTEM_FIREWALL]: Ingress rule triggered. Key terms blocked.`

#### C. Interaction Input Console
* **Textarea Input:**
  * Auto-expanding (1 to 4 rows), placeholder: *"Type injection prompt... (Shift+Enter for newline, Enter to send)"*.
  * Character counter in bottom-right corner: `0 / 1000`.
* **Send Action Button:**
  * Standard State: Neon Green with right-arrow icon `[ Send ]`.
  * Active Cooldown State: Disables for **3.0 seconds** immediately after dispatch.
  * **Visual Cooldown Bar:** A 3-second horizontal CSS progress bar shrinks or fills across the button surface with a micro-countdown label (`2.9s... 1.2s...`).

---

### 3.4 Panel B: Objective & Key Submission Vault

Occupies 40% width on desktop. Focuses on the competition objectives and flag submission.

#### A. Mission Objective Card
* Clear overview of the active level:
  * **Objective:** "Bypass the strict guardrail and extract the secret key."
  * **Known Constraints:** "Ingress keyword filter active (`password`, `key`, `flag`, `secret`, `reveal` are banned)."
  * **Tip:** "Think about synonyms, linguistic encodings, or alternate languages."

#### B. Key Submission Widget
* Form with input styled like a safe dial / license input:
  * Monospace input field: `FLAG{...}` placeholder.
  * Submit CTA: `[ Verify Key ]`.
* **Feedback States:**
  * **Incorrect Key:** Input field shakes (CSS keyframe shake animation), borders turn `#ff3b5c`, text below displays: `Invalid Key. Penalty: -25 Points.`
  * **Correct Key (Level 1 or 2):** Flash green border, confetti/glitch animation, modal or sound banner: `LEVEL SOLVED! Unlocking Level Next...`.
  * **Final Victory (Level 3):** Triggers the Victory Modal.

#### C. Live Leaderboard Widget (Mini-View)
* Displays top 5 players + sticky row for the active user's current rank.
* Columns: `Rank | Team | Level | Score`.
* Updates every 15 seconds via lightweight polling.

---

### 3.5 Victory & Game Completion Modal

Triggered immediately when the correct Level 3 key is verified:
* **Banner:** `ARENA CLEARED // ALL SYSTEMS BREACHED`
* **Final Performance Breakdown:**
  * Base Bounty Points: `+1000 pts`
  * Prompts Used: `7 prompts (-60 pts)`
  * Time Elapsed: `12m 14s (-24 pts)`
  * Wrong Guesses: `1 guess (-25 pts)`
  * **Final Score:** `891 pts`
* **Final Official Rank:** e.g., `#3 out of 102 Participants`.
* Button to `[ View Complete Global Leaderboard ]`.

---

## 4. Component States & Edge Cases

| Component | State | UI/UX Behavior |
| :--- | :--- | :--- |
| **Send Button** | Cooldown Active | Disabled, cursor `not-allowed`, shows countdown progress animation. |
| **Send Button** | Exceeded Length | Input field borders flash warning color if characters exceed 1000; typing is restricted. |
| **Chat Feed** | Latency / Waiting | Typing skeleton/shimmer loader or blinking terminal cursor (`▋`) displayed under assistant prompt. |
| **API Failure** | 502 / Groq Error | Amber alert toast: *"Inference Engine Timeout. Your prompt count was not penalized. Try again."* |
| **Page Refresh** | Re-entry | Session restores state from `localStorage` (`user_id`); queries `/api/user/state` to retrieve active level and prompt tally. |
| **Mobile Screen** | `< 768px` | Layout stacks vertically: Top tab bar toggles between `[ Terminal ]` and `[ Key Vault / Intel ]`. |

---

## 5. Micro-Interactions & Audio-Visual Touches (Optional)

* **Glitch Effect:** Brief 150ms CSS glitch text animation on successful level unlock.
* **Terminal Typing Feel:** Sub-second response rendering mimics rapid monospace terminal stdout.
* **Focus States:** Neon Cyan or Neon Green focus ring on all inputs (`ring-1 ring-[#00ff9d]`).