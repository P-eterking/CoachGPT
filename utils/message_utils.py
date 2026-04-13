from config import line_bot_api, rich_menu_manager, DOMAIN, question_manager, client
from linebot.v3.messaging import (
    ReplyMessageRequest, TextMessage, PostbackAction, QuickReply,
    QuickReplyItem, FlexMessage, FlexCarousel, FlexBubble, FlexImage,
    FlexText, FlexBox, FlexButton, AudioMessage, ShowLoadingAnimationRequest,
    VideoMessage, URIAction
)
from manager.richmenu import *
from linebot.v3.messaging.exceptions import ApiException
from linebot.v3.messaging.models import SetWebhookEndpointRequest
from utils.models import ChatSummary, QuestionSet, SpeechAssessment, NPCChatResponse, QuestionAnswerResponse, ImprovementHintResponse
import json
from utils.file_utils import (
    get_user_state, getHistory, get_rich_menu_id, isEnabled, isResponse, 
    set_rich_menu_id, save_config, get_rich_menu_category_from_id, 
    clear_rich_menu_id, config, load_game_theme_config, get_game_level_info,
    get_user_game_score, get_max_theme_score, get_user_game_progress,
    get_questions_per_level, get_user_question_score, get_user_unlocked_level,
    get_user_level_score, get_display_feedback, get_levels_per_theme,
    get_game_info_config, get_theme_display_number,
    get_new_test_question, get_new_test_questions_count, get_new_test_questions_all
)

URL = f'https://{DOMAIN}'
IMG_EXT = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')
CHAT_CATEGORY = ["Travel", "Sports", "Interview", "English Skills"]
CHAT_CATEGORY_IMAGE_URL = ["/templates/chat/travel.jpg", "/templates/chat/sports.jpg", "/templates/chat/interview.jpg", "/templates/chat/english_skills.jpg"]

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


async def question_message(user_id, category, sub):
    question = question_manager.get_question(category, sub)
    history = getHistory(user_id, f'{category}-{sub}')
    
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
            )
        )
        contents.append(history_bubble)
    
    # Instructions bubble
    instruction_bubble = FlexBubble(
        size='mega',
        body=FlexBox(
            layout='vertical',
            justifyContent='center',
            alignItems='center',
            spacing='md',
            contents=[
                FlexText(
                    text='請在發送文字訊息的鍵盤位置，點擊麥克風符號錄音並發送語音訊息以作答。為了獲得高分請盡量用完整句子作答！\nTo answer, please tap the microphone icon near the text keyboard to record and send a voice message. For a higher score, please try to answer in complete sentences!',
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


async def result_message(assessment: SpeechAssessment, category: str, sub: int):
    display_feedback = get_display_feedback()
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
        if assessment.eng_suggestion:
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
        if assessment.better_ans:
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
                    text=f'Topic {get_theme_display_number(theme_id)} Level {level_idx + 1}: {level_info["title"]}',
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
                    text='[Tip] Click NPC icons in the menu below to chat with NPCs and get clues!(Videos may take a moment to load. If you encounter a black screen, please reload the video and wait patiently. Thank you!)',
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
        get_min_score_to_pass
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
    
    # If all passed or force show, display all questions for free selection
    if all_passed or force_show_all:
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
        altText=f'Topic {topic_num} Level {level_idx + 1} Questions',
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
                             reference_comparison: str = "") -> FlexMessage:
    """Show game result and score - English feedback first, Chinese feedback second
    
    Button logic:
    - Score < 6: Show "Try Again" + "Improvement Hint"
    - Score 6-9: Show "Try Again" + "Improvement Hint" + "Next Question"
    - Score = 10: Show only "Next Question"
    """
    display_feedback = get_display_feedback()
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
    # Score < 6: "Try Again" + "Improvement Hint"
    # Score 6-9: "Try Again" + "Improvement Hint" + "Next Question"
    # Score = 10: Only "Next Question"
    from utils.file_utils import get_min_score_to_pass, is_level_all_questions_passed, get_next_unpassed_question, get_questions_per_level
    min_score = get_min_score_to_pass()
    is_passed = score >= min_score
    is_perfect = score == 10
    all_level_passed = is_level_all_questions_passed(user_id, theme_id, level_idx)
    questions_per_level_count = get_questions_per_level()
    
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
    
    # If passed current question (score >= 6), show next question button
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
    """
    rules_eng = (
        "Welcome to the Mystery Game! "
        "In this scenario-based puzzle game, you will play the role of a detective assistant, "
        "asking NPC characters about case details to solve a series of riddles. "
        "Each of the three NPCs knows different information -- if you cannot find the answer, "
        "try asking a different character! "
        "There are 3 themes in total, each with 5 levels, and each level has 3 small puzzles. "
        "Don't be intimidated by the number of questions -- the game will provide sufficient "
        "clues and guidance to help you progress. Enjoy the game!"
    )
    rules_chi = (
        "歡迎來到情境解謎遊戲！"
        "在這個情境式解謎遊戲中，你將扮演偵探助手的角色，"
        "向 NPC 角色詢問案件細節以破解一道道謎題。"
        "三個 NPC 人物知道的資訊都不同，如果問不出答案不妨換個人問問看喔！"
        "此遊戲總共有三個主題，每個主題有五道關卡，每個關卡又有三個小謎題，"
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
    
    bubble = FlexBubble(
        size='giga',
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
    bubbles = []
    
    for level in theme_config.levels:
        is_locked = level.id > unlocked_level
        
        if is_locked:
            continue  # Don't show locked levels
        
        # Get level score
        level_score = get_user_level_score(user_id, theme_id, level.id)
        max_level_score = get_questions_per_level() * 10
        is_completed = level_score >= get_questions_per_level() * 6  # All questions passed
        
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
    
    # If there are still locked levels, show a hint
    if unlocked_level < len(theme_config.levels) - 1:
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
                text=f'Exercise {i}: {answered}/{total_q}',
                wrap=True,
                size='md',
                color=color,
                margin='lg',
            )
        )
    
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

# ========== [END] Game Message Functions ==========

CHI_HINT = [
    'Please enter your class number\n請依照指示輸入你的課程編號\n1 for English Presentation(4-12)\n2 for English Presentation(4-34)\n3 for English Culture(1-56)\n4 for English Culture(1-78)\n5 for Others',
    'Next, what is your department?\nFor example: Information Management\nEnter "Back" to go back.\n接著，請輸入你的系級\n如：資管一乙\n輸入 "Back" 可返回上一步',
    'Next, what is your student ID?\nFor example: 11352237\nEnter "Back" to go back.\n接著，請輸入你的學號\n如：11352237\n輸入 "Back" 可返回上一步',
    'Next, what is your name?\nFor example: Paul Wang\nEnter "Back" to go back.\n接著，請輸入你的姓名\n如：王聰明\n輸入 "Back" 可返回上一步',
]

ENG_HINT =[
    'Enter your class number\n1 for English Presentation(4-12)\n2 for English Presentation(4-34)\n3 for English Culture and Lifestyle(1-56)\n4 for English Culture and Lifestyle(1-78)\n5 for Others',
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
    user_state = get_user_state(user_id)
    if user_state.category:
        return
    try:
        rich_menu_id = await rich_menu_manager.get_rich_menu_id(user_id)
        category = get_rich_menu_category_from_id(rich_menu_id)
        if not category:
            raise ApiException('No rich menu category found.')
        user_state.category = category
    except ApiException as e:
        # [FIX #2] For rag_mode (service4), default to menu_game instead of menu
        is_rag = config.get('rag_mode', False)
        default_menu = 'menu_game' if is_rag else 'menu'
        rich_menu_id = get_rich_menu_id(default_menu)
        await rich_menu_manager.link_rich_menu_to_user(user_id=user_id, rich_menu_id=rich_menu_id)
        user_state.category = default_menu
    except Exception as e:
        print(e)

# ========== [START] new_test 題目訊息 (pretest1 / posttest1 rich menu) ==========

async def new_test_question_message(user_id: str, sub: int, base_category: str) -> FlexMessage:
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
            )
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

async def create_rich_menu():
    await line_bot_api.set_webhook_endpoint(SetWebhookEndpointRequest(endpoint=f'{URL}/callback'))
    configs = load_rich_menu_configs()
    response = await rich_menu_manager.get_all_rich_menus()
    if len(response) != len(configs['rich_menus'].items()):
        print("Deleting all rich menus...")
        for r in response:
            await rich_menu_manager.delete_rich_menu(r.rich_menu_id)
        clear_rich_menu_id()
    
    # Decide default menu based on RAG mode
    target_default = 'menu_game' if config.get('rag_mode', False) else 'menu'
    
    for menu_name, config_data in configs['rich_menus'].items():
        rich_menu_manager.set_display_name(menu_name, config_data.get('chat_bar_text'))
        if get_rich_menu_id(menu_name):
            continue
        try:
            builder = build_rich_menu_from_config(menu_name, config_data)
            rich_menu_id = await rich_menu_manager.create_rich_menu(builder)
            image_file = config_data.get("file")
            if image_file:
                image_path = os.path.join("./templates/richmenu", image_file)
                await rich_menu_manager.upload_rich_menu_image(rich_menu_id, image_path)
            
            # If current menu is target default, set as default
            if menu_name == target_default:
                await rich_menu_manager.set_default_rich_menu(rich_menu_id)
                
            set_rich_menu_id(rich_menu_id, menu_name)
            print(f'Rich Menu {menu_name} created with ID: {rich_menu_id}')
        except Exception as e:
            print(f'[ERROR] Failed to create rich menu {menu_name}: {e}')
            import traceback
            traceback.print_exc()
    await save_config()