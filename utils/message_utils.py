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
from utils.models import ChatSummary, QuestionSet, SpeechAssessment
import json
from utils.file_utils import (
    get_user_state, getHistory, get_rich_menu_id, isEnabled, isResponse, 
    set_rich_menu_id, save_config, get_rich_menu_category_from_id, 
    clear_rich_menu_id, config, load_game_theme_config, get_game_level_info,
    get_user_game_score, get_max_theme_score, get_user_game_progress,
    get_questions_per_level, get_user_question_score, get_user_level_score,
    get_display_feedback  # 修改6: 新增
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
        
        The JSON object must use the schema: {json.dumps(SpeechAssessment.model_json_schema(), indent=2)}
    """

# [舊版] 遊戲系統指令 - 保留向後相容
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

Output MUST be valid JSON:
{{
  "npc_reply": "Your concise in-character response (English, 1-3 sentences)",
  "feedback": "Brief grammar/vocab tip (Traditional Chinese, 1 sentence max)",
  "score": 8
}}
"""

# ========== 修改2&3: NPC對話專用系統指令 (含語言偵測) ==========
NPC_CHAT_SYSTEM_INSTRUCTION = """
You are an NPC in an immersive mystery game. Stay strictly in character.

Your Identity: {persona}

Background Knowledge (use only when relevant to the question):
{context}

Recent Conversation:
{history}

CRITICAL RULES:
1. LANGUAGE CHECK FIRST: 
   - Determine if the user's message is in English
   - If NOT English (e.g., Chinese, Japanese, Korean): Set is_english=false, respond IN CHARACTER saying you don't understand that language, politely request they speak English
   - If English: Set is_english=true, continue normally

2. CONCISE RESPONSES: Keep replies short and natural (1-3 sentences max). Only answer what was asked.

3. NO SPOILERS: Never volunteer information the player didn't ask about. Let them discover through questions.

4. STAY IN CHARACTER: Respond as your character would. If asked something outside your knowledge, deflect naturally.

5. DO NOT COPY: Rephrase context information naturally as dialogue. Never copy-paste.

6. LANGUAGE TIPS: If the user made grammar or vocabulary mistakes, provide ONE brief tip in Traditional Chinese.

Output MUST be valid JSON:
{{
  "npc_reply": "Your concise in-character response (English, 1-3 sentences)",
  "feedback": "Brief grammar/vocab tip if needed (Traditional Chinese, 1 sentence max, empty string if no issues)",
  "is_english": true
}}
"""

# ========== 修改6: 題目回答專用系統指令 ==========
QUESTION_ANSWER_SYSTEM_INSTRUCTION = """
You are evaluating a student's spoken English answer to a question in a mystery game context.

Question: {question}
Reference Answer (for content comparison): {reference_answer}
User's Answer: {user_answer}

SCORING CRITERIA (0-10 total):
- Content Accuracy (0-5): How well does the answer address the question? Does it match key points from the reference?
- Language Quality (0-5): Grammar, vocabulary, fluency, and clarity of expression.

EVALUATION STEPS:
1. Compare user's answer to the reference answer for content accuracy
2. Evaluate grammar, vocabulary usage, and sentence structure
3. Provide constructive feedback in both Traditional Chinese and English
4. Assign a fair score based on the criteria above

Output MUST be valid JSON:
{{
  "score": 7,
  "feedback_chi": "評語回饋 (繁體中文，包含優點與改進建議)",
  "feedback_eng": "Feedback in English (strengths and suggestions)",
  "reference_comparison": "Brief comparison with reference answer (English)"
}}
"""

# ========== 結束修改 ==========

SYSTEM_SUMMARY_INSTRUCTION = f"""
    You are an English teaching expert analyzing conversation transcripts between non-native English speakers and AI. Provide concise analysis within 300 words using the sandwich communication method (positive feedback - improvement suggestions - encouragement) in both Traditional Chinese and English.
    Analysis Focus Areas
    - Vocabulary Variety: Does the student repeat the same words (e.g., only using "delicious" for expressing tasty)?
    - Basic Grammar: Subject-verb agreement (oral standards, not overly strict)
    - Response Relevance: Does the student answer questions appropriately, not off-topic?

    Output start by highlighting what the student did well, then specifically point out 1-2 main issues and solutions, finally, provide positive support.

    Keep within 300 words with a friendly and specific tone and first person perspective in plain text format.
    """

SYSTEM_SUMMARY_AND_SCORE_INSTRUCTION = f"""
    You are an English teaching expert analyzing conversation transcripts between non-native English speakers and AI. Provide concise analysis within 300 words using the sandwich communication method (positive feedback - improvement suggestions - encouragement) in both Traditional Chinese and English.
    Analysis Focus Areas
    - Vocabulary Variety: Does the student repeat the same words (e.g., only using "delicious" for expressing tasty)?
    - Basic Grammar: Subject-verb agreement (oral standards, not overly strict)
    - Response Relevance: Does the student answer questions appropriately, not off-topic?

    Output start by highlighting what the student did well, then specifically point out 1-2 main issues and solutions, finally, provide positive support.

    Keep within 300 words with a friendly and specific tone and first person perspective in plain text format.
    """

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
    from utils.file_utils import getData
    ud = getData().get(user_id)
    if not ud:
        return TextMessage(text='找不到資料。\nData not found.')
    history = ud.history
    bubbles = []
    for key, value in history.items():
        category, sub = key.split('-')
        scores = [h.score for h in value]
        avg_score = sum(scores) / len(scores) if scores else 0
        bubbles.append(FlexBubble(
            size='kilo',
            body=FlexBox(
                layout='vertical',
                spacing='sm',
                contents=[
                    FlexText(
                        text=f'{category.upper()} Q{int(sub)+1}',
                        wrap=True,
                        weight='bold',
                        size='lg',
                        align='center',
                    ),
                    FlexText(
                        text=f'嘗試次數 Attempts: {len(scores)}',
                        size='sm',
                        align='center',
                        color='#888888',
                    ),
                    FlexText(
                        text=f'平均分數 Avg: {avg_score:.1f}',
                        size='sm',
                        align='center',
                        color='#00aa00' if avg_score >= 7 else '#ff8800',
                    ),
                ]
            )
        ))
    if not bubbles:
        return TextMessage(text='尚無練習紀錄。\nNo practice history yet.')
    return FlexMessage(altText='練習進度 Progress', contents=FlexCarousel(contents=bubbles))

async def result_message(result: SpeechAssessment, category: str, sub: int):
    is_rag = config.get('rag_mode', False)
    display_feedback = get_display_feedback()  # 修改6: 使用新函數
    
    # 分數文字
    score_text = f'{result.score}分' if result.score else '未評分'
    
    # 根據分數決定顏色
    score_color = '#00aa00' if result.score and result.score >= 7 else '#ff8800' if result.score and result.score >= 4 else '#ff0000'
    
    bubbles = []
    
    # 結果標題卡片
    title_bubble = FlexBubble(
        size='giga',
        body=FlexBox(
            layout='vertical',
            justifyContent='center',
            alignItems='center',
            spacing='lg',
            contents=[
                FlexText(
                    text=f'Q{sub+1} 結果 Result',
                    wrap=True,
                    weight='bold',
                    size='xxl',
                    align='center',
                    color="#001174",
                ),
                FlexText(
                    text=score_text,
                    wrap=True,
                    size='xxl',
                    align='center',
                    color=score_color,
                ),
            ]
        )
    )
    bubbles.append(title_bubble)
    
    # 修改6: RAG 模式下，NPC 回覆永遠顯示
    if is_rag and result.better_ans:
        npc_reply_bubble = FlexBubble(
            size='giga',
            body=FlexBox(
                layout='vertical',
                spacing='sm',
                contents=[
                    FlexText(
                        text='劇情回應 NPC Reply',
                        wrap=True,
                        weight='bold',
                        size='xl',
                    ),
                    FlexText(
                        text=result.better_ans,
                        wrap=True,
                        size='md',
                        color='#5b5b5b',
                        margin='md',
                    ),
                ]
            )
        )
        bubbles.append(npc_reply_bubble)
    
    # 修改6: 建議卡片只在 display_feedback 為 true 時顯示
    if display_feedback:
        result_title = '評語回饋 Feedback' if is_rag else '改善建議\nImprovement'
        
        # 中文建議
        if result.chi_suggestion:
            chi_bubble = FlexBubble(
                size='giga',
                body=FlexBox(
                    layout='vertical',
                    spacing='sm',
                    contents=[
                        FlexText(
                            text='建議 Suggestion',
                            wrap=True,
                            weight='bold',
                            size='xl',
                        ),
                        FlexText(
                            text=result.chi_suggestion,
                            wrap=True,
                            size='md',
                            color='#5b5b5b',
                            margin='md',
                        ),
                    ]
                )
            )
            bubbles.append(chi_bubble)
        
        # 英文建議
        if result.eng_suggestion:
            eng_bubble = FlexBubble(
                size='giga',
                body=FlexBox(
                    layout='vertical',
                    spacing='sm',
                    contents=[
                        FlexText(
                            text='Suggestion',
                            wrap=True,
                            weight='bold',
                            size='xl',
                        ),
                        FlexText(
                            text=result.eng_suggestion,
                            wrap=True,
                            size='md',
                            color='#5b5b5b',
                            margin='md',
                        ),
                    ]
                )
            )
            bubbles.append(eng_bubble)
    
        # 在非 RAG 模式下，顯示改善後的回答
        if not is_rag and result.better_ans:
            improvement_bubble = FlexBubble(
                size='giga',
                body=FlexBox(
                    layout='vertical',
                    spacing='sm',
                    contents=[
                        FlexText(
                            text=result_title,
                            wrap=True,
                            weight='bold',
                            size='xl',
                        ),
                        FlexBox(
                            layout='vertical',
                            margin='md',
                            contents=[
                                FlexText(
                                    text=result.better_ans, 
                                    color='#5b5b5b',
                                    size='sm',
                                    wrap=True,
                                    flex=1,
                                ),
                            ]
                        ),
                    ],
                ),
            )
            bubbles.append(improvement_bubble)

    # 在非 RAG 模式且未開啟回饋時，顯示簡化結果
    if not isResponse(category) and not is_rag:
        bubbles = [
             FlexBubble(
                size='giga',
                body=FlexBox(
                    layout='vertical',
                    justifyContent='center',
                    alignItems='center',
                    contents=[
                        FlexText(
                            text=f'Q{sub+1} 作答完成 Complete',
                            wrap=True,
                            weight='bold',
                            size='xxl',
                        ),
                        FlexBox(
                            layout='vertical',
                            margin='md',
                            contents=[
                                FlexText(
                                    text=score_text,
                                    color='#5b5b5b',
                                    size='xl',
                                    wrap=True,
                                    flex=1,
                                ),
                            ]
                        ),
                    ],
                ),
            ),
        ]

    msg = FlexMessage(
        altText=f'Q{sub+1} 練習結果 Result',
        contents=FlexCarousel(contents=bubbles)
    )
    
    msg.quick_reply = QuickReply(items=[
        QuickReplyItem(action=PostbackAction(label='再次回答 Again',data=f'action=record&sub={sub}')),
    ])
    if len(question_manager.get_all_questions(category))-1 > sub:
        msg.quick_reply.items.append(QuickReplyItem(action=PostbackAction(label='下一題 Next', data=f'action=record&sub={sub+1}')))
    return msg

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

async def question_message(user_id, category, sub):
    messages = []
    question = question_manager.get_question(category, sub)
    contents = [
        FlexText(
            text=f'Q{sub+1}',
            wrap=True,
            weight='bold',
            size='xxl',
        ),
        FlexBox(
            layout='baseline',
            margin='md',
            contents=[
                FlexText(
                    text=question.text,
                    color='#5b5b5b',
                    size='lg',
                    margin='md',
                    wrap=True,
                    flex=1,
                ),
            ]
        ),
    ]
    
    if question.image_url:
        contents.insert(0, FlexImage(
            url=f'{URL}{question.image_url}',
            size='full',
            aspect_ratio='4:3',
            aspect_mode='cover',
            margin='md',
            flex=1,
        ))
    
    messages.append(FlexBubble(  
            size='mega',
            body=FlexBox(
                layout='vertical',
                wrap=True,
                contents=contents,
                justifyContent='space-around',
            ),
            footer=FlexBox(
                layout='vertical',
                wrap=True,
                alignItems='center',
                contents=[
                    FlexText(
                        text='請發送語音訊息作答！',
                        size='md',
                        wrap=True,
                    ),
                    FlexText(
                        text='Send a voice message!',
                        size='md',
                        wrap=True,
                    ),
                ]
            ),
        )
    )
    
    if question.extra_info:
        for info in question.extra_info:
            messages.append(FlexBubble(
                size='mega',
                body=FlexBox(
                    layout='vertical',
                    spacing='lg',
                    contents=[
                        FlexText(
                            text=info[0],
                            wrap=True,
                            weight='bold',
                            size='xl',
                        ),
                        FlexText(
                            text=info[1],
                            wrap=True,
                            size='md',
                            color='#5b5b5b',
                        ),
                    ]
                )
            ))
    
    return FlexMessage(
        altText=f'Q{sub+1}',
        contents=FlexCarousel(contents=messages)
    )

async def carousel_message(user_id, category, page: int = 0):
    questions = question_manager.get_all_questions(category)
    if not questions:
        return TextMessage(text='找不到問題。\nQuestions not found.')
    
    items_per_page = 10
    total_pages = (len(questions) + items_per_page - 1) // items_per_page
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(questions))
    
    bubbles = []
    for i in range(start_idx, end_idx):
        q = questions[i]
        bubble = FlexBubble(
            size='kilo',
            body=FlexBox(
                layout='vertical',
                spacing='sm',
                justifyContent='center',
                alignItems='center',
                contents=[
                    FlexText(
                        text=f'Q{i+1}',
                        wrap=True,
                        weight='bold',
                        size='xl',
                        align='center',
                    ),
                    FlexButton(
                        action=PostbackAction(
                            label='作答 Answer',
                            data=f'action=record&sub={i}'
                        ),
                        style='primary',
                    ),
                ]
            )
        )
        bubbles.append(bubble)
    
    # 添加分頁導航
    if total_pages > 1:
        nav_contents = []
        if page > 0:
            nav_contents.append(FlexButton(
                action=PostbackAction(
                    label='上一頁 Prev',
                    data=f'action=carousel&page={page-1}'
                ),
                style='secondary',
            ))
        if page < total_pages - 1:
            nav_contents.append(FlexButton(
                action=PostbackAction(
                    label='下一頁 Next',
                    data=f'action=carousel&page={page+1}'
                ),
                style='secondary',
            ))
        
        if nav_contents:
            nav_bubble = FlexBubble(
                size='kilo',
                body=FlexBox(
                    layout='vertical',
                    spacing='sm',
                    justifyContent='center',
                    alignItems='center',
                    contents=[
                        FlexText(
                            text=f'頁 {page+1}/{total_pages}',
                            wrap=True,
                            size='md',
                            align='center',
                        ),
                    ] + nav_contents
                )
            )
            bubbles.append(nav_bubble)
    
    return FlexMessage(
        altText=f'{category.upper()} 題目列表 Q{start_idx+1}-Q{end_idx}',
        contents=FlexCarousel(contents=bubbles)
    )

# ========== [新增] 遊戲訊息函數 ==========

# 修改4: 支援影片自動播放
async def game_prologue_message(theme_id: str) -> list:
    """顯示主題前情提要/背景故事，支援影片自動播放"""
    messages = []  # 修改: 改為回傳列表
    
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
    
    # 修改4: 如果有介紹影片則先播放
    if theme_config.intro_video:
        video_url = f'{URL}/templates/videos/{theme_config.intro_video}'
        # 使用封面圖片作為預覽，或使用影片預覽圖
        if theme_config.cover_image:
            preview_url = f'{URL}{theme_config.cover_image}'
        else:
            preview_url = f'{URL}/templates/videos/{theme_config.intro_video.replace(".mp4", "_preview.jpg")}'
        
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
                    text='前情提要 Prologue',
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
            npc_contents.append(
                FlexText(
                    text=f"- {npc.name}",
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
        altText=f'{theme_config.name} - 前情提要 Prologue',
        contents=FlexCarousel(contents=bubbles)
    ))
    
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

async def game_questions_carousel(theme_id: str, level_idx: int, user_id: str) -> FlexMessage:
    """顯示關卡題目的可滑動卡片"""
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
    
    for q_idx, question in enumerate(questions):
        # 檢查使用者是否已回答此題
        best_score = get_user_question_score(user_id, theme_id, level_idx, q_idx)
        has_answered = best_score > 0
        
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
            body_contents.append(
                FlexText(
                    text=f'最佳分數 Best: {best_score}/10',
                    wrap=True,
                    size='sm',
                    color='#00aa00',
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
                contents=[
                    FlexButton(
                        action=PostbackAction(
                            label='回答 Answer' if not has_answered else '再試一次 Try Again',
                            data=f'action=game_answer&theme={theme_id}&level={level_idx}&question={q_idx}'
                        ),
                        style='primary',
                    ),
                ]
            )
        )
        bubbles.append(bubble)
    
    return FlexMessage(
        altText=f'關卡 Level {level_idx + 1} 題目 Questions',
        contents=FlexCarousel(contents=bubbles)
    )

# 修改6: 分數永遠顯示，回饋條件顯示
async def game_score_message(user_id: str, theme_id: str, level_idx: int, question_idx: int, 
                             score: int, is_new_high: bool, npc_reply: str = None, 
                             feedback_chi: str = None, feedback_eng: str = None) -> FlexMessage:
    """顯示遊戲結果與分數 - 分數永遠顯示，回饋條件顯示"""
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
    
    # 總分也永遠顯示
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
    
    # 修改6: 回饋卡片 - 只在 display_feedback 為 true 時顯示
    if display_feedback:
        # 中文回饋
        if feedback_chi:
            chi_feedback_bubble = FlexBubble(
                size='giga',
                body=FlexBox(
                    layout='vertical',
                    spacing='sm',
                    contents=[
                        FlexText(
                            text='評語回饋 Feedback',
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
        
        # 英文回饋
        if feedback_eng:
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
        
        # 舊版相容：如果只有單一 npc_reply (用於舊版 GameResponse)
        if npc_reply and not feedback_chi and not feedback_eng:
            reply_bubble = FlexBubble(
                size='giga',
                body=FlexBox(
                    layout='vertical',
                    spacing='sm',
                    contents=[
                        FlexText(
                            text='劇情回應 NPC Reply',
                            wrap=True,
                            weight='bold',
                            size='xl',
                        ),
                        FlexText(
                            text=npc_reply,
                            wrap=True,
                            size='md',
                            color='#5b5b5b',
                            margin='md',
                        ),
                    ]
                )
            )
            bubbles.append(reply_bubble)
    
    msg = FlexMessage(
        altText=f'Q{question_idx + 1} 結果 Result',
        contents=FlexCarousel(contents=bubbles)
    )
    
    # 快速回覆按鈕
    msg.quick_reply = QuickReply(items=[
        QuickReplyItem(action=PostbackAction(
            label='再試一次 Try Again',
            data=f'action=game_answer&theme={theme_id}&level={level_idx}&question={question_idx}'
        )),
        QuickReplyItem(action=PostbackAction(
            label='題目列表 Questions',
            data=f'action=game_questions&theme={theme_id}&level={level_idx}'
        )),
    ])
    
    return msg

# ========== 修改5: NPC 選擇顯示卡片 ==========
async def game_npc_card_message(theme_id: str, npc_idx: int) -> FlexMessage:
    """顯示 NPC 卡片，包含頭像和背景介紹"""
    from utils.file_utils import get_game_npc_info
    
    npc_info = get_game_npc_info(theme_id, npc_idx)
    
    if not npc_info:
        return FlexMessage(
            altText='找不到角色 NPC not found',
            contents=FlexBubble(
                body=FlexBox(
                    layout='vertical',
                    contents=[FlexText(text='找不到角色資訊。\nNPC information not found.', wrap=True)]
                )
            )
        )
    
    body_contents = [
        FlexText(
            text=npc_info['name'],
            wrap=True,
            weight='bold',
            size='xxl',
            align='center',
        ),
        FlexText(
            text='角色背景 Character Background',
            wrap=True,
            size='md',
            align='center',
            color='#666666',
            margin='md',
        ),
        FlexText(
            text=npc_info['persona'],
            wrap=True,
            size='md',
            color='#5b5b5b',
            margin='lg',
        ),
    ]
    
    bubble = FlexBubble(
        size='giga',
        body=FlexBox(
            layout='vertical',
            spacing='md',
            contents=body_contents
        ),
        footer=FlexBox(
            layout='vertical',
            spacing='sm',
            contents=[
                FlexText(
                    text='發送語音訊息開始對話\nSend a voice message to start talking',
                    wrap=True,
                    size='sm',
                    align='center',
                    color='#888888',
                ),
            ]
        )
    )
    
    # 如果有 NPC 頭像則顯示
    if npc_info.get('image'):
        bubble.hero = FlexImage(
            url=f'{URL}/templates/rag_test/{npc_info["image"]}',
            size='full',
            aspect_ratio='1:1',
            aspect_mode='cover',
        )
    
    return FlexMessage(
        altText=f'{npc_info["name"]} - 角色卡 Character Card',
        contents=bubble
    )

# ========== 修改2&3: NPC 對話回應訊息 ==========
async def game_npc_chat_response_message(npc_name: str, npc_reply: str, 
                                          feedback: str = None, is_english: bool = True) -> FlexMessage:
    """顯示 NPC 對話回應，包含語言提示"""
    display_feedback = get_display_feedback()
    
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
    
    # NPC 回覆卡片 - 永遠顯示
    reply_bubble = FlexBubble(
        size='giga',
        body=FlexBox(
            layout='vertical',
            spacing='sm',
            contents=[
                FlexText(
                    text=f'{npc_name} 說：',
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
        )
    )
    bubbles.append(reply_bubble)
    
    # 語言建議卡片 - 只在 display_feedback 為 true 且有建議時顯示
    if display_feedback and feedback:
        feedback_bubble = FlexBubble(
            size='giga',
            body=FlexBox(
                layout='vertical',
                spacing='sm',
                contents=[
                    FlexText(
                        text='語言建議 Language Tips',
                        wrap=True,
                        weight='bold',
                        size='lg',
                    ),
                    FlexText(
                        text=feedback,
                        wrap=True,
                        size='md',
                        color='#5b5b5b',
                        margin='md',
                    ),
                ]
            )
        )
        bubbles.append(feedback_bubble)
    
    return FlexMessage(
        altText=f'{npc_name} 的回應',
        contents=FlexCarousel(contents=bubbles)
    )

# ========== 結束修改 ==========

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
    """顯示 NPC 選擇介面"""
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
                    text=f"已回答題數 Answered: {progress['questions_answered']}",
                    wrap=True,
                    size='md',
                    align='center',
                    color='#5b5b5b',
                ),
            ]
        )
    )
    bubbles.append(progress_bubble)
    
    # NPC 選擇卡片
    for npc_idx, npc in enumerate(theme_config.npcs):
        npc_body_contents = [
            FlexText(
                text=npc.name,
                wrap=True,
                weight='bold',
                size='lg',
                align='center',
            ),
            FlexButton(
                action=PostbackAction(
                    label='對話 Talk',
                    data=f'action=game_npc&theme={theme_id}&npc={npc_idx}'
                ),
                style='primary',
            ),
        ]
        
        npc_bubble = FlexBubble(
            size='mega',
            body=FlexBox(
                layout='vertical',
                spacing='md',
                justifyContent='center',
                alignItems='center',
                contents=npc_body_contents
            )
        )
        
        # 如果有 NPC 頭像則顯示
        if npc.image:
            npc_bubble.hero = FlexImage(
                url=f'{URL}/templates/rag_test/{npc.image}',
                size='full',
                aspect_ratio='1:1',
                aspect_mode='cover',
            )
        
        bubbles.append(npc_bubble)
    
    return FlexMessage(
        altText=f'{theme_config.name} - 選擇角色 Select NPC',
        contents=FlexCarousel(contents=bubbles)
    )

async def game_level_select_message(theme_id: str, user_id: str) -> FlexMessage:
    """顯示關卡選擇介面"""
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
    
    bubbles = []
    
    for level in theme_config.levels:
        level_score = get_user_level_score(user_id, theme_id, level.id)
        questions_per_level = get_questions_per_level()
        max_level_score = questions_per_level * 10
        
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
                    color='#00aa00',
                    margin='sm',
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
    
    return FlexMessage(
        altText=f'{theme_config.name} - 選擇關卡 Select Level',
        contents=FlexCarousel(contents=bubbles)
    )

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