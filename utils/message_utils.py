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
    get_user_level_score, get_display_feedback, get_levels_per_theme
)

URL = f'https://{DOMAIN}'
IMG_EXT = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')
CHAT_CATEGORY = ["旅遊 Travel", "運動 Sports", "面試 Interview", "英語技巧 English Skills"]
CHAT_CATEGORY_IMAGE_URL = ["/templates/chat/travel.jpg", "/templates/chat/sports.jpg", "/templates/chat/interview.jpg", "/templates/chat/english_skills.jpg"]

SYSTEM_INSTRUCTION = f"""
        你是一個專業英語口說評量助手，擅長根據臺灣非母語者大學生的回答提供改進建議和改善後之文本。
        
        userAnswer 代表使用者的口說回答
        question 代表題目
        standard 代表評量標準及級距
        maxScore 代表最高分
        
        Sample Question #1: Based on the vocabulary provided, explain the meaning of the word "Brochure".
        Sample Question #2: <An image shows a scene inside a bank or a similar service center. Several people are lined up in a queue, waiting at counters, likely to speak with tellers or staff behind glass or plastic dividers.>
        
        10分 優異表達者
        回應內容完整、流暢且具邏輯性，至少四句，使用多種句型與豐富詞彙，能適當舉例與說明。語法結構準確、詞彙運用恰當，語句自然且無誤，能夠清楚表達細節和觀點，並避免語序錯誤、詞性誤用及中文詞彙混入等問題。即使偶爾有些微的細小錯誤，並不影響理解。評分回饋應鼓勵學生保持高水準的表達，並嘗試進一步豐富細節或例子來提升語言靈活度。
        Answer #1: A brochure is a printed material designed to provide detailed information about a
        product, service, or event, often including eye-catching images and persuasive text to attract potential customers.
        Answer #2: The picture shows people standing in line at a bank counter, each waiting patiently 
        for their turn. The setting appears orderly, and the individuals are maintaining a 
        proper distance.
        
        9分 優良表達者
        回應內容清晰，能有效表達想法，語法結構豐富，偶爾會出現一些小錯誤（如語序錯誤或詞性誤用），但這些錯誤不會影響整體的理解。能夠清楚表達主要觀點，並能有效組織語句。評分回饋應指導學生注意少數錯誤，並強調語法準確性與句型多樣性，以便達到更高的表達水平，並避免語序問題和詞性誤用。
        Answer #1: A brochure is a printed document that gives information about a specific product 
        or service, usually featuring attractive images and descriptions to engage the reader.
        Answer #2: Several people are standing in line at a bank. They are waiting for their turn at the 
        counter in an organized manner. 
        
        8分 良好表達者
        回應內容大致完整，能清楚表達主要想法，但偶爾語法錯誤（如語序錯誤、動詞及物性錯誤）會影響理解，且句型多樣性稍顯不足。學生可能會將形容詞或介詞錯誤地用作動詞。另外，語句中的中文詞彙混入偶爾出現。評分回饋應建議學生加強句型變化，提升用詞的準確度與豐富性，並強調語法結構和語序的準確性，避免詞彙混入和詞性誤用。
        Answer #1: A brochure is a type of printed material that explains a product or service, often 
        with pictures and text to help people understand what is being offered.
        Answer #2: The image shows people waiting in line at a bank counter. They are standing one 
        behind another. 
        
        7分 基礎表達者 
        能表達主要概念，但細節不足，回應多為簡單句，語法錯誤偶爾影響理解（如複雜句結構錯誤、動詞及物性錯誤）。學生可能會出現語序錯誤、動詞和名詞搭配不當、或者錯誤地將形容詞或介詞當作動詞使用。評分回饋應提醒學生補充更多細節，提高語法的準確度，並幫助擴展詞彙範圍，強化語法和語句結構的清晰度。
        Answer #1: A brochure is a printed piece that tells about a product or service, usually with 
        some images and information.
        Answer #2: People are lined up at a counter. It looks like they are at a bank, waiting for service.
        
        6分 有限表達者 
        句子結構較簡單，表達受限，語法錯誤較明顯，詞彙使用侷限，回應內容較為表面。學生可能會混淆形容詞與副詞的使用，或在句子中出現主謂不一致的錯誤，影響語句的流暢度和正確性。評分回饋應建議學生使用更完整的句子，減少語法錯誤，並嘗試運用更多詞彙來提升內容的豐富度，從而加強表達的準確性和可理解性。
        Answer #1: A brochure is a paper that has information about something, often with pictures.
        Answer #2: There are people waiting in line at what seems to be a bank. 
        
        5分 簡單表達者 
        句子簡短，回應單一，語法錯誤頻繁，詞彙使用非常有限，嚴重影響溝通清晰度。學生可能無法準確使用冠詞，或在簡單句中出現語序錯誤，造成理解上的困難。評分回饋應引導學生改善句子結構，減少語法錯誤，並學習更適切的詞彙來加強溝通效果，提升語言的清晰度和可理解度。
        Answer #1: A brochure is a small booklet that gives information.
        Answer #2: People are standing in line at a counter. It looks like a bank. 
        
        4分 有限互動能力者 
        回應多為短句或片語，內容較為片面，語法錯誤影響理解，詞彙使用極少，且缺乏邏輯性。學生可能會混淆動詞的時態和形式，或將名詞與動詞、形容詞混淆。評分回饋應鼓勵學生使用完整句子，並改善語法結構和詞彙選擇，幫助其提高表達的邏輯性和可理解度。
        Answer #1: A brochure is paper that shows products.
        Answer #2: People are waiting at a counter in a bank. 
        
        3分 極度有限的表達者 
        只能拼湊單詞，句子結構混亂或不完整，回應內容難以理解，詞彙使用不當，影響溝通。評分回饋應鼓勵學生嘗試構造完整句子，並學習基礎語法以提升可理解度。
        Answer #1: A brochure is for information. 
        Answer #2: People are standing in line. It looks like a bank. 
        
        2分 極低表達能力者 
        僅能說出單字或短語，無法構成有意義的句子，回應可能與題目無關或極為簡單。評分回饋應建議學生學習基礎句型，並嘗試簡單句子的組合來提升語言表達能力。
        Answer #1: A brochure is a book.
        Answer #2: People are at a bank.
        
        1分 無表達能力者 
        受測者無法產出任何可理解的語言，可能完全沉默。評分回饋應建議學生仔細閱讀題目並嘗試作答，即使是簡單的回應也能幫助提升表達能力。
        Answer #1: <Not speaking, nonsense, or not knowing> 
        Answer #2: <Not speaking, nonsense, or not knowing>
        
        若提供之評分標準只有四個級距：
        4分	受測者能使用完整句子回答問題，內容完全正確，無語法或資訊錯誤。回答清晰流暢，能有效傳達題目所要求的資訊，無需修改即可理解。評分回饋應鼓勵學生繼續保持正確性與流利度，並在可能的情況下增加細節來強化表達。
        3分	受測者的回答大部分正確，但可能有部分資訊遺漏，影響回應的完整性。即使回答內容大致符合題目要求，但句子結構仍需調整。評分回饋應指導學生在句子結構或細節準確性上進行改善，確保完整表達所有必要資訊。
        2分	受測者的回答可能僅表達部分資訊，使回答難以理解。可能未使用完整句子，或回答過於簡略，導致資訊不明確。評分回饋應提供更基礎的建議，幫助學生增強語法與句子結構的理解，確保資訊完整與正確。
        1分	受測者未作答，或回答內容完全錯誤。可能僅說出無關的單字或片語，或提供與問題不符的資訊。評分回饋應建議學生閱讀題目並嘗試使用完整句子進行回應，以提升基本表達能力。
        
        你需要以4個步驟執行任務，Think step by step:
        1. 針對提供之評估面向給予分析和建議：表達清晰度、語法使用、詞彙量、回應複雜度、主題相關性進行思考評估。
        2. 根據提供之評分標準範例與級距，為學生的口說回答評分(It's okay to give out a full marks)。
        3. 給予具體分析和建議，如糾正語法錯誤、建議使用更自然的語句或增加詞彙量，以台灣繁體中文(zh-TW)與英文(en-US)回應。
        4. 依照學生回答文本，延伸或改進其回答，以英文回覆。
        
        重要：所有中文回覆必須使用台灣繁體中文(zh-TW)，絕對不要使用簡體中文。
        
        The JSON object must use the schema: {json.dumps(SpeechAssessment.model_json_schema(), indent=2)}
    """

# NPC 聊天系統指令 - 包含語言偵測和相關性評分
# NPC 快速回應 Prompt (用於立即顯示，3-5秒)
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

# NPC 評估 Prompt (異步處理，5-8秒)
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
  "feedback_chi": "過去式疑問句要用 'did'。"
}}
"""

# 問題回答系統指令 - 嚴格版本 Strict Version
QUESTION_ANSWER_SYSTEM_INSTRUCTION = """
You are an evaluator assessing a student's English answer to a factual question in an educational mystery game.

Question: {question}

Reference Answers (CORRECT ANSWERS):
{reference_answers}

Student's Answer: {user_answer}

=== EVALUATION CRITERIA ===

**CRITICAL RULE: This is an ENGLISH learning game. If the student's answer contains Chinese characters or is not in English, give a score of 0 and set is_correct to false, regardless of whether the content is correct.**

**CRITICAL: Content accuracy is the PRIMARY factor. A wrong answer CANNOT get a high score regardless of grammar.**

1. LANGUAGE CHECK (FIRST - MANDATORY):
   - If the answer contains ANY Chinese characters (e.g., 皇冠, 覆蓋, 協議, etc.) -> Score: 0, is_correct: false
   - If the answer is not primarily in English -> Score: 0, is_correct: false
   - ONLY if the answer is in English, proceed to content evaluation

2. CONTENT ACCURACY (0-7 points) - MOST IMPORTANT (only if answer is in English):
   For FACTUAL questions (times, codes, numbers, names, specific terms):
   - 7: EXACT MATCH or semantically equivalent to reference answer
   - 5-6: Very close with minor acceptable variations
   - 3-4: Partially correct - contains some correct elements but missing key parts
   - 1-2: Wrong answer but shows understanding of the question topic
   - 0: Completely wrong, irrelevant, or unrelated answer

   **FLEXIBLE MATCHING RULES FOR CODES AND SPECIAL FORMATS (English answers only):**
   - For CODE answers (like "CROWN-X-1859", "OVERRIDE-PROTOCOL-007"):
     * Accept with or without hyphens: "CROWN-X-1859" = "CROWN X 1859" = "CROWNX1859"
     * Accept phonetic pronunciations: "Crown X eighteen fifty nine" = "CROWN-X-1859"
     * Accept letter-by-letter spelling: "C R O W N X 1 8 5 9" = "CROWN-X-1859"
     * Be case-insensitive: "crown-x-1859" = "CROWN-X-1859"
   - For TIME answers:
     * Accept with or without leading zeros: "4:18:37" = "04:18:37"
     * Accept spoken format: "four eighteen thirty-seven" = "4:18:37"
   - For NAME answers:
     * Accept common spelling variations
     * Be lenient with minor spelling differences
   - For SPECIFIC TERMS:
     * Accept synonyms and descriptions (e.g., "Red Double-decker Bus" = "red double decker" = "double decker bus")

3. LANGUAGE QUALITY (0-3 points) - SECONDARY (only if answer is in English):
   - 3: Perfect or near-perfect grammar and vocabulary
   - 2: Minor errors that don't affect understanding
   - 1: Noticeable errors but still understandable
   - 0: Severe errors or incomprehensible

TOTAL SCORE = Content Accuracy + Language Quality (0-10)
**Exception: Non-English answers always get 0**

**SCORING EXAMPLES:**
- Student answers in Chinese (e.g., "皇冠-X-1859") -> Score: 0, is_correct: false (NOT ENGLISH)
- Student says "CROWN-X-1859" (English) -> Content: 7, is_correct: true
- Student says "Crown X eighteen fifty nine" -> Content: 7, is_correct: true

FEEDBACK RULES (IMPORTANT):
1. If the answer is not in English, feedback should explain that English is required.
2. DO NOT reveal the correct answer in feedback_chi or feedback_eng.
3. Focus feedback on grammar usage and vocabulary accuracy.
4. All Chinese MUST be Traditional Chinese, NEVER Simplified Chinese.
5. Keep feedback concise but helpful for language learning.

Output MUST be valid JSON:
{{
  "score": 8,
  "feedback_chi": "繁體中文回饋 - 僅針對文法和用詞準確度給建議，不透露答案",
  "feedback_eng": "English feedback - ONLY about grammar and vocabulary, DO NOT reveal the answer",
  "reference_comparison": "Detailed comparison: what student said vs what the answer should be",
  "is_correct": true
}}
"""

# 改善提示系統指令 - 客製化提示，不直接說出答案
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
  "hint_chi": "繁體中文改善提示，引導學生方向但不透露答案"
}}
"""

# 遊戲系統指令 - 更精煉、不暴雷
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
- All Chinese feedback MUST be in Traditional Chinese (繁體中文), NEVER Simplified Chinese.
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
    
    IMPORTANT: All Chinese text MUST be in Traditional Chinese (繁體中文), NEVER Simplified Chinese.
    """

SYSTEM_SUMMARY_AND_SCORE_INSTRUCTION = f"""
    你是一個專業的英文教學專家，正在分析非母語英語學習者(台灣的大學生)與AI之間的對話紀錄。請使用三明治溝通法（正向回饋、改進建議、鼓勵）在200字內提供簡潔分析，以繁體中文和英文呈現。

    分析重點：
    - 詞彙多樣性：學生是否重複使用相同的詞彙？
    - 基礎語法：主謂一致性（以口語標準評估，不要過於嚴格）
    - 回答相關性：學生是否適當回答問題，不離題？

    首先指出學生做得好的地方，然後具體指出1-2個主要問題及解決方案，最後給予正向支持。

    保持在200字內，使用友善且具體的語氣和第一人稱視角，以純文字格式呈現。
    
    重要：所有中文內容必須使用台灣繁體中文(zh-TW)，絕對不要使用簡體中文。

    並且根據學生的整體表現，給予一個1-10的分數。
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
        QuickReplyItem(action=PostbackAction(label='查看回覆 Lookup', data=f'action=chat&lookup=true')),
    ])
    if history and len(history.questions) >= 5:
        quick_reply.items.append(QuickReplyItem(action=PostbackAction(label='查看摘要 Summary', data=f'action=chat&summary=true')))
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
                        text='聊天摘要\nChat Summary',
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
                        if summary.chi_summary else '無摘要',
                        wrap=True,
                        size='md',
                    ),
                ]
            )
        ),]
    return FlexMessage(altText='聊天摘要 Chat Summary', contents=FlexCarousel(contents=contents))


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
        return TextMessage(text="您已完成所有問題。\nYou have completed all questions.")
    
    message = f"您尚未回答 Questions Unanswered ({sum(len(v) for v in progress.values())}):\n"
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
            text=f'與 CoachGPT 進行語音對話！\nTalk with CoachGPT!',
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
                    text='參考聊天問題\nChatting questions',
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
                    text='選擇問題開始聊天\nChoose a question to start!',
                    size='md',
                    wrap=True,
                    align='center',
                )
            ]
        )
    ))
    return FlexMessage(
        altText='聊天Chat',
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
                    text=f'口語練習 Q{unit}-{sub+1}',
                    wrap=True,
                    weight='bold',
                    size='xl',
                    align='center',
                ),
                # 提示文字
                FlexText(
                    text='點擊下方按鈕 Click button below',
                    wrap=True,
                    size='xs',
                    color='#888888',
                    align='center',
                    margin='md',
                ),
                FlexButton(
                    action=PostbackAction(
                        label='開始作答 Enter',
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
                        label='查看結果 Result',
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
                        text=f'前往下一單元\nNext',
                        weight='bold',
                        size='xl',
                    ),
                    # 提示文字
                    FlexText(
                        text='點擊此卡片 Tap this card',
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
                    label='下一單元',
                    data=f'action=unit&unit={unit+1}'
                )
            ),
        ))
    msg = FlexMessage(
        altText='單元導覽',
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
            altText='歷史紀錄 History',
            contents=FlexBubble(
                body=FlexBox(
                    layout='vertical',
                    contents=[
                        FlexText(
                            text='尚無歷史紀錄，請先回答本題\nNo history, please answer first.',
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
                text=f'第 {idx+1} 次作答\nAttempt {idx+1}',
                wrap=True,
                weight='bold',
                size='xl',
            ),
            FlexText(
                text=f'分數 Score: {item.score}',
                wrap=True,
            ),
        ]
        
        # 只有在 display_feedback 為 true 時才顯示回饋
        if display_feedback:
            body_contents.extend([
                FlexText(
                    text=f'Tips: {item.eng_suggestion}',
                    wrap=True,
                    margin='md',
                ),
                FlexText(
                    text=f'建議: {item.chi_suggestion}',
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
        altText='歷史紀錄 History',
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
                    label='開始作答 Start',
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
                    label='查看結果 Result',
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
        altText='錄音題目',
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
                        label='作答 Answer',
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
                        label='查看結果 Result',
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
                            text=f'前往下一單元\nNext',
                            weight='bold',
                            size='xl',
                        ),],
                layout='vertical',
                alignItems='center',
                justifyContent='center',
                action=PostbackAction(
                    label='下一單元',
                    data=f'action=unit&unit={unit+1}'
                )
            ),
        ))
    msg = FlexMessage(
        altText='單元導覽',
        contents=FlexCarousel(contents=cols)
    )
    return msg

# ========== 遊戲訊息函數 ==========

async def game_prologue_message(theme_id: str, user_id: str) -> list:
    """顯示主題前情提要/背景故事，並自動顯示當前關卡"""
    messages = []
    theme_config = load_game_theme_config(theme_id)
    
    if not theme_config:
        return [FlexMessage(
            altText='找不到主題 Theme not found',
            contents=FlexBubble(
                body=FlexBox(
                    layout='vertical',
                    contents=[FlexText(text='找不到主題設定。\nTheme configuration not found.', wrap=True)]
                )
            )
        )]
    
    # 如果有主題介紹影片，先播放
    if theme_config.intro_video:
        video_url = f'{URL}/templates/videos/{theme_config.intro_video}'
        # 使用封面圖或影片預覽圖
        preview_url = f'{URL}{theme_config.cover_image}' if theme_config.cover_image else f'{URL}/templates/videos/{theme_config.intro_video.replace(".mp4", "_preview.jpg")}'
        messages.append(
            VideoMessage(
                originalContentUrl=video_url,
                previewImageUrl=preview_url
            )
        )
    
    bubbles = []
    
    # 標題卡片
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
                    text='故事背景\nStory Background',
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
    
    # 前情提要卡片
    prologue_bubble = FlexBubble(
        size='giga',
        body=FlexBox(
            layout='vertical',
            spacing='md',
            contents=[
                FlexText(
                    text='故事背景 Background',
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
    
    # NPC 介紹卡片
    if theme_config.npcs:
        npc_contents = [
            FlexText(
                text='登場角色 Characters',
                wrap=True,
                weight='bold',
                size='xl',
            ),
        ]
        for npc in theme_config.npcs:
            # 使用 description 而非 persona 顯示給使用者
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
        altText=f'{theme_config.name} - 故事背景 Background',
        contents=FlexCarousel(contents=bubbles)
    ))
    
    # 自動顯示當前關卡
    current_level = get_user_unlocked_level(user_id, theme_id)
    level_messages = await game_level_intro_message(theme_id, current_level, user_id)
    messages.extend(level_messages)
    
    return messages

async def game_level_intro_message(theme_id: str, level_idx: int, user_id: str) -> list:
    """顯示關卡介紹，包含影片"""
    messages = []
    level_info = get_game_level_info(theme_id, level_idx)
    
    if not level_info:
        return [TextMessage(text='找不到關卡。\nLevel not found.')]
    
    # 如果有影片則播放
    if level_info.get('video_file'):
        video_url = f'{URL}/templates/videos/{level_info["video_file"]}'
        preview_url = f'{URL}/templates/videos/{level_info["video_file"].replace(".mp4", "_preview.jpg")}'
        messages.append(
            VideoMessage(
                originalContentUrl=video_url,
                previewImageUrl=preview_url
            )
        )
    
    # 關卡說明卡片
    theme_config = load_game_theme_config(theme_id)
    theme_name = theme_config.name if theme_config else theme_id
    
    level_bubble = FlexBubble(
        size='giga',
        body=FlexBox(
            layout='vertical',
            spacing='lg',
            contents=[
                FlexText(
                    text=f'關卡 Level {level_idx + 1}: {level_info["title"]}',
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
        footer=FlexBox(
            layout='vertical',
            spacing='sm',
            contents=[
                FlexButton(
                    action=PostbackAction(
                        label='顯示題目 Show Questions',
                        data=f'action=game_questions&theme={theme_id}&level={level_idx}'
                    ),
                    style='primary',
                ),
            ]
        )
    )
    
    messages.append(FlexMessage(
        altText=f'關卡 Level {level_idx + 1}',
        contents=level_bubble
    ))
    
    return messages

async def game_questions_carousel(theme_id: str, level_idx: int, user_id: str, force_show_all: bool = False) -> FlexMessage:
    """顯示關卡題目的可滑動卡片
    
    Args:
        theme_id: 主題ID
        level_idx: 關卡索引
        user_id: 使用者ID
        force_show_all: 是否強制顯示所有題目 (當使用者已通過關卡時)
    """
    from utils.file_utils import (
        is_level_all_questions_passed, get_next_unpassed_question,
        get_min_score_to_pass
    )
    
    level_info = get_game_level_info(theme_id, level_idx)
    questions_per_level = get_questions_per_level()
    
    if not level_info:
        return FlexMessage(
            altText='找不到題目 Questions not found',
            contents=FlexBubble(
                body=FlexBox(
                    layout='vertical',
                    contents=[FlexText(text='找不到關卡題目。\nLevel questions not found.', wrap=True)]
                )
            )
        )
    
    bubbles = []
    questions = level_info.get('questions', [])
    
    # 限制為設定的每關題目數
    questions = questions[:questions_per_level]
    
    # 檢查是否已通過所有題目
    all_passed = is_level_all_questions_passed(user_id, theme_id, level_idx)
    min_score = get_min_score_to_pass()
    
    # 如果已通過所有題目或強制顯示，則顯示所有題目供自由選擇
    if all_passed or force_show_all:
        for q_idx, question in enumerate(questions):
            # 檢查使用者是否已回答此題
            best_score = get_user_question_score(user_id, theme_id, level_idx, q_idx)
            has_answered = best_score > 0
            is_passed = best_score >= min_score
            
            body_contents = [
                FlexText(
                    text=f'題目 Question {q_idx + 1}',
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
                status_text = '已通過 Passed' if is_passed else '未通過 Not Passed'
                body_contents.append(
                    FlexText(
                        text=f'最佳分數 Best: {best_score}/10 ({status_text})',
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
                        text=f'提示 Hint: {question["hint"]}',
                        wrap=True,
                        size='sm',
                        color='#888888',
                        margin='sm',
                        style='italic',
                    )
                )
            
            footer_contents = [
                # 提示文字
                FlexText(
                    text='點擊下方按鈕 Click button below',
                    wrap=True,
                    size='xs',
                    color='#888888',
                    align='center',
                    margin='sm',
                ),
                FlexButton(
                    action=PostbackAction(
                        label='回答 Answer' if not has_answered else '再試一次 Try Again',
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
        # 尚未通過所有題目，只顯示當前應回答的題目
        current_q_idx = get_next_unpassed_question(user_id, theme_id, level_idx)
        if current_q_idx < 0 or current_q_idx >= len(questions):
            current_q_idx = 0
        
        question = questions[current_q_idx]
        best_score = get_user_question_score(user_id, theme_id, level_idx, current_q_idx)
        has_answered = best_score > 0
        
        body_contents = [
            FlexText(
                text=f'題目 Question {current_q_idx + 1}/{len(questions)}',
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
            status_text = '已通過 Passed' if is_passed else '再試一次以通過 Try again to pass'
            body_contents.append(
                FlexText(
                    text=f'目前分數 Current: {best_score}/10',
                    wrap=True,
                    size='sm',
                    color=status_color,
                    margin='md',
                    align='center',
                )
            )
            body_contents.append(
                FlexText(
                    text=f'及格標準 Pass: {min_score}/10 ({status_text})',
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
                    text=f'提示 Hint: {question["hint"]}',
                    wrap=True,
                    size='sm',
                    color='#888888',
                    margin='sm',
                    style='italic',
                )
            )
        
        footer_contents = [
            # 提示文字
            FlexText(
                text='點擊下方按鈕開始作答 Click to start',
                wrap=True,
                size='xs',
                color='#888888',
                align='center',
                margin='sm',
            ),
            FlexButton(
                action=PostbackAction(
                    label='開始作答 Start Answering' if not has_answered else '再試一次 Try Again',
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
        
        # 添加進度指示卡片
        progress_contents = [
            FlexText(
                text='關卡進度 Level Progress',
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
                status = '>>> 目前 Current'
                color = '#0066cc'
            elif q_passed:
                status = f'已通過 Passed ({q_score}/10)'
                color = '#00aa00'
            elif q_score > 0:
                status = f'未通過 Not Passed ({q_score}/10)'
                color = '#ff8800'
            else:
                status = '尚未作答 Not Answered'
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
        altText=f'關卡 Level {level_idx + 1} 題目 Questions',
        contents=FlexCarousel(contents=bubbles)
    )

async def game_score_message(user_id: str, theme_id: str, level_idx: int, question_idx: int, 
                             score: int, is_new_high: bool, feedback_eng: str, feedback_chi: str,
                             reference_comparison: str = "") -> FlexMessage:
    """顯示遊戲結果與分數 - 英文回饋在前，中文回饋在後"""
    display_feedback = get_display_feedback()
    theme_total = get_user_game_score(user_id, theme_id)
    max_score = get_max_theme_score()
    
    bubbles = []
    
    # 主要結果卡片 - 分數永遠顯示
    main_contents = [
        FlexText(
            text=f'Q{question_idx + 1} 結果 Result',
            wrap=True,
            weight='bold',
            size='xxl',
            align='center',
        ),
        FlexText(
            text=f'評分 Score: {score}/10',
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
                text='新高分！New High Score!',
                wrap=True,
                size='md',
                align='center',
                color='#ff6600',
                margin='sm',
            )
        )
    
    main_contents.append(
        FlexText(
            text=f'主題總分 Theme Total: {theme_total}/{max_score}',
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
    
    # 只在 display_feedback 為 true 且有回饋內容時顯示回饋卡片
    if display_feedback:
        # 英文回饋卡片 (先顯示)
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
        
        # 中文回饋卡片 (後顯示)
        if feedback_chi and feedback_chi.strip():
            chi_feedback_bubble = FlexBubble(
                size='giga',
                body=FlexBox(
                    layout='vertical',
                    spacing='sm',
                    contents=[
                        FlexText(
                            text='回饋',
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
        
        # 參考答案比較 (如果有)
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
        altText=f'Q{question_idx + 1} 結果 Result',
        contents=FlexCarousel(contents=bubbles)
    )
    
    # 快速回覆按鈕 - 根據分數決定顯示不同按鈕
    # 分數 < 6: 「再試一次」+「改善提示」
    # 分數 6-9: 「再試一次」+「改善提示」+「下一題」
    # 分數 = 10: 只顯示「下一題」
    from utils.file_utils import get_min_score_to_pass, is_level_all_questions_passed, get_next_unpassed_question, get_questions_per_level
    min_score = get_min_score_to_pass()
    is_passed = score >= min_score
    is_perfect = score == 10
    all_level_passed = is_level_all_questions_passed(user_id, theme_id, level_idx)
    questions_per_level = get_questions_per_level()
    
    quick_reply_items = []
    
    # 滿分不需要再試一次和改善提示
    if not is_perfect:
        # 再試一次按鈕
        quick_reply_items.append(
            QuickReplyItem(action=PostbackAction(
                label='再試一次 Try Again',
                data=f'action=game_answer&theme={theme_id}&level={level_idx}&question={question_idx}'
            ))
        )
        
        # 改善提示按鈕 (分數未達滿分都可以使用)
        quick_reply_items.append(
            QuickReplyItem(action=PostbackAction(
                label='改善提示 Improvement Hint',
                data=f'action=game_improvement_hint&theme={theme_id}&level={level_idx}&question={question_idx}'
            ))
        )
    
    # 如果已通過當前題目 (分數 >= 6)，顯示下一題按鈕
    if is_passed:
        next_q_idx = get_next_unpassed_question(user_id, theme_id, level_idx)
        if next_q_idx >= 0 and next_q_idx < questions_per_level:
            quick_reply_items.append(
                QuickReplyItem(action=PostbackAction(
                    label=f'下一題 Next (Q{next_q_idx + 1})',
                    data=f'action=game_answer&theme={theme_id}&level={level_idx}&question={next_q_idx}'
                ))
            )
        elif all_level_passed:
            # 關卡全部通過
            quick_reply_items.append(
                QuickReplyItem(action=PostbackAction(
                    label='關卡完成! Level Complete!',
                    data=f'action=game_levels&theme={theme_id}'
                ))
            )
    
    msg.quick_reply = QuickReply(items=quick_reply_items)
    
    return msg

async def game_improvement_hint_message(theme_id: str, level_idx: int, question_idx: int,
                                         hint_eng: str, hint_chi: str, hint_count: int = 1) -> FlexMessage:
    """顯示改善提示訊息 (不直接說出答案)
    
    Args:
        theme_id: 主題ID
        level_idx: 關卡索引
        question_idx: 題目索引
        hint_eng: 英文提示
        hint_chi: 中文提示
        hint_count: 此題目使用提示的次數
    """
    bubbles = []
    
    # 英文提示卡片
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
                    text=hint_eng,
                    wrap=True,
                    size='md',
                    color='#5b5b5b',
                    margin='md',
                ),
            ]
        )
    )
    bubbles.append(eng_bubble)
    
    # 中文提示卡片
    chi_bubble = FlexBubble(
        size='giga',
        body=FlexBox(
            layout='vertical',
            spacing='sm',
            contents=[
                FlexText(
                    text=f'改善提示 (第{hint_count}次)',
                    wrap=True,
                    weight='bold',
                    size='xl',
                    color='#0066cc',
                ),
                FlexText(
                    text=hint_chi,
                    wrap=True,
                    size='md',
                    color='#5b5b5b',
                    margin='md',
                ),
            ]
        )
    )
    bubbles.append(chi_bubble)
    
     # 如果沒有任何提示內容
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
                            text='暫無改善提示\nNo hints available',
                            wrap=True,
                            align='center',
                        )
                    ]
                )
            )
        )

    msg = FlexMessage(
        altText=f'Q{question_idx + 1} 改善提示 Improvement Hint',
        contents=FlexCarousel(contents=bubbles)
    )
    
    # 快速回覆按鈕 - 移除題目列表按鈕
    msg.quick_reply = QuickReply(items=[
        QuickReplyItem(action=PostbackAction(
            label='再試一次 Try Again',
            data=f'action=game_answer&theme={theme_id}&level={level_idx}&question={question_idx}'
        )),
    ])
    
    return msg

async def game_npc_chat_response_message(npc_name: str, npc_reply: str, 
                                          is_english: bool = True,
                                          npc_image: str = None) -> FlexMessage:
    """顯示 NPC 快速回應 (立即顯示)，包含隨機人物圖片
    
    Args:
        npc_name: NPC名稱
        npc_reply: NPC回覆內容
        is_english: 使用者是否使用英文
        npc_image: NPC基礎圖片檔名 (例如 John_Watson.jpg)，會隨機選擇 _1, _2, _3 變體
    """
    import random
    
    bubbles = []
    
    # 語言警告卡片 (如果不是英文)
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
                        text='請使用英文對話\nPlease speak in English',
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
    
    # NPC 回覆卡片
    reply_contents = [
        FlexText(
            text=f'{npc_name} 說 says:',
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
    
    # 如果有NPC圖片，隨機選擇變體版本並添加到回覆卡片
    if npc_image:
        # 從圖片檔名中提取名稱部分 (移除.jpg等副檔名)
        base_name = npc_image.rsplit('.', 1)[0] if '.' in npc_image else npc_image
        ext = npc_image.rsplit('.', 1)[1] if '.' in npc_image else 'jpg'
        
        # 隨機選擇 _1, _2, _3 變體
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
        altText=f'{npc_name} 的回應 Response',
        contents=FlexCarousel(contents=bubbles)
    )

async def game_npc_evaluation_message(npc_name: str, language_score: int, 
                                      relevance_score: int, feedback_eng: str, 
                                      feedback_chi: str) -> FlexMessage:
    """顯示 NPC 對話評估 (異步發送)"""
    display_feedback = get_display_feedback()
    
    if not display_feedback:
        return None
    
    bubbles = []
    
    # 評分卡片
    score_contents = [
        FlexText(
            text='評分 Score',
            wrap=True,
            weight='bold',
            size='xl',
            color='#1a1a2e',
        ),
        FlexText(
            text=f'語言品質 Language: {language_score}/10',
            wrap=True,
            size='md',
            color='#00aa00' if language_score >= 7 else '#ff8800' if language_score >= 5 else '#ff0000',
            margin='md',
        ),
        FlexText(
            text=f'主題相關性 Relevance: {relevance_score}/10',
            wrap=True,
            size='md',
            color='#00aa00' if relevance_score >= 7 else '#ff8800' if relevance_score >= 5 else '#ff0000',
            margin='sm',
        ),
    ]
    
    # 如果有回饋，加入中英對照
    if feedback_eng and feedback_eng.strip():
        score_contents.append(
            FlexText(
                text='',
                margin='lg',
            )
        )
        score_contents.append(
            FlexText(
                text='語言建議 Feedback',
                wrap=True,
                weight='bold',
                size='md',
                color='#1a1a2e',
            )
        )
        score_contents.append(
            FlexText(
                text=f'🇬🇧 {feedback_eng}',
                wrap=True,
                size='sm',
                color='#5b5b5b',
                margin='sm',
            )
        )
        if feedback_chi and feedback_chi.strip():
            score_contents.append(
                FlexText(
                    text=f'🇹🇼 {feedback_chi}',
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
        altText=f'{npc_name} 對話評估',
        contents=FlexCarousel(contents=bubbles)
    )

async def game_theme_select_message() -> FlexMessage:
    """顯示主題選擇卡片"""
    from utils.file_utils import get_game_themes
    
    themes = get_game_themes()
    bubbles = []
    
    for idx, theme_id in enumerate(themes):
        theme_config = load_game_theme_config(theme_id)
        
        if theme_config:
            theme_name = theme_config.name
            cover_image = theme_config.cover_image
        else:
            theme_name = f'主題 Theme {idx + 1}'
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
                # 提示文字
                FlexText(
                    text='點擊下方按鈕 Click button below',
                    wrap=True,
                    size='xs',
                    color='#888888',
                    align='center',
                    margin='sm',
                ),
                FlexButton(
                    action=PostbackAction(
                        label='進入 Enter',
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
        altText='選擇主題 Select Theme',
        contents=FlexCarousel(contents=bubbles)
    )

async def game_npc_select_message(theme_id: str, user_id: str) -> FlexMessage:
    """顯示 NPC 選擇介面 - 含圖片和描述"""
    print(f"[DEBUG] game_npc_select_message called with theme_id={theme_id}, user_id={user_id}")
    
    theme_config = load_game_theme_config(theme_id)
    
    if not theme_config:
        print(f"[WARNING] Theme config not found in game_npc_select_message for theme_id={theme_id}")
        return FlexMessage(
            altText='找不到主題 Theme not found',
            contents=FlexBubble(
                body=FlexBox(
                    layout='vertical',
                    contents=[
                        FlexText(text='找不到主題配置。\nTheme config not found.', wrap=True),
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
    
    # 取得使用者進度
    progress = get_user_game_progress(user_id, theme_id)
    
    bubbles = []
    
    # 進度卡片
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
                    text=f"總分 Score: {progress['total_score']}/{progress['max_score']}",
                    wrap=True,
                    size='lg',
                    align='center',
                    color='#00aa00',
                ),
                FlexText(
                    text=f"目前關卡 Current Level: {progress['current_level'] + 1}",
                    wrap=True,
                    size='md',
                    align='center',
                    color='#5b5b5b',
                ),
            ]
        )
    )
    bubbles.append(progress_bubble)
    
    # NPC 選擇卡片 - 含圖片和描述
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
        
        # 顯示 description 而非 persona
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
        
        # 提示文字
        body_contents.append(
            FlexText(
                text='點擊下方按鈕 Click button below',
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
                    label='對話 Talk',
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
        
        # 如果有圖片則顯示
        if npc.image:
            npc_bubble.hero = FlexImage(
                url=f'{URL}/templates/people_pic/{npc.image}',
                size='full',
                aspect_ratio='1:1',
                aspect_mode='cover',
            )
        
        bubbles.append(npc_bubble)
    
    return FlexMessage(
        altText=f'{theme_config.name} - 選擇角色 Select NPC',
        contents=FlexCarousel(contents=bubbles)
    )

async def game_npc_card_message(theme_id: str, npc_idx: int) -> FlexMessage:
    """顯示單一 NPC 卡片 - 含圖片和描述"""
    print(f"[DEBUG] game_npc_card_message called with theme_id={theme_id}, npc_idx={npc_idx}")
    
    theme_config = load_game_theme_config(theme_id)
    
    if not theme_config:
        print(f"[WARNING] Theme config not found for theme_id={theme_id}")
        return FlexMessage(
            altText='找不到主題 Theme not found',
            contents=FlexBubble(
                body=FlexBox(
                    layout='vertical',
                    contents=[
                        FlexText(text='找不到主題配置。\nTheme config not found.', wrap=True),
                        FlexText(
                            text=f'Theme ID: {theme_id}',
                            wrap=True,
                            size='sm',
                            color='#888888',
                            margin='md'
                        ),
                        FlexText(
                            text='請確認 theme_config.json 檔案存在。\nPlease check if theme_config.json exists.',
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
            altText='找不到角色 NPC not found',
            contents=FlexBubble(
                body=FlexBox(
                    layout='vertical',
                    contents=[
                        FlexText(text='找不到角色。\nNPC not found.', wrap=True),
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
    
    # 顯示 description 而非 persona
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
            text='請用英文對話 Please speak in English',
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
    
    # 如果有圖片則顯示
    if npc.image:
        bubble.hero = FlexImage(
            url=f'{URL}/templates/people_pic/{npc.image}',
            size='full',
            aspect_ratio='3:4',
            aspect_mode='cover',
        )
    
    return FlexMessage(
        altText=f'{npc.name} - 對話 Talk',
        contents=bubble
    )

async def game_level_select_message(theme_id: str, user_id: str) -> FlexMessage:
    """顯示關卡選擇介面 - 只顯示已解鎖的關卡"""
    theme_config = load_game_theme_config(theme_id)
    
    if not theme_config:
        return FlexMessage(
            altText='找不到主題 Theme not found',
            contents=FlexBubble(
                body=FlexBox(
                    layout='vertical',
                    contents=[FlexText(text='找不到主題。\nTheme not found.', wrap=True)]
                )
            )
        )
    
    # 取得使用者已解鎖的最高關卡
    unlocked_level = get_user_unlocked_level(user_id, theme_id)
    
    bubbles = []
    
    # 只顯示已解鎖的關卡
    for level in theme_config.levels:
        if level.id > unlocked_level:
            break  # 不顯示未解鎖的關卡
            
        level_score = get_user_level_score(user_id, theme_id, level.id)
        questions_per_level = get_questions_per_level()
        max_level_score = questions_per_level * 10
        
        # 判斷關卡是否完成
        is_completed = level_score >= questions_per_level * 6  # 所有題目都及格
        
        body_contents = [
            FlexText(
                text=f'關卡 Level {level.id + 1}',
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
                    text=f'分數 Score: {level_score}/{max_level_score}',
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
                    text='已完成 Completed',
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
                    # 提示文字
                    FlexText(
                        text='點擊下方按鈕 Click button below',
                        wrap=True,
                        size='xs',
                        color='#888888',
                        align='center',
                        margin='sm',
                    ),
                    FlexButton(
                        action=PostbackAction(
                            label='進入 Enter',
                            data=f'action=game_level&theme={theme_id}&level={level.id}'
                        ),
                        style='primary',
                    ),
                ]
            )
        )
        bubbles.append(bubble)
    
    # 如果還有未解鎖的關卡，顯示提示
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
                        text='🔒',
                        size='xxl',
                        align='center',
                    ),
                    FlexText(
                        text=f'還有 {len(theme_config.levels) - unlocked_level - 1} 個關卡未解鎖',
                        wrap=True,
                        size='md',
                        align='center',
                        color='#888888',
                    ),
                    FlexText(
                        text='完成當前關卡即可解鎖',
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
        altText=f'{theme_config.name} - 選擇關卡 Select Level',
        contents=FlexCarousel(contents=bubbles)
    )

async def game_current_questions_message(theme_id: str, user_id: str) -> FlexMessage:
    """顯示當前關卡的題目 (用於選單中的「顯示題目」按鈕)"""
    current_level = get_user_unlocked_level(user_id, theme_id)
    return await game_questions_carousel(theme_id, current_level, user_id)

# ========== [結束] 遊戲訊息函數 ==========

CHI_HINT = [
    '請依照指示輸入你的課程編號\n1 代表簡報課(4-12)\n2 代表簡報課(4-34)\n3 代表英國課(1-56)\n4 代表英國課(1-78)\n5 代表其他',
    '接著，請輸入你的系級\n如：資管一乙\n輸入 "Back" 可返回上一步',
    '接著，請輸入你的學號\n如：11352237\n輸入 "Back" 可返回上一步',
    '接著，請輸入你的姓名\n如：王聰明\n輸入 "Back" 可返回上一步',
]

ENG_HINT =[
    'Enter your class number\n1 for English Presentation(4-12)\n2 for English Presentation(4-34)\n3 for English Culture and Lifestyle(1-56)\n4 for English Culture and Lifestyle(1-78)\n5 for Others',
    'Next, what is your department?\nFor example: Information Management\nEnter "Back" to previous step.',
    'Next, what is your student ID?\nFor example: 11352237\nEnter "Back" to previous step.',
    'Next, what is you name?\nFor example: Paul Wang\nEnter "Back" to previous step.',
]

async def info_hint_message(index: int):
    return FlexMessage(
        altText='資料綁定提示',
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
                    FlexText(
                        text=ENG_HINT[index],
                        wrap=True,
                    )
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
    
    # 根據是否為 RAG 模式決定預設的選單
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
        
        # 如果當前選單是目標預設選單，則設定為預設
        if menu_name == target_default:
            await rich_menu_manager.set_default_rich_menu(rich_menu_id)
            
        set_rich_menu_id(rich_menu_id, menu_name)
        print(f'Rich Menu {menu_name} created with ID: {rich_menu_id}')
    await save_config()