# CoachGPT — AI-Powered English Speaking Practice Chatbot
串接ChatGPT的line chatbot，以遊戲化的設計和後設認知學習，提供大專學生全新的英語口說練習系統。透過RAG提升評分與回饋的標準一致性，能夠準確評估學生使用此系統的練習成效。本系統功能包含口說前後測、AI NPC情境式解謎遊戲、SEL之情感察覺與表達、與AI自由聊天、多組練習題。

> A LINE-based chatbot system designed for Taiwanese college students to practice English speaking through immersive scenario-based activities, AI-scored voice assessments, and Social-Emotional Learning modules.

---

## Table of Contents

- [Project Overview](#project-overview)
- [System Architecture](#system-architecture)
- [Core Features](#core-features)
- [Service 4 & 5 — Key Contributions](#service-4--5--key-contributions)
  - [Scenario Mystery Game](#1-scenario-mystery-game-情境解謎遊戲)
  - [SEL Board Game Modules](#2-sel-board-game-modules-社會情緒學習)
  - [New Test Format](#3-new-test-format-pretest1--posttest1)
  - [Fallback Guide Chatbot](#4-fallback-guide-chatbot)
  - [NPC Voice Output Mode (Service 5)](#5-npc-voice-output-mode-service-5)
  - [Advanced Progress Tracking](#6-advanced-progress-tracking)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Configuration Reference](#configuration-reference)
- [Rich Menu & Navigation](#rich-menu--navigation)
- [Admin Controls](#admin-controls)
- [Data Models](#data-models)

---

## Project Overview

CoachGPT is a multi-instance LINE Messaging API chatbot that enables college students to practice English speaking by sending **voice messages** directly in LINE. An AI pipeline transcribes speech, scores responses on a 1–10 rubric, and provides bilingual feedback (Traditional Chinese + English).

The system is designed to run as **five parallel service instances**, each configured for a different class section or feature set. Services 1–3 cover foundational exercises and tests; **Services 4 and 5 are the primary research contributions**, adding an immersive mystery game, SEL learning modules, NPC voice synthesis, and a smart guide chatbot.

```
LINE User ──► LINE Platform ──► Webhook (FastAPI)
                                     │
                    ┌────────────────┼─────────────────────┐
                    │                │                     │
              service1:8000    service4:8005         service5:8006
              (Class A)      (Game + SEL)          (Game + SEL + TTS)
```

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI App                             │
│  ┌──────────┐  ┌────────────┐  ┌──────────────┐               │
│  │  routes  │  │  handlers  │  │ message_utils│               │
│  └────┬─────┘  └─────┬──────┘  └──────┬───────┘               │
│       │               │                │                        │
│  ┌────▼───────────────▼────────────────▼───────────┐           │
│  │              file_utils / models                │           │
│  │  User data · Config · Game state · RAG cache    │           │
│  └─────────────────────────────────────────────────┘           │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │QuestionMgr  │  │RichMenuMgr   │  │   OpenAI Client      │  │
│  │(category/)  │  │(LINE SDK)    │  │  GPT-4o · Whisper    │  │
│  └─────────────┘  └──────────────┘  │  TTS · Embeddings    │  │
└─────────────────────────────────────┴──────────────────────────┘
                        │
              ┌─────────▼─────────┐
              │   Data (volumes)  │
              │  user_data{N}.json│
              │  config{N}.json   │
              └───────────────────┘
```

**Request flow for a voice message:**
1. User sends audio → LINE transcodes to M4A
2. FastAPI webhook receives the event
3. Audio is fetched and converted → OpenAI Whisper transcribes to text
4. GPT-4o scores the transcript against a rubric (1–10 scale)
5. Bilingual feedback is generated and returned as Flex Messages

---

## Core Features

| Feature | Description | Services |
|---|---|---|
| **Voice Assessment** | Transcribe, score, and provide bilingual feedback on spoken English responses | All |
| **Exercises (ex1–ex6)** | Vocabulary, picture description, opinion, scenario-based speaking tasks | All |
| **Pre/Post-Test** | Standardised assessments with controlled question sets | All |
| **Chat Practice** | Open-ended AI conversation with topic selection | All |
| **Rich Menu Navigation** | Tap-based UI panels in LINE for all interactions | All |
| **Admin Panel** | Toggle sections on/off, enable/disable feedback, reload questions | All |
| **Scenario Mystery Game** | Multi-level puzzle game with NPC dialogue and RAG-based clues | 4, 5 |
| **SEL Modules** | 6 board-game-themed Social-Emotional Learning units | 4, 5 |
| **NPC Voice Output** | TTS-synthesised NPC audio replies with "Show Text" fallback | 5 |
| **Fallback Guide AI** | Off-topic query deflection using a guide document | 4, 5 |
| **New Test Format** | Structured 5-question test with image prompts | 4, 5 |

---

## Service 4 & 5 — Key Contributions

Services 4 and 5 operate in `rag_mode: true`, which unlocks the full feature set described below. Service 5 additionally enables NPC voice output (`npc_voice_output: true`).

---

### 1. Scenario Mystery Game (情境解謎遊戲)

The centerpiece of Service 4/5. Students take on the role of a detective assistant in a London-themed mystery, asking NPC characters questions via voice to collect clues, then answering factual puzzle questions to advance.

#### Structure

```
Mystery Game
├── Topic 1: Famous Attractions & Transportation in London
│   ├── Level 1: The Frozen Big Ben        (3 questions)
│   ├── Level 2: Westminster Bridge        (3 questions)
│   ├── Level 3: The Silent Rosetta        (3 questions)
│   ├── Level 4: The Knowledge Challenge   (3 questions)
│   └── Level 5: The Secret of the Coronation (3 questions)
├── Topic 2: The Second-hand Market
│   └── 5 levels × 3 questions
└── Topic 3: British Afternoon Tea
    └── 5 levels × 3 questions
```

**Total: 3 topics × 5 levels × 3 questions = 45 scoreable puzzle questions**

#### NPC System (RAG-Based)

Each topic features three named NPCs whose knowledge is loaded from Markdown character profiles at runtime. The RAG pipeline uses OpenAI Embeddings to retrieve contextually relevant character knowledge in response to the student's voice question.

| NPC | Role | Knowledge Domain |
|---|---|---|
| Sherlock Holmes | Consulting Detective | Visual deductions, precise numbers |
| Dr. John Watson | Army Doctor | Physical evidence, witness intel |
| Mycroft Holmes | Government Official | Authorization codes, classified data |

Each NPC responds in-character using a two-phase pipeline:
- **Phase 1 (immediate, ~3–5 sec):** GPT-4o generates the NPC dialogue and sends it to the user right away
- **Phase 2 (async, background):** GPT-4o-mini evaluates language quality and relevance, then saves the structured assessment

#### Answering Mode

The game supports two question-progression modes configurable via `config.json`:

| Mode | `one_by_one` | Behaviour |
|---|---|---|
| Sequential | `true` | Pass the current question (≥ `min_score_to_pass`) to unlock the next |
| Open | `false` | All levels and questions are accessible immediately |

#### Scoring & Tiered Rubric

Puzzle questions use a **tiered 10-level few-shot rubric** embedded in `theme_config.json`. Each score level provides example answers so GPT-4o can calibrate consistently. The system distinguishes:
- Content accuracy (6 pts) — is the key answer correct?
- Sentence completeness and grammar (4 pts) — is English used properly?

Flexible spoken-code matching handles common speech-recognition variations (e.g. "Crown ex eighteen fifty nine" → `CROWN-X-1859`).

---

### 2. SEL Board Game Modules (社會情緒學習)

Six independent units, each linked to a familiar board game context. Students reflect on their game experiences by answering open-ended questions in either **English or Traditional Chinese**, supported by a specialised SEL evaluation prompt.

| Unit | Board Game | Chinese Name |
|---|---|---|
| sel1 | Monopoly | 地產大亨 |
| sel2 | The Game of Life | 生命之旅 |
| sel3 | FLIP (reframing negatives) | 換言一新 |
| sel4 | Balancing Tower Game | 瑪利歐驚險塔 |
| sel5 | Piranha Plant Escape | 瑪利歐食人花 |
| sel6 | Seven! (strategy card game) | Seven! |

#### Language Selection

When a student enters a SEL unit, they choose their answering language via a card:
- **English mode** — transcription in English, bilingual feedback (EN + ZH-TW)
- **Chinese mode** — transcription in Chinese, Chinese-only feedback, no grammar penalty

This toggle is controlled per-session and stored in `UserState.sel_language`.

#### SEL Evaluation Philosophy

The SEL prompt evaluates against the **five SEL core competencies** rather than content correctness:

1. Self-Awareness (自我覺察)
2. Self-Management (自我管理)
3. Social Awareness (社會覺察)
4. Relationship Skills (人際關係技巧)
5. Responsible Decision-Making (負責任的決定)

Key design principles:
- No "suggested answer" is shown — this avoids framing the student's personal reflection
- Multi-attempt continuity: previous attempts on the same question are fed back to GPT so that brief follow-up answers are scored as additive improvements, not isolated fragments
- Warm, growth-oriented feedback encourages Non-Violent Communication (NVC) expression

---

### 3. New Test Format (pretest1 / posttest1)

A dedicated 5-question assessment (`category/new_test.json`) distinct from the standard pre/post-test questions. Each question includes an image prompt and a tiered 10-level scoring rubric tied to British culture topics that align with the mystery game themes.

Questions cover: cultural impressions, landmarks, second-hand markets, afternoon tea, and cultural advice — matching the game's thematic content to create pre/post measurement of content-specific language growth.

---

### 4. Fallback Guide Chatbot

In Service 4/5, any text message that is not a slash command is routed to a lightweight bilingual guide AI (GPT-4o-mini). It uses `category/chatbot_guide.md` as its knowledge base and strictly:
- Answers only CoachGPT-related how-to questions
- Deflects all off-topic queries with a fixed refusal message
- Keeps responses under 60 words (bilingual: English + Traditional Chinese)

This provides a first line of support without requiring administrator intervention for common "how do I use this?" questions.

---

### 5. NPC Voice Output Mode (Service 5)

Service 5 extends NPC chat responses with synthesised audio using **OpenAI TTS (`gpt-4o-mini-tts`)**. The NPC's in-character reply text is converted to an MP3 file served from the static files directory.

**User experience flow:**
1. Student sends voice question to NPC
2. NPC character image card is sent immediately (while audio renders)
3. Audio message arrives with two quick-reply buttons:
   - **Show Text / 顯示文字** — reveals the NPC reply as a text card (usage count tracked for research)
   - **Go to Answer / 前往作答** — navigates to the current level's question cards

Each NPC can be assigned a specific TTS voice and style instruction in `theme_config.json`:
```json
{
  "tts_voice": "onyx",
  "tts_instructions": "Speak with a calm British Received Pronunciation accent."
}
```

---

### 6. Advanced Progress Tracking

Service 4/5 provides a dedicated progress dashboard split into four categories, accessible from the menu:

| Category | What is shown |
|---|---|
| **Pre-test** | pretest1 (5 Qs) + pretest2 (5 Qs), answered/total per question |
| **Game** | Per-topic passed count (e.g. 12/15 for Topic 1) across all themes |
| **Post-test** | posttest1 (5 Qs) + posttest2 (5 Qs) |
| **Other** | Exercises ex1–ex6 + 6 SEL units, per-question breakdown |

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Web Framework** | FastAPI (Python 3.12) |
| **LINE Integration** | LINE Messaging API v3 (Python SDK) |
| **AI / LLM** | OpenAI GPT-4o (assessment, NPC, SEL), GPT-4o-mini (evaluation, guide) |
| **Speech-to-Text** | OpenAI Whisper (`gpt-4o-mini-transcribe`) |
| **Text-to-Speech** | OpenAI TTS (`gpt-4o-mini-tts`) — Service 5 only |
| **Embeddings / RAG** | OpenAI `text-embedding-3-small` + cosine similarity |
| **Audio Processing** | pydub + ffmpeg |
| **Containerisation** | Docker + Docker Compose |
| **Tunnel / Reverse Proxy** | Cloudflare Tunnel (cloudflared) |
| **Data Storage** | JSON files (mounted Docker volumes) |
| **Package Management** | uv (Astral) |

---

## Project Structure

```
.
├── app.py                    # FastAPI app, lifespan hooks
├── routes.py                 # Webhook endpoint, event dispatcher
├── handlers.py               # Core event handlers (text, audio, postback)
├── config.py                 # Global singletons (LINE client, OpenAI, QuestionManager)
├── analyze.py                # Offline analytics script
├── start.sh                  # Container entrypoint
├── Dockerfile
├── docker-compose.yml        # 5 service instances + Cloudflare tunnel
│
├── manager/
│   ├── question_manager.py   # Loads and manages question JSON files
│   └── richmenu.py           # Rich menu builder and manager
│
├── utils/
│   ├── models.py             # Pydantic models (User, SpeechAssessment, GameScores, …)
│   ├── file_utils.py         # User data, config, game state, RAG cache
│   └── message_utils.py      # All Flex Message builders, system prompts
│
├── category/
│   ├── ex1.json … ex6.json   # Exercise question banks
│   ├── pretest.json          # Standard pre-test questions
│   ├── posttest.json         # Standard post-test questions
│   ├── new_test.json         # New format test (pretest1/posttest1)
│   ├── sel1.json … sel6.json # SEL unit question banks
│   ├── rich_menu.json        # Rich menu definitions and grid layouts
│   ├── chatbot_guide.md      # Fallback guide knowledge base
│   └── rag_docs/
│       ├── theme1/           # London attractions
│       │   ├── theme_config.json
│       │   ├── Theme_1_Level_1_Sherlock_Holmes.md
│       │   ├── Theme_1_Level_1_John_Watson.md
│       │   └── Theme_1_Level_1_Mycroft_Holmes.md
│       ├── theme2/           # Second-hand market
│       └── theme3/           # British afternoon tea
│
├── templates/
│   ├── richmenu/             # Rich menu images
│   ├── videos/               # Game level videos
│   ├── people_pic/           # NPC character images (3 variants each)
│   ├── themes/               # Theme cover images
│   ├── level_img/            # Per-level hero images (theme{X}_level{Y}_img.jpg)
│   ├── ragQuestion/          # Per-question answer card images
│   ├── sel/                  # SEL unit cover images
│   ├── audio/                # Generated TTS audio files (runtime)
│   └── …                     # Exercise and test images
│
└── data/                     # Persistent Docker volume
    ├── user_data.json         # Service 1
    ├── user_data2.json        # Service 2
    ├── user_data5.json        # Service 5
    ├── config.json            # Service 1
    └── config5.json           # Service 5
```

---

## Setup & Installation

### Prerequisites

- Docker & Docker Compose
- A LINE Official Account with Messaging API enabled
- OpenAI API key
- Cloudflare Tunnel token (or alternative reverse proxy)

### 1. Clone and configure

```bash
git clone <repo-url>
cd <repo-dir>
cp .env.template .env
```

Edit `.env` with your credentials:

```env
LINE_CHANNEL_ACCESS_TOKEN=<service1_token>
LINE_CHANNEL_SECRET=<service1_secret>
LINE_CHANNEL_ACCESS_TOKEN4=<service4_token>
LINE_CHANNEL_SECRET4=<service4_secret>
LINE_CHANNEL_ACCESS_TOKEN5=<service5_token>
LINE_CHANNEL_SECRET5=<service5_secret>
OPENAI_API_KEY=<your_openai_key>
DOMAIN=<your_cloudflare_domain>
DOMAIN4=<service4_domain>
DOMAIN5=<service5_domain>
```

### 2. Prepare data directories

```bash
mkdir -p data
echo '{}' > data/user_data.json
echo '{}' > data/user_data5.json
# Create config files with the default structure for each service
```

### 3. Start services

```bash
# All services
docker compose up -d

# Service 4 and 5 only
docker compose up -d service4 service5 tunnel
```

### 4. Initial rich menu setup

Rich menus are created automatically on first startup via the `lifespan` hook in `app.py`. The first run contacts the LINE API to provision all menus defined in `category/rich_menu.json`.

To force a full rebuild after image or layout changes:

```bash
RICH_MENU_FORCE_REBUILD=1 docker compose restart service4
```

Or use the in-chat admin command after logging in as admin:
```
/refresh_all_menus
```

---

## Configuration Reference

Each service reads `config.json` at startup. Key fields:

```json
{
  "admin": ["U..."],                  // LINE user IDs with admin access
  "enabled": ["ex1", "ex2", "rag_test", "pretest", "posttest", "sel1"],
  "response": ["ex1", "pretest"],     // Categories that show feedback to students
  "rag_mode": true,                   // Enable game + guide features (Service 4/5)
  "service_number": 4,                // Determines which features activate
  "npc_voice_output": false,          // Enable TTS for NPC replies (Service 5: true)
  "display_feedback": true,           // Master switch for feedback cards
  "one_by_one": false,                // false = open mode (all questions available)
  "min_score_to_pass": 3,             // Passing threshold for game questions (1-10)
  "sel_language_selection_enabled": true,  // Show language picker when entering SEL
  "game_themes": ["theme1", "theme2", "theme3"],
  "levels_per_theme": 5,
  "questions_per_level": 3,
  "enable_level_card_image": true,    // Show hero image on level intro cards
  "fix_standard_newlines": true,      // Preserve newlines in rubric text
  "use_tiered_standard_for_sel": true // Use few-shot format for SEL rubric
}
```

### Admin Slash Commands

Available to any user who has run `/magic`:

| Command | Description |
|---|---|
| `/magic` | Grant yourself admin status |
| `/unmagic` | Drop admin status (for student-view testing) |
| `/unlink` | Remove your own account binding |
| `/refresh_menu <name>` | Delete and rebuild a single rich menu by name |
| `/refresh_all_menus` | Force-rebuild every rich menu |
| `/help` | Show all available commands |

---

## Rich Menu & Navigation

The navigation system uses LINE's Rich Menu with a grid of postback buttons. The menu hierarchy for Service 4/5:

```
menu_game (default)
├── pretest  ──► pretest1 / pretest2
├── game     ──► game_lobby ──► game_theme_select ──► game_theme{1,2,3}
│                                                       ├── NPC 1, 2, 3  (chat)
│                                                       ├── Levels        (answer)
│                                                       └── Answer        (next unanswered)
├── posttest ──► posttest1 / posttest2
├── menu_other ──► exercises ──► ex1 … ex6
│                 ├── chat   ──► topic selection
│                 └── sel    ──► sel1 … sel6
└── admin    ──► game_admin ──► enabled / respond toggles
```

Smart menu reuse: on startup, existing LINE-side menus are matched by name and reused without API calls, preventing 429 rate-limit errors during normal restarts.

---

## Admin Controls

From the admin panel in LINE, administrators can:

- **Toggle sections on/off** — students receive a clear "not yet open" message when tapping a disabled section's menu button; they are immediately re-linked to the main menu
- **Toggle feedback on/off per category** — useful for exam conditions where showing feedback would reveal answers
- **Save data** — manually flush user data to disk
- **Reload questions** — hot-reload question JSON files and clear the game theme cache without restarting

---

## Data Models

Key Pydantic models (`utils/models.py`):

```python
User
├── id, dep, name, class_time
├── history: dict[str, list[SpeechAssessment]]  # keyed by "category-sub"
├── chat: ChatHistory
├── game_scores: GameScores
│   └── themes: dict[theme_id, GameThemeScore]
│       └── levels: dict[level_idx, GameLevelScore]
│           └── questions: dict[q_idx, GameQuestionScore]
│               ├── best_score, attempts, hint_count
├── npc_chat_history: dict[str, list[dict]]
├── question_history: dict[str, list[dict]]
└── show_text_count: int                         # Service 5 TTS research metric

SpeechAssessment
├── score: int          # 1–10
├── transcript: str     # Whisper output
├── chi_suggestion: str # Traditional Chinese feedback
├── eng_suggestion: str # English feedback
├── better_ans: str     # Suggested improved response
└── timestamp: float
```

User data is persisted as JSON to Docker-mounted volumes (`data/user_data{N}.json`) and auto-saved every 60 minutes, or manually via `/saveall` or the admin panel.

---

## Notes on British Culture Theme

The game content and new test questions are deliberately aligned with British culture topics — London transport, second-hand markets (Brick Lane), and afternoon tea — to create a coherent pre-test → learning → post-test arc. The mystery game narrative serves as the learning context, and the New Test (pretest1/posttest1) measures comprehension of that same cultural content, enabling measurement of speaking proficiency gains tied to specific thematic input.

---

*Built with FastAPI · LINE Messaging API · OpenAI GPT-4o · Deployed via Docker + Cloudflare Tunnel*
