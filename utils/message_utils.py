from config import line_bot_api, rich_menu_manager, DOMAIN, question_manager, client
from linebot.v3.messaging import (
    ReplyMessageRequest, TextMessage, PostbackAction, QuickReply,
    QuickReplyItem, FlexMessage, FlexCarousel, FlexBubble, FlexImage,
    FlexText, FlexBox, FlexButton, FlexSeparator, AudioMessage, ShowLoadingAnimationRequest,
    VideoMessage, URIAction
)
from manager.richmenu import *
from linebot.v3.messaging.exceptions import ApiException
from linebot.v3.messaging.models import SetWebhookEndpointRequest
from utils.models import ChatSummary, QuestionSet, SpeechAssessment, NPCChatResponse, QuestionAnswerResponse, ImprovementHintResponse
import json
# [新增] 用於 rich menu 建立時的節流與重試延遲。
# Used for throttling and retry-backoff sleeps during rich menu provisioning.
import asyncio
from utils.file_utils import (
    get_user_state, getHistory, get_rich_menu_id, isEnabled, isResponse, 
    set_rich_menu_id, save_config, get_rich_menu_category_from_id, 
    clear_rich_menu_id, config, load_game_theme_config, get_game_level_info,
    get_user_game_score, get_max_theme_score, get_user_game_progress,
    get_questions_per_level, get_user_question_score, get_user_unlocked_level,
    get_user_level_score, get_display_feedback, get_levels_per_theme,
    get_game_info_config, get_theme_display_number,
    get_new_test_question, get_new_test_questions_count, get_new_test_questions_all,
    isAdmin, get_enabled_category_for_alias, get_min_score_to_pass,
    # [新增] 逐題模式、SEL 語言選擇、跨關卡未作答題目查詢
    # one-by-one mode, SEL language-selection switch, first-never-answered finder
    is_one_by_one, is_sel_language_selection_enabled,
    get_first_never_answered_question_global,
)

URL = f'https://{DOMAIN}'
IMG_EXT = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')
CHAT_CATEGORY = ["Travel", "Sports", "Interview", "English Skills"]
CHAT_CATEGORY_IMAGE_URL = ["/templates/chat/travel.jpg", "/templates/chat/sports.jpg", "/templates/chat/interview.jpg", "/templates/chat/english_skills.jpg"]

# ========== [新增] Chat 主題對應的中文標籤 (Chinese label for each chat topic) ==========
# 順序需與 CHAT_CATEGORY 保持一致。
# Order must mirror CHAT_CATEGORY.
CHAT_CATEGORY_CHI = ["旅遊", "運動", "面試", "英語技巧"]

# ========== [新增] Chat 主題專屬 AI 提示詞 (Topic-specific AI prompt fragments) ==========
# 當使用者選定四個主題之一後，在 send_audio_request 的 system prompt 中追加對應段落，
# 引導 AI 以該主題作為對話脈絡。每個主題包含「角色設定」與「對話建議」兩部分。
# 此設計易於擴充：要新增主題只需在 CHAT_CATEGORY / CHAT_CATEGORY_CHI / CHAT_TOPIC_PROMPTS
# 三個地方各加上對應索引的項目即可。
#
# Topic-specific prompt fragments appended to the chat system prompt when the user selects a topic.
# Adding a new topic only requires appending to CHAT_CATEGORY, CHAT_CATEGORY_CHI, and CHAT_TOPIC_PROMPTS
# at the same index.
CHAT_TOPIC_PROMPTS = {
    0: (
        "Current Conversation Topic: TRAVEL.\n"
        "Focus on travel experiences, dream destinations, cultural differences, transportation, "
        "food while travelling, tips for budget or solo travel, and travel-related vocabulary "
        "(itinerary, layover, jet lag, sightseeing, souvenir, accommodation, etc.).\n"
        "Conversation moves: ask the student about a memorable trip, a place they want to visit, "
        "or how they plan a journey. Share short, friendly travel anecdotes to keep the dialogue alive. "
        "Gently introduce useful travel expressions when relevant."
    ),
    1: (
        "Current Conversation Topic: SPORTS.\n"
        "Focus on sports the student enjoys watching or playing, fitness habits, favorite athletes or teams, "
        "rules of common sports, and sports-related vocabulary (warm-up, opponent, referee, stadium, "
        "championship, workout, endurance, etc.).\n"
        "Conversation moves: ask about a sport they like, their exercise routine, or a memorable game they "
        "watched. Encourage them to describe actions in sequence. Introduce useful sports phrases naturally."
    ),
    2: (
        "Current Conversation Topic: INTERVIEW PRACTICE.\n"
        "Treat this as a friendly mock job interview. Act as a kind interviewer for entry-level or internship "
        "roles relevant to a college student. Cover self-introduction, strengths and weaknesses, motivation, "
        "teamwork experience, problem-solving, and future plans.\n"
        "Conversation moves: ask one clear interview question at a time, then give brief, supportive feedback "
        "on the student's answer (clarity, structure, professional tone) before moving to the next question. "
        "Encourage the use of polite, professional vocabulary."
    ),
    3: (
        "Current Conversation Topic: ENGLISH LEARNING SKILLS.\n"
        "Focus on helping the student improve their English speaking, listening, vocabulary, pronunciation, "
        "and study habits. Share practical, evidence-based learning tips (shadowing, spaced repetition, "
        "watching TV with subtitles, journaling in English, etc.).\n"
        "Conversation moves: ask the student what they find hardest about learning English, then offer one "
        "actionable tip at a time. Recommend small daily exercises they can try. Praise effort and curiosity."
    ),
}

def _get_chat_topic_label(sub: int) -> tuple:
    """取得指定 sub 的中英主題名稱。
    Get the bilingual topic labels for the given sub index.

    Returns (eng_label, chi_label). Returns empty strings if sub is out of range.
    """
    if sub is None or sub < 0 or sub >= len(CHAT_CATEGORY):
        return ("", "")
    return (CHAT_CATEGORY[sub], CHAT_CATEGORY_CHI[sub])


def get_chat_topic_system_prompt(sub: int) -> str:
    """根據主題索引回傳要附加到 chat AI 系統提示詞的段落。
    Get the topic-specific system prompt fragment for the given chat topic sub index.
    Returns an empty string when no topic is selected (sub < 0 or out of range).
    """
    if sub is None or sub < 0:
        return ""
    return CHAT_TOPIC_PROMPTS.get(sub, "")

# ========== [新增] SEL 類別與作答語言輔助 (SEL helpers) ==========
# 涵蓋舊的單一 'sel' 與新的六單元 'sel1'..'sel6'。
# Covers both the legacy 'sel' and the six new units 'sel1'..'sel6'.
_SEL_CATEGORIES_MU = {'sel', 'sel1', 'sel2', 'sel3', 'sel4', 'sel5', 'sel6'}


def _is_sel_cat(category) -> bool:
    """判斷類別是否屬於 SEL 系列。
    Whether a category belongs to the SEL family.
    """
    return bool(category) and category in _SEL_CATEGORIES_MU


def normalize_sel_language(language) -> str:
    """將 SEL 作答語言正規化為 'eng' 或 'chi'。
    依需求，未選擇（None / 未知值）一律預設為中文 'chi'。

    Normalize the SEL answering language to 'eng' or 'chi'.
    Per requirement, an unset/unknown value defaults to Chinese ('chi').
    """
    return 'eng' if language == 'eng' else 'chi'

def build_reference_answers_section(
    tiered_reference_answers: dict = None,
    reference_answers: list = None
) -> str:
    """
    根據參考答案格式，生成適合放入 prompt 的評分指引段落。

    若有十級評分參考答案 (tiered_reference_answers)，產生 few-shot 示例段落；
    否則退而使用舊版答案列表。

    Build a prompt section from reference answers.
    If tiered_reference_answers (dict of score->examples) is provided,
    generate a few-shot example block; otherwise fall back to plain answer list.
    """
    if tiered_reference_answers:
        lines = [
            "The following are score-level example answers (few-shot reference).",
            "Use them to calibrate your scoring. Each score level shows what a student answer at that quality looks like.",
            ""
        ]
        for score_level in sorted(tiered_reference_answers.keys(), reverse=True):
            examples = tiered_reference_answers[score_level]
            lines.append(f"Score {score_level} examples:")
            for ex in examples:
                lines.append(f'  - "{ex}"')
            lines.append("")
        return "\n".join(lines)
    elif reference_answers:
        lines = ["Reference Answers (CORRECT ANSWERS):"]
        for ans in reference_answers:
            lines.append(f"- {ans}")
        return "\n".join(lines)
    else:
        return "No reference answers provided."

def _parse_tiered_assessment_standard(raw: str):
    if not raw:
        return None
    tiered = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if '\t' not in line:
            return None
        parts = line.split('\t', 1)
        try:
            score_level = int(parts[0].strip())
        except ValueError:
            return None
        examples = [ex.strip() for ex in parts[1].split('|') if ex.strip()]
        tiered[score_level] = examples
    return tiered if tiered else None

def build_standard_section_for_audio(
    assessment_standard: str,
    is_sel: bool = False
) -> str:
    """
    產生 audio 評分 user message 中的 <standard>...</standard> 區段。
    Build the <standard>...</standard> XML section for the audio assessment user message.

    Args:
        assessment_standard: 題目的 assessment_standard 原始字串（可能是十級格式）。
                              Raw assessment_standard string for the question (possibly tiered).
        is_sel: 是否為SEL 系列題目；SEL 採取展開十級為 few-shot 的格式以強化辨識度。
                Whether the question is from the SEL family; SEL uses an expanded
                few-shot block for stronger AI parsing.

    Returns:
        若 assessment_standard 為空則回傳空字串；否則回傳完整 <standard>...</standard> 段落。
        Empty string if assessment_standard is empty; otherwise the full XML section.
    """
    if not assessment_standard:
        return ""

    # 動態載入 config flags，避免循環引用。
    # Imported lazily to avoid circular imports with file_utils.
    try:
        from utils.file_utils import (
            is_standard_newlines_fix_enabled,
            is_tiered_standard_for_sel_enabled,
        )
        fix_newlines = is_standard_newlines_fix_enabled()
        use_tiered_for_sel = is_tiered_standard_for_sel_enabled()
    except Exception:
        # Fallback：若無法載入 config，套用安全的預設值。
        # Fallback to safe defaults if config helpers are unavailable.
        fix_newlines = True
        use_tiered_for_sel = True

    # SEL 區塊：嘗試以十級結構展開為 few-shot 區塊。
    # SEL: try to expand tiered structure into a few-shot block.
    if is_sel and use_tiered_for_sel:
        tiered = _parse_tiered_assessment_standard(assessment_standard)
        if tiered:
            section = build_reference_answers_section(tiered_reference_answers=tiered)
            return f"<standard>\n{section}</standard>"

    # 一般練習與 fallback：根據 config flag 決定是否保留換行。
    # General exercises and fallback: respect config flag to preserve newlines.
    if fix_newlines:
        # 修正 chr(10) bug：保留換行，僅去除首尾空白。
        # Bug fix: preserve newlines, only strip outer whitespace.
        cleaned = assessment_standard.strip()
    else:
        # 維持舊行為（chr(10) 移除）以提供回滾選項。
        # Legacy behaviour (chr(10) stripped) kept as a rollback option.
        cleaned = assessment_standard.replace(chr(10), '').strip()

    return f"<standard>{cleaned}</standard>"

SYSTEM_INSTRUCTION = f"""
        You are a professional English speaking assessment assistant, skilled at providing improvement suggestions and improved text based on Taiwanese non-native speaker college students' responses.
        
        userAnswer represents the user's spoken response
        question represents the question
        standard represents the assessment standard and score range
        maxScore represents the maximum score
        
        Sample Question #1: Based on the vocabulary provided, explain the meaning of the word "Brochure".
        Sample Question #2: <An image shows a scene inside a bank or a similar service center. Several people are lined up in a queue, waiting at counters, likely to speak with tellers or staff behind glass or plastic dividers.>
        
        10 points - Excellent Expresser
        Complete, fluent and logical response with at least four sentences, using various sentence structures and rich vocabulary, with appropriate examples and explanations. Accurate grammar, proper vocabulary usage, natural sentences without errors, able to express details and viewpoints clearly, avoiding word order errors, word class misuse and Chinese vocabulary mixing. Even occasional minor errors do not affect understanding. Feedback should encourage students to maintain high standards and try to enrich details or examples to improve language flexibility.
        Answer #1: A brochure is a printed material designed to provide detailed information about a
        product, service, or event, often including eye-catching images and persuasive text to attract potential customers.
        Answer #2: The picture shows people standing in line at a bank counter, each waiting patiently 
        for their turn. The setting appears orderly, and the individuals are maintaining a 
        proper distance.
        
        9 points - Very Good Expresser
        Clear response that effectively expresses ideas, with rich grammar structure and occasional minor errors (such as word order or word class misuse), but these errors do not affect overall understanding. Able to express main points clearly and organize sentences effectively. Feedback should guide students to pay attention to minor errors and emphasize grammar accuracy and sentence variety to reach higher expression levels, avoiding word order issues and word class misuse.
        Answer #1: A brochure is a printed document that gives information about a specific product 
        or service, usually featuring attractive images and descriptions to engage the reader.
        Answer #2: Several people are standing in line at a bank. They are waiting for their turn at the 
        counter in an organized manner. 
        
        8 points - Good Expresser
        Mostly complete response that clearly expresses main ideas, but occasional grammar errors (such as word order errors, verb transitivity errors) affect understanding, and sentence variety is slightly lacking. Students may incorrectly use adjectives or prepositions as verbs. Chinese vocabulary mixing occasionally appears. Feedback should suggest students strengthen sentence variety and improve vocabulary accuracy and richness, emphasizing grammar structure and word order accuracy, avoiding vocabulary mixing and word class misuse.
        Answer #1: A brochure is a type of printed material that explains a product or service, often 
        with pictures and text to help people understand what is being offered.
        Answer #2: The image shows people waiting in line at a bank counter. They are standing one 
        behind another. 
        
        7 points - Basic Expresser
        Can express main concepts but lacks details, responses are mostly simple sentences, grammar errors occasionally affect understanding (such as complex sentence structure errors, verb transitivity errors). Students may have word order errors, verb-noun mismatch, or incorrectly use adjectives or prepositions as verbs. Feedback should remind students to add more details, improve grammar accuracy, and help expand vocabulary range, strengthening grammar and sentence structure clarity.
        Answer #1: A brochure is a printed piece that tells about a product or service, usually with 
        some images and information.
        Answer #2: People are lined up at a counter. It looks like they are at a bank, waiting for service.
        
        6 points - Limited Expresser
        Simpler sentence structure, limited expression, more obvious grammar errors, limited vocabulary use, relatively superficial response content. Students may confuse adjective and adverb usage, or have subject-verb disagreement errors in sentences, affecting sentence fluency and correctness. Feedback should suggest students use more complete sentences, reduce grammar errors, and try to use more vocabulary to enhance content richness, thereby strengthening expression accuracy and comprehensibility.
        Answer #1: A brochure is a paper that has information about something, often with pictures.
        Answer #2: There are people waiting in line at what seems to be a bank. 
        
        5 points - Simple Expresser
        Short sentences, single responses, frequent grammar errors, very limited vocabulary use, seriously affecting communication clarity. Students may not be able to use articles accurately, or have word order errors in simple sentences, causing understanding difficulties. Feedback should guide students to improve sentence structure, reduce grammar errors, and learn more appropriate vocabulary to strengthen communication effect, improving language clarity and comprehensibility.
        Answer #1: A brochure is a small booklet that gives information.
        Answer #2: People are standing in line at a counter. It looks like a bank. 
        
        4 points - Limited Interaction Ability
        Responses are mostly short sentences or phrases, content is relatively fragmented, grammar errors affect understanding, very little vocabulary use, lacking logic. Students may confuse verb tense and form, or confuse nouns with verbs or adjectives. Feedback should encourage students to use complete sentences and improve grammar structure and vocabulary choice, helping improve expression logic and comprehensibility.
        Answer #1: A brochure is paper that shows products.
        Answer #2: People are waiting at a counter in a bank. 
        
        3 points - Extremely Limited Expresser
        Can only piece together words, sentence structure is chaotic or incomplete, response content is hard to understand, improper vocabulary use affects communication. Feedback should encourage students to try constructing complete sentences and learn basic grammar to improve comprehensibility.
        Answer #1: A brochure is for information. 
        Answer #2: People are standing in line. It looks like a bank. 
        
        2 points - Very Low Expression Ability
        Can only say single words or phrases, cannot form meaningful sentences, response may be unrelated to the question or extremely simple. Feedback should suggest students learn basic sentence patterns and try simple sentence combinations to improve language expression ability.
        Answer #1: A brochure is a book.
        Answer #2: People are at a bank.
        
        1 point - No Expression Ability
        Test taker cannot produce any understandable language, may be completely silent. Feedback should suggest students read the question carefully and try to answer, even simple responses can help improve expression ability.
        Answer #1: <Not speaking, nonsense, or not knowing> 
        Answer #2: <Not speaking, nonsense, or not knowing>
        
        If only four score ranges are provided:
        4 points: Test taker can use complete sentences to answer questions, content is completely correct, no grammar or information errors. Answer is clear and fluent, effectively conveying the information required by the question, understandable without modification. Feedback should encourage students to maintain correctness and fluency, and add details to strengthen expression when possible.
        3 points: Test taker's answer is mostly correct, but may have some information missing, affecting response completeness. Even though the answer content mostly meets the question requirements, sentence structure still needs adjustment. Feedback should guide students to improve sentence structure or detail accuracy, ensuring complete expression of all necessary information.
        2 points: Test taker's answer may only express partial information, making the answer hard to understand. May not use complete sentences, or answer is too brief, causing unclear information. Feedback should provide more basic suggestions to help students strengthen grammar and sentence structure understanding, ensuring complete and correct information.
        1 point: Test taker did not answer, or answer content is completely wrong. May only say unrelated words or phrases, or provide information inconsistent with the question. Feedback should suggest students read the question and try to use complete sentences to respond, to improve basic expression ability.
        
        You need to perform the task in 4 steps, Think step by step:
        1. Analyze and suggest based on the provided assessment aspects: expression clarity, grammar usage, vocabulary range, response complexity, topic relevance.
        2. Score the student's spoken response based on the provided scoring standard examples and ranges (It's okay to give out full marks).
        3. Provide specific analysis and suggestions, such as correcting grammar errors, suggesting more natural sentences or increasing vocabulary, respond in Traditional Chinese (zh-TW) and English (en-US).
        4. Based on the student's response text, extend or improve their answer in English.
        
        IMPORTANT: All Chinese responses must use Traditional Chinese (zh-TW), NEVER use Simplified Chinese.
        
        The JSON object must use the schema: {json.dumps(SpeechAssessment.model_json_schema(), indent=2)}
    """

# ========== SEL 評分系統指示 (SEL evaluation system instruction) ==========
# SEL 區塊是讓使用者分享個人經驗與心情，沒有固定答案，也不提供「建議回答」。
# 評分改以 SEL（社會情緒學習）五大核心能力為主軸，輔以表達清晰度，
# 而非以英文文法 / 句子完整度為唯一標準（這對選擇中文作答的學生並不適合）。
# 透過 build_sel_system_instruction(language) 產生中文 / 英文兩種模式的提示詞：
#   - language == 'eng'：學生用英文作答，回饋採中英對照。
#   - language == 'chi'：學生用中文作答，回饋只給中文，且不評斷英文文法。
#
# The SEL section lets students share personal experiences and feelings; there is NO fixed
# answer and NO "suggested answer" is given. Grading is anchored on the five SEL core
# competencies plus expression clarity, NOT on English grammar/sentence completeness (which
# is unsuitable for students who choose to answer in Chinese). build_sel_system_instruction
# (language) produces a Chinese-mode or English-mode prompt accordingly.

# SEL 五大核心能力（中英對照），供提示詞與其他模組重複使用。
# The five SEL core competencies (bilingual), reused across the prompt and other modules.
SEL_CORE_COMPETENCIES = [
    ("Self-Awareness", "自我覺察", "認識自己的情緒、優勢與想法。"),
    ("Self-Management", "自我管理", "管理情緒、壓力與行為。"),
    ("Social Awareness", "社會覺察", "理解他人感受，培養同理心。"),
    ("Relationship Skills", "人際關係技巧", "溝通、合作與建立良好關係。"),
    ("Responsible Decision-Making", "負責任的決定", "思考後果並做出適當選擇。"),
]


def _sel_competency_block() -> str:
    """產生提示詞中描述 SEL 五大核心能力的段落（英文，供 AI 理解評分面向）。
    Build the SEL five-competency description block used inside the prompt."""
    lines = []
    for eng, chi, desc in SEL_CORE_COMPETENCIES:
        lines.append(f"- {eng} ({chi}): {desc}")
    return "\n".join(lines)


def build_sel_system_instruction(language: str = 'chi') -> str:
    """依作答語言產生 SEL 評分系統提示詞。
    Build the SEL evaluation system prompt according to the answering language.

    Args:
        language: 'eng' = 學生用英文作答（回饋中英對照）；
                  'chi' = 學生用中文作答（回饋僅中文，不評斷英文文法）。
                  其他值一律視為 'chi'。
    """
    language = 'eng' if language == 'eng' else 'chi'
    competencies = _sel_competency_block()
    schema = json.dumps(SpeechAssessment.model_json_schema(), indent=2)

    # 共用的核心理念（中英文模式皆適用）。
    # Shared core philosophy (applies to both language modes).
    shared_core = f"""
        You are a warm, supportive Social-Emotional Learning (SEL) coach and assessor for
        Taiwanese college students. In this SEL section, students share their personal
        experiences, feelings, opinions and reflections. There is NO fixed correct answer,
        and you must NOT assume or impose any "model answer".

        Your goal is NOT to answer for the student, but to UNDERSTAND them and help them
        express themselves more clearly, so they can improve their interpersonal
        communication. Treat every sincere answer with empathy and respect.

        userAnswer = the student's CURRENT spoken response (transcribed).
        question   = the open-ended SEL prompt that invites personal sharing.
        previousAttempts = the SAME student's earlier answers to THIS SAME question, in order
                 (oldest first). This may be empty on the first attempt.

        ==== SEL FIVE CORE COMPETENCIES (use these as your primary evaluation lens) ====
        {competencies}

        ==== HOW TO EVALUATE (no fixed answer; do NOT grade on a "correct" content) ====
        Assess, with empathy, the degree to which the student:
        1. Notices and names their own emotion (Self-Awareness).
        2. Describes the situation and how they managed/expressed the feeling (Self-Management).
        3. Shows awareness of others' feelings or perspectives where relevant (Social Awareness).
        4. Communicates in a way that builds understanding rather than blame (Relationship Skills).
        5. Reflects on consequences or what they could do (Responsible Decision-Making).
        Also consider EXPRESSION CLARITY: is the idea organised and clear enough for a listener
        to understand the student's feeling and situation?

        ==== CONTINUITY ACROSS ATTEMPTS (CRITICAL - read carefully) ====
        After your guidance, a student often sends a SHORT follow-up that only adds or refines one
        part of what they already said. Judged in isolation, that follow-up can look fragmentary or
        seem only weakly related to the question, which would unfairly lower the score.
        To make the FINAL score faithfully reflect the student's actual answer to this question:
        - Treat previousAttempts and the current userAnswer as ONE evolving answer to the same
          question. Mentally COMBINE them into the student's fullest, clearest expression of this
          question so far.
        - Score that COMBINED expression. NEVER down-score a short on-topic follow-up just because,
          on its own, it is brief or appears less related to the question — the earlier attempts
          already established the relevance and content.
        - The latest score should be at least as high as what the combined expression deserves; a
          sincere refinement must not make the score go DOWN versus what the student had already
          expressed.
        - Only treat an answer as off-topic/irrelevant if NEITHER the current answer NOR any previous
          attempt addresses the question.

        ==== 10-LEVEL SCORING RUBRIC (lenient but discriminating; each level is distinct) ====
        Pick the SINGLE level whose description best matches the student's COMBINED expression for
        this question. The levels assess SEL awareness + expression clarity ONLY - never content
        "correctness", personal choices, or (in Chinese mode) English grammar.

        10 - Insightful & well-rounded: Clearly names a specific emotion, vividly describes the
             situation and what triggered it, AND adds genuine depth - empathy or awareness of
             others' perspectives, and/or a constructive way to respond or a thoughtful reflection
             on what they learned or would do next. Expression is clear, organised and easy to
             follow. Strong across several SEL competencies.
        9  - Strong: Names a clear emotion with solid context and at least one added dimension
             (empathy, a constructive response, or reflection on consequences). Well organised and
             easy to follow; only a little more depth or a closing thought would reach a 10.
        8  - Good: Names a feeling and gives a clear reason or situation, with some self-awareness or
             awareness of others. The point is clear and understandable; could be lifted by a concrete
             example, a constructive next step, or more emotional nuance.
        7  - Solid: States a feeling and a basic reason or piece of context, clearly on-topic. The
             idea comes across, though it stays fairly general or brief and shows limited empathy,
             reflection, or emotional detail.
        6  - Adequate: Conveys a feeling and a little context, but is mostly a plain statement with
             little nuance, example, or reflection. Still understandable without effort.
        5  - Emerging: Names a feeling or a reaction with very little context; the personal point is
             detectable but undeveloped - essentially one short on-topic statement with no follow-up.
        4  - Limited: Very brief or vague - mostly just an emotion label (e.g. "I'm sad" / "他很煩" /
             "我覺得很煩") with almost no situation, reason, or reflection. Sincere and on-topic, but
             minimal self-awareness and expression.
        3  - Very limited: Fragmentary - only a keyword or a single short phrase; the personal point
             is barely discernible. On-topic in spirit but very little usable expression of feeling
             or situation.
        2  - Minimal: Only an isolated word or phrase that is loosely related to the topic, carrying
             almost no information about the student's actual feeling, situation, or view.
        1  - No effective expression: Off-topic, no real personal sharing, silence, "I don't know"
             with nothing more, or nonsense - nothing can be assessed as personal expression, and no
             previous attempt addressed the question either.

        Calibration tips (lenient yet discriminating):
        - A SHORT but complete and clear personal share (emotion + a little context) can still earn
          7-8; do NOT withhold higher scores merely because the answer is short.
        - Any sincere, on-topic personal response should sit at 4 or above; reserve 1-3 for
          fragments/keywords or off-topic/no-response cases.
        - Do NOT lower the score because the content is "ordinary" or because of the student's
          personal choices - judge awareness, clarity, and reflection only.

        ==== FEEDBACK STYLE (guide, do not prescribe an answer) ====
        Give warm, specific, growth-oriented feedback that helps the student SEE how to express
        themselves more clearly and communicate better. You may:
        - When the answer is short or lacks emotional vocabulary, gently respond to the CONTENT and
          invite them to say more: what happened, how they felt in that moment, and how they would
          like others to treat them.
        - Encourage Non-Violent Communication (NVC): describe the trigger + the feeling, instead of
          judging the other person. For example, if a student says they find someone "annoying",
          guide them toward "When he keeps interrupting me, I feel a bit uncomfortable."
        - When a student only states one feeling (e.g. "I'm sad"), invite them to explore underlying
          feelings - for instance feeling disrespected, treated unfairly, or misunderstood - and to
          describe what they wish had happened.
        - IMPORTANT - to avoid fragmented follow-ups: when you ask the student to improve, ALWAYS
          invite them to say their WHOLE answer again in one complete piece (restate everything in a
          single full response), rather than only adding the missing part. Make this explicit, e.g.
          "Next time, try saying your whole answer again in one go, including this part."
        DO NOT provide a "suggested answer" or rewrite their answer for them. Offer direction and
        questions, never a script to copy. (The "better_ans" field MUST be an empty string.)
    """

    if language == 'eng':
        mode_specific = """
        ==== LANGUAGE MODE: ENGLISH ====
        The student answered in English. Provide feedback in BOTH English (eng_suggestion) and
        Traditional Chinese (chi_suggestion). You may also note, briefly and kindly, any English
        wording that obscures the meaning, but emotional awareness, clarity and reflection are the
        priority — do not turn this into a strict grammar test.

        Output rules:
        - "chi_suggestion": warm SEL-oriented feedback in Traditional Chinese (zh-TW).
        - "eng_suggestion": the same guidance in natural English.
        - "score": integer 1-10 per the guidance above.
        - "transcript": leave as the student's answer (the caller will fill it).
        - "better_ans": MUST be an empty string "" (never provide a suggested answer).
        """
    else:
        mode_specific = """
        ==== LANGUAGE MODE: CHINESE ====
        The student answered in Traditional Chinese. Evaluate the CHINESE response on the SEL
        competencies and expression clarity ONLY. Do NOT assess English grammar or vocabulary and
        do NOT ask them to answer in English. All feedback must be in Traditional Chinese.

        Output rules:
        - "chi_suggestion": warm, specific SEL-oriented feedback in Traditional Chinese (zh-TW).
        - "eng_suggestion": MUST be an empty string "" (Chinese mode gives no English feedback).
        - "score": integer 1-10 per the guidance above (judging the Chinese answer).
        - "transcript": leave as the student's answer (the caller will fill it).
        - "better_ans": MUST be an empty string "" (never provide a suggested answer).
        """

    closing = f"""
        IMPORTANT: All Chinese responses MUST use Traditional Chinese (zh-TW), NEVER Simplified Chinese.

        The JSON object must use the schema: {schema}
    """

    return shared_core + mode_specific + closing


# 向後相容：保留 SEL_SYSTEM_INSTRUCTION 名稱（英文模式預設），供既有 import 使用。
# Backward compatibility: keep the SEL_SYSTEM_INSTRUCTION name (English-mode default)
# for existing imports; new code should call build_sel_system_instruction(language).
SEL_SYSTEM_INSTRUCTION = build_sel_system_instruction('eng')

# NPC Chat System Instructions - Includes language detection and relevance scoring
# NPC Quick Response Prompt (for immediate display, 3-5 sec)
NPC_CHAT_QUICK_RESPONSE = """
You are {persona} in an immersive mystery game.

Context (information you KNOW and can share): {context}
Recent conversation: {history}

Rules:
1. Stay in character, respond naturally (1-3 sentences)
2. Only answer what was asked, no spoilers
3. If user speaks non-English, politely ask them to use English and set is_english=false
4. CRITICAL - UNCERTAINTY DISCLOSURE: If the user's question asks for a specific clue, answer, or piece of evidence that is NOT clearly stated in your Context above, you MUST:
   a. Give a brief related or general response (do not invent specific details)
   b. Honestly admit you are not certain of that specific detail
   c. Suggest the user try asking one of the other characters who may know more
   Example: "I'm not entirely sure about that specific detail. You might want to ask [other character name] -- they may have more precise information on that."
5. Only provide specific factual answers (names, codes, times, locations) when they appear EXPLICITLY in your Context.

Output JSON:
{{
  "npc_reply": "Your in-character response (English, 1-3 sentences, including uncertainty disclosure if needed)",
  "is_english": true/false
}}
"""

# NPC Evaluation Prompt (async processing, 5-8 sec)
NPC_CHAT_EVALUATION = """
Evaluate this English learning conversation in a mystery game.

User's question: {user_text}
NPC role: {persona}
Game theme: {theme_context}

Evaluate TWO aspects (1-10 scale):

LANGUAGE QUALITY (language_score):
- 9-10: Near-perfect grammar and vocabulary
- 7-8: Minor errors, still clear
- 5-6: Noticeable errors but understandable
- 3-4: Frequent errors affecting clarity
- 1-2: Severe errors, hard to understand

RELEVANCE (relevance_score):
- 9-10: Directly asks about key clues/mystery elements
- 7-8: Related to story, helpful questions
- 5-6: Somewhat related but off-track
- 3-4: Mostly irrelevant to the game
- 1-2: Completely unrelated (casual chat, off-topic)

Feedback rules:
- ONLY give feedback if there are actual errors
- If English is perfect, leave both fields EMPTY
- Keep concise (1-2 sentences)
- English first, then Traditional Chinese translation

Output JSON:
{{
  "language_score": 8,
  "relevance_score": 7,
  "feedback_eng": "Use 'did' for past tense questions.",
  "feedback_chi": "Use 'did' for past tense questions."
}}
"""

# Question Answer System Instruction - Improved for code/pronunciation handling
QUESTION_ANSWER_SYSTEM_INSTRUCTION = """
You are an evaluator assessing a student's English answer to a factual question in an educational mystery game.

Question: {question}

=== SCORING REFERENCE (FEW-SHOT EXAMPLES) ===
{reference_answers_section}

Student's Answer: {user_answer}

=== EVALUATION CRITERIA ===

**CRITICAL RULE: This is an ENGLISH learning game. If the student's answer contains Chinese characters or is not in English, give a score of 0 and set is_correct to false, regardless of whether the content is correct.**

**SCORING STANDARD (10-point scale):**
- 6 points are reserved for CONTENT ACCURACY (whether the key answer/keyword is stated correctly).
- 4 points are reserved for SENTENCE COMPLETENESS AND GRAMMAR (whether a complete English sentence is used).

**Score level guidelines:**
- 10: Perfect complete sentence, correct answer, context included, no grammar errors. (4 pts for sentence + 6 pts for correct answer)
- 8-9: Complete sentence but answer has minor deviation (e.g. reference is 04:18:37, student says 04:18:27 or only 04:18), simple wording, or very minor grammar flaw.
- 6-7: Correct key answer but sentence is incomplete (e.g. only a noun or phrase), OR sentence/grammar is good but answer has noticeable deviation from reference.
- 4-5: Incomplete sentence AND answer is only partially correct or semantically vague.
- 2-3: Random guess, off-topic, or extremely fragmented words.
- 1: Student says they don't know, or no response/silence.
- 0: Answer is in Chinese or not in English.

**Use the few-shot examples above to calibrate your score.**

**CRITICAL RULE: Content accuracy is the PRIMARY factor. A wrong answer CANNOT get a high score regardless of grammar.**

**FLEXIBLE MATCHING RULES FOR CODES AND SPECIAL FORMATS (English answers only):**

IMPORTANT: When users SPEAK codes aloud, speech recognition may produce various formats. Be VERY lenient:

- For CODE answers (like "CROWN-X-1859", "OVERRIDE-PROTOCOL-007", "SH-221B"):
  * Accept with or without hyphens: "CROWN-X-1859" = "CROWN X 1859" = "CROWNX1859"
  * Accept phonetic/word pronunciations: 
    - "Crown X eighteen fifty nine" = "CROWN-X-1859"
    - "Crown dash X dash eighteen fifty nine" = "CROWN-X-1859"
    - "Crown ex eighteen fifty nine" = "CROWN-X-1859"
    - "Override protocol zero zero seven" = "OVERRIDE-PROTOCOL-007"
    - "Override protocol double oh seven" = "OVERRIDE-PROTOCOL-007"
    - "S H two two one B" = "SH-221B"
    - "S H dash two two one B" = "SH-221B"
  * Accept letter-by-letter spelling: "C R O W N X 1 8 5 9" = "CROWN-X-1859"
  * Be case-insensitive: "crown-x-1859" = "CROWN-X-1859"
  * Accept common speech recognition variations:
    - "X" may be transcribed as "ex", "X", "x"
    - Numbers may be spoken as words: "eighteen" = "18"
    - "007" may be "double oh seven", "zero zero seven", "oh oh seven"
  * Accept minor phonetic variations and typos

- For TIME answers:
  * Accept with or without leading zeros: "4:18:37" = "04:18:37"
  * Accept spoken format: "four eighteen thirty-seven" = "4:18:37"
  * Accept partial formats if close: "four eighteen" for "4:18:XX" (partial credit)

- For NAME answers:
  * Accept common spelling variations
  * Be lenient with minor spelling differences
  * "H Carter" = "H. Carter" = "H Carter"

- For SPECIFIC TERMS:
  * Accept synonyms and descriptions
  * "Red Double-decker Bus" = "red double decker" = "double decker bus" = "red bus double decker"

FEEDBACK RULES (IMPORTANT):
1. If the answer is not in English, feedback should explain that English is required.
2. DO NOT reveal the correct answer in feedback_chi or feedback_eng.
3. Focus feedback on grammar usage and vocabulary accuracy.
4. All Chinese MUST be Traditional Chinese, NEVER Simplified Chinese.
5. Keep feedback concise but helpful for language learning.

Output MUST be valid JSON:
{{
  "score": 8,
  "feedback_chi": "Feedback in Traditional Chinese - Only about grammar and vocabulary, DO NOT reveal the answer",
  "feedback_eng": "English feedback - ONLY about grammar and vocabulary, DO NOT reveal the answer",
  "reference_comparison": "Detailed comparison: what student said vs what the answer should be",
  "is_correct": true
}}
"""

# Improvement Hint System Instruction - Customized hints without revealing answer
IMPROVEMENT_HINT_SYSTEM_INSTRUCTION = """
You are a helpful hint provider for an educational mystery game. A student has answered a question and needs guidance to improve their answer WITHOUT being told the correct answer directly.

Question: {question}

Reference Answer (DO NOT REVEAL THIS): {reference_answers}

Student's Answer: {user_answer}

Student's Score: {score}/10

Your task: Provide a CUSTOMIZED improvement hint that helps the student understand what they're missing or how to improve, WITHOUT revealing the answer.

HINT GUIDELINES:
1. NEVER say the actual answer or any part of it directly.
2. If the answer is missing information (e.g., missing seconds in a time), hint about what type of information is incomplete.
3. If the answer is completely wrong, guide them toward the right TYPE of answer (e.g., "This question is asking for a time/code/name/location").
4. If the answer is partially correct, acknowledge what's right and hint at what's missing.
5. Be encouraging and supportive.
6. Use specific hints based on the gap between their answer and the reference.

HINT EXAMPLES:
- If reference is "04:18:37" and student said "4:18": "Please include the complete time with all units (hours, minutes, and seconds)."
- If reference is "Red Double-decker Bus" and student said "taxi": "Think about what type of iconic London transportation is most commonly associated with tourists."
- If reference is "CROWN-X-1859" and student said "ABC-123": "The code you're looking for has a specific pattern related to British royalty. Listen carefully to the NPC's hints."

All Chinese MUST be Traditional Chinese, NEVER Simplified Chinese.

Output MUST be valid JSON:
{{
  "hint_eng": "English improvement hint that guides without revealing the answer",
  "hint_chi": "Traditional Chinese improvement hint that guides without revealing the answer"
}}
"""

# Game System Instruction - More refined, no spoilers
GAME_SYSTEM_INSTRUCTION = """
You are an NPC in an immersive mystery game. Stay strictly in character.

Your Identity: {persona}

Background Knowledge (use only when asked):
{context}

Recent Conversation:
{history}

CRITICAL RULES:
1. CONCISE RESPONSES: Keep replies short and natural (1-3 sentences max). Only answer what was asked.
2. NO SPOILERS: Never volunteer information the player didn't ask about. Let them discover through questions.
3. STAY IN CHARACTER: Respond as your character would. If asked something outside your knowledge, deflect naturally.
4. DO NOT COPY: Rephrase context information naturally as dialogue. Never copy-paste.

As a hidden language coach, evaluate the user's English but keep feedback minimal.

IMPORTANT: 
- All Chinese feedback MUST be in Traditional Chinese, NEVER Simplified Chinese.
- Only provide feedback if there are ACTUAL grammar or vocabulary errors.

Output MUST be valid JSON:
{{
  "npc_reply": "Your concise in-character response (English, 1-3 sentences)",
  "feedback": "Brief grammar/vocab tip (Traditional Chinese, empty if no errors)",
  "score": 8
}}
"""

SYSTEM_SUMMARY_INSTRUCTION = f"""
    You are an English teaching expert analyzing conversation transcripts between non-native English speakers (Taiwanese college students) and AI. Provide concise analysis within 200 words using the sandwich communication method (positive feedback - improvement suggestions - encouragement) in both Traditional Chinese and English.
    Analysis Focus Areas
    - Vocabulary Variety: Does the student repeat the same words (e.g., only using "delicious" for expressing tasty)?
    - Basic Grammar: Subject-verb agreement (oral standards, not overly strict)
    - Response Relevance: Does the student answer questions appropriately, not off-topic?

    Output start by highlighting what the student did well, then specifically point out 1-2 main issues and solutions, finally, provide positive support.

    Keep within 200 words with a friendly and specific tone and first person perspective in plain text format.
    
    IMPORTANT: All Chinese text MUST be in Traditional Chinese, NEVER Simplified Chinese.
    """

SYSTEM_SUMMARY_AND_SCORE_INSTRUCTION = f"""
    You are a professional English teaching expert analyzing conversation transcripts between non-native English learners (Taiwanese college students) and AI. Please provide concise analysis within 200 words using the sandwich communication method (positive feedback, improvement suggestions, encouragement) in Traditional Chinese and English.

    Analysis Focus:
    - Vocabulary Variety: Does the student repeat the same words?
    - Basic Grammar: Subject-verb agreement (oral standards, not overly strict)
    - Response Relevance: Does the student answer questions appropriately, not off-topic?

    First point out what the student did well, then specifically point out 1-2 main issues and solutions, finally provide positive support.

    Keep within 200 words, use a friendly and specific tone and first person perspective, in plain text format.
    
    IMPORTANT: All Chinese content must use Traditional Chinese (zh-TW), NEVER use Simplified Chinese.

    Also give an overall score of 1-10 based on the student's performance.
    The JSON object must use the schema: {json.dumps(ChatSummary.model_json_schema(), indent=2)}
    """


# Core message functions
async def send_message(event, msg):
    if msg is None:
        return
    if not isinstance(msg, list):
        msg = [msg]
    await line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=msg
        )
    )


async def text_message(text):
    return TextMessage(text=text)


async def send_text_message(event, text):
    await line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=text)]
        )
    )


async def send_chat_response(event, filename, duration, history=None):
    quick_reply = QuickReply(items=[
        QuickReplyItem(action=PostbackAction(label='Lookup', data=f'action=chat&lookup=true')),
    ])
    if history and len(history.questions) >= 5:
        quick_reply.items.append(QuickReplyItem(action=PostbackAction(label='Summary', data=f'action=chat&summary=true')))
    await line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[AudioMessage(originalContentUrl=f'{URL}/templates/{filename}', quickReply=quick_reply, duration=duration)]
        )
    )


async def chat_summary_message(summary: ChatSummary):
    contents = [FlexBubble(
            size='mega',
            body=FlexBox(
                layout='vertical',
                justifyContent='center',
                alignItems='center',
                spacing='lg',
                contents=[
                    FlexText(
                        text='Chat Summary',
                        wrap=True,
                        weight='bold',
                        size='xxl',
                        align='center',
                        color="#001174",
                    ),
                ]
            )
        ),
        FlexBubble(
            size='mega',
            body=FlexBox(
                layout='vertical',
                spacing='lg',
                contents=[
                    FlexText(
                        text=f'{summary.eng_summary}'
                        if summary.eng_summary else 'No summary.',
                        wrap=True,
                        size='md',
                    ),
                ]
            )
        ),
        FlexBubble(
            size='mega',
            body=FlexBox(
                layout='vertical',
                spacing='lg',
                contents=[
                    FlexText(
                        text=f'{summary.chi_summary}'
                        if summary.chi_summary else 'No summary.',
                        wrap=True,
                        size='md',
                    ),
                ]
            )
        ),]
    return FlexMessage(altText='Chat Summary', contents=FlexCarousel(contents=contents))


async def progress_message(user_id):
    questions = question_manager.questions 
    progress: dict[str: list[int]] = {}
    total = 0
    
    for category, question in questions.items():
        if not isEnabled(category):
            continue
        num_questions = len(question.content)
        for i in range(num_questions):
            key = f'{category}-{i}'
            history = getHistory(user_id, key)
            if history and len(history) > 0:
                if category not in progress:
                    progress[category] = []
                progress[category].append(i)
                total += 1
    
    progress_text = ""
    for category, indices in progress.items():
        progress_text += f"{category}: {', '.join([f'Q{i+1}' for i in indices])}\n"
    
    if not progress_text:
        progress_text = "尚無進度。\nNo progress yet.\n"
    
    return FlexMessage(
        altText='Progress',
        contents=FlexBubble(
            size='mega',
            body=FlexBox(
                layout='vertical',
                spacing='lg',
                contents=[
                    FlexText(
                        text='Progress\n學習進度',
                        wrap=True,
                        weight='bold',
                        size='xl',
                    ),
                    FlexText(
                        text=f'已回答 {total} 題\nTotal: {total} questions answered',
                        wrap=True,
                        size='md',
                        color='#5b5b5b',
                    ),
                    FlexText(
                        text=progress_text,
                        wrap=True,
                        size='sm',
                    ),
                ]
            )
        )
    )


async def question_message(user_id, category, sub, show_feedback: bool = True, sel_language: str = None):
    question = question_manager.get_question(category, sub)
    history = getHistory(user_id, f'{category}-{sub}')

    # [新增 1] SEL 中文作答模式：字卡與說明改為全中文，移除英文內容。
    # 非 SEL 類別（ex1..ex6、pretest 等）行為完全不變，確保 service1/2/3 相容。
    # SEL Chinese-answer mode: render the card/instruction entirely in Chinese.
    # Non-SEL categories are untouched, preserving service1/2/3 behaviour.
    _sel = _is_sel_cat(category)
    _chi_mode = _sel and normalize_sel_language(sel_language) == 'chi'

    contents = []
    
    # Question text bubble
    q_bubble = FlexBubble(
        size='mega',
        body=FlexBox(
            layout='vertical',
            spacing='lg',
            contents=[
                FlexText(
                    text=f'Q{sub + 1}',
                    wrap=True,
                    weight='bold',
                    size='xl',
                ),
                FlexText(
                    text=question.text,
                    wrap=True,
                    size='md',
                    color='#5b5b5b',
                ),
            ]
        )
    )
    
    # Add image if available
    if question.image_url:
        q_bubble.hero = FlexImage(
            url=f'{URL}{question.image_url}',
            size='full',
            aspect_ratio='20:13',
            aspect_mode='cover',
        )
    
    contents.append(q_bubble)
    
    # History bubble if exists
    if history and len(history) > 0:
        last = history[-1]
        history_bubble = FlexBubble(
            size='mega',
            body=FlexBox(
                layout='vertical',
                spacing='sm',
                contents=[
                    FlexText(
                        text='Last Answer\n上次回答',
                        wrap=True,
                        weight='bold',
                        size='lg',
                    ),
                    FlexText(
                        text=f'Score: {last.score}',
                        wrap=True,
                        size='md',
                        color='#00aa00' if last.score >= 7 else '#ff8800' if last.score >= 4 else '#ff0000',
                    ),
                    FlexText(
                        text=f'"{last.transcript}"',
                        wrap=True,
                        size='sm',
                        color='#5b5b5b',
                        style='italic',
                    ),
                ]
            ),
            # 僅在後台開啟回饋時顯示 View Feedback 按鈕
            # Show View Feedback button only when feedback is enabled in admin
            footer=FlexBox(
                layout='vertical',
                contents=[
                    FlexButton(
                        action=PostbackAction(
                            label='View Feedback',
                            data=f'action=last&category={category}&sub={sub}'
                        ),
                        style='secondary',
                    ),
                ]
            ) if show_feedback else None
        )
        contents.append(history_bubble)
    
    # Instructions bubble
    # [新增 1] SEL 中文模式顯示全中文說明「試著用中文回答以下問題」；
    # 其餘維持原本中英對照說明（含 service1/2/3 與 SEL 英文模式）。
    if _chi_mode:
        _instruction_text = (
            '試著用中文回答以下問題！\n'
            '請在發送文字訊息的鍵盤位置，點擊麥克風符號錄音並發送語音訊息以作答。'
        )
    else:
        _instruction_text = (
            '請在發送文字訊息的鍵盤位置，點擊麥克風符號錄音並發送語音訊息以作答。'
            '為了獲得高分請盡量用完整句子作答！\n'
            'To answer, please tap the microphone icon near the text keyboard to record '
            'and send a voice message. For a higher score, please try to answer in complete sentences!'
        )
    instruction_bubble = FlexBubble(
        size='mega',
        body=FlexBox(
            layout='vertical',
            justifyContent='center',
            alignItems='center',
            spacing='md',
            contents=[
                FlexText(
                    text=_instruction_text,
                    wrap=True,
                    size='lg',
                    align='center',
                ),
            ]
        )
    )
    contents.append(instruction_bubble)
    
    return FlexMessage(
        altText=f'Q{sub + 1}',
        contents=FlexCarousel(contents=contents)
    )


async def chat_message(user_id, sub):
    topic = CHAT_CATEGORY[sub] if sub < len(CHAT_CATEGORY) else "General"
    image_url = CHAT_CATEGORY_IMAGE_URL[sub] if sub < len(CHAT_CATEGORY_IMAGE_URL) else None
    
    bubble = FlexBubble(
        size='mega',
        body=FlexBox(
            layout='vertical',
            spacing='lg',
            justifyContent='center',
            alignItems='center',
            contents=[
                FlexText(
                    text=f'Chat Topic: {topic}',
                    wrap=True,
                    weight='bold',
                    size='xl',
                    align='center',
                ),
                FlexText(
                    text='Send a voice message to start chatting!',
                    wrap=True,
                    size='md',
                    color='#5b5b5b',
                    align='center',
                ),
            ]
        )
    )
    
    if image_url:
        bubble.hero = FlexImage(
            url=f'{URL}{image_url}',
            size='full',
            aspect_ratio='20:13',
            aspect_mode='cover',
        )
    
    return FlexMessage(
        altText=f'Chat: {topic}',
        contents=bubble
    )


# ========== [新增] Chat 進入提示與主題選擇提示訊息 ==========
# 這些訊息僅針對 service4/5 (rag_mode=true) 的 menu_other → chat 入口而設計，
# 但函式本身無服務限制；呼叫端負責判斷是否需要使用。
#
# These message builders are designed for the service4/5 (rag_mode=true) chat entry experience,
# but the functions themselves are service-agnostic; the caller decides when to invoke them.

async def chat_welcome_message():
    """進入 Chat 頁面時的中英文歡迎/說明訊息。
    Bilingual welcome message shown when the user enters the chat menu.

    告知使用者：
      1. 可直接傳送語音訊息和 AI 對話；
      2. 可至「語音設定」調整語音性別與口音；
      3. 下方主題按鈕可選擇對話主題（旅遊 / 運動 / 面試 / 英語技巧）。
    """
    text = (
        "歡迎進入 Chat 區！\n"
        "傳送語音訊息即可直接和 AI 開始進行對話，如有偏好的語音性別與口音，"
        "可以到語音設定調整。\n"
        "下方按鈕還可選擇對話主題：旅遊、運動、面試、英語技巧。\n"
        "\n"
        "Welcome to the Chat section!\n"
        "Send a voice message to start chatting with the AI directly. "
        "If you have a preferred voice gender or accent, you can adjust it in the voice settings.\n"
        "You may also tap the buttons below to choose a topic: Travel, Sports, Interview, or English Skills."
    )
    return TextMessage(text=text)


async def chat_topic_intro_message(sub: int):
    """使用者選擇 Chat 主題（旅遊 / 運動 / 面試 / 英語技巧）後送出的中英文確認訊息。
    Bilingual confirmation message shown after the user picks a chat topic.

    Args:
        sub: 主題索引（0=旅遊 / 1=運動 / 2=面試 / 3=英語技巧）。
             Topic index (0=Travel / 1=Sports / 2=Interview / 3=English Skills).
    """
    eng_label, chi_label = _get_chat_topic_label(sub)
    if not eng_label:
        # 防呆：若 sub 超出範圍，回傳一般提示。
        # Safety fallback: if sub is out of range, return a generic prompt.
        text = (
            "您已進入聊天模式，請傳送語音訊息開始與 AI 對話。\n"
            "You have entered chat mode. Please send a voice message to start chatting with the AI."
        )
        return TextMessage(text=text)

    # 為四個主題客製化中英對照的提示文案。
    # Topic-specific bilingual intro text for the four supported topics.
    TOPIC_TEMPLATES_CHI = {
        0: "您已選擇「旅遊」主題，AI 將與您聊聊有關旅遊的話題，例如旅行經驗、嚮往的目的地或旅遊小撇步。",
        1: "您已選擇「運動」主題，AI 將與您聊聊有關運動的話題，例如喜歡的運動、運動習慣或印象深刻的比賽。",
        2: "您已選擇「面試」主題，AI 將以親切的面試官身份和您進行模擬面試對話，協助您熟悉常見面試問題。",
        3: "您已選擇「英語技巧」主題，AI 將與您討論英語學習相關的技巧，並提供口說、聽力與字彙等方面的實用建議。",
    }
    TOPIC_TEMPLATES_ENG = {
        0: "You have selected the \"Travel\" topic. The AI will chat with you about travel-related subjects, such as travel experiences, dream destinations, or travel tips.",
        1: "You have selected the \"Sports\" topic. The AI will chat with you about sports, including your favorite sports, exercise habits, or memorable matches.",
        2: "You have selected the \"Interview\" topic. The AI will act as a friendly interviewer and run a mock interview to help you practice common interview questions.",
        3: "You have selected the \"English Skills\" topic. The AI will discuss English-learning skills with you and offer practical tips on speaking, listening, and vocabulary.",
    }

    chi_text = TOPIC_TEMPLATES_CHI.get(sub, f"您已選擇「{chi_label}」主題，AI 將圍繞此主題與您對話。")
    eng_text = TOPIC_TEMPLATES_ENG.get(sub, f"You have selected the \"{eng_label}\" topic. The AI will guide the conversation around this topic.")

    text = (
        f"{eng_text}\n"
        f"Please send a voice message to start the conversation.\n"
        f"\n"
        f"{chi_text}\n"
        f"請傳送語音訊息開始對話。"
    )
    return TextMessage(text=text)


# ========== [新增 (SEL 多單元)] SEL 六個單元的設定與單元介紹卡片 ==========
# SEL six-unit configuration and the unit intro card builder.
#
# 設計：每一個 SEL 單元在進入時都會先顯示一張卡片，卡片包含該單元的圖片與雙語說明，
# 使用者了解該單元的桌遊背景後，才從 rich menu 中選擇題目作答。
# 圖片預設放在 /templates/sel/sel{N}.jpg；若圖片缺失則僅顯示文字。
#
# Design: when a user enters a SEL unit, an intro card is shown first. The card carries the
# unit image and the bilingual description, so the user knows which board game context the
# unit is based on before selecting questions. Images default to /templates/sel/sel{N}.jpg;
# if the image is missing, the card renders text-only.

SEL_UNITS_CONFIG = {
    1: {
        "name_eng": "Monopoly",
        "name_chi": "超級瑪利歐地產大亨",
        "image": "/templates/sel/monopoly.jpg",
    },
    2: {
        "name_eng": "The Game of Life",
        "name_chi": "生命之旅",
        "image": "/templates/sel/life_game.jpg",
    },
    3: {
        "name_eng": "FLIP",
        "name_chi": "換言一新",
        "image": "/templates/sel/flip.jpg",
    },
    4: {
        "name_eng": "Balancing Tower Game",
        "name_chi": "瑪利歐驚險塔",
        "image": "/templates/sel/scare_tower.jpg",
    },
    5: {
        "name_eng": "Piranha Plant Escape",
        "name_chi": "瑪利歐食人花遊戲",
        "image": "/templates/sel/eat_flower.png",
    },
    6: {
        "name_eng": "Seven!",
        "name_chi": "Seven!",
        "image": "/templates/sel/seven!.jpg",
    },
}


def get_sel_unit_config(unit_num: int) -> dict:
    """取得指定 SEL 單元的設定（含中英文名稱與圖片網址）。
    Get the SEL unit configuration (bilingual names and image path) for the given unit number.
    """
    return SEL_UNITS_CONFIG.get(unit_num, {})


def get_sel_unit_name(unit_num: int, language: str = 'both') -> str:
    """取得 SEL 單元的中文 / 英文 / 中英對照名稱。
    Get the SEL unit name in English, Traditional Chinese, or both (combined).
    """
    cfg = get_sel_unit_config(unit_num)
    if not cfg:
        return ''
    if language == 'eng':
        return cfg.get('name_eng', '')
    if language == 'chi':
        return cfg.get('name_chi', '')
    return f"{cfg.get('name_eng', '')} / {cfg.get('name_chi', '')}".strip(' /')


async def sel_unit_intro_message(unit_num: int, language: str = 'eng'):
    """進入 SEL 單元時顯示的介紹卡片（依作答語言調整）。
    Intro card shown when the user enters a SEL unit (adapts to answering language).

      - language == 'eng'：維持原本中英對照設計（英文在前、中文在後），鼓勵用英文作答。
      - language == 'chi'：全中文卡片，移除英文內容，說明文字為「試著用中文回答以下問題」。

    Card content:
      - Unit image (if available)
      - Unit name (bilingual in English mode; Chinese-only in Chinese mode)
      - Instruction line:
          * English mode: bilingual (English first, then Chinese).
          * Chinese mode: Chinese only ("試著用中文回答以下問題").
    """
    language = normalize_sel_language(language)
    cfg = get_sel_unit_config(unit_num)
    if not cfg:
        # 防呆：未知單元編號時退回純文字提示。
        # Safety fallback: unknown unit number returns a plain text notice.
        return TextMessage(text=f"Unknown SEL unit / 未知的 SEL 單元: {unit_num}")

    name_eng = cfg.get('name_eng', '')
    name_chi = cfg.get('name_chi', '')
    image_path = cfg.get('image', '')

    if language == 'chi':
        # ===== 中文作答模式：全中文卡片 =====
        intro_chi = (
            f"請依照你在玩「{name_chi}」桌遊時的情形，試著用中文回答以下問題。"
        )
        body_contents = [
            FlexText(
                text=f"SEL 單元 {unit_num}",
                wrap=True,
                weight='bold',
                size='md',
                color='#888888',
                align='center',
            ),
            FlexText(
                text=name_chi if name_chi else f"單元 {unit_num}",
                wrap=True,
                weight='bold',
                size='xl',
                align='center',
                color='#001174',
            ),
            FlexSeparator(margin='md'),
            FlexText(
                text=intro_chi,
                wrap=True,
                size='md',
                color='#333333',
                margin='md',
            ),
            FlexText(
                text="點擊下方題目按鈕開始作答。",
                wrap=True,
                size='sm',
                color='#888888',
                align='center',
                margin='lg',
            ),
        ]
    else:
        # ===== 英文作答模式：維持原本中英對照設計 =====
        intro_eng = (
            f"Please answer the following questions in English based on your experience "
            f"when playing the \"{name_eng}\" board game."
        )
        intro_chi = (
            f"請依照你在玩「{name_chi}」桌遊時的情形，試著用英文回答以下問題。"
        )
        body_contents = [
            FlexText(
                text=f"SEL Unit {unit_num}",
                wrap=True,
                weight='bold',
                size='md',
                color='#888888',
                align='center',
            ),
            FlexText(
                text=name_eng if name_eng else f"Unit {unit_num}",
                wrap=True,
                weight='bold',
                size='xl',
                align='center',
                color='#001174',
            ),
            FlexText(
                text=name_chi if name_chi else '',
                wrap=True,
                weight='bold',
                size='lg',
                align='center',
                color='#001174',
            ),
            FlexSeparator(margin='md'),
            FlexText(
                text=intro_eng,
                wrap=True,
                size='md',
                color='#333333',
                margin='md',
            ),
            FlexText(
                text=intro_chi,
                wrap=True,
                size='md',
                color='#5b5b5b',
                margin='md',
            ),
            FlexText(
                text="Tap a question button below to begin.\n點擊下方題目按鈕開始作答。",
                wrap=True,
                size='sm',
                color='#888888',
                align='center',
                margin='lg',
            ),
        ]

    bubble = FlexBubble(
        size='mega',
        body=FlexBox(
            layout='vertical',
            spacing='sm',
            contents=body_contents,
        ),
    )

    # 若有圖片路徑則加入 hero 區。
    # Add hero image when an image path is configured.
    if image_path:
        # image_path 可能是相對於網站根目錄的路徑（以 / 開頭），也可能是檔名。
        # The image_path may be either a root-relative path (leading "/") or a bare filename.
        if image_path.startswith('http://') or image_path.startswith('https://'):
            full_url = image_path
        elif image_path.startswith('/'):
            full_url = f"{URL}{image_path}"
        else:
            full_url = f"{URL}/templates/sel/{image_path}"
        bubble.hero = FlexImage(
            url=full_url,
            size='full',
            aspect_ratio='20:13',
            aspect_mode='cover',
        )

    return FlexMessage(
        altText=f"SEL Unit {unit_num}: {name_eng}",
        contents=bubble,
    )


async def sel_language_select_message(unit_num: int):
    """[新增 1] 進入 SEL 單元時，先以卡片詢問學生要用中文或英文作答。
    Language-selection card shown when entering a SEL unit: ask the student whether to
    answer in Chinese or English.

    - 「用英文作答 / Answer in English」-> postback action=sel_lang&lang=eng&unit=N
    - 「用中文作答 / Answer in Chinese」 -> postback action=sel_lang&lang=chi&unit=N
    下方以鼓勵文字邀請學生嘗試用英文作答。
    A short encouragement to try English is shown below the buttons.
    """
    name_eng = get_sel_unit_name(unit_num, 'eng')
    name_chi = get_sel_unit_name(unit_num, 'chi')
    title_eng = name_eng if name_eng else f"Unit {unit_num}"

    bubble = FlexBubble(
        size='mega',
        body=FlexBox(
            layout='vertical',
            spacing='md',
            contents=[
                FlexText(
                    text=f"SEL Unit {unit_num}",
                    wrap=True,
                    weight='bold',
                    size='md',
                    color='#888888',
                    align='center',
                ),
                FlexText(
                    text=f"{title_eng}\n{name_chi}".strip(),
                    wrap=True,
                    weight='bold',
                    size='xl',
                    align='center',
                    color='#001174',
                ),
                FlexSeparator(margin='md'),
                FlexText(
                    text="How would you like to answer?\n請問你想用哪一種語言作答？",
                    wrap=True,
                    weight='bold',
                    size='md',
                    align='center',
                    color='#333333',
                    margin='md',
                ),
                FlexText(
                    text=(
                        "Tip: Answering in English is great practice and helps you improve faster!\n"
                        "小提醒：用英文作答能多練習英語、進步更快，鼓勵你挑戰看看！"
                    ),
                    wrap=True,
                    size='sm',
                    color='#888888',
                    align='center',
                    margin='md',
                ),
            ]
        ),
        footer=FlexBox(
            layout='vertical',
            spacing='sm',
            contents=[
                FlexButton(
                    style='primary',
                    color='#00aa00',
                    action=PostbackAction(
                        label='Answer in English / 用英文作答',
                        data=f'action=sel_lang&lang=eng&unit={unit_num}'
                    ),
                ),
                FlexButton(
                    style='primary',
                    color='#0066cc',
                    action=PostbackAction(
                        label='Answer in Chinese / 用中文作答',
                        data=f'action=sel_lang&lang=chi&unit={unit_num}'
                    ),
                ),
            ]
        )
    )

    return FlexMessage(
        altText=f"SEL Unit {unit_num} - Choose answering language / 選擇作答語言",
        contents=bubble,
    )


async def result_message(assessment: SpeechAssessment, category: str, sub: int,
                         show_feedback: bool = None, sel_language: str = None):
    """顯示作答結果。score 卡片永遠顯示；feedback 卡片由 show_feedback 控制。
    若 show_feedback 為 None，退而使用全域 display_feedback 設定。

    SEL 類別特例：
      - 不顯示「建議回答 / Suggested Answer」卡片（避免框架住學生的回應）。
      - sel_language == 'chi' 時不顯示英文回饋卡片（中文作答只給中文回饋）。
    其他類別行為完全不變，維持 service1/2/3 相容。

    Show assessment result. Score card always renders; feedback cards are
    controlled by show_feedback. Falls back to global display_feedback when None.
    SEL special-casing: never show the "Suggested Answer" card; in Chinese mode,
    omit the English feedback card. Other categories are unchanged.
    """
    display_feedback = show_feedback if show_feedback is not None else get_display_feedback()
    _sel = _is_sel_cat(category)
    _chi_only = _sel and normalize_sel_language(sel_language) == 'chi'
    bubbles = []
    
    # Score bubble
    score_bubble = FlexBubble(
        size='mega',
        body=FlexBox(
            layout='vertical',
            justifyContent='center',
            alignItems='center',
            spacing='md',
            contents=[
                FlexText(
                    text=f'Q{sub + 1} Result',
                    wrap=True,
                    weight='bold',
                    size='xl',
                    align='center',
                ),
                FlexText(
                    text=f'Score: {assessment.score}/10',
                    wrap=True,
                    size='xxl',
                    align='center',
                    color='#00aa00' if assessment.score >= 7 else '#ff8800' if assessment.score >= 4 else '#ff0000',
                ),
                FlexText(
                    text=f'Your answer: "{assessment.transcript}"',
                    wrap=True,
                    size='sm',
                    color='#5b5b5b',
                    align='center',
                    style='italic',
                ),
            ]
        )
    )
    bubbles.append(score_bubble)
    
    if display_feedback:
        # English feedback
        if assessment.eng_suggestion and not _chi_only:
            eng_bubble = FlexBubble(
                size='mega',
                body=FlexBox(
                    layout='vertical',
                    spacing='sm',
                    contents=[
                        FlexText(
                            text='Feedback\n回饋',
                            wrap=True,
                            weight='bold',
                            size='lg',
                        ),
                        FlexText(
                            text=assessment.eng_suggestion,
                            wrap=True,
                            size='md',
                            color='#5b5b5b',
                        ),
                    ]
                )
            )
            bubbles.append(eng_bubble)
        
        # Chinese feedback
        if assessment.chi_suggestion:
            chi_bubble = FlexBubble(
                size='mega',
                body=FlexBox(
                    layout='vertical',
                    spacing='sm',
                    contents=[
                        FlexText(
                            text='Feedback\n回饋',
                            wrap=True,
                            weight='bold',
                            size='lg',
                        ),
                        FlexText(
                            text=assessment.chi_suggestion,
                            wrap=True,
                            size='md',
                            color='#5b5b5b',
                        ),
                    ]
                )
            )
            bubbles.append(chi_bubble)
        
        # Better answer
        # SEL 類別不顯示「建議回答」，避免框架住學生的回應；其餘類別維持原行為。
        if assessment.better_ans and not _sel:
            better_bubble = FlexBubble(
                size='mega',
                body=FlexBox(
                    layout='vertical',
                    spacing='sm',
                    contents=[
                        FlexText(
                            text='Suggested Answer\n建議回答',
                            wrap=True,
                            weight='bold',
                            size='lg',
                        ),
                        FlexText(
                            text=assessment.better_ans,
                            wrap=True,
                            size='md',
                            color='#5b5b5b',
                        ),
                    ]
                )
            )
            bubbles.append(better_bubble)
    
    return FlexMessage(
        altText=f'Q{sub + 1} Result',
        contents=FlexCarousel(contents=bubbles)
    )


async def carousel_message(user_id, category, page=0):
    """Generate carousel message for question selection"""
    questions = question_manager.get_unit(category, page)
    if not questions:
        return FlexMessage(
            altText='No questions found',
            contents=FlexBubble(
                body=FlexBox(
                    layout='vertical',
                    contents=[FlexText(text='No questions found for this unit.', wrap=True)]
                )
            )
        )
    
    bubbles = []
    start_idx = page * 10
    
    for i, question in enumerate(questions):
        q_idx = start_idx + i
        history = getHistory(user_id, f'{category}-{q_idx}')
        has_answered = history and len(history) > 0
        last_score = history[-1].score if has_answered else 0
        
        body_contents = [
            FlexText(
                text=f'Q{q_idx + 1}',
                wrap=True,
                weight='bold',
                size='lg',
            ),
            FlexText(
                text=question.text[:100] + ('...' if len(question.text) > 100 else ''),
                wrap=True,
                size='sm',
                color='#5b5b5b',
            ),
        ]
        
        if has_answered:
            body_contents.append(
                FlexText(
                    text=f'Last Score: {last_score}/10',
                    wrap=True,
                    size='sm',
                    color='#00aa00' if last_score >= 7 else '#ff8800' if last_score >= 4 else '#ff0000',
                    margin='md',
                )
            )
        
        bubble = FlexBubble(
            size='kilo',
            body=FlexBox(
                layout='vertical',
                spacing='sm',
                contents=body_contents
            ),
            footer=FlexBox(
                layout='vertical',
                contents=[
                    FlexButton(
                        action=PostbackAction(
                            label='Start' if not has_answered else 'Try Again',
                            data=f'action=record&sub={q_idx}'
                        ),
                        style='primary',
                        height='sm',
                    ),
                ]
            )
        )
        
        if question.image_url:
            bubble.hero = FlexImage(
                url=f'{URL}{question.image_url}',
                size='full',
                aspect_ratio='20:13',
                aspect_mode='cover',
            )
        
        bubbles.append(bubble)
    
    # Add navigation bubble if needed
    all_questions = question_manager.get_all_questions(category)
    total_pages = (len(all_questions) + 9) // 10
    
    if total_pages > 1:
        nav_contents = [
            FlexText(
                text=f'Page {page + 1}/{total_pages}',
                wrap=True,
                size='sm',
                align='center',
            ),
        ]
        
        nav_buttons = []
        if page > 0:
            nav_buttons.append(
                FlexButton(
                    action=PostbackAction(
                        label='Previous',
                        data=f'action=carousel&page={page - 1}'
                    ),
                    style='secondary',
                    height='sm',
                )
            )
        if page < total_pages - 1:
            nav_buttons.append(
                FlexButton(
                    action=PostbackAction(
                        label='Next',
                        data=f'action=carousel&page={page + 1}'
                    ),
                    style='secondary',
                    height='sm',
                )
            )
        
        if nav_buttons:
            nav_bubble = FlexBubble(
                size='kilo',
                body=FlexBox(
                    layout='vertical',
                    spacing='sm',
                    justifyContent='center',
                    contents=nav_contents
                ),
                footer=FlexBox(
                    layout='vertical',
                    spacing='sm',
                    contents=nav_buttons
                )
            )
            bubbles.append(nav_bubble)
    
    return FlexMessage(
        altText=f'{category} Questions',
        contents=FlexCarousel(contents=bubbles)
    )


# ========== [START] Game Message Functions ==========

async def game_prologue_message(theme_id: str):
    """Show theme prologue/backstory with optional intro video"""
    theme_config = load_game_theme_config(theme_id)
    
    if not theme_config:
        return [FlexMessage(
            altText='Topic not found',
            contents=FlexBubble(
                body=FlexBox(
                    layout='vertical',
                    contents=[FlexText(text='Topic configuration not found.', wrap=True)]
                )
            )
        )]
    
    messages = []
    
    # If there's an intro video, add it first
    if theme_config.intro_video:
        video_url = f'{URL}/templates/videos/{theme_config.intro_video}'
        preview_url = f'{URL}/templates/videos/{theme_config.intro_video.replace(".mp4", "_preview.jpg")}'
        messages.append(
            VideoMessage(
                originalContentUrl=video_url,
                previewImageUrl=preview_url
            )
        )
    
    # Build prologue bubble footer BEFORE creating FlexMessage to ensure it always renders
    # Fix #1: footer is fully constructed first, then passed into the bubble constructor
    prologue_footer_contents = [
        FlexButton(
            action=PostbackAction(
                label='Select Level / 進入關卡',
                data=f'action=game_levels&theme={theme_id}'
            ),
            style='primary',
            color='#00aa00',
            height='sm',
        ),
    ]
    
    # Prologue card — footer built above is passed directly into the constructor
    prologue_bubble = FlexBubble(
        size='giga',
        body=FlexBox(
            layout='vertical',
            spacing='lg',
            contents=[
                FlexText(
                    text=theme_config.name,
                    wrap=True,
                    weight='bold',
                    size='xxl',
                ),
                FlexText(
                    text='Story summary',
                    wrap=True,
                    weight='bold',
                    size='lg',
                    color='#1a1a2e',
                ),
                FlexText(
                    text=theme_config.prologue,
                    wrap=True,
                    size='md',
                    color='#5b5b5b',
                ),
                # Hint text for user guidance (bilingual)
                FlexText(
                    text='---',
                    wrap=True,
                    size='xxs',
                    color='#cccccc',
                    align='center',
                    margin='lg',
                ),
                FlexText(
                    text='[Tip] Click "Select Level" below to choose a level, or chat with NPCs in the menu to get clues!',
                    wrap=True,
                    size='xs',
                    color='#888888',
                    margin='sm',
                ),
                FlexText(
                    text='[提示] 點擊下方「進入關卡」選擇關卡，或點選選單中的角色與 NPC 聊天以獲得解謎線索！',
                    wrap=True,
                    size='xs',
                    color='#888888',
                    margin='xs',
                ),
            ]
        ),
        footer=FlexBox(
            layout='vertical',
            contents=prologue_footer_contents
        )
    )
    
    if theme_config.cover_image:
        prologue_bubble.hero = FlexImage(
            url=f'{URL}{theme_config.cover_image}',
            size='full',
            aspect_ratio='20:13',
            aspect_mode='cover',
        )
    
    prologue_msg = FlexMessage(
        altText=f'{theme_config.name} - Story summary',
        contents=prologue_bubble
    )
    
    # QuickReply for novel link (if available)
    if getattr(theme_config, 'novel_url', None):
        prologue_msg.quick_reply = QuickReply(items=[
            QuickReplyItem(action=URIAction(
                label='Novel / 小說全文',
                uri=theme_config.novel_url
            )),
        ])
    
    messages.append(prologue_msg)
    
    return messages

async def game_level_intro_message(theme_id: str, level_idx: int, user_id: str):
    """Show level intro: (1) description card, (2) optional video"""
    level_info = get_game_level_info(theme_id, level_idx)
    
    if not level_info:
        return [FlexMessage(
            altText='Level not found',
            contents=FlexBubble(
                body=FlexBox(
                    layout='vertical',
                    contents=[FlexText(text='Level information not found.', wrap=True)]
                )
            )
        )]
    
    messages = []
    
    # (1) Level description card FIRST
    theme_config = load_game_theme_config(theme_id)
    theme_name = theme_config.name if theme_config else theme_id
    
    level_bubble = FlexBubble(
        size='giga',
        body=FlexBox(
            layout='vertical',
            spacing='lg',
            contents=[
                FlexText(
                    text=f'Topic {get_theme_display_number(theme_id)}, Level {level_idx + 1}: {level_info["title"]}',
                    wrap=True,
                    weight='bold',
                    size='xl',
                ),
                FlexText(
                    text=level_info['description'],
                    wrap=True,
                    size='md',
                    color='#5b5b5b',
                ),
                FlexText(
                    text='---',
                    wrap=True,
                    size='xxs',
                    color='#cccccc',
                    align='center',
                    margin='lg',
                ),
                FlexText(
                    text='[Tip] Click NPC icons in the menu below to chat with NPCs and get clues!(Videos may take a moment to load. If you encounter a black screen, please reopen the video and wait patiently. Thank you!)',
                    wrap=True,
                    size='xs',
                    color='#888888',
                    margin='sm',
                ),
                FlexText(
                    text='[提示] 點擊下方選單中的角色圖示，與 NPC 聊天以獲得解謎線索!(由於影片加載需要時間，因此若影片出現黑屏請重開影片並耐心等候，感謝)',
                    wrap=True,
                    size='xs',
                    color='#888888',
                    margin='xs',
                ),
            ]
        ),
        footer=FlexBox(
            layout='vertical',
            contents=[
                FlexButton(
                    action=PostbackAction(
                        label='Show Questions / 顯示題目',
                        data=f'action=game_questions&theme={theme_id}&level={level_idx}'
                    ),
                    style='primary',
                ),
            ]
        )
    )
    
    try:
        from utils.file_utils import is_level_card_image_enabled, get_level_card_image_path
        if is_level_card_image_enabled():
            level_image_path = get_level_card_image_path(theme_id, level_idx)
            if level_image_path:
                level_bubble.hero = FlexImage(
                    url=f'{URL}{level_image_path}',
                    size='full',
                    aspect_ratio='20:13',
                    aspect_mode='cover',
                )
    except Exception as _img_err:
        # 圖片載入失敗不應阻擋主流程，僅警告。
        # Hero image resolution failure must not block the main flow.
        print(f"[WARN] game_level_intro_message: hero image lookup failed: {_img_err}")
    
    messages.append(FlexMessage(
        altText=f'Level {level_idx + 1}',
        contents=level_bubble
    ))
    
    # (2) Video AFTER description
    if level_info.get('video_file'):
        video_url = f'{URL}/templates/videos/{level_info["video_file"]}'
        preview_url = f'{URL}/templates/videos/{level_info["video_file"].replace(".mp4", "_preview.jpg")}'
        messages.append(
            VideoMessage(
                originalContentUrl=video_url,
                previewImageUrl=preview_url
            )
        )
    
    return messages

async def game_questions_carousel(theme_id: str, level_idx: int, user_id: str, force_show_all: bool = False) -> FlexMessage:
    """Show level questions as scrollable cards
    
    Args:
        theme_id: Theme ID
        level_idx: Level index
        user_id: User ID
        force_show_all: Whether to force show all questions (when user has passed the level)
    """
    from utils.file_utils import (
        is_level_all_questions_passed, get_next_unpassed_question,
        get_min_score_to_pass, is_one_by_one
    )
    
    level_info = get_game_level_info(theme_id, level_idx)
    questions_per_level = get_questions_per_level()
    topic_num = get_theme_display_number(theme_id)
    
    if not level_info:
        return FlexMessage(
            altText='Questions not found',
            contents=FlexBubble(
                body=FlexBox(
                    layout='vertical',
                    contents=[FlexText(text='Level questions not found.', wrap=True)]
                )
            )
        )
    
    bubbles = []
    questions = level_info.get('questions', [])
    
    # Limit to configured questions per level
    questions = questions[:questions_per_level]
    
    # Check if all questions passed
    all_passed = is_level_all_questions_passed(user_id, theme_id, level_idx)
    min_score = get_min_score_to_pass()
    
    # one_by_one=False（開放模式）時，整關所有題目都同時開放自由作答，
    # 因此一律走「顯示全部題目」分支，不再僅顯示目前未通過的單一題目。
    # In open mode (one_by_one=False), every question in the level is available at once,
    # so always take the "show all questions" branch instead of showing only the current one.
    show_all = all_passed or force_show_all or (not is_one_by_one())
    
    # If all passed or force show (or open mode), display all questions for free selection
    if show_all:
        for q_idx, question in enumerate(questions):
            # Check if user has answered this question
            best_score = get_user_question_score(user_id, theme_id, level_idx, q_idx)
            has_answered = best_score > 0
            is_passed = best_score >= min_score
            
            body_contents = [
                FlexText(
                    text=f'Topic {topic_num} Question {level_idx + 1}-{q_idx + 1}\n主題 {topic_num} 題目 {level_idx + 1}-{q_idx + 1}',
                    wrap=True,
                    weight='bold',
                    size='lg',
                    align='center',
                ),
                FlexText(
                    text=question['text'],
                    wrap=True,
                    size='md',
                    color='#5b5b5b',
                    margin='md',
                ),
            ]
            
            if has_answered:
                status_color = '#00aa00' if is_passed else '#ff8800'
                status_text = 'Passed' if is_passed else 'Not Passed'
                status_text_chi = '已通過' if is_passed else '未通過'
                body_contents.append(
                    FlexText(
                        text=f'Best: {best_score}/10 ({status_text}/{status_text_chi})',
                        wrap=True,
                        size='sm',
                        color=status_color,
                        margin='md',
                        align='center',
                    )
                )
            
            if question.get('hint'):
                body_contents.append(
                    FlexText(
                        text=f'Hint: {question["hint"]}',
                        wrap=True,
                        size='sm',
                        color='#888888',
                        margin='sm',
                        style='italic',
                    )
                )
            
            footer_contents = [
                FlexText(
                    text='Click button below\n點擊下方按鈕',
                    wrap=True,
                    size='xs',
                    color='#888888',
                    align='center',
                    margin='sm',
                ),
                FlexButton(
                    action=PostbackAction(
                        label='Answer' if not has_answered else 'Try Again',
                        data=f'action=game_answer&theme={theme_id}&level={level_idx}&question={q_idx}'
                    ),
                    style='primary',
                ),
            ]
            
            bubble = FlexBubble(
                size='mega',
                body=FlexBox(
                    layout='vertical',
                    spacing='md',
                    contents=body_contents
                ),
                footer=FlexBox(
                    layout='vertical',
                    spacing='sm',
                    contents=footer_contents
                )
            )
            bubbles.append(bubble)
    else:
        # Not all passed yet, only show current question to answer
        current_q_idx = get_next_unpassed_question(user_id, theme_id, level_idx)
        if current_q_idx < 0 or current_q_idx >= len(questions):
            current_q_idx = 0
        
        question = questions[current_q_idx]
        best_score = get_user_question_score(user_id, theme_id, level_idx, current_q_idx)
        has_answered = best_score > 0
        
        body_contents = [
            FlexText(
                text=f'Topic {topic_num} Question {level_idx + 1}-{current_q_idx + 1}\n主題 {topic_num} 題目 {level_idx + 1}-{current_q_idx + 1}',
                wrap=True,
                weight='bold',
                size='lg',
                align='center',
            ),
            FlexText(
                text=question['text'],
                wrap=True,
                size='md',
                color='#5b5b5b',
                margin='md',
            ),
        ]
        
        if has_answered:
            is_passed = best_score >= min_score
            status_color = '#00aa00' if is_passed else '#ff8800'
            status_text = 'Passed' if is_passed else 'Try again to pass'
            status_text_chi = '已通過' if is_passed else '再試一次以通過'
            body_contents.append(
                FlexText(
                    text=f'Current: {best_score}/10\n目前分數',
                    wrap=True,
                    size='sm',
                    color=status_color,
                    margin='md',
                    align='center',
                )
            )
            body_contents.append(
                FlexText(
                    text=f'Pass: {min_score}/10 ({status_text}/{status_text_chi})\n及格標準',
                    wrap=True,
                    size='xs',
                    color='#888888',
                    margin='xs',
                    align='center',
                )
            )
        
        if question.get('hint'):
            body_contents.append(
                FlexText(
                    text=f'Hint: {question["hint"]}',
                    wrap=True,
                    size='sm',
                    color='#888888',
                    margin='sm',
                    style='italic',
                )
            )
        
        footer_contents = [
            FlexText(
                text='Click to start\n點擊下方按鈕開始作答',
                wrap=True,
                size='xs',
                color='#888888',
                align='center',
                margin='sm',
            ),
            FlexButton(
                action=PostbackAction(
                    label='Start Answering' if not has_answered else 'Try Again',
                    data=f'action=game_answer&theme={theme_id}&level={level_idx}&question={current_q_idx}'
                ),
                style='primary',
            ),
        ]
        
        bubble = FlexBubble(
            size='mega',
            body=FlexBox(
                layout='vertical',
                spacing='md',
                contents=body_contents
            ),
            footer=FlexBox(
                layout='vertical',
                spacing='sm',
                contents=footer_contents
            )
        )
        bubbles.append(bubble)
        
        # Add progress indicator card
        progress_contents = [
            FlexText(
                text=f'Topic {topic_num} Level Progress\n主題 {topic_num} 關卡進度',
                wrap=True,
                weight='bold',
                size='lg',
                align='center',
            ),
        ]
        
        for q_i in range(len(questions)):
            q_score = get_user_question_score(user_id, theme_id, level_idx, q_i)
            q_passed = q_score >= min_score
            if q_i == current_q_idx:
                status = '>>> Current'
                color = '#0066cc'
            elif q_passed:
                status = f'Passed ({q_score}/10)'
                color = '#00aa00'
            elif q_score > 0:
                status = f'Not Passed ({q_score}/10)'
                color = '#ff8800'
            else:
                status = 'Not Answered'
                color = '#888888'
            
            progress_contents.append(
                FlexText(
                    text=f'T{topic_num} Q{level_idx + 1}-{q_i + 1}: {status}',
                    wrap=True,
                    size='sm',
                    color=color,
                    margin='sm',
                )
            )
        
        progress_bubble = FlexBubble(
            size='mega',
            body=FlexBox(
                layout='vertical',
                spacing='sm',
                contents=progress_contents
            )
        )
        bubbles.append(progress_bubble)
    
    return FlexMessage(
        altText=f'Topic {topic_num}, Level {level_idx + 1} Questions',
        contents=FlexCarousel(contents=bubbles)
    )

async def game_answer_card_message(
    theme_id: str, level_idx: int, question_idx: int,
    q_text: str, has_talked_to_npc: bool = True
) -> FlexMessage:
    """Show a question card with image and hint texts when the user selects a question to answer.

    The hero image is resolved from the ragQuestion template folder using the naming convention:
    topic{X}_Q{Y}-{Z}.jpg  (X = display topic number, Y = level number, Z = question number)

    Two bilingual hint texts are rendered in small gray font inside the card body:
      1. Microphone instruction hint
      2. NPC hint (shown only when has_talked_to_npc is False)
    """
    topic_num = get_theme_display_number(theme_id)
    q_label = f'Topic {topic_num} Q{level_idx + 1}-{question_idx + 1}'
    q_label_chi = f'主題 {topic_num} 題目 {level_idx + 1}-{question_idx + 1}'

    # Image filename follows the convention seen in templates/ragQuestion/
    image_filename = f'topic{topic_num}_Q{level_idx + 1}-{question_idx + 1}.jpg'
    image_url = f'{URL}/templates/ragQuestion/{image_filename}'

    body_contents = [
        FlexText(
            text=f'{q_label} / {q_label_chi}',
            wrap=True,
            weight='bold',
            size='lg',
        ),
    ]

    if q_text:
        body_contents.append(
            FlexText(
                text=q_text,
                wrap=True,
                size='md',
                color='#333333',
                margin='md',
            )
        )

    # Hint 1: microphone recording instruction (bilingual, small gray)
    body_contents.append(
        FlexText(
            text=(
                '請在發送文字訊息的鍵盤位置，點擊麥克風符號錄音並發送語音訊息以作答。'
                '為了獲得高分請盡量用完整句子作答！\n'
                'To answer, tap the microphone icon near the text keyboard to record '
                'and send a voice message. For a higher score, please answer in complete sentences!'
            ),
            wrap=True,
            size='xs',
            color='#888888',
            margin='lg',
        )
    )

    # Hint 2: NPC suggestion hint (bilingual, small gray) — only when NPC not yet visited
    if not has_talked_to_npc:
        body_contents.append(
            FlexText(
                text=(
                    '是不是還不知道答案啊？可以先去選單中點擊角色圖像，向 NPC 詢問案件細節喔！\n'
                    'Not sure about the answer? Try clicking on NPC icons in the menu to ask for clues!'
                ),
                wrap=True,
                size='xs',
                color='#888888',
                margin='sm',
            )
        )

    bubble = FlexBubble(
        size='giga',
        hero=FlexImage(
            url=image_url,
            size='full',
            aspect_ratio='20:13',
            aspect_mode='cover',
        ),
        body=FlexBox(
            layout='vertical',
            spacing='sm',
            contents=body_contents
        )
    )

    alt_text_q = q_text[:40] + '...' if len(q_text) > 40 else q_text
    return FlexMessage(
        altText=f'{q_label}: {alt_text_q}' if q_text else q_label,
        contents=bubble
    )

async def game_score_message(user_id: str, theme_id: str, level_idx: int, question_idx: int, 
                             score: int, is_new_high: bool, feedback_eng: str = "", feedback_chi: str = "",
                             reference_comparison: str = "", show_feedback: bool = None) -> FlexMessage:
    """Show game result and score - English feedback first, Chinese feedback second.
    Score card always renders; feedback cards are controlled by show_feedback.
    Falls back to global display_feedback when show_feedback is None.

    Button logic (passing threshold = min_score_to_pass, read from config):
    - Below threshold: Show "Try Again" + "Improvement Hint"
    - At/above threshold (not perfect): "Try Again" + "Improvement Hint" + "Next Question"
    - Perfect score (10): Show only "Next Question"
    In open mode (one_by_one=False) the "Next Question" button points to the next
    unanswered question across all levels and is always offered when one exists.
    """
    display_feedback = show_feedback if show_feedback is not None else get_display_feedback()
    theme_total = get_user_game_score(user_id, theme_id)
    max_score = get_max_theme_score()
    topic_num = get_theme_display_number(theme_id)
    
    bubbles = []
    
    # Main result card - score always shows
    main_contents = [
        FlexText(
            text=f'Topic {topic_num} Q{level_idx + 1}-{question_idx + 1} Result\n主題 {topic_num} 結果',
            wrap=True,
            weight='bold',
            size='xxl',
            align='center',
        ),
        FlexText(
            text=f'Score: {score}/10\n評分',
            wrap=True,
            size='xl',
            align='center',
            color='#00aa00' if score >= 7 else '#ff8800' if score >= 4 else '#ff0000',
            margin='md',
        ),
    ]
    
    # 當分數未達最低通過分數時，在卡片中顯示最低通過分數規則，避免學生感到疑惑。
    # Show minimum passing score rule when score is below threshold, so students understand why they cannot proceed.
    _min_score = get_min_score_to_pass()
    if score < _min_score:
        main_contents.append(
            FlexText(
                text=f'Minimum passing score: {_min_score}/10\n最低通過分數：{_min_score} 分',
                wrap=True,
                size='sm',
                align='center',
                color='#cc6600',
                margin='sm',
            )
        )
    
    if is_new_high:
        main_contents.append(
            FlexText(
                text='New High Score!\n新高分！',
                wrap=True,
                size='md',
                align='center',
                color='#ff6600',
                margin='sm',
            )
        )
    
    main_contents.append(
        FlexText(
            text=f'Topic Total: {theme_total}/{max_score}\n主題總分',
            wrap=True,
            size='md',
            align='center',
            color='#5b5b5b',
            margin='md',
        )
    )
    
    main_bubble = FlexBubble(
        size='giga',
        body=FlexBox(
            layout='vertical',
            justifyContent='center',
            alignItems='center',
            spacing='sm',
            contents=main_contents
        )
    )
    bubbles.append(main_bubble)
    
    # Only show feedback cards when display_feedback is true and has content
    if display_feedback:
        # English feedback card (show first)
        if feedback_eng and feedback_eng.strip():
            eng_feedback_bubble = FlexBubble(
                size='giga',
                body=FlexBox(
                    layout='vertical',
                    spacing='sm',
                    contents=[
                        FlexText(
                            text='Feedback',
                            wrap=True,
                            weight='bold',
                            size='xl',
                        ),
                        FlexText(
                            text=feedback_eng,
                            wrap=True,
                            size='md',
                            color='#5b5b5b',
                            margin='md',
                        ),
                    ]
                )
            )
            bubbles.append(eng_feedback_bubble)
        
        # Chinese feedback card (show second)
        if feedback_chi and feedback_chi.strip():
            chi_feedback_bubble = FlexBubble(
                size='giga',
                body=FlexBox(
                    layout='vertical',
                    spacing='sm',
                    contents=[
                        FlexText(
                            text='Feedback',
                            wrap=True,
                            weight='bold',
                            size='xl',
                        ),
                        FlexText(
                            text=feedback_chi,
                            wrap=True,
                            size='md',
                            color='#5b5b5b',
                            margin='md',
                        ),
                    ]
                )
            )
            bubbles.append(chi_feedback_bubble)
        
        # Reference comparison (if available)
        if reference_comparison and reference_comparison.strip():
            ref_bubble = FlexBubble(
                size='giga',
                body=FlexBox(
                    layout='vertical',
                    spacing='sm',
                    contents=[
                        FlexText(
                            text='Answer Analysis',
                            wrap=True,
                            weight='bold',
                            size='xl',
                        ),
                        FlexText(
                            text=reference_comparison,
                            wrap=True,
                            size='md',
                            color='#5b5b5b',
                            margin='md',
                        ),
                    ]
                )
            )
            bubbles.append(ref_bubble)
    
    msg = FlexMessage(
        altText=f'Topic {topic_num} Q{level_idx + 1}-{question_idx + 1} Result',
        contents=FlexCarousel(contents=bubbles)
    )
    
    # Quick reply buttons - based on score decide which buttons to show
    # Threshold = min_score_to_pass (from config). Perfect (10) only shows "Next".
    from utils.file_utils import (
        is_level_all_questions_passed, get_next_unpassed_question, get_questions_per_level,
        is_one_by_one, get_next_unanswered_question_global, get_theme_display_number
    )
    min_score = get_min_score_to_pass()
    is_passed = score >= min_score
    is_perfect = score == 10
    all_level_passed = is_level_all_questions_passed(user_id, theme_id, level_idx)
    questions_per_level_count = get_questions_per_level()
    _open_mode = not is_one_by_one()
    
    quick_reply_items = []
    
    # Perfect score (10) - no need for try again or improvement hint
    if not is_perfect:
        # Try Again button
        quick_reply_items.append(
            QuickReplyItem(action=PostbackAction(
                label='Try Again',
                data=f'action=game_answer&theme={theme_id}&level={level_idx}&question={question_idx}'
            ))
        )
        
        # Improvement Hint button (not perfect, can use)
        quick_reply_items.append(
            QuickReplyItem(action=PostbackAction(
                label='Improvement Hint',
                data=f'action=game_improvement_hint&theme={theme_id}&level={level_idx}&question={question_idx}'
            ))
        )
    
    if _open_mode:
        # 開放模式：「下一題」跳到跨關卡的下一個未通過題目，且一律提供（不需先通過本題）。
        # Open mode: "Next" jumps to the next unpassed question across all levels and is
        # always offered, regardless of whether the current question was passed.
        nxt_level, nxt_q = get_next_unanswered_question_global(user_id, theme_id)
        if nxt_level >= 0 and nxt_q >= 0:
            t_num = get_theme_display_number(theme_id)
            quick_reply_items.append(
                QuickReplyItem(action=PostbackAction(
                    label=f'Next (Q{nxt_level + 1}-{nxt_q + 1})',
                    data=f'action=game_answer&theme={theme_id}&level={nxt_level}&question={nxt_q}'
                ))
            )
        else:
            # 全部題目皆已通過：提供回關卡選單的入口。
            # All questions passed: offer a way back to the level menu.
            quick_reply_items.append(
                QuickReplyItem(action=PostbackAction(
                    label='All Done / 全部完成',
                    data=f'action=game_levels&theme={theme_id}'
                ))
            )
    else:
        # 逐題模式：通過本題後才顯示「下一題」(同一關內的下一個未通過題目)。
        # Sequential mode: only show "Next" after passing the current question.
        if is_passed:
            next_q_idx = get_next_unpassed_question(user_id, theme_id, level_idx)
            if next_q_idx >= 0 and next_q_idx < questions_per_level_count:
                quick_reply_items.append(
                    QuickReplyItem(action=PostbackAction(
                        label=f'Next (Q{next_q_idx + 1})',
                        data=f'action=game_answer&theme={theme_id}&level={level_idx}&question={next_q_idx}'
                    ))
                )
            elif all_level_passed:
                # Level all passed
                quick_reply_items.append(
                    QuickReplyItem(action=PostbackAction(
                        label='Level Completed!',
                        data=f'action=game_levels&theme={theme_id}'
                    ))
                )
    
    if quick_reply_items:
        msg.quick_reply = QuickReply(items=quick_reply_items)
    
    return msg

async def game_improvement_hint_message(theme_id: str, level_idx: int, question_idx: int,
                                         hint_eng: str, hint_chi: str, hint_count: int = 1) -> FlexMessage:
    """Show improvement hint message (without revealing answer)
    
    Args:
        theme_id: Theme ID
        level_idx: Level index
        question_idx: Question index
        hint_eng: English hint
        hint_chi: Chinese hint
        hint_count: Number of times hints have been used for this question
    """
    bubbles = []
    
    # English hint card
    eng_bubble = FlexBubble(
        size='giga',
        body=FlexBox(
            layout='vertical',
            spacing='sm',
            contents=[
                FlexText(
                    text=f'Improvement Hint (#{hint_count})',
                    wrap=True,
                    weight='bold',
                    size='xl',
                    color='#0066cc',
                ),
                FlexText(
                    text=hint_eng if hint_eng else "No hint available.",
                    wrap=True,
                    size='md',
                    color='#5b5b5b',
                    margin='md',
                ),
            ]
        )
    )
    bubbles.append(eng_bubble)
    
    # Chinese hint card
    chi_bubble = FlexBubble(
        size='giga',
        body=FlexBox(
            layout='vertical',
            spacing='sm',
            contents=[
                FlexText(
                    text=f'Improvement Hint (#{hint_count})',
                    wrap=True,
                    weight='bold',
                    size='xl',
                    color='#0066cc',
                ),
                FlexText(
                    text=hint_chi if hint_chi else "No hint available.",
                    wrap=True,
                    size='md',
                    color='#5b5b5b',
                    margin='md',
                ),
            ]
        )
    )
    bubbles.append(chi_bubble)
    
    # If no hint content at all
    if not hint_eng and not hint_chi:
        bubbles = [
            FlexBubble(
                size='giga',
                body=FlexBox(
                    layout='vertical',
                    justifyContent='center',
                    alignItems='center',
                    contents=[
                        FlexText(
                            text='No hints available\n暫無改善提示',
                            wrap=True,
                            align='center',
                        )
                    ]
                )
            )
        ]

    msg = FlexMessage(
        altText=f'Q{level_idx + 1}-{question_idx + 1} Improvement Hint',
        contents=FlexCarousel(contents=bubbles)
    )
    
    # Quick reply button - only Try Again (removed Question List button)
    msg.quick_reply = QuickReply(items=[
        QuickReplyItem(action=PostbackAction(
            label='Try Again',
            data=f'action=game_answer&theme={theme_id}&level={level_idx}&question={question_idx}'
        )),
    ])
    
    return msg

async def game_npc_chat_response_message(npc_name: str, npc_reply: str, 
                                          is_english: bool = True,
                                          npc_image: str = None) -> FlexMessage:
    """Show NPC quick response (immediate display), with random character image
    
    Args:
        npc_name: NPC name
        npc_reply: NPC response content
        is_english: Whether user used English
        npc_image: NPC base image filename (e.g. John_Watson.jpg), will randomly select _1, _2, _3 variant
    """
    import random
    
    bubbles = []
    
    # Language warning card (if not English)
    if not is_english:
        warning_bubble = FlexBubble(
            size='giga',
            body=FlexBox(
                layout='vertical',
                spacing='md',
                justifyContent='center',
                alignItems='center',
                contents=[
                    FlexText(
                        text='Please speak in English\n請使用英文對話',
                        wrap=True,
                        weight='bold',
                        size='lg',
                        align='center',
                        color='#ff6600',
                    ),
                ]
            )
        )
        bubbles.append(warning_bubble)
    
    # NPC reply card
    reply_contents = [
        FlexText(
            text=f'{npc_name} says:',
            wrap=True,
            weight='bold',
            size='lg',
            color='#1a1a2e',
        ),
        FlexText(
            text=npc_reply if npc_reply else "...",
            wrap=True,
            size='md',
            color='#5b5b5b',
            margin='md',
        ),
    ]
    
    reply_bubble = FlexBubble(
        size='giga',
        body=FlexBox(
            layout='vertical',
            spacing='sm',
            contents=reply_contents
        )
    )
    
    # If there's NPC image, randomly select variant and add to reply card
    if npc_image:
        # Extract name part from image filename (remove .jpg etc)
        base_name = npc_image.rsplit('.', 1)[0] if '.' in npc_image else npc_image
        ext = npc_image.rsplit('.', 1)[1] if '.' in npc_image else 'jpg'
        
        # Randomly select _1, _2, _3 variant
        variant = random.choice([1, 2, 3])
        random_image = f'{base_name}_{variant}.{ext}'
        
        reply_bubble.hero = FlexImage(
            url=f'{URL}/templates/people_pic/{random_image}',
            size='full',
            aspect_ratio='3:4',
            aspect_mode='cover',
        )
    
    bubbles.append(reply_bubble)
    
    msg = FlexMessage(
        altText=f'{npc_name} Response',
        contents=FlexCarousel(contents=bubbles)
    )
    
    # [Fix #4] Add hint: if user has enough clues, go to answer
    msg.quick_reply = QuickReply(items=[
        QuickReplyItem(action=PostbackAction(
            label='Go to Answer / 前往作答',
            data='action=game_current_questions'
        )),
    ])
    
    return msg

async def game_npc_evaluation_message(npc_name: str, language_score: int, 
                                      relevance_score: int, feedback_eng: str, 
                                      feedback_chi: str) -> FlexMessage:
    """Show NPC chat evaluation (sent asynchronously)"""
    display_feedback = get_display_feedback()
    
    if not display_feedback:
        return None
    
    bubbles = []
    
    # Score card
    score_contents = [
        FlexText(
            text='Score',
            wrap=True,
            weight='bold',
            size='xl',
            color='#1a1a2e',
        ),
        FlexText(
            text=f'Language: {language_score}/10',
            wrap=True,
            size='md',
            color='#00aa00' if language_score >= 7 else '#ff8800' if language_score >= 5 else '#ff0000',
            margin='md',
        ),
        FlexText(
            text=f'Relevance: {relevance_score}/10',
            wrap=True,
            size='md',
            color='#00aa00' if relevance_score >= 7 else '#ff8800' if relevance_score >= 5 else '#ff0000',
            margin='sm',
        ),
    ]
    
    # If there's feedback, add bilingual comparison
    if feedback_eng and feedback_eng.strip():
        score_contents.append(
            FlexText(
                text='',
                margin='lg',
            )
        )
        score_contents.append(
            FlexText(
                text='Feedback',
                wrap=True,
                weight='bold',
                size='md',
                color='#1a1a2e',
            )
        )
        score_contents.append(
            FlexText(
                text=f'{feedback_eng}',
                wrap=True,
                size='sm',
                color='#5b5b5b',
                margin='sm',
            )
        )
        if feedback_chi and feedback_chi.strip():
            score_contents.append(
                FlexText(
                    text=f'{feedback_chi}',
                    wrap=True,
                    size='sm',
                    color='#5b5b5b',
                    margin='xs',
                )
            )
    
    score_bubble = FlexBubble(
        size='giga',
        body=FlexBox(
            layout='vertical',
            spacing='sm',
            contents=score_contents
        )
    )
    bubbles.append(score_bubble)
    
    return FlexMessage(
        altText=f'{npc_name} Chat Evaluation',
        contents=FlexCarousel(contents=bubbles)
    )

async def game_rules_instruction_message() -> FlexMessage:
    """Show game rules instruction card (bilingual).
    Used when user presses the Game Rules button in the game lobby menu.

    規則文字中的主題數、關卡數、每關題數、最低通過分數，以及「逐關解鎖 / 自由作答」
    的說明，全部依 config 動態產生。只要管理員更動 game_themes / levels_per_theme /
    questions_per_level / min_score_to_pass / one_by_one，這張卡片的描述就會自動連動更新。
    """
    from utils.file_utils import (
        get_game_themes, get_levels_per_theme, get_questions_per_level,
        get_min_score_to_pass, is_one_by_one
    )
    num_themes = len(get_game_themes())
    num_levels = get_levels_per_theme()
    num_questions = get_questions_per_level()
    min_pass = get_min_score_to_pass()
    open_mode = not is_one_by_one()

    # 依作答模式產生不同的進度說明（逐關解鎖 vs 自由作答）。
    # Progression sentence differs by mode (sequential unlock vs free answering).
    if open_mode:
        progress_eng = (
            f"All levels and questions are open from the start, so you can answer in any order you like. "
            f"A question counts as passed once you score at least {min_pass} out of 10. "
        )
        progress_chi = (
            f"所有關卡與題目一開始就全部開放，你可以依自己喜歡的順序作答。"
            f"每題只要達到 {min_pass} 分（滿分 10 分）即視為通過。"
        )
    else:
        progress_eng = (
            f"Answer the questions level by level: pass the current question (score at least "
            f"{min_pass} out of 10) to move on, and clear a level to unlock the next one. "
        )
        progress_chi = (
            f"請逐關作答：每題達到 {min_pass} 分（滿分 10 分）即可通過並前往下一題，"
            f"通關後即可解鎖下一關。"
        )

    rules_eng = (
        "Welcome to the Mystery Game! "
        "In this scenario-based puzzle game, you will play the role of a detective assistant, "
        "asking NPC characters about case details to solve a series of riddles. "
        "Each NPC knows different information -- if you cannot find the answer, "
        "try asking a different character! "
        f"There are {num_themes} topics in total, each with {num_levels} levels, "
        f"and each level has {num_questions} small puzzles. "
        f"{progress_eng}"
        "Don't be intimidated by the number of questions -- the game will provide sufficient "
        "clues and guidance to help you progress. Enjoy the game!"
    )
    rules_chi = (
        "歡迎來到情境解謎遊戲！"
        "在這個情境式解謎遊戲中，你將扮演偵探助手的角色，"
        "向 NPC 角色詢問案件細節以破解一道道謎題。"
        "每位 NPC 人物知道的資訊都不同，如果問不出答案不妨換個人問問看喔！"
        f"此遊戲總共有 {num_themes} 個主題，每個主題有 {num_levels} 道關卡，"
        f"每個關卡又有 {num_questions} 個小謎題。"
        f"{progress_chi}"
        "請不要被題目數量嚇到，遊戲中一定會提供足夠的線索和引導協助你破關。請享受遊戲吧！"
    )
    
    bubble = FlexBubble(
        size='giga',
        body=FlexBox(
            layout='vertical',
            spacing='lg',
            contents=[
                FlexText(
                    text='Game Rules\n遊戲規則',
                    wrap=True,
                    weight='bold',
                    size='xxl',
                    align='center',
                    color='#1a1a2e',
                ),
                FlexText(
                    text=rules_eng,
                    wrap=True,
                    size='md',
                    color='#5b5b5b',
                    margin='lg',
                ),
                FlexText(
                    text='---',
                    wrap=True,
                    size='xxs',
                    color='#cccccc',
                    align='center',
                    margin='lg',
                ),
                FlexText(
                    text=rules_chi,
                    wrap=True,
                    size='md',
                    color='#5b5b5b',
                    margin='sm',
                ),
            ]
        )
    )
    
    msg = FlexMessage(
        altText='Game Rules / 遊戲規則',
        contents=bubble
    )
    
    # Quick reply: guide user to next item (story)
    msg.quick_reply = QuickReply(items=[
        QuickReplyItem(action=PostbackAction(
            label='Story / 故事背景',
            data='action=game_info&section=story'
        )),
    ])
    
    return msg


async def game_story_message() -> FlexMessage:
    """Show game story / backstory card (bilingual).
    Used when user presses the Story button in the game lobby menu.
    """
    game_info = get_game_info_config()
    story_eng = game_info.get('story_eng', '')
    story_chi = game_info.get('story_chi', '')
    
    if not story_eng and not story_chi:
        story_eng = (
            "In a world where mystery lurks in every corner of London, "
            "three brilliant minds stand ready to help you solve the case."
        )
        story_chi = (
            "在倫敦每個角落都潛藏謎團的世界中，"
            "三位傑出的人物隨時準備好協助你破解案件。"
        )
    
    # ===== [Change 1] Map image: displayed above the story text.
    # The image is placed in the bubble hero so it always appears at the top.
    # Path: templates/map/map.jpg (served via the static files route).
    # To disable this image, set MAP_IMAGE_ENABLED to False.
    # ===== 地圖圖片：顯示於故事背景文字上方。
    # 圖片放在 bubble hero 使其永遠出現在最上方。
    # 路徑：templates/map/map.jpg（透過靜態檔案路由提供）。
    # 若要停用此圖片，請將 MAP_IMAGE_ENABLED 設為 False。
    MAP_IMAGE_ENABLED = True
    MAP_IMAGE_PATH = '/templates/map/map.jpg'

    hero_image = (
        FlexImage(
            url=f'{URL}{MAP_IMAGE_PATH}',
            size='full',
            aspect_ratio='20:13',
            aspect_mode='fit',
        )
        if MAP_IMAGE_ENABLED
        else None
    )

    bubble = FlexBubble(
        size='giga',
        hero=hero_image,
        body=FlexBox(
            layout='vertical',
            spacing='lg',
            contents=[
                FlexText(
                    text='Story setting / 故事背景',
                    wrap=True,
                    weight='bold',
                    size='xxl',
                    align='center',
                    color='#1a1a2e',
                ),
                FlexText(
                    text=story_eng,
                    wrap=True,
                    size='md',
                    color='#5b5b5b',
                    margin='lg',
                ),
                FlexText(
                    text='---',
                    wrap=True,
                    size='xxs',
                    color='#cccccc',
                    align='center',
                    margin='lg',
                ),
                FlexText(
                    text=story_chi,
                    wrap=True,
                    size='md',
                    color='#5b5b5b',
                    margin='sm',
                ),
            ]
        )
    )

    msg = FlexMessage(
        altText='Story / 故事背景',
        contents=bubble
    )
    
    # Quick reply: guide user to next item (characters)
    msg.quick_reply = QuickReply(items=[
        QuickReplyItem(action=PostbackAction(
            label='Game Rules / 遊戲規則',
            data='action=game_info&section=rules'
        )),
        QuickReplyItem(action=PostbackAction(
            label='Characters / 人物介紹',
            data='action=game_info&section=characters'
        )),
    ])
    
    return msg


async def game_characters_message() -> list:
    """Show game characters intro video.
    Used when user presses the Characters button in the game lobby menu.
    Returns a list of messages (video + optional text fallback).
    
    Path handling for game_characters_video config:
    - If the value starts with '/' it is treated as a URL path relative to the site root,
      e.g. '/templates/videos/characters_intro.mp4'  ->  {URL}/templates/videos/characters_intro.mp4
    - If the value does NOT start with '/' it is treated as a bare filename inside
      /templates/videos/, e.g. 'characters_intro.mp4'  ->  {URL}/templates/videos/characters_intro.mp4
    Either format works; just be consistent.  Example values:
      'game_characters_video': 'characters_intro.mp4'
      'game_characters_video': '/templates/videos/characters_intro.mp4'
    """
    game_info = get_game_info_config()
    video_value = game_info.get('characters_video', '')
    
    messages = []
    
    if video_value:
        # Normalise path: if it already starts with '/' use it directly,
        # otherwise treat it as a bare filename inside /templates/videos/
        if video_value.startswith('/'):
            video_url = f'{URL}{video_value}'
            preview_url = f'{URL}{video_value.replace(".mp4", "_preview.jpg")}'
        else:
            video_url = f'{URL}/templates/videos/{video_value}'
            preview_url = f'{URL}/templates/videos/{video_value.replace(".mp4", "_preview.jpg")}'
        
        messages.append(
            TextMessage(
                text=(
                    "由於影片加載需要時間，因此若影片出現黑屏請重開影片並耐心等候，感謝！\n"
                    "Videos may take a moment to load. If you encounter a black screen, please reopen the video and wait patiently. Thank you!"
                )
            )
        )

        messages.append(
            VideoMessage(
                originalContentUrl=video_url,
                previewImageUrl=preview_url
            )
        )
    else:
        # Fallback text card if no video configured
        fallback_bubble = FlexBubble(
            size='giga',
            body=FlexBox(
                layout='vertical',
                spacing='lg',
                contents=[
                    FlexText(
                        text='Characters / 人物介紹',
                        wrap=True,
                        weight='bold',
                        size='xxl',
                        align='center',
                        color='#1a1a2e',
                    ),
                    FlexText(
                        text='Character introduction video is not yet available.\n人物介紹影片尚未設定。',
                        wrap=True,
                        size='md',
                        color='#888888',
                        margin='lg',
                        align='center',
                    ),
                ]
            )
        )
        fallback_msg = FlexMessage(
            altText='Characters / 人物介紹',
            contents=fallback_bubble
        )
        # Quick reply: guide user
        fallback_msg.quick_reply = QuickReply(items=[
            QuickReplyItem(action=PostbackAction(
                label='Game Rules / 遊戲規則',
                data='action=game_info&section=rules'
            )),
            QuickReplyItem(action=PostbackAction(
                label='Structure / 題目架構',
                data='action=game_info&section=structure'
            )),
        ])
        messages.append(fallback_msg)
    
    return messages


async def game_structure_message() -> FlexMessage:
    """Show game structure image.
    Used when user presses the Structure button in the game lobby menu.
    Uses aspect_mode='fit' so the full image is always visible without cropping.
    """
    game_info = get_game_info_config()
    structure_image = game_info.get('structure_image', '')
    
    if structure_image:
        # Normalise: if already a full path (starts with '/') use directly,
        # otherwise treat as bare filename inside /templates/
        if structure_image.startswith('/'):
            img_url = f'{URL}{structure_image}'
        else:
            img_url = f'{URL}/templates/{structure_image}'
        
        bubble = FlexBubble(
            size='giga',
            hero=FlexImage(
                url=img_url,
                size='full',
                aspect_ratio='1:1',
                aspect_mode='fit',
            ),
            body=FlexBox(
                layout='vertical',
                spacing='sm',
                contents=[
                    FlexText(
                        text='Question Structure / 題目架構',
                        wrap=True,
                        weight='bold',
                        size='lg',
                        align='center',
                    ),
                ]
            )
        )
    else:
        # Fallback if no image configured
        bubble = FlexBubble(
            size='giga',
            body=FlexBox(
                layout='vertical',
                spacing='lg',
                contents=[
                    FlexText(
                        text='Question Structure / 題目架構',
                        wrap=True,
                        weight='bold',
                        size='xxl',
                        align='center',
                        color='#1a1a2e',
                    ),
                    FlexText(
                        text='Question structure image is not yet available.\n題目架構圖片尚未設定。',
                        wrap=True,
                        size='md',
                        color='#888888',
                        margin='lg',
                        align='center',
                    ),
                ]
            )
        )
    
    msg = FlexMessage(
        altText='Question Structure / 題目架構',
        contents=bubble
    )
    
    # Quick reply: guide user to select topic
    msg.quick_reply = QuickReply(items=[
        QuickReplyItem(action=PostbackAction(
            label='Select Topic / 選擇主題',
            data='action=game_show_themes'
        )),
    ])
    
    return msg

async def game_theme_select_message() -> FlexMessage:
    """Show theme selection cards.
    Called when user presses 'Select Theme' from the game lobby or game_theme_select menu.
    """
    from utils.file_utils import get_game_themes
    
    themes = get_game_themes()
    bubbles = []
    
    for idx, theme_id in enumerate(themes):
        theme_config = load_game_theme_config(theme_id)
        
        if theme_config:
            theme_name = theme_config.name
            cover_image = theme_config.cover_image
        else:
            theme_name = f'Topic {idx + 1}'
            cover_image = None
        
        body = FlexBox(
            layout='vertical',
            spacing='lg',
            justifyContent='center',
            alignItems='center',
            contents=[
                FlexText(
                    text=f'Topic {idx + 1}',
                    wrap=True,
                    weight='bold',
                    size='sm',
                    color='#888888',
                    align='center',
                ),
                FlexText(
                    text=theme_name,
                    wrap=True,
                    weight='bold',
                    size='xl',
                    align='center',
                ),
                FlexText(
                    text='Click button below',
                    wrap=True,
                    size='xs',
                    color='#888888',
                    align='center',
                    margin='sm',
                ),
                FlexButton(
                    action=PostbackAction(
                        label=f'Enter Topic {idx + 1}',
                        data=f'action=game_theme&theme={theme_id}'
                    ),
                    style='primary',
                ),
            ]
        )
        
        bubble = FlexBubble(
            size='mega',
            body=body
        )
        
        if cover_image:
            bubble.hero = FlexImage(
                url=f'{URL}{cover_image}',
                size='full',
                aspect_ratio='20:13',
                aspect_mode='cover',
            )
        
        bubbles.append(bubble)
    
    msg = FlexMessage(
        altText='Select Topic',
        contents=FlexCarousel(contents=bubbles)
    )
    
    # Quick reply to guide back to game structure info
    msg.quick_reply = QuickReply(items=[
        QuickReplyItem(action=PostbackAction(
            label='Structure / 題目架構',
            data='action=game_info&section=structure'
        )),
    ])
    
    return msg

async def game_npc_select_message(theme_id: str, user_id: str) -> FlexMessage:
    """Show NPC selection interface - with images and descriptions"""
    print(f"[DEBUG] game_npc_select_message called with theme_id={theme_id}, user_id={user_id}")
    
    theme_config = load_game_theme_config(theme_id)
    
    if not theme_config:
        print(f"[WARNING] Theme config not found in game_npc_select_message for theme_id={theme_id}")
        return FlexMessage(
            altText='Topic not found',
            contents=FlexBubble(
                body=FlexBox(
                    layout='vertical',
                    contents=[
                        FlexText(text='Topic config not found.', wrap=True),
                        FlexText(
                            text=f'Topic ID: {theme_id}',
                            wrap=True,
                            size='sm',
                            color='#888888',
                            margin='md'
                        )
                    ]
                )
            )
        )
    
    print(f"[DEBUG] Theme config loaded: name={theme_config.name}, npcs={len(theme_config.npcs)}")
    
    # Get user progress
    progress = get_user_game_progress(user_id, theme_id)
    
    bubbles = []
    
    # Progress card
    progress_bubble = FlexBubble(
        size='mega',
        body=FlexBox(
            layout='vertical',
            spacing='md',
            contents=[
                FlexText(
                    text=theme_config.name,
                    wrap=True,
                    weight='bold',
                    size='xl',
                    align='center',
                ),
                FlexText(
                    text=f"Score: {progress['total_score']}/{progress['max_score']}",
                    wrap=True,
                    size='lg',
                    align='center',
                    color='#00aa00',
                ),
                FlexText(
                    text=f"Current Level: {progress['current_level'] + 1}",
                    wrap=True,
                    size='md',
                    align='center',
                    color='#5b5b5b',
                ),
            ]
        )
    )
    bubbles.append(progress_bubble)
    
    # NPC selection cards - with images and descriptions
    for npc_idx, npc in enumerate(theme_config.npcs):
        print(f"[DEBUG] Processing NPC {npc_idx}: name={npc.name}, has_description={bool(npc.description)}")
        
        body_contents = [
            FlexText(
                text=npc.name,
                wrap=True,
                weight='bold',
                size='lg',
                align='center',
            ),
        ]
        
        # Add NPC description if available
        if npc.description:
            body_contents.append(
                FlexText(
                    text=npc.description,
                    wrap=True,
                    size='sm',
                    color='#5b5b5b',
                    margin='md',
                )
            )
        
        bubble = FlexBubble(
            size='mega',
            body=FlexBox(
                layout='vertical',
                spacing='md',
                contents=body_contents
            ),
            footer=FlexBox(
                layout='vertical',
                contents=[
                    FlexButton(
                        action=PostbackAction(
                            label='Chat',
                            data=f'action=game_npc&theme={theme_id}&npc={npc_idx}'
                        ),
                        style='primary',
                    ),
                ]
            )
        )
        
        # Add NPC image if available
        if npc.image:
            bubble.hero = FlexImage(
                url=f'{URL}/templates/people_pic/{npc.image}',
                size='full',
                aspect_ratio='3:4',
                aspect_mode='cover',
            )
        
        bubbles.append(bubble)
    
    return FlexMessage(
        altText=f'{theme_config.name} - Select NPC',
        contents=FlexCarousel(contents=bubbles)
    )

async def game_npc_card_message(theme_id: str, npc_idx: int) -> FlexMessage:
    """Show NPC card with introduction and chat prompt"""
    from utils.file_utils import get_game_npc_info
    
    npc_info = get_game_npc_info(theme_id, npc_idx)
    
    if not npc_info:
        return FlexMessage(
            altText='NPC not found',
            contents=FlexBubble(
                body=FlexBox(
                    layout='vertical',
                    contents=[FlexText(text='NPC information not found.', wrap=True)]
                )
            )
        )
    
    body_contents = [
        FlexText(
            text=npc_info['name'],
            wrap=True,
            weight='bold',
            size='xl',
            align='center',
        ),
    ]
    
    # Add description if available
    if npc_info.get('description'):
        body_contents.append(
            FlexText(
                text=npc_info['description'],
                wrap=True,
                size='md',
                color='#5b5b5b',
                margin='md',
            )
        )
    
    # Add background if available
    if npc_info.get('background'):
        body_contents.append(
            FlexText(
                text=npc_info['background'],
                wrap=True,
                size='sm',
                color='#888888',
                margin='sm',
                style='italic',
            )
        )
    
    # Add instruction
    body_contents.append(
        FlexText(
            text='Send a voice message to chat!',
            wrap=True,
            size='md',
            color='#0066cc',
            margin='lg',
            align='center',
        )
    )
    
    bubble = FlexBubble(
        size='mega',
        body=FlexBox(
            layout='vertical',
            spacing='md',
            contents=body_contents
        )
    )
    
    # Add NPC image if available
    if npc_info.get('image'):
        bubble.hero = FlexImage(
            url=f'{URL}/templates/people_pic/{npc_info["image"]}',
            size='full',
            aspect_ratio='3:4',
            aspect_mode='cover',
        )
    
    return FlexMessage(
        altText=f'{npc_info["name"]} - Chat',
        contents=bubble
    )

async def game_level_select_message(theme_id: str, user_id: str) -> FlexMessage:
    """Show level selection cards"""
    theme_config = load_game_theme_config(theme_id)
    
    if not theme_config:
        return FlexMessage(
            altText='Topic not found',
            contents=FlexBubble(
                body=FlexBox(
                    layout='vertical',
                    contents=[FlexText(text='Topic configuration not found.', wrap=True)]
                )
            )
        )
    
    unlocked_level = get_user_unlocked_level(user_id, theme_id)
    # one_by_one=False（開放模式）時，所有關卡都開放、不鎖定。
    # In open mode (one_by_one=False) every level is available and none is locked.
    _open_mode = not is_one_by_one()
    bubbles = []
    
    for level in theme_config.levels:
        # 開放模式下不鎖定任何關卡；逐關模式維持「高於已解鎖關卡即鎖定」。
        # In open mode no level is locked; in sequential mode lock levels above the unlocked one.
        is_locked = (level.id > unlocked_level) and (not _open_mode)
        
        if is_locked:
            continue  # Don't show locked levels
        
        # Get level score
        level_score = get_user_level_score(user_id, theme_id, level.id)
        max_level_score = get_questions_per_level() * 10
        # 及格門檻改用動態 min_score_to_pass，移除硬編碼的 6。
        # Use dynamic min_score_to_pass instead of the hardcoded 6.
        is_completed = level_score >= get_questions_per_level() * get_min_score_to_pass()  # All questions passed
        
        body_contents = [
            FlexText(
                text=f'Level {level.id + 1}',
                wrap=True,
                weight='bold',
                size='xl',
                align='center',
            ),
            FlexText(
                text=level.title,
                wrap=True,
                size='lg',
                color='#1a1a2e',
                align='center',
            ),
            FlexText(
                text=f'Score: {level_score}/{max_level_score}',
                wrap=True,
                size='sm',
                align='center',
                color='#00aa00' if is_completed else '#ff8800',
                margin='sm',
            )
        ]
        
        if is_completed:
            body_contents.append(
                FlexText(
                    text='Completed',
                    wrap=True,
                    size='sm',
                    align='center',
                    color='#00aa00',
                )
            )
        
        bubble = FlexBubble(
            size='mega',
            body=FlexBox(
                layout='vertical',
                spacing='md',
                justifyContent='center',
                alignItems='center',
                contents=body_contents
            ),
            footer=FlexBox(
                layout='vertical',
                contents=[
                    FlexText(
                        text='Click button below',
                        wrap=True,
                        size='xs',
                        color='#888888',
                        align='center',
                        margin='sm',
                    ),
                    FlexButton(
                        action=PostbackAction(
                            label=f'Enter Level {level.id + 1}',
                            data=f'action=game_level&theme={theme_id}&level={level.id}'
                        ),
                        style='primary',
                    ),
                ]
            )
        )
        bubbles.append(bubble)
    
    # If there are still locked levels, show a hint (only in sequential one-by-one mode)
    # 開放模式下沒有鎖定關卡，不顯示此提示。
    if (not _open_mode) and unlocked_level < len(theme_config.levels) - 1:
        locked_bubble = FlexBubble(
            size='mega',
            body=FlexBox(
                layout='vertical',
                spacing='md',
                justifyContent='center',
                alignItems='center',
                contents=[
                    FlexText(
                        text='🔒Locked',
                        size='xxl',
                        align='center',
                    ),
                    FlexText(
                        text=f'{len(theme_config.levels) - unlocked_level - 1} remaining levels locked',
                        wrap=True,
                        size='md',
                        align='center',
                        color='#888888',
                    ),
                    FlexText(
                        text='Complete current level to unlock\n完成當前關卡即可解鎖',
                        wrap=True,
                        size='sm',
                        align='center',
                        color='#888888',
                    ),
                ]
            )
        )
        bubbles.append(locked_bubble)
    
    return FlexMessage(
        altText=f'{theme_config.name} - Select Level',
        contents=FlexCarousel(contents=bubbles)
    )

async def game_current_questions_message(theme_id: str, user_id: str) -> FlexMessage:
    """Show current level questions (for menu's "Show Questions" button)"""
    current_level = get_user_unlocked_level(user_id, theme_id)
    return await game_questions_carousel(theme_id, current_level, user_id)

async def progress_select_message() -> FlexMessage:
    """Show progress category selection (for service4 menu_game)"""
    categories = [
        ("Pretest\n前測", "action=progress_detail&category=pretest"),
        ("Game\n遊戲", "action=progress_detail&category=game"),
        ("Posttest\n後測", "action=progress_detail&category=posttest"),
        ("Other\n其他", "action=progress_detail&category=other"),
    ]
    
    bubbles = []
    for label, data in categories:
        bubble = FlexBubble(
            size='kilo',
            body=FlexBox(
                layout='vertical',
                justifyContent='center',
                alignItems='center',
                spacing='md',
                contents=[
                    FlexText(
                        text=label,
                        wrap=True,
                        weight='bold',
                        size='lg',
                        align='center',
                    ),
                ]
            ),
            footer=FlexBox(
                layout='vertical',
                contents=[
                    FlexButton(
                        action=PostbackAction(
                            label='View / 查看',
                            data=data
                        ),
                        style='primary',
                        height='sm',
                    ),
                ]
            )
        )
        bubbles.append(bubble)
    
    return FlexMessage(
        altText='Select Progress Category / 選擇進度類別',
        contents=FlexCarousel(contents=bubbles)
    )

async def game_progress_message(user_id: str) -> FlexMessage:
    """Show game progress summary: x/15 per theme"""
    from utils.file_utils import get_game_themes, get_min_score_to_pass, get_user_question_score, get_levels_per_theme, get_questions_per_level
    
    themes = get_game_themes()
    levels_per_theme = get_levels_per_theme()
    questions_per_level = get_questions_per_level()
    total_per_theme = levels_per_theme * questions_per_level  # 5 * 3 = 15
    min_pass = get_min_score_to_pass()
    
    body_contents = [
        FlexText(
            text='Game Progress\n遊戲進度',
            wrap=True,
            weight='bold',
            size='xl',
            align='center',
        ),
    ]
    
    for theme_id in themes:
        # Load theme name
        theme_config = load_game_theme_config(theme_id)
        theme_name = theme_config.name if theme_config else f'Theme {theme_id}'
        
        # Count passed questions across all levels
        passed_count = 0
        for lv_idx in range(levels_per_theme):
            for q_idx in range(questions_per_level):
                score = get_user_question_score(user_id, theme_id, lv_idx, q_idx)
                if score >= min_pass:
                    passed_count += 1
        
        color = '#00aa00' if passed_count == total_per_theme else '#5b5b5b'
        body_contents.append(
            FlexText(
                text=f'{theme_name}: {passed_count}/{total_per_theme}',
                wrap=True,
                size='md',
                color=color,
                margin='lg',
            )
        )
    
    return FlexMessage(
        altText='Game Progress / 遊戲進度',
        contents=FlexBubble(
            size='mega',
            body=FlexBox(
                layout='vertical',
                spacing='sm',
                contents=body_contents
            )
        )
    )

async def other_progress_message(user_id: str) -> FlexMessage:
    """Show progress for exercises (ex1-ex6)"""
    body_contents = [
        FlexText(
            text='Other Progress\n其他進度',
            wrap=True,
            weight='bold',
            size='xl',
            align='center',
        ),
    ]
    
    # Question counts per exercise: ex1=5, ex2=5, ex3=6, ex4=10, ex5=6, ex6=3
    EXERCISE_QUESTION_COUNTS = {
        1: 5,
        2: 5,
        3: 6,
        4: 10,
        5: 6,
        6: 3,
    }
    
    # Show exercises ex1-ex6 regardless of enabled status
    for i in range(1, 7):
        cat = f'ex{i}'
        total_q = EXERCISE_QUESTION_COUNTS.get(i, 5)
        answered = 0
        for q_idx in range(total_q):
            history = getHistory(user_id, f'{cat}-{q_idx}')
            if history and len(history) > 0:
                answered += 1
        color = '#00aa00' if answered == total_q else '#5b5b5b'
        body_contents.append(
            FlexText(
                text=f'Exercise {i} / 練習{i}: {answered}/{total_q}',
                wrap=True,
                size='md',
                color=color,
                margin='lg',
            )
        )

    # ===== [Change 2] SEL progress =====
    # [新增 (SEL 多單元)] SEL 已擴充為六個獨立單元（sel1..sel6），每個單元各 5 題。
    # 進度顯示時，分別列出每個單元已作答題數。
    #
    # The SEL section now consists of six independent units (sel1..sel6),
    # each with 5 questions. Show per-unit progress instead of a single combined line.
    SEL_QUESTION_COUNT = 5
    SEL_UNITS = [
        ('sel1', 'Monopoly / 地產大亨'),
        ('sel2', 'The Game of Life / 生命之旅'),
        ('sel3', 'FLIP / 換言一新'),
        ('sel4', 'Balancing Tower / 驚險塔'),
        ('sel5', 'Piranha Plant / 食人花'),
        ('sel6', 'Seven!'),
    ]
    body_contents.append(
        FlexText(
            text='SEL',
            wrap=True,
            size='md',
            weight='bold',
            color='#1a1a2e',
            margin='lg',
        )
    )
    for sel_cat, sel_label in SEL_UNITS:
        unit_answered = 0
        for q_idx in range(SEL_QUESTION_COUNT):
            history = getHistory(user_id, f'{sel_cat}-{q_idx}')
            if history and len(history) > 0:
                unit_answered += 1
        unit_color = '#00aa00' if unit_answered == SEL_QUESTION_COUNT else '#5b5b5b'
        body_contents.append(
            FlexText(
                text=f'  - {sel_label}: {unit_answered}/{SEL_QUESTION_COUNT}',
                wrap=True,
                size='sm',
                color=unit_color,
                margin='sm',
            )
        )
    # ===== [End Change 2] =====

    return FlexMessage(
        altText='Other Progress / 其他進度',
        contents=FlexBubble(
            size='mega',
            body=FlexBox(
                layout='vertical',
                spacing='sm',
                contents=body_contents
            )
        )
    )


def _build_test_section_bubble(
    user_id: str,
    section_label: str,
    section_label_chi: str,
    category: str,
    total_q: int,
) -> FlexBubble:
    """建立單一測驗區塊的進度泡泡，每題一行，全部完成顯示綠色，否則灰色。
    Build a single test section progress bubble; each question is one row,
    green if answered, gray if not.
    """
    answered_count = 0
    q_rows = []

    for q_idx in range(total_q):
        history = getHistory(user_id, f'{category}-{q_idx}')
        answered = history and len(history) > 0
        if answered:
            answered_count += 1

        color = '#00aa00' if answered else '#aaaaaa'
        status_eng = 'Answered' if answered else 'Not yet answered'
        status_chi = '已作答' if answered else '尚未作答'

        q_rows.append(
            FlexBox(
                layout='horizontal',
                spacing='sm',
                margin='sm',
                contents=[
                    FlexText(
                        text=f'Q{q_idx + 1}',
                        size='sm',
                        color=color,
                        flex=1,
                        weight='bold',
                    ),
                    FlexText(
                        text=f'{status_eng} / {status_chi}',
                        size='sm',
                        color=color,
                        flex=4,
                        wrap=True,
                    ),
                ]
            )
        )

    all_done = answered_count == total_q
    summary_color = '#00aa00' if all_done else '#5b5b5b'

    header_contents = [
        FlexText(
            text=f'{section_label} / {section_label_chi}',
            wrap=True,
            weight='bold',
            size='lg',
            color='#1a1a2e',
        ),
        FlexText(
            text=f'{answered_count}/{total_q} answered / 已作答',
            wrap=True,
            size='sm',
            color=summary_color,
            margin='xs',
        ),
        FlexSeparator(margin='md'),
    ]

    return FlexBubble(
        size='mega',
        body=FlexBox(
            layout='vertical',
            spacing='sm',
            contents=header_contents + q_rows
        )
    )


async def pretest_progress_message(user_id: str) -> FlexMessage:
    """顯示前測進度，分為前測1 (5題) 和前測2 (5題) 兩個泡泡。
    Show pre-test progress split into Pre-test 1 (5 Qs) and Pre-test 2 (5 Qs).
    全部作答完成顯示綠色，未完成顯示灰色。
    Fully completed sections are shown in green; incomplete ones in gray.
    """
    NEW_TEST_TOTAL = 5
    PRETEST2_TOTAL = 5

    bubble1 = _build_test_section_bubble(
        user_id,
        section_label='Pre-test 1',
        section_label_chi='前測1',
        category='pretest1',
        total_q=NEW_TEST_TOTAL,
    )
    bubble2 = _build_test_section_bubble(
        user_id,
        section_label='Pre-test 2',
        section_label_chi='前測2',
        category='pretest',
        total_q=PRETEST2_TOTAL,
    )

    return FlexMessage(
        altText='Pre-test Progress / 前測進度',
        contents=FlexCarousel(contents=[bubble1, bubble2])
    )


async def posttest_progress_message(user_id: str) -> FlexMessage:
    """顯示後測進度，分為後測1 (5題) 和後測2 (5題) 兩個泡泡。
    Show post-test progress split into Post-test 1 (5 Qs) and Post-test 2 (5 Qs).
    全部作答完成顯示綠色，未完成顯示灰色。
    Fully completed sections are shown in green; incomplete ones in gray.
    """
    NEW_TEST_TOTAL = 5
    POSTTEST2_TOTAL = 5

    bubble1 = _build_test_section_bubble(
        user_id,
        section_label='Post-test 1',
        section_label_chi='後測1',
        category='posttest1',
        total_q=NEW_TEST_TOTAL,
    )
    bubble2 = _build_test_section_bubble(
        user_id,
        section_label='Post-test 2',
        section_label_chi='後測2',
        category='posttest',
        total_q=POSTTEST2_TOTAL,
    )

    return FlexMessage(
        altText='Post-test Progress / 後測進度',
        contents=FlexCarousel(contents=[bubble1, bubble2])
    )

# ========== [END] Game Message Functions ==========

CHI_HINT = [
    'Please enter your class number\n請依照指示輸入你的課程編號\n1. Board Game Design Class A(4-12)\n2. Board Game Design Class B(4-34)\n3. British Culture Class A(5-12)\n4. British Culture Class B(5-34)\n5. Others',
    'Next, what is your department?\nFor example: Information Management\nEnter "Back" to go back.\n接著，請輸入你的系級\n如：資管一乙\n輸入 "Back" 可返回上一步',
    'Next, what is your student ID?\nFor example: 11352237\nEnter "Back" to go back.\n接著，請輸入你的學號\n如：11352237\n輸入 "Back" 可返回上一步',
    'Next, what is your name?\nFor example: Paul Wang\nEnter "Back" to go back.\n接著，請輸入你的姓名\n如：王聰明\n輸入 "Back" 可返回上一步',
]

ENG_HINT =[
    'Enter your class number\n1. Board Game Design Class A(4-12)\n2. Board Game Design Class B(4-34)\n3. British Culture Class A(5-12)\n4. British Culture Class B(5-34)\n5. Others',
    'Next, what is your department?\nFor example: Information Management\nEnter "Back" to previous step.',
    'Next, what is your student ID?\nFor example: 11352237\nEnter "Back" to previous step.',
    'Next, what is you name?\nFor example: Paul Wang\nEnter "Back" to previous step.',
]

async def info_hint_message(index: int):
    return FlexMessage(
        altText='Data Binding Hint',
        contents=FlexBubble(
            size='mega',
            body=FlexBox(
                layout='vertical',
                spacing='lg',
                contents=[
                    FlexText(
                        text=CHI_HINT[index],
                        wrap=True,
                        size='md',
                    ),
                ]
            )
        )
    )
async def show_loading(user_id, secs=20):
    await line_bot_api.show_loading_animation(show_loading_animation_request=ShowLoadingAnimationRequest(chatId=user_id, loadingSeconds=secs), async_req=True).get()
    
async def handle_rich_menu(user_id):
    """初始化或修正使用者的 rich menu 狀態。
    Initialise or correct the user's rich menu state.

    每次互動開始時都會呼叫此函式。除了原本的「偵測目前選單並設定 category」邏輯外，
    還會主動檢查使用者目前所在的選單區塊是否仍處於開放狀態，若已被管理員關閉，
    立即將使用者重新連結回預設主選單，確保無法在關閉後的區塊繼續操作。

    Called at the start of every interaction. In addition to the original
    'detect current menu and set category' logic, it actively checks whether
    the user's current menu section is still enabled. If the admin has since
    disabled it, the user is immediately re-linked to the default main menu.
    """
    _SWITCH_CONTROLLED = {
        'pretest', 'posttest', 'rag_test',
        'ex1', 'ex2', 'ex3', 'ex4', 'ex5', 'ex6', 'chat',
        # [新增 (SEL 多單元)] 將六個 SEL 單元納入即時開關監控，
        # 與 handlers.py 的 _SWITCH_CONTROLLED 同步，確保管理員關閉後立即驅離使用者。
        # Include the six SEL units so admin disable actions evict users immediately,
        # matching the _SWITCH_CONTROLLED set in handlers.py.
        'sel', 'sel1', 'sel2', 'sel3', 'sel4', 'sel5', 'sel6',
    }

    user_state = get_user_state(user_id)
    is_rag = config.get('rag_mode', False)
    default_menu = 'menu_game' if is_rag else 'menu'

    if user_state.category:
        # 即使 category 已知，仍需驗證該區塊是否仍開放（管理員可能在使用者進入後才關閉）。
        # Even if the category is already known, verify the section is still enabled
        # (admin may have disabled it after the user navigated in).
        enabled_cat = get_enabled_category_for_alias(user_state.category)
        if (
            enabled_cat in _SWITCH_CONTROLLED
            and not isEnabled(enabled_cat)
            and not isAdmin(user_id)
        ):
            # 使用者仍停留在已關閉的區塊，立即踢回主選單。
            # User is still on a now-disabled section; kick them back to main menu.
            default_menu_id = get_rich_menu_id(default_menu)
            if default_menu_id:
                try:
                    await rich_menu_manager.link_rich_menu_to_user(
                        user_id=user_id, rich_menu_id=default_menu_id
                    )
                except Exception as _evict_err:
                    print(f"[WARN] handle_rich_menu eviction failed: {_evict_err}")
            user_state.category = default_menu
            user_state.in_npc_chat = False
        return

    # category 尚未設定：從 LINE 平台查詢使用者目前連結的 rich menu。
    # Category not yet set: query LINE platform for the user's currently linked menu.
    try:
        rich_menu_id = await rich_menu_manager.get_rich_menu_id(user_id)
        category = get_rich_menu_category_from_id(rich_menu_id)
        if not category:
            raise ApiException('No rich menu category found.')
        # 查詢到的 category 也需要通過 enabled 檢查。
        # The detected category also needs to pass the enabled check.
        enabled_cat = get_enabled_category_for_alias(category)
        if (
            enabled_cat in _SWITCH_CONTROLLED
            and not isEnabled(enabled_cat)
            and not isAdmin(user_id)
        ):
            default_menu_id = get_rich_menu_id(default_menu)
            if default_menu_id:
                try:
                    await rich_menu_manager.link_rich_menu_to_user(
                        user_id=user_id, rich_menu_id=default_menu_id
                    )
                except Exception as _evict_err:
                    print(f"[WARN] handle_rich_menu eviction (fresh) failed: {_evict_err}")
            user_state.category = default_menu
        else:
            user_state.category = category
    except ApiException:
        # LINE 回報沒有連結的 rich menu，連結預設主選單。
        # LINE reports no linked rich menu; link the default main menu.
        default_menu_id = get_rich_menu_id(default_menu)
        if default_menu_id:
            await rich_menu_manager.link_rich_menu_to_user(
                user_id=user_id, rich_menu_id=default_menu_id
            )
        user_state.category = default_menu
    except Exception as e:
        print(e)

# ========== [START] new_test 題目訊息 (pretest1 / posttest1 rich menu) ==========

async def new_test_question_message(user_id: str, sub: int, base_category: str, show_feedback: bool = True) -> FlexMessage:
    """顯示 new_test 單道題目卡片 (含作答紀錄)。
    Show a single new_test question card with history if available.

    Args:
        user_id: 使用者 ID
        sub: 題目索引 (0-based)
        base_category: 'pretest' 或 'posttest'
    """
    question = get_new_test_question(sub)
    if not question:
        return FlexMessage(
            altText='Question not found',
            contents=FlexBubble(
                body=FlexBox(
                    layout='vertical',
                    contents=[FlexText(text='Question not found.\n找不到題目。', wrap=True)]
                )
            )
        )

    section_category = f'{base_category}1'
    history = getHistory(user_id, f'{section_category}-{sub}')

    contents = []

    # 題目卡
    q_bubble = FlexBubble(
        size='mega',
        body=FlexBox(
            layout='vertical',
            spacing='lg',
            contents=[
                FlexText(
                    text=f'Q{sub + 1}',
                    wrap=True,
                    weight='bold',
                    size='xl',
                ),
                FlexText(
                    text=question.text,
                    wrap=True,
                    size='md',
                    color='#5b5b5b',
                ),
            ]
        )
    )
    if question.image_url:
        q_bubble.hero = FlexImage(
            url=f'{URL}{question.image_url}',
            size='full',
            aspect_ratio='20:13',
            aspect_mode='cover',
        )
    contents.append(q_bubble)

    # 歷史紀錄卡 (若有)
    if history and len(history) > 0:
        last = history[-1]
        contents.append(FlexBubble(
            size='mega',
            body=FlexBox(
                layout='vertical',
                spacing='sm',
                contents=[
                    FlexText(
                        text='Last Answer\n上次回答',
                        wrap=True,
                        weight='bold',
                        size='lg',
                    ),
                    FlexText(
                        text=f'Score: {last.score}',
                        wrap=True,
                        size='md',
                        color='#00aa00' if last.score >= 7 else '#ff8800' if last.score >= 4 else '#ff0000',
                    ),
                    FlexText(
                        text=f'"{last.transcript}"',
                        wrap=True,
                        size='sm',
                        color='#5b5b5b',
                        style='italic',
                    ),
                ]
            ),
            # 僅在後台開啟回饋時顯示 View Feedback 按鈕
            # Show View Feedback button only when feedback is enabled in admin
            footer=FlexBox(
                layout='vertical',
                contents=[
                    FlexButton(
                        action=PostbackAction(
                            label='View Feedback',
                            data=f'action=new_test_last&base={base_category}&sub={sub}'
                        ),
                        style='secondary',
                    ),
                ]
            ) if show_feedback else None
        ))

    # 作答提示卡
    contents.append(FlexBubble(
        size='mega',
        body=FlexBox(
            layout='vertical',
            justifyContent='center',
            alignItems='center',
            spacing='md',
            contents=[
                FlexText(
                    text=(
                        '請在發送文字訊息的鍵盤位置，點擊麥克風符號錄音並發送語音訊息以作答。'
                        '為了獲得高分請盡量用完整句子作答！\n'
                        'To answer, tap the microphone icon near the text keyboard to record '
                        'and send a voice message. For a higher score, please answer in complete sentences!'
                    ),
                    wrap=True,
                    size='lg',
                    align='center',
                ),
            ]
        )
    ))

    return FlexMessage(
        altText=f'Q{sub + 1}',
        contents=FlexCarousel(contents=contents)
    )

# ========== [END] 前測1/後測1 區塊選擇與 new_test 題目訊息 ==========


# ========== [START] NPC 語音輸出相關訊息 (service4/service5) ==========

async def game_npc_voice_response_messages(
    npc_name: str,
    npc_reply: str,
    is_english: bool,
    npc_image,
    audio_filename: str,
    audio_duration: int
) -> list:
    """NPC 語音回覆模式：回傳訊息列表 [語言警告卡(若有), 圖片卡, 語音訊息]。
    NPC voice response mode: returns message list [warning card (if any), image card, audio message].

    圖片卡只顯示 NPC 人物圖片，不顯示文字回覆。
    語音訊息附帶「顯示文字 / Show Text」及「前往作答 / Go to Answer」快速回覆按鈕。
    The image card shows only the NPC character image without the reply text.
    The audio message includes 'Show Text' and 'Go to Answer' quick reply buttons.

    Args:
        npc_name: NPC 名稱
        npc_reply: NPC 回覆文字 (僅用於 altText，不顯示在卡片上)
        is_english: 使用者是否使用英文
        npc_image: NPC 圖片檔名 (e.g. John_Watson.jpg)
        audio_filename: 語音檔案路徑 (相對於 templates/)
        audio_duration: 語音長度 (毫秒)
    """
    import random

    messages = []

    # 語言警告卡片 (使用者未使用英文時)
    if not is_english:
        warning_bubble = FlexBubble(
            size='giga',
            body=FlexBox(
                layout='vertical',
                spacing='md',
                justifyContent='center',
                alignItems='center',
                contents=[
                    FlexText(
                        text='Please speak in English\n請使用英文對話',
                        wrap=True,
                        weight='bold',
                        size='lg',
                        align='center',
                        color='#ff6600',
                    ),
                ]
            )
        )
        messages.append(FlexMessage(
            altText='Please speak in English / 請使用英文',
            contents=warning_bubble
        ))

    # NPC 圖片卡 (只顯示人物圖片，不含文字回覆)
    if npc_image:
        base_name = npc_image.rsplit('.', 1)[0] if '.' in npc_image else npc_image
        ext = npc_image.rsplit('.', 1)[1] if '.' in npc_image else 'jpg'
        variant = random.choice([1, 2, 3])
        random_image = f'{base_name}_{variant}.{ext}'

        image_bubble = FlexBubble(
            size='giga',
            hero=FlexImage(
                url=f'{URL}/templates/people_pic/{random_image}',
                size='full',
                aspect_ratio='3:4',
                aspect_mode='cover',
            ),
            body=FlexBox(
                layout='vertical',
                spacing='sm',
                contents=[
                    FlexText(
                        text=npc_name,
                        wrap=True,
                        weight='bold',
                        size='lg',
                        align='center',
                        color='#1a1a2e',
                    ),
                    FlexText(
                        text='Listen to the audio message below.\n請聆聽下方語音訊息。',
                        wrap=True,
                        size='sm',
                        color='#888888',
                        align='center',
                    ),
                ]
            )
        )
        messages.append(FlexMessage(
            altText=f'{npc_name} is speaking...',
            contents=image_bubble
        ))

    # 語音訊息 (附快速回覆按鈕)
    quick_reply = QuickReply(items=[
        QuickReplyItem(action=PostbackAction(
            label='Show Text / 顯示文字',
            data='action=game_show_npc_text'
        )),
        QuickReplyItem(action=PostbackAction(
            label='Go to Answer / 前往作答',
            data='action=game_current_questions'
        )),
    ])

    audio_msg = AudioMessage(
        originalContentUrl=f'{URL}/templates/{audio_filename}',
        duration=audio_duration,
        quickReply=quick_reply
    )
    messages.append(audio_msg)

    return messages


async def game_npc_text_card_message(
    npc_name: str,
    npc_reply: str,
    npc_image=None
) -> FlexMessage:
    """顯示 NPC 文字回覆卡片，由「顯示文字 / Show Text」按鈕觸發。
    Show NPC text reply card, triggered by the 'Show Text' quick reply button.

    此為語音模式下使用者主動查看文字時的卡片，外觀與原本 game_npc_chat_response_message 相同。
    This is the text variant for voice mode; it mirrors game_npc_chat_response_message in appearance.
    """
    import random

    bubbles = []

    reply_contents = [
        FlexText(
            text=f'{npc_name} says:',
            wrap=True,
            weight='bold',
            size='lg',
            color='#1a1a2e',
        ),
        FlexText(
            text=npc_reply if npc_reply else '...',
            wrap=True,
            size='md',
            color='#5b5b5b',
            margin='md',
        ),
    ]

    reply_bubble = FlexBubble(
        size='giga',
        body=FlexBox(
            layout='vertical',
            spacing='sm',
            contents=reply_contents
        )
    )

    if npc_image:
        base_name = npc_image.rsplit('.', 1)[0] if '.' in npc_image else npc_image
        ext = npc_image.rsplit('.', 1)[1] if '.' in npc_image else 'jpg'
        variant = random.choice([1, 2, 3])
        random_image = f'{base_name}_{variant}.{ext}'
        reply_bubble.hero = FlexImage(
            url=f'{URL}/templates/people_pic/{random_image}',
            size='full',
            aspect_ratio='3:4',
            aspect_mode='cover',
        )

    bubbles.append(reply_bubble)

    msg = FlexMessage(
        altText=f'{npc_name} Response',
        contents=FlexCarousel(contents=bubbles)
    )

    msg.quick_reply = QuickReply(items=[
        QuickReplyItem(action=PostbackAction(
            label='Go to Answer / 前往作答',
            data='action=game_current_questions'
        )),
    ])

    return msg

# ========== [END] NPC 語音輸出相關訊息 ==========

# ========== [新增] LINE 速率限制處理 (Rate-limit handling helpers) ==========
# 啟動時批次重建 rich menu 容易在短時間內超過 LINE 的速率限制（HTTP 429）。
# 以下兩個常數可控制節流行為，必要時可調大。
#
# Bulk rebuilding rich menus at startup easily exceeds LINE's burst rate limit (HTTP 429).
# The two constants below control throttling; raise them if you still hit 429.
RICH_MENU_API_DELAY = 0.6          # 每個 rich menu 操作之間的最小間隔 (秒)
                                   # Minimum delay between each rich menu API operation (seconds).
RICH_MENU_RATE_LIMIT_MAX_RETRY = 6  # 遇到 429 時的最大重試次數 (採用指數退避)
                                   # Max retries on 429 (with exponential backoff).


async def _call_with_rate_limit_retry(coro_func, *args, op_desc: str = "LINE API",
                                       max_retries: int = RICH_MENU_RATE_LIMIT_MAX_RETRY,
                                       base_delay: float = 2.0,
                                       **kwargs):
    """以指數退避方式重試會被速率限制的 LINE API 呼叫。
    Retry a rate-limited LINE API coroutine with exponential backoff.

    Args:
        coro_func: 要呼叫的 async 函式（不要先 await，這裡會代為 await）。
                   The async function to call (do NOT pre-await it).
        op_desc:   描述用字串，會在日誌中印出。
                   Human-readable description for logging.
        max_retries: 最大重試次數。Max attempts.
        base_delay:  指數退避基底秒數。Base seconds for exponential backoff.

    Returns:
        被呼叫函式的回傳值；若多次重試後仍失敗，原樣拋出最後一次的 ApiException。
        The wrapped coroutine's return value, or re-raises the final ApiException
        if all retries are exhausted.
    """
    last_exc = None
    for attempt in range(max_retries):
        try:
            return await coro_func(*args, **kwargs)
        except ApiException as e:
            last_exc = e
            # 僅在 429 才重試，其餘錯誤直接拋出。
            # Only retry on 429; bubble up everything else immediately.
            if getattr(e, 'status', None) != 429:
                raise
            if attempt >= max_retries - 1:
                break
            wait = base_delay * (2 ** attempt)
            print(
                f"[WARN] 429 rate-limited on {op_desc} (attempt {attempt + 1}/{max_retries}); "
                f"waiting {wait:.1f}s before retry."
            )
            await asyncio.sleep(wait)
    # 重試耗盡，拋出最後一次的例外。
    # Retries exhausted; raise the last captured exception.
    raise last_exc


async def create_rich_menu(force_rebuild: bool = None):
    """建立或同步 rich menu 到 LINE 平台。
    Provision rich menus on the LINE platform.

    執行策略 / Strategy
    ------------------
    預設採用「智能重用 (smart reuse)」模式：
      1. 讀取 LINE 上現有的所有 rich menu，建立「menu 名稱 → ID」對照表。
      2. 對 rich_menu.json 裡的每個 menu：
           - 若名稱已存在於 LINE，直接重用該 ID（不打任何建立 / 上傳 API），
             僅在需要時把它設為預設 menu。
           - 若不存在，才執行建立 → 上傳圖片 → （視情況）設為預設。
      3. 若該 menu 是預設 menu，無論重用或新建都會呼叫 set_default。
      4. 此模式下不會主動刪除任何既有 menu（避免燒掉 LINE 的 burst 配額）；
         若 LINE 上有多餘的舊 menu 需要清理，請透過 LINE Official Account Manager
         手動刪除（LINE 文件指出該介面的刪除不受 API 速率限制）。

    若需要強制全部重建（例如改了按鈕的 action type、或要清掉舊版殘留），
    在 docker-compose / 環境變數中設定 RICH_MENU_FORCE_REBUILD=1 即可。
    此時會走「先刪光全部 → 再依序重建」的舊邏輯，並完整套用 429 退避重試。

    Default mode is *smart reuse*: existing menus on LINE are matched by name and
    their IDs are reused with zero API calls. Missing menus are created
    individually. No existing menus are deleted, which avoids the LINE burst
    rate-limit cascade. Set RICH_MENU_FORCE_REBUILD=1 in the environment to fall
    back to the original force-delete-and-rebuild behaviour (with retries).
    """
    await line_bot_api.set_webhook_endpoint(SetWebhookEndpointRequest(endpoint=f'{URL}/callback'))
    configs = load_rich_menu_configs()

    # [更新] 強制重建開關現在優先取自呼叫者傳入的參數；若未指定，再讀取環境變數。
    # 這讓管理員指令 /refresh_all_menus 可以在不修改環境變數的情況下觸發強制重建。
    # The force_rebuild flag now prefers the explicit argument; falls back to the
    # environment variable when not provided. This lets the /refresh_all_menus admin
    # command trigger a force rebuild without having to mutate process environment.
    if force_rebuild is None:
        force_rebuild = os.environ.get('RICH_MENU_FORCE_REBUILD', '').lower() in ('1', 'true', 'yes')

    # 讀取 LINE 上目前存在的所有 rich menu。
    # Inventory the rich menus already present on the LINE platform.
    try:
        existing_menus = await rich_menu_manager.get_all_rich_menus()
    except Exception as _list_err:
        print(f"[WARN] Could not list existing rich menus: {_list_err}")
        existing_menus = []

    # 建立「menu 名稱 → rich_menu_id」對照表，重複名稱以最後一個為準。
    # Build a name→id map of existing menus (later duplicates win).
    existing_by_name = {}
    for m in (existing_menus or []):
        name = getattr(m, 'name', None)
        rid = getattr(m, 'rich_menu_id', None)
        if name and rid:
            existing_by_name[name] = rid

    desired_names = set(configs.get('rich_menus', {}).keys())
    target_default = 'menu_game' if config.get('rag_mode', False) else 'menu'

    if force_rebuild:
        # ===== 強制重建模式 =====
        # Force-rebuild mode: delete every existing menu, then recreate from configs.
        # 每個刪除呼叫之間皆 sleep 並走 429 重試，避免一次打爆 burst quota。
        if existing_menus:
            print(f"[RICH_MENU] Force rebuild: deleting {len(existing_menus)} existing rich menu(s)...")
            for r in existing_menus:
                try:
                    await _call_with_rate_limit_retry(
                        rich_menu_manager.delete_rich_menu,
                        r.rich_menu_id,
                        op_desc=f"delete_rich_menu({r.rich_menu_id})",
                    )
                except Exception as _del_err:
                    print(f"[WARN] Could not delete rich menu {r.rich_menu_id}: {_del_err}")
                await asyncio.sleep(RICH_MENU_API_DELAY)
        clear_rich_menu_id()
        existing_by_name = {}  # 已全部刪除，重置對照表 / map is now empty
    else:
        # ===== 智能重用模式 (預設) =====
        # Smart reuse (default): preserve existing menus and reuse their IDs by name.
        # 由於僅根據名稱比對，若你修改了 rich_menu.json 中某個 menu 的版面或按鈕動作，
        # 該 menu 在 LINE 上仍然是舊內容；此時請改用 RICH_MENU_FORCE_REBUILD=1 重啟一次。
        # Reuse is name-only; if you change a menu's layout or actions in rich_menu.json,
        # run once with RICH_MENU_FORCE_REBUILD=1 to refresh.
        reused = sum(1 for n in desired_names if n in existing_by_name)
        missing = len(desired_names) - reused
        leftover = len(set(existing_by_name.keys()) - desired_names)
        print(
            f"[RICH_MENU] Smart reuse: {reused} reusable / {missing} to create / "
            f"{leftover} leftover on LINE (not deleted)."
        )
        # 清空本地 ID 快取後重新填入，確保 rich_menu_ids 與 LINE 上實際狀況同步。
        # Clear the local ID cache and refill it so rich_menu_ids stays in sync with LINE.
        clear_rich_menu_id()

    for menu_name, config_data in configs['rich_menus'].items():
        rich_menu_manager.set_display_name(menu_name, config_data.get('chat_bar_text'))
        try:
            if (not force_rebuild) and menu_name in existing_by_name:
                # 重用既有 menu：不打建立 / 上傳 API，僅將 ID 寫回本地 config。
                # Reuse path: don't call create/upload; just record the existing ID.
                rich_menu_id = existing_by_name[menu_name]
                if menu_name == target_default:
                    # 預設 menu 仍需設定一次，確保預設指向當前版本（這支 API 很輕，沒問題）。
                    # The default menu setter must still run so the default points to the
                    # reused menu (this endpoint is light and won't hit the burst limit).
                    await _call_with_rate_limit_retry(
                        rich_menu_manager.set_default_rich_menu,
                        rich_menu_id,
                        op_desc=f"set_default_rich_menu({menu_name})",
                    )
                set_rich_menu_id(rich_menu_id, menu_name)
                print(f"Rich Menu {menu_name} reused: {rich_menu_id}")
            else:
                # 建立新 menu：建立 → 上傳圖片 → （視情況）設為預設。
                # Create path: create → upload image → (optionally) set as default.
                builder = build_rich_menu_from_config(menu_name, config_data)
                rich_menu_id = await _call_with_rate_limit_retry(
                    rich_menu_manager.create_rich_menu,
                    builder,
                    op_desc=f"create_rich_menu({menu_name})",
                )
                image_file = config_data.get("file")
                if image_file:
                    image_path = os.path.join("./templates/richmenu", image_file)
                    await _call_with_rate_limit_retry(
                        rich_menu_manager.upload_rich_menu_image,
                        rich_menu_id, image_path,
                        op_desc=f"upload_rich_menu_image({menu_name})",
                    )
                if menu_name == target_default:
                    await _call_with_rate_limit_retry(
                        rich_menu_manager.set_default_rich_menu,
                        rich_menu_id,
                        op_desc=f"set_default_rich_menu({menu_name})",
                    )
                set_rich_menu_id(rich_menu_id, menu_name)
                print(f"Rich Menu {menu_name} created with ID: {rich_menu_id}")
        except Exception as e:
            print(f"[ERROR] Failed to process rich menu {menu_name}: {e}")
            import traceback
            traceback.print_exc()
        # 每個 menu 之間固定 sleep，避免任何高密度 API 呼叫觸發 LINE 的 burst 限制。
        # Sleep between menus to avoid bursty API patterns even in reuse mode.
        await asyncio.sleep(RICH_MENU_API_DELAY)

    await save_config()

# ========== [新增] 重建單一 rich menu (Refresh a single rich menu) ==========
# 配合管理員指令 /refresh_menu <name> 使用。
# 當 rich_menu.json 沒改、但某張選單的圖片檔案內容換掉時，智能重用模式因為
# 「名稱仍存在於 LINE」會直接重用，不會自動上傳新圖片；此函式提供「精準刪除
# 並重建單一 menu」的能力，讓圖片更新可以在不打斷其他選單的情況下生效。
#
# Companion helper for the /refresh_menu <name> admin command. Smart reuse keeps
# an existing LINE menu when its name matches, so simply replacing an image file
# on disk does NOT propagate to LINE. This helper deletes any LINE-side menu(s)
# with the given name and re-creates exactly that one, leaving every other menu
# untouched.
async def refresh_single_rich_menu(menu_name: str):
    """刪除並重建指定名稱的單一 rich menu。
    Delete and rebuild a single rich menu identified by name.

    Returns:
        tuple[bool, str]: (success, human-readable status message in bilingual form).
    """
    configs = load_rich_menu_configs()
    if menu_name not in configs.get('rich_menus', {}):
        return (
            False,
            f"找不到名為 '{menu_name}' 的選單設定，請檢查 rich_menu.json。\n"
            f"Menu '{menu_name}' is not defined in rich_menu.json."
        )

    # 列出 LINE 上所有現有 menu，刪除所有同名項目（包含因失敗部署殘留的副本）。
    # List every menu on LINE and delete all entries sharing the target name
    # (including stale duplicates from past failed deployments).
    deleted_count = 0
    try:
        existing_menus = await rich_menu_manager.get_all_rich_menus()
    except Exception as e:
        return (
            False,
            f"無法讀取 LINE 上的現有選單清單：{e}\n"
            f"Could not list existing rich menus on LINE: {e}"
        )

    for m in (existing_menus or []):
        if getattr(m, 'name', None) == menu_name:
            try:
                await _call_with_rate_limit_retry(
                    rich_menu_manager.delete_rich_menu,
                    m.rich_menu_id,
                    op_desc=f"delete_rich_menu({m.rich_menu_id})",
                )
                deleted_count += 1
            except Exception as e:
                print(f"[WARN] Could not delete rich menu {m.rich_menu_id}: {e}")
            await asyncio.sleep(RICH_MENU_API_DELAY)

    # 重新建立該 menu，並上傳對應的圖片。
    # Recreate the menu and upload its image.
    config_data = configs['rich_menus'][menu_name]
    rich_menu_manager.set_display_name(menu_name, config_data.get('chat_bar_text'))
    try:
        builder = build_rich_menu_from_config(menu_name, config_data)
        rich_menu_id = await _call_with_rate_limit_retry(
            rich_menu_manager.create_rich_menu,
            builder,
            op_desc=f"create_rich_menu({menu_name})",
        )
        image_file = config_data.get("file")
        if image_file:
            image_path = os.path.join("./templates/richmenu", image_file)
            await _call_with_rate_limit_retry(
                rich_menu_manager.upload_rich_menu_image,
                rich_menu_id, image_path,
                op_desc=f"upload_rich_menu_image({menu_name})",
            )
        # 若這支恰好是預設 menu，必須再設一次預設（因為舊 ID 已被刪除）。
        # If this happens to be the default menu, re-set the default since the
        # previous default ID was just deleted.
        target_default = 'menu_game' if config.get('rag_mode', False) else 'menu'
        if menu_name == target_default:
            await _call_with_rate_limit_retry(
                rich_menu_manager.set_default_rich_menu,
                rich_menu_id,
                op_desc=f"set_default_rich_menu({menu_name})",
            )
        set_rich_menu_id(rich_menu_id, menu_name)
        await save_config()
        return (
            True,
            f"已重建選單『{menu_name}』(刪除 {deleted_count} 個舊版本)\n新 ID: {rich_menu_id}\n\n"
            f"Rebuilt menu '{menu_name}' (deleted {deleted_count} stale version(s)).\nNew ID: {rich_menu_id}"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return (
            False,
            f"重建『{menu_name}』失敗：{e}\n"
            f"Failed to rebuild '{menu_name}': {e}"
        )