from config import line_bot_api, rich_menu_manager, DOMAIN, question_manager, client
from linebot.v3.messaging import (
    ReplyMessageRequest, TextMessage, PostbackAction, QuickReply,
    QuickReplyItem, FlexMessage, FlexCarousel, FlexBubble, FlexImage,
    FlexText, FlexBox, FlexButton, AudioMessage, ShowLoadingAnimationRequest,
    VideoMessage
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
    get_hint_usage_count, increment_hint_usage, get_last_question_answer  # [NEW] 新增 hint 相關函數
)

URL = f'https://{DOMAIN}'
IMG_EXT = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')
CHAT_CATEGORY = ["Travel", "Sports", "Interview", "English Skills"]
CHAT_CATEGORY_IMAGE_URL = ["/templates/chat/travel.jpg", "/templates/chat/sports.jpg", "/templates/chat/interview.jpg", "/templates/chat/english_skills.jpg"]

SYSTEM_INSTRUCTION = f"""
        You are a professional English oral assessment assistant, specializing in providing improvement suggestions and improved text for non-native Taiwanese college students' answers.
        
        userAnswer represents the user's oral answer
        question represents the question
        standard represents the assessment criteria and score range
        maxScore represents the maximum score
        
        Sample Question #1: Based on the vocabulary provided, explain the meaning of the word "Brochure".
        Sample Question #2: <An image shows a scene inside a bank or a similar service center. Several people are lined up in a queue, waiting at counters, likely to speak with tellers or staff behind glass or plastic dividers.>
        
        10 points - Excellent Communicator
        Response is complete, fluent, and logical, with at least four sentences, using a variety of sentence structures and rich vocabulary, able to provide appropriate examples and explanations. Grammar structure is accurate, vocabulary usage is appropriate, sentences are natural and error-free, able to clearly express details and viewpoints, avoiding word order errors, part-of-speech misuse, and mixing in Chinese vocabulary. Even if there are occasional minor errors, they do not affect understanding. Scoring feedback should encourage students to maintain high standards of expression and try to further enrich details or examples to improve language flexibility.
        Answer #1: A brochure is a printed material designed to provide detailed information about a
        product, service, or event, often including eye-catching images and persuasive text to attract potential customers.
        Answer #2: The picture shows people standing in line at a bank counter, each waiting patiently 
        for their turn. The setting appears orderly, and the individuals are maintaining a 
        proper distance.
        
        9 points - Good Communicator
        Response is clear, able to effectively express ideas, grammar structure is rich, occasional small errors (such as word order errors or part-of-speech misuse), but these errors do not affect overall understanding. Able to clearly express main viewpoints and effectively organize sentences. Scoring feedback should guide students to pay attention to a few errors and emphasize grammar accuracy and sentence variety to achieve higher expression levels, avoiding word order issues and part-of-speech misuse.
        Answer #1: A brochure is a printed document that gives information about a specific product 
        or service, usually featuring attractive images and descriptions to engage the reader.
        Answer #2: Several people are standing in line at a bank. They are waiting for their turn at the 
        counter in an organized manner. 
        
        8 points - Good Communicator
        Response is mostly complete, able to clearly express main ideas, but occasional grammar errors (such as word order errors, verb transitivity errors) affect understanding, and sentence variety is slightly insufficient. Students may incorrectly use adjectives or prepositions as verbs. Additionally, mixing in Chinese vocabulary occasionally occurs in sentences. Scoring feedback should suggest students strengthen sentence variety, improve vocabulary accuracy and richness, and emphasize grammar structure and word order accuracy, avoiding vocabulary mixing and part-of-speech misuse.
        Answer #1: A brochure is a type of printed material that explains a product or service, often 
        with pictures and text to help people understand what is being offered.
        Answer #2: The image shows people waiting in line at a bank counter. They are standing one 
        behind another. 
        
        7 points - Basic Communicator 
        Able to express main concepts, but lacks detail, response consists mostly of simple sentences, grammar errors occasionally affect understanding (such as complex sentence structure errors, verb transitivity errors). Students may have word order errors, improper verb-noun collocations, or incorrectly use adjectives or prepositions as verbs. Scoring feedback should remind students to add more details, improve grammar accuracy, and help expand vocabulary range, strengthening grammar and sentence structure clarity.
        Answer #1: A brochure is a printed piece that tells about a product or service, usually with 
        some images and information.
        Answer #2: People are lined up at a counter. It looks like they are at a bank, waiting for service.
        
        6 points - Limited Communicator 
        Sentence structure is relatively simple, expression is limited, grammar errors are quite obvious, vocabulary usage is restricted, response content is relatively superficial. Students may confuse adjective and adverb usage, or have subject-verb agreement errors in sentences, affecting sentence fluency and correctness. Scoring feedback should suggest students use more complete sentences, reduce grammar errors, and try to use more vocabulary to improve content richness, thus strengthening expression accuracy and comprehensibility.
        Answer #1: A brochure is a paper that has information about something, often with pictures.
        Answer #2: There are people waiting in line at what seems to be a bank. 
        
        5 points - Simple Communicator 
        Sentences are short, response is single, grammar errors are frequent, vocabulary usage is very limited, seriously affecting communication clarity. Students may not be able to accurately use articles, or have word order errors in simple sentences, causing comprehension difficulties. Scoring feedback should guide students to improve sentence structure, reduce grammar errors, and learn more appropriate vocabulary to strengthen communication effects, improving language clarity and comprehensibility.
        Answer #1: A brochure is a small booklet that gives information.
        Answer #2: People are standing in line at a counter. It looks like a bank. 
        
        4 points - Limited Interaction Ability 
        Response consists mostly of short sentences or phrases, content is relatively one-sided, grammar errors affect understanding, vocabulary usage is extremely limited, and lacks logic. Students may confuse verb tenses and forms, or confuse nouns with verbs and adjectives. Scoring feedback should encourage students to use complete sentences and improve grammar structure and vocabulary selection, helping them improve expression logic and comprehensibility.
        Answer #1: A brochure is paper that shows products.
        Answer #2: People are waiting at a counter in a bank. 
        
        3 points - Extremely Limited Communicator 
        Only able to piece together words, sentence structure is chaotic or incomplete, response content is difficult to understand, vocabulary usage is inappropriate, affecting communication. Scoring feedback should encourage students to try to construct complete sentences and learn basic grammar to improve comprehensibility.
        Answer #1: A brochure is for information. 
        Answer #2: People are standing in line. It looks like a bank. 
        
        2 points - Extremely Low Expression Ability 
        Only able to say single words or phrases, unable to form meaningful sentences, response may be unrelated to the question or extremely simple. Scoring feedback should suggest students learn basic sentence patterns and try simple sentence combinations to improve language expression ability.
        Answer #1: A brochure is a book.
        Answer #2: People are at a bank.
        
        1 point - No Expression Ability 
        Test taker is unable to produce any comprehensible language, may be completely silent. Scoring feedback should suggest students carefully read the question and try to answer, even a simple response can help improve expression ability.
        Answer #1: <Not speaking, nonsense, or not knowing> 
        Answer #2: <Not speaking, nonsense, or not knowing>
        
        If the provided scoring criteria only has four levels:
        4 points - Test taker can use complete sentences to answer questions, content is completely correct, no grammar or information errors. Answer is clear and fluent, able to effectively convey the information required by the question, understandable without modification. Scoring feedback should encourage students to continue maintaining correctness and fluency, and add details to strengthen expression when possible.
        3 points - Test taker's answer is mostly correct, but may have some information missing, affecting response completeness. Even if answer content mostly meets question requirements, sentence structure still needs adjustment. Scoring feedback should guide students to improve sentence structure or detail accuracy, ensuring complete expression of all necessary information.
        2 points - Test taker's answer may only express partial information, making the answer difficult to understand. May not use complete sentences, or answer is too brief, causing unclear information. Scoring feedback should provide more basic suggestions to help students strengthen grammar and sentence structure understanding, ensuring information is complete and correct.
        1 point - Test taker did not answer, or answer content is completely wrong. May only say unrelated words or phrases, or provide information that does not match the question. Scoring feedback should suggest students read the question and try to respond using complete sentences to improve basic expression ability.
        
        You need to execute the task in 4 steps, Think step by step:
        1. Analyze and provide suggestions for the provided evaluation aspects: clarity of expression, grammar usage, vocabulary, response complexity, topic relevance.
        2. Score the student's oral answer according to the provided scoring criteria examples and levels (It's okay to give out a full marks).
        3. Provide specific analysis and suggestions, such as correcting grammar errors, suggesting more natural sentences or increasing vocabulary, respond in Traditional Chinese (zh-TW) and English (en-US).
        4. Based on the student's answer text, extend or improve their answer, respond in English.
        
        IMPORTANT: All Chinese responses must use Traditional Chinese (zh-TW), never use Simplified Chinese.
        
        The JSON object must use the schema: {json.dumps(SpeechAssessment.model_json_schema(), indent=2)}
    """

# NPC Chat Quick Response Prompt (for immediate display, 3-5 seconds)
NPC_CHAT_QUICK_RESPONSE = """
You are {persona} in an immersive mystery game.

Context: {context}
Recent conversation: {history}

Rules:
1. Stay in character, respond naturally (1-3 sentences)
2. Only answer what was asked, no spoilers
3. If user speaks non-English, politely ask them to use English and set is_english=false

Output JSON:
{{
  "npc_reply": "Your in-character response",
  "is_english": true/false
}}
"""

# NPC Evaluation Prompt (async processing, 5-8 seconds)
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
  "feedback_chi": "Past tense questions should use 'did'."
}}
"""

# Question Answer System Instruction - Strict Version
QUESTION_ANSWER_SYSTEM_INSTRUCTION = """
You are a STRICT evaluator assessing a student's answer to a factual question in an educational mystery game.

Question: {question}

Reference Answers (THE ONLY CORRECT ANSWERS):
{reference_answers}

Student's Answer: {user_answer}

=== STRICT EVALUATION CRITERIA ===

**CRITICAL: Content accuracy is the PRIMARY factor. A wrong answer CANNOT get a high score regardless of grammar.**

1. CONTENT ACCURACY (0-7 points) - MOST IMPORTANT:
   For FACTUAL questions (times, codes, numbers, names, specific terms):
   - 7: EXACT MATCH or semantically equivalent to reference answer
   - 5-6: Very close with minor acceptable variations (e.g., "04:18:37" vs "4:18:37", "Red Double-decker Bus" vs "red double decker bus")
   - 3-4: Partially correct - contains some correct elements but missing key parts
   - 1-2: Wrong answer but shows understanding of the question topic
   - 0: Completely wrong, irrelevant, or unrelated answer

   STRICT MATCHING RULES:
   - For TIME answers: Must match exactly (e.g., "4:18:37" - anything else like "3:45" is WRONG = 0 points)
   - For CODE answers: Must match exactly (e.g., "CROWN-X-1859" - any other code is WRONG = 0 points)
   - For NAME answers: Must match the correct name (e.g., "Geoffrey Chaucer" - other names are WRONG = 0 points)
   - For SPECIFIC TERMS: Must match the reference (e.g., "Red Double-decker Bus" - "taxi" is WRONG = 0 points)

2. LANGUAGE QUALITY (0-3 points) - SECONDARY:
   - 3: Perfect or near-perfect grammar and vocabulary
   - 2: Minor errors that don't affect understanding
   - 1: Noticeable errors but still understandable
   - 0: Severe errors or incomprehensible

TOTAL SCORE = Content Accuracy + Language Quality (0-10)

**IMPORTANT SCORING EXAMPLES:**
- Question: "What time is displayed?" Reference: "04:18:37"
  - Student says "4:18:37" -> Content: 7, is_correct: true
  - Student says "four eighteen thirty-seven" -> Content: 7, is_correct: true
  - Student says "3:45" -> Content: 0, is_correct: false (WRONG TIME)
  - Student says "around four o'clock" -> Content: 1-2, is_correct: false (TOO VAGUE)

- Question: "What is the maintenance code?" Reference: "CROWN-X-1859"
  - Student says "CROWN-X-1859" -> Content: 7, is_correct: true
  - Student says "Crown X 1859" -> Content: 6, is_correct: true (format variation OK)
  - Student says "ABC-123" -> Content: 0, is_correct: false (WRONG CODE)

FEEDBACK RULES (IMPORTANT - Focus on Grammar and Vocabulary ONLY):
1. DO NOT reveal the correct answer in feedback_chi or feedback_eng.
2. Focus feedback ONLY on the student's grammar usage and vocabulary accuracy.
3. Point out grammatical errors such as: tense mistakes, subject-verb agreement, article usage, preposition errors.
4. Suggest vocabulary improvements: more precise words, better expressions, avoiding repetition.
5. If the answer is wrong, the reference_comparison can mention the answer is incorrect, but feedback should still focus on language quality.
6. All Chinese MUST be Traditional Chinese, NEVER Simplified Chinese.
7. Keep feedback concise but helpful for language learning.

IMPORTANT: is_correct should ONLY be true if the student's answer matches or is very close to the reference answer.

Output MUST be valid JSON:
{{
  "score": 8,
  "feedback_chi": "Traditional Chinese feedback - ONLY about grammar and vocabulary, DO NOT reveal the answer",
  "feedback_eng": "English feedback - ONLY about grammar and vocabulary, DO NOT reveal the answer",
  "reference_comparison": "Detailed comparison: what student said vs what the answer should be",
  "is_correct": true
}}
"""

# Improvement Hint System Instruction - Customized hints without revealing the answer
IMPROVEMENT_HINT_SYSTEM_INSTRUCTION = """
You are a helpful hint provider for an educational mystery game. A student has answered a question and needs guidance to improve their answer WITHOUT being told the correct answer directly.

Question: {question}

Reference Answer (DO NOT REVEAL THIS): {reference_answer}

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
  "hint_chi": "Traditional Chinese improvement hint that guides the student without revealing the answer"
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
    You are a professional English teaching expert, analyzing conversation transcripts between non-native English speakers (Taiwanese college students) and AI. Please provide concise analysis within 200 words using the sandwich communication method (positive feedback - improvement suggestions - encouragement) in Traditional Chinese and English.

    Analysis Focus Areas:
    - Vocabulary Variety: Does the student repeat the same words?
    - Basic Grammar: Subject-verb agreement (evaluate using oral standards, not overly strict)
    - Response Relevance: Does the student answer questions appropriately, not off-topic?

    Start by highlighting what the student did well, then specifically point out 1-2 main issues and solutions, finally, provide positive support.

    Keep within 200 words, use a friendly and specific tone and first person perspective, in plain text format.
    
    IMPORTANT: All Chinese content must use Traditional Chinese (zh-TW), never use Simplified Chinese.

    And based on the student's overall performance, give a score from 1-10.
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
                        text=f'{summary.score}',
                        wrap=True,
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
                        if summary.chi_summary else 'No summary available.',
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
        if any([keyword in category for keyword in ['ex4', 'ex5', 'ex6']]):
            continue
        for num, _ in enumerate(question.content):
            total += 1
            if getHistory(user_id, f'{category}-{num}'):
                continue
            if category not in progress:
                progress[category] = []
            progress[category].append(num)
                
    if len(progress) == 0:
        return TextMessage(text="You have completed all questions.\n您已完成所有問題。")
    
    message = f"Questions Unanswered ({sum(len(v) for v in progress.values())}):\n尚未回答的問題:\n"
    for category, subs in progress.items():
        if len(subs) > 0:
            message += f"\n{rich_menu_manager.get_display_name(category).split('#')[0].strip()}:\n"
        for i, sub in enumerate(subs):
            message += f"{chr(10) if i > 0 else ''} - Q{sub+1}"
    
    return TextMessage(text=message)


async def chat_message(user_id, sub):
    completion = await client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        response_format=QuestionSet,
        max_completion_tokens=512,
        temperature=1.4,
        top_p=0.9,
        frequency_penalty=0.5,
        presence_penalty=0.5,
        messages=[
            {
                "role": "user",
                "content": f"As a non-native English college student, generate three questions that are suitable for me to practice about {CHAT_CATEGORY[sub]} in English.\n",
            }
        ],
    )
    result = QuestionSet.model_validate_json(completion.choices[0].message.content)
    messages = []
    contents = [
        FlexImage(
            url=f'{URL}{CHAT_CATEGORY_IMAGE_URL[sub]}',
            size='full',
            aspect_ratio='1:1',
            aspect_mode='cover',
            margin='md',
            flex=1,
        ),
        FlexText(
            text=CHAT_CATEGORY[sub].replace(' ', '\n', 1) if len(CHAT_CATEGORY[sub]) > 12 else CHAT_CATEGORY[sub],
            wrap=True,
            weight='bold',
            size='xxl',
            flex=1,
        ),
        FlexText(
            text=f'Talk with CoachGPT!\n與 CoachGPT 進行語音對話！',
            color='#5b5b5b',
            size='lg',
            wrap=True,
            flex=1,
        ),
    ]

    messages.append(FlexBubble(  
            size='mega',
            body=FlexBox(
                layout='vertical',
                wrap=True,
                contents=contents,
                justifyContent='space-around',
            ),
        )
    )
    messages.append(FlexBubble(
        size='mega', 
        body=FlexBox(
            layout='vertical',
            spacing='lg',
            justifyContent='center',
            contents=[
                FlexText(
                    text='Reference Chatting Questions\n參考聊天問題',
                    wrap=True,
                    weight='bold',
                    size='xl',
                    align='center',
                ),
                FlexText(
                    text='\n\n'.join([f'Q{i+1}. {q}' for i, q in enumerate(result.questions)]),
                    wrap=True,
                    size='lg',
                ),
            ]
        ),
        footer=FlexBox(
            layout='vertical',
            alignItems='center',
            contents=[
                FlexText(
                    text='Choose a question to start!\n選擇問題開始聊天',
                    size='md',
                    wrap=True,
                    align='center',
                )
            ]
        )
    ))
    return FlexMessage(
        altText='Chat',
        contents=FlexCarousel(contents=messages)
    )


async def carousel_message(user_id, category, unit):
    if len(question_manager.get_all_questions(category)) < unit:
        return None
    cols = []
    for sub,j in enumerate(question_manager.get_unit(category,unit-1)):
        body = FlexBox(
            layout='vertical',
            spacing='lg',
            contents=[
                FlexText(
                    text=f'Oral Practice Q{unit}-{sub+1}\n口語練習',
                    wrap=True,
                    weight='bold',
                    size='xl',
                    align='center',
                ),
                # Hint text
                FlexText(
                    text='Click button below\n點擊下方按鈕',
                    wrap=True,
                    size='xs',
                    color='#888888',
                    align='center',
                    margin='md',
                ),
                FlexButton(
                    action=PostbackAction(
                        label='Enter',
                        data=f'action=record&unit={unit-1}&sub={sub}'
                    ),
                    height='sm',
                    style='primary',
                ),
            ]
        )
        if getHistory(user_id, f'{category}-{unit-1}-{sub}'):
            body.contents.append(
                FlexButton(
                    action=PostbackAction(
                        label='Result',
                        data=f'action=result&category={category}&unit={unit-1}&sub={sub}'
                    ),
                    height='sm',
                    style='secondary',
                )
            )
        cols.append(FlexBubble(
            hero=FlexImage(
                url=f'{URL}/templates/{category}/cover{unit}-{sub+1}.jpg',
                size='full',
                aspect_ratio='20:13',
                aspect_mode='cover',
            ),
            body=body
        ))
    if len(question_manager.get_all_questions(category)) > unit:
        cols.append(FlexBubble(
            body=FlexBox(
                contents=[
                    FlexText(
                        text=f'Next\n前往下一單元',
                        weight='bold',
                        size='xl',
                    ),
                    # Hint text
                    FlexText(
                        text='Tap this card\n點擊此卡片',
                        wrap=True,
                        size='xs',
                        color='#888888',
                        align='center',
                        margin='md',
                    ),
                ],
                layout='vertical',
                alignItems='center',
                justifyContent='center',
                action=PostbackAction(
                    label='Next Unit',
                    data=f'action=unit&unit={unit+1}'
                )
            ),
        ))
    msg = FlexMessage(
        altText='Unit Navigation',
        contents=FlexCarousel(contents=cols)
    )
    return msg


async def convert_to_voice(text: str, voice: str):
    response = await client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice=voice,
        input=text,
        instructions="Speak slowly and clearly with a calm and friendly tone.",
        response_format="mp3"
    )
    return response

async def get_assessment(system: str, user_content: str):
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_content}
        ],
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content

async def get_summary(system: str, user_content: str):
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_content}
        ]
    )
    return response.choices[0].message.content

async def get_assessment_with_image(system: str, user_content: str, image_url: str):
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": [
                {"type": "text", "text": user_content},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]}
        ],
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content

async def result_message(user_id, category, unit, sub) -> FlexMessage:
    history = getHistory(user_id, f'{category}-{unit}-{sub}')
    if history is None:
        return FlexMessage(
            altText='History',
            contents=FlexBubble(
                body=FlexBox(
                    layout='vertical',
                    contents=[
                        FlexText(
                            text='No history, please answer first.\n尚無歷史紀錄，請先回答本題',
                            wrap=True,
                        )
                    ]
                )
            )
        )
    cols = []
    for idx, item in enumerate(history):
        display_feedback = get_display_feedback()
        
        body_contents = [
            FlexText(
                text=f'Attempt {idx+1}\n第 {idx+1} 次作答',
                wrap=True,
                weight='bold',
                size='xl',
            ),
            FlexText(
                text=f'Score: {item.score}\n分數',
                wrap=True,
            ),
        ]
        
        # Only show feedback when display_feedback is true
        if display_feedback:
            body_contents.extend([
                FlexText(
                    text=f'Tips: {item.eng_suggestion}',
                    wrap=True,
                    margin='md',
                ),
                FlexText(
                    text=f'Suggestion: {item.chi_suggestion}',
                    wrap=True,
                ),
            ])
        
        cols.append(FlexBubble(
            body=FlexBox(
                layout='vertical',
                contents=body_contents
            )
        ))
    return FlexMessage(
        altText='History',
        contents=FlexCarousel(contents=cols)
    )

async def record_message(user_id, category, unit, sub):
    question = question_manager.get_question(category, unit, sub)
    user_state = get_user_state(user_id)
    user_state.sub = sub
    
    body_contents = [
        FlexText(
            text=question.text,
            wrap=True,
            weight='bold',
            size='lg',
        )
    ]
    
    if question.extra_info:
        for info in question.extra_info:
            body_contents.append(FlexText(
                text=f'{info[0]}: {info[1]}',
                wrap=True,
                margin='sm',
            ))
    
    footer = FlexBox(
        layout='horizontal',
        spacing='sm',
        contents=[
            FlexButton(
                action=PostbackAction(
                    label='Start',
                    data=f'action=start&category={category}&unit={unit}&sub={sub}'
                ),
                height='sm',
                style='primary',
            ),
        ]
    )
    
    if getHistory(user_id, f'{category}-{unit-1}-{sub}'):
        footer.contents.append(
            FlexButton(
                action=PostbackAction(
                    label='Result',
                    data=f'action=result&category={category}&unit={unit-1}&sub={sub}'
                ),
                height='sm',
                style='secondary',
            )
        )
    
    bubble = FlexBubble(
        body=FlexBox(
            layout='vertical',
            contents=body_contents
        ),
        footer=footer
    )
    
    if question.image_url:
        if question.image_url.lower().endswith(IMG_EXT):
            bubble.hero = FlexImage(
                url=f'{URL}{question.image_url}',
                size='full',
                aspect_ratio='20:13',
                aspect_mode='cover',
            )

    return FlexMessage(
        altText='Recording Question',
        contents=bubble
    )

async def question_message(user_id, category, unit):
    questions = question_manager.get_all_questions(category)
    questions = questions[unit]
    user_state = get_user_state(user_id)
    cols = []
    for sub, question in enumerate(questions.content):
        body = FlexBox(
            layout='vertical',
            contents=[
                FlexText(
                    text=question.text,
                    wrap=True,
                    size='md',
                ),
                FlexButton(
                    action=PostbackAction(
                        label='Answer',
                        data=f'action=record&sub={sub}'
                    ),
                    height='sm',
                    style='primary',
                ),
            ]
        )
        if getHistory(user_id, f'{category}-{unit-1}-{sub}'):
            body.contents.append(
                FlexButton(
                    action=PostbackAction(
                        label='Result',
                        data=f'action=result&category={category}&unit={unit-1}&sub={sub}'
                    ),
                    height='sm',
                    style='secondary',
                )
            )
        cols.append(FlexBubble(
            hero=FlexImage(
                url=f'{URL}/templates/{category}/cover{unit}-{sub+1}.jpg',
                size='full',
                aspect_ratio='20:13',
                aspect_mode='cover',
            ),
            body=body
        ))
    if len(question_manager.get_all_questions(category)) > unit:
        cols.append(FlexBubble(
            body=FlexBox(
                contents=[
                    FlexText(
                            text=f'Next\n前往下一單元',
                            weight='bold',
                            size='xl',
                        ),],
                layout='vertical',
                alignItems='center',
                justifyContent='center',
                action=PostbackAction(
                    label='Next Unit',
                    data=f'action=unit&unit={unit+1}'
                )
            ),
        ))
    msg = FlexMessage(
        altText='Unit Navigation',
        contents=FlexCarousel(contents=cols)
    )
    return msg

# ========== Game Message Functions ==========

async def game_prologue_message(theme_id: str, user_id: str) -> list:
    """Display theme prologue/background story and automatically show current level with questions"""
    messages = []
    theme_config = load_game_theme_config(theme_id)
    
    if not theme_config:
        return [FlexMessage(
            altText='Theme not found',
            contents=FlexBubble(
                body=FlexBox(
                    layout='vertical',
                    contents=[FlexText(text='Theme configuration not found.\n找不到主題設定。', wrap=True)]
                )
            )
        )]
    
    # If there's an intro video, play it first
    if theme_config.intro_video:
        video_url = f'{URL}/templates/videos/{theme_config.intro_video}'
        # Use cover image or video preview
        preview_url = f'{URL}{theme_config.cover_image}' if theme_config.cover_image else f'{URL}/templates/videos/{theme_config.intro_video.replace(".mp4", "_preview.jpg")}'
        messages.append(
            VideoMessage(
                originalContentUrl=video_url,
                previewImageUrl=preview_url
            )
        )
    
    bubbles = []
    
    # Title card
    title_bubble = FlexBubble(
        size='giga',
        body=FlexBox(
            layout='vertical',
            justifyContent='center',
            alignItems='center',
            spacing='lg',
            contents=[
                FlexText(
                    text=theme_config.name,
                    wrap=True,
                    weight='bold',
                    size='xxl',
                    align='center',
                    color="#1a1a2e",
                ),
                FlexText(
                    text='Story Background\n故事背景',
                    wrap=True,
                    size='lg',
                    align='center',
                    color="#4a4a6a",
                ),
            ]
        )
    )
    
    if theme_config.cover_image:
        title_bubble.hero = FlexImage(
            url=f'{URL}{theme_config.cover_image}',
            size='full',
            aspect_ratio='20:13',
            aspect_mode='cover',
        )
    
    bubbles.append(title_bubble)
    
    # Prologue card
    prologue_bubble = FlexBubble(
        size='giga',
        body=FlexBox(
            layout='vertical',
            spacing='md',
            contents=[
                FlexText(
                    text='Background\n故事背景',
                    wrap=True,
                    weight='bold',
                    size='xl',
                ),
                FlexText(
                    text=theme_config.prologue,
                    wrap=True,
                    size='md',
                    color='#5b5b5b',
                ),
            ]
        )
    )
    bubbles.append(prologue_bubble)
    
    # NPC introduction card
    if theme_config.npcs:
        npc_contents = [
            FlexText(
                text='Characters\n登場角色',
                wrap=True,
                weight='bold',
                size='xl',
            ),
        ]
        for npc in theme_config.npcs:
            # Use description instead of persona for user display
            npc_text = f"- {npc.name}"
            if npc.description:
                npc_text += f": {npc.description}"
            npc_contents.append(
                FlexText(
                    text=npc_text,
                    wrap=True,
                    size='md',
                    color='#5b5b5b',
                    margin='sm',
                )
            )
        
        npc_bubble = FlexBubble(
            size='giga',
            body=FlexBox(
                layout='vertical',
                spacing='sm',
                contents=npc_contents
            )
        )
        bubbles.append(npc_bubble)
    
    messages.append(FlexMessage(
        altText=f'{theme_config.name} - Background',
        contents=FlexCarousel(contents=bubbles)
    ))
    
    # [MODIFIED] Automatically show current level intro and questions
    current_level = get_user_unlocked_level(user_id, theme_id)
    level_messages = await game_level_intro_message(theme_id, current_level, user_id)
    messages.extend(level_messages)
    
    # [NEW] Automatically show questions for the current level
    questions_message = await game_questions_carousel(theme_id, current_level, user_id)
    messages.append(questions_message)
    
    # [NEW] Add NPC hint message
    npc_hint_message = await game_npc_hint_message()
    messages.append(npc_hint_message)
    
    return messages

# [NEW] NPC hint message function
async def game_npc_hint_message() -> TextMessage:
    """Display hint message prompting user to click on NPC characters in the menu"""
    hint_text = (
        "Tip: Click on the character icons in the menu below to chat with NPCs and get clues for solving the puzzle!\n\n"
        "提示：點擊下方選單中的角色圖示，與 NPC 聊天以獲得解謎線索！"
    )
    return TextMessage(text=hint_text)

async def game_level_intro_message(theme_id: str, level_idx: int, user_id: str) -> list:
    """Display level introduction including video"""
    messages = []
    level_info = get_game_level_info(theme_id, level_idx)
    
    if not level_info:
        return [TextMessage(text='Level not found.\n找不到關卡。')]
    
    # Play video if available
    if level_info.get('video_file'):
        video_url = f'{URL}/templates/videos/{level_info["video_file"]}'
        preview_url = f'{URL}/templates/videos/{level_info["video_file"].replace(".mp4", "_preview.jpg")}'
        messages.append(
            VideoMessage(
                originalContentUrl=video_url,
                previewImageUrl=preview_url
            )
        )
    
    # Level description card
    theme_config = load_game_theme_config(theme_id)
    theme_name = theme_config.name if theme_config else theme_id
    
    level_bubble = FlexBubble(
        size='giga',
        body=FlexBox(
            layout='vertical',
            spacing='lg',
            contents=[
                FlexText(
                    text=f'Level {level_idx + 1}: {level_info["title"]}\n關卡 {level_idx + 1}',
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
            ]
        ),
        # [MODIFIED] Removed the "Show Questions" button since questions are auto-shown
    )
    
    messages.append(FlexMessage(
        altText=f'Level {level_idx + 1}',
        contents=level_bubble
    ))
    
    return messages

async def game_questions_carousel(theme_id: str, level_idx: int, user_id: str, force_show_all: bool = False) -> FlexMessage:
    """Display level questions as scrollable cards
    
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
    
    if not level_info:
        return FlexMessage(
            altText='Questions not found',
            contents=FlexBubble(
                body=FlexBox(
                    layout='vertical',
                    contents=[FlexText(text='Level questions not found.\n找不到關卡題目。', wrap=True)]
                )
            )
        )
    
    bubbles = []
    questions = level_info.get('questions', [])
    
    # Limit to configured questions per level
    questions = questions[:questions_per_level]
    
    # Check if all questions are passed
    all_passed = is_level_all_questions_passed(user_id, theme_id, level_idx)
    min_score = get_min_score_to_pass()
    
    # If all questions passed or force show, display all questions for free selection
    if all_passed or force_show_all:
        for q_idx, question in enumerate(questions):
            # Check if user has answered this question
            best_score = get_user_question_score(user_id, theme_id, level_idx, q_idx)
            has_answered = best_score > 0
            is_passed = best_score >= min_score
            
            body_contents = [
                FlexText(
                    text=f'Question {q_idx + 1}\n題目 {q_idx + 1}',
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
                # Hint text
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
        # Not all questions passed, show only current question to answer
        current_q_idx = get_next_unpassed_question(user_id, theme_id, level_idx)
        if current_q_idx < 0 or current_q_idx >= len(questions):
            current_q_idx = 0
        
        question = questions[current_q_idx]
        best_score = get_user_question_score(user_id, theme_id, level_idx, current_q_idx)
        has_answered = best_score > 0
        
        body_contents = [
            FlexText(
                text=f'Question {current_q_idx + 1}/{len(questions)}\n題目 {current_q_idx + 1}/{len(questions)}',
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
            # Hint text
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
                text='Level Progress\n關卡進度',
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
                    text=f'Q{q_i + 1}: {status}',
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
        altText=f'Level {level_idx + 1} Questions',
        contents=FlexCarousel(contents=bubbles)
    )

async def game_score_message(user_id: str, theme_id: str, level_idx: int, question_idx: int, 
                             score: int, is_new_high: bool, feedback_eng: str, feedback_chi: str,
                             reference_comparison: str = "") -> FlexMessage:
    """Display game result and score - English feedback first, Chinese feedback second
    
    [MODIFIED] Button logic based on score:
    - Score < 6: "Try Again", "Improvement Hint", "Question List"
    - Score >= 6 but < 10: "Try Again", "Improvement Hint", "Question List", "Next Question"
    - Score = 10: "Question List", "Next Question" (no improvement hint needed)
    """
    display_feedback = get_display_feedback()
    theme_total = get_user_game_score(user_id, theme_id)
    max_score = get_max_theme_score()
    
    bubbles = []
    
    # Main result card - score always displayed
    main_contents = [
        FlexText(
            text=f'Q{question_idx + 1} Result\n結果',
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
            text=f'Theme Total: {theme_total}/{max_score}\n主題總分',
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
    
    # Only show feedback cards when display_feedback is true and there is feedback content
    if display_feedback:
        # English feedback card (shown first)
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
        
        # Chinese feedback card (shown second)
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
        altText=f'Q{question_idx + 1} Result',
        contents=FlexCarousel(contents=bubbles)
    )
    
    # [MODIFIED] Quick reply buttons based on score thresholds
    from utils.file_utils import get_min_score_to_pass, is_level_all_questions_passed, get_next_unpassed_question, get_questions_per_level
    min_score = get_min_score_to_pass()
    is_passed = score >= min_score
    is_perfect = score >= 10
    all_level_passed = is_level_all_questions_passed(user_id, theme_id, level_idx)
    questions_per_level = get_questions_per_level()
    
    quick_reply_items = []
    
    # [MODIFIED] Button logic based on score
    if is_perfect:
        # Score = 10: No improvement hint needed, only "Question List" and "Next Question"
        pass  # No "Try Again" or "Improvement Hint" for perfect score
    else:
        # Score < 10: Show "Try Again" button
        quick_reply_items.append(
            QuickReplyItem(action=PostbackAction(
                label='Try Again',
                data=f'action=game_answer&theme={theme_id}&level={level_idx}&question={question_idx}'
            ))
        )
        
        # Score < 10: Show "Improvement Hint" button
        quick_reply_items.append(
            QuickReplyItem(action=PostbackAction(
                label='Improvement Hint',
                data=f'action=game_improvement_hint&theme={theme_id}&level={level_idx}&question={question_idx}'
            ))
        )
    
    # Question List button (always shown)
    quick_reply_items.append(
        QuickReplyItem(action=PostbackAction(
            label='Question List',
            data=f'action=game_questions&theme={theme_id}&level={level_idx}'
        ))
    )
    
    # If current question is passed, show "Next Question" button (if there's a next question)
    if is_passed:
        next_q_idx = get_next_unpassed_question(user_id, theme_id, level_idx)
        if next_q_idx >= 0 and next_q_idx < questions_per_level:
            quick_reply_items.append(
                QuickReplyItem(action=PostbackAction(
                    label=f'Next (Q{next_q_idx + 1})',
                    data=f'action=game_answer&theme={theme_id}&level={level_idx}&question={next_q_idx}'
                ))
            )
        elif all_level_passed:
            # Level completed
            quick_reply_items.append(
                QuickReplyItem(action=PostbackAction(
                    label='Level Complete!',
                    data=f'action=game_levels&theme={theme_id}'
                ))
            )
    
    msg.quick_reply = QuickReply(items=quick_reply_items)
    
    return msg

async def game_improvement_hint_message(theme_id: str, level_idx: int, question_idx: int,
                                         hint_eng: str, hint_chi: str) -> FlexMessage:
    """Display improvement hint message (without revealing the answer)"""
    # [NEW] Get hint usage count
    bubbles = []
    
    # English hint card
    eng_bubble = FlexBubble(
        size='giga',
        body=FlexBox(
            layout='vertical',
            spacing='sm',
            contents=[
                FlexText(
                    text='Improvement Hint',
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
                    text='Improvement Hint',
                    wrap=True,
                    weight='bold',
                    size='xl',
                    color='#0066cc',
                ),
                FlexText(
                    text=hint_chi if hint_chi else "暫無改善提示。",
                    wrap=True,
                    size='md',
                    color='#5b5b5b',
                    margin='md',
                ),
            ]
        )
    )
    bubbles.append(chi_bubble)
    
    # If no bubbles (shouldn't happen but just in case)
    if not bubbles:
        bubbles.append(
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
        )

    msg = FlexMessage(
        altText=f'Q{question_idx + 1} Improvement Hint',
        contents=FlexCarousel(contents=bubbles)
    )
    
    # Quick reply buttons
    msg.quick_reply = QuickReply(items=[
        QuickReplyItem(action=PostbackAction(
            label='Try Again',
            data=f'action=game_answer&theme={theme_id}&level={level_idx}&question={question_idx}'
        )),
        QuickReplyItem(action=PostbackAction(
            label='Question List',
            data=f'action=game_questions&theme={theme_id}&level={level_idx}'
        )),
    ])
    
    return msg

async def game_npc_chat_response_message(npc_name: str, npc_reply: str, 
                                          is_english: bool = True,
                                          npc_image: str = None) -> FlexMessage:
    """Display NPC quick response (immediately displayed), with random character image
    
    Args:
        npc_name: NPC name
        npc_reply: NPC reply content
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
    
    # If there's an NPC image, randomly select a variant and add to reply card
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
    
    return FlexMessage(
        altText=f'{npc_name} Response',
        contents=FlexCarousel(contents=bubbles)
    )

async def game_npc_evaluation_message(npc_name: str, language_score: int, 
                                      relevance_score: int, feedback_eng: str, 
                                      feedback_chi: str) -> FlexMessage:
    """Display NPC conversation evaluation (async sent)"""
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
    
    # If there's feedback, add bilingual feedback
    if feedback_eng and feedback_eng.strip():
        score_contents.append(
            FlexText(
                text='',
                margin='lg',
            )
        )
        score_contents.append(
            FlexText(
                text='Language Feedback',
                wrap=True,
                weight='bold',
                size='md',
                color='#1a1a2e',
            )
        )
        score_contents.append(
            FlexText(
                text=f'EN: {feedback_eng}',
                wrap=True,
                size='sm',
                color='#5b5b5b',
                margin='sm',
            )
        )
        if feedback_chi and feedback_chi.strip():
            score_contents.append(
                FlexText(
                    text=f'TW: {feedback_chi}',
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
        altText=f'{npc_name} Conversation Evaluation',
        contents=FlexCarousel(contents=bubbles)
    )

async def game_theme_select_message() -> FlexMessage:
    """Display theme selection cards"""
    from utils.file_utils import get_game_themes
    
    themes = get_game_themes()
    bubbles = []
    
    for idx, theme_id in enumerate(themes):
        theme_config = load_game_theme_config(theme_id)
        
        if theme_config:
            theme_name = theme_config.name
            cover_image = theme_config.cover_image
        else:
            theme_name = f'Theme {idx + 1}'
            cover_image = None
        
        body = FlexBox(
            layout='vertical',
            spacing='lg',
            justifyContent='center',
            alignItems='center',
            contents=[
                FlexText(
                    text=theme_name,
                    wrap=True,
                    weight='bold',
                    size='xl',
                    align='center',
                ),
                # Hint text
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
                        label='Enter',
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
    
    return FlexMessage(
        altText='Select Theme',
        contents=FlexCarousel(contents=bubbles)
    )

async def game_npc_select_message(theme_id: str, user_id: str) -> FlexMessage:
    """Display NPC selection interface - with images and descriptions"""
    print(f"[DEBUG] game_npc_select_message called with theme_id={theme_id}, user_id={user_id}")
    
    theme_config = load_game_theme_config(theme_id)
    
    if not theme_config:
        print(f"[WARNING] Theme config not found in game_npc_select_message for theme_id={theme_id}")
        return FlexMessage(
            altText='Theme not found',
            contents=FlexBubble(
                body=FlexBox(
                    layout='vertical',
                    contents=[
                        FlexText(text='Theme config not found.\n找不到主題配置。', wrap=True),
                        FlexText(
                            text=f'Theme ID: {theme_id}',
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
                    text=f"Score: {progress['total_score']}/{progress['max_score']}\n總分",
                    wrap=True,
                    size='lg',
                    align='center',
                    color='#00aa00',
                ),
                FlexText(
                    text=f"Current Level: {progress['current_level'] + 1}\n目前關卡",
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
        
        # Display description instead of persona
        if npc.description:
            body_contents.append(
                FlexText(
                    text=npc.description,
                    wrap=True,
                    size='sm',
                    color='#5b5b5b',
                    margin='sm',
                )
            )
        
        # Hint text
        body_contents.append(
            FlexText(
                text='Click button below\n點擊下方按鈕',
                wrap=True,
                size='xs',
                color='#888888',
                align='center',
                margin='sm',
            )
        )
        
        body_contents.append(
            FlexButton(
                action=PostbackAction(
                    label='Talk',
                    data=f'action=game_npc&theme={theme_id}&npc={npc_idx}'
                ),
                style='primary',
                margin='md',
            )
        )
        
        npc_bubble = FlexBubble(
            size='mega',
            body=FlexBox(
                layout='vertical',
                spacing='md',
                justifyContent='center',
                alignItems='center',
                contents=body_contents
            )
        )
        
        # If there's an image, display it
        if npc.image:
            npc_bubble.hero = FlexImage(
                url=f'{URL}/templates/people_pic/{npc.image}',
                size='full',
                aspect_ratio='1:1',
                aspect_mode='cover',
            )
        
        bubbles.append(npc_bubble)
    
    return FlexMessage(
        altText=f'{theme_config.name} - Select NPC',
        contents=FlexCarousel(contents=bubbles)
    )

async def game_npc_card_message(theme_id: str, npc_idx: int) -> FlexMessage:
    """Display single NPC card - with image and description"""
    print(f"[DEBUG] game_npc_card_message called with theme_id={theme_id}, npc_idx={npc_idx}")
    
    theme_config = load_game_theme_config(theme_id)
    
    if not theme_config:
        print(f"[WARNING] Theme config not found for theme_id={theme_id}")
        return FlexMessage(
            altText='Theme not found',
            contents=FlexBubble(
                body=FlexBox(
                    layout='vertical',
                    contents=[
                        FlexText(text='Theme config not found.\n找不到主題配置。', wrap=True),
                        FlexText(
                            text=f'Theme ID: {theme_id}',
                            wrap=True,
                            size='sm',
                            color='#888888',
                            margin='md'
                        ),
                        FlexText(
                            text='Please check if theme_config.json exists.\n請確認 theme_config.json 檔案存在。',
                            wrap=True,
                            size='sm',
                            color='#888888',
                            margin='md'
                        )
                    ]
                )
            )
        )
    
    npc = theme_config.get_npc(npc_idx)
    if not npc:
        print(f"[WARNING] NPC not found for theme_id={theme_id}, npc_idx={npc_idx}")
        return FlexMessage(
            altText='NPC not found',
            contents=FlexBubble(
                body=FlexBox(
                    layout='vertical',
                    contents=[
                        FlexText(text='NPC not found.\n找不到角色。', wrap=True),
                        FlexText(
                            text=f'NPC Index: {npc_idx} (Available: {len(theme_config.npcs)})',
                            wrap=True,
                            size='sm',
                            color='#888888',
                            margin='md'
                        )
                    ]
                )
            )
        )
    
    print(f"[DEBUG] NPC found: name={npc.name}, has_description={bool(npc.description)}, has_image={bool(npc.image)}")
    
    body_contents = [
        FlexText(
            text=npc.name,
            wrap=True,
            weight='bold',
            size='xl',
            align='center',
        ),
    ]
    
    # Display description instead of persona
    if npc.description:
        body_contents.append(
            FlexText(
                text=npc.description,
                wrap=True,
                size='md',
                color='#5b5b5b',
                margin='md',
            )
        )
    
    body_contents.append(
        FlexText(
            text='Please speak in English\n請用英文對話',
            wrap=True,
            size='sm',
            color='#0066cc',
            margin='lg',
            align='center',
        )
    )
    
    bubble = FlexBubble(
        size='giga',
        body=FlexBox(
            layout='vertical',
            spacing='md',
            justifyContent='center',
            alignItems='center',
            contents=body_contents
        )
    )
    
    # If there's an image, display it
    if npc.image:
        bubble.hero = FlexImage(
            url=f'{URL}/templates/people_pic/{npc.image}',
            size='full',
            aspect_ratio='3:4',
            aspect_mode='cover',
        )
    
    return FlexMessage(
        altText=f'{npc.name} - Talk',
        contents=bubble
    )

async def game_level_select_message(theme_id: str, user_id: str) -> FlexMessage:
    """Display level selection interface - only show unlocked levels"""
    theme_config = load_game_theme_config(theme_id)
    
    if not theme_config:
        return FlexMessage(
            altText='Theme not found',
            contents=FlexBubble(
                body=FlexBox(
                    layout='vertical',
                    contents=[FlexText(text='Theme not found.\n找不到主題。', wrap=True)]
                )
            )
        )
    
    # Get user's highest unlocked level
    unlocked_level = get_user_unlocked_level(user_id, theme_id)
    
    bubbles = []
    
    # Only show unlocked levels
    for level in theme_config.levels:
        if level.id > unlocked_level:
            break  # Don't show locked levels
            
        level_score = get_user_level_score(user_id, theme_id, level.id)
        questions_per_level = get_questions_per_level()
        max_level_score = questions_per_level * 10
        
        # Determine if level is completed
        is_completed = level_score >= questions_per_level * 6  # All questions passed
        
        body_contents = [
            FlexText(
                text=f'Level {level.id + 1}\n關卡 {level.id + 1}',
                wrap=True,
                weight='bold',
                size='lg',
                align='center',
            ),
            FlexText(
                text=level.title,
                wrap=True,
                size='md',
                align='center',
                color='#5b5b5b',
            ),
        ]
        
        if level_score > 0:
            body_contents.append(
                FlexText(
                    text=f'Score: {level_score}/{max_level_score}\n分數',
                    wrap=True,
                    size='sm',
                    align='center',
                    color='#00aa00' if is_completed else '#ff8800',
                    margin='sm',
                )
            )
        
        if is_completed:
            body_contents.append(
                FlexText(
                    text='Completed\n已完成',
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
                    # Hint text
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
                            label='Enter',
                            data=f'action=game_level&theme={theme_id}&level={level.id}'
                        ),
                        style='primary',
                    ),
                ]
            )
        )
        bubbles.append(bubble)
    
    # If there are still locked levels, show hint
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
                        text='Locked',
                        size='xxl',
                        align='center',
                    ),
                    FlexText(
                        text=f'{len(theme_config.levels) - unlocked_level - 1} more levels locked\n還有 {len(theme_config.levels) - unlocked_level - 1} 個關卡未解鎖',
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
    """Display current level questions (for the "Show Questions" button in the menu)"""
    current_level = get_user_unlocked_level(user_id, theme_id)
    return await game_questions_carousel(theme_id, current_level, user_id)

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
        rich_menu_id = get_rich_menu_id('menu')
        await rich_menu_manager.link_rich_menu_to_user(user_id=user_id, rich_menu_id=rich_menu_id)
        user_state.category = 'menu'
    except Exception as e:
        print(e)

async def create_rich_menu():
    await line_bot_api.set_webhook_endpoint(SetWebhookEndpointRequest(endpoint=f'{URL}/callback'))
    configs = load_rich_menu_configs()
    response = await rich_menu_manager.get_all_rich_menus()
    if len(response) != len(configs['rich_menus'].items()):
        print("Deleting all rich menus...")
        for r in response:
            await rich_menu_manager.delete_rich_menu(r.rich_menu_id)
        clear_rich_menu_id()
    
    # Determine default menu based on RAG mode
    target_default = 'menu_game' if config.get('rag_mode', False) else 'menu'
    
    for menu_name, config_data in configs['rich_menus'].items():
        rich_menu_manager.set_display_name(menu_name, config_data.get('chat_bar_text'))
        if get_rich_menu_id(menu_name):
            continue
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
    await save_config()