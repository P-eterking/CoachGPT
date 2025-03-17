from config import line_bot_api, rich_menu_manager, DOMAIN, question_manager
from linebot.v3.messaging import (
    ReplyMessageRequest, TextMessage, PostbackAction, QuickReply,
    QuickReplyItem, FlexMessage, FlexCarousel, FlexBubble, FlexImage,
    FlexText, FlexBox, FlexButton, AudioMessage
)
from manager.richmenu import *
from linebot.v3.messaging.exceptions import ApiException
from linebot.v3.messaging.models import SetWebhookEndpointRequest
from utils.models import SpeechAssessment
import json
from utils.file_utils import (
    get_user_state, getHistory, get_rich_menu_id, isEnabled, isResponse, set_rich_menu_id, save_config, get_rich_menu_category_from_id, clear_rich_menu_id
)
# 設定主網址和分類變數
URL = f'https://{DOMAIN}'
IMG_EXT = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')

# 系統評估提示語，指導如何進行回答分析
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
        
        若評分標準為四個級距：
        4	受測者能使用完整句子回答問題，內容完全正確，無語法或資訊錯誤。回答清晰流暢，能有效傳達題目所要求的資訊，無需修改即可理解。評分回饋應鼓勵學生繼續保持正確性與流利度，並在可能的情況下增加細節來強化表達。
        3	受測者的回答大部分正確，但可能有部分資訊遺漏，影響回應的完整性。即使回答內容大致符合題目要求，但句子結構仍需調整。評分回饋應指導學生在句子結構或細節準確性上進行改善，確保完整表達所有必要資訊。
        2	受測者的回答可能僅表達部分資訊，使回答難以理解。可能未使用完整句子，或回答過於簡略，導致資訊不明確。評分回饋應提供更基礎的建議，幫助學生增強語法與句子結構的理解，確保資訊完整與正確。
        1	受測者未作答，或回答內容完全錯誤。可能僅說出無關的單字或片語，或提供與問題不符的資訊。評分回饋應建議學生閱讀題目並嘗試使用完整句子進行回應，以提升基本表達能力。
        
        你需要以4個步驟執行任務，Think step by step:
        1. 針對提供之評估面向給予分析和建議：表達清晰度、語法使用、詞彙量、回應複雜度、主題相關性進行思考評估。
        2. 根據提供之評分標準範例與級距，為學生的口說回答評分(It's okay to give out a full marks)。
        3. 給予具體分析和建議，如糾正語法錯誤、建議使用更自然的語句或增加詞彙量，以台灣繁體中文(zh-TW)與英文(en-US)回應。
        4. 依照學生回答文本，延伸或改進其回答，以英文回覆。
        
        The JSON object must use the schema: {json.dumps(SpeechAssessment.model_json_schema(), indent=2)}
    """
    
async def send_message(event, msg):
    """
    發送訊息給使用者。
    
    Sends a message to the user.

    Args:
        event: 事件物件，包含回覆token。
        msg: 要發送的訊息，可以是單一訊息或訊息列表。
    """
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
    """
    建立文字訊息物件。
    
    Creates a text message object.

    Args:
        text: 要發送的文字內容。
    
    Returns:
        TextMessage: 文字訊息物件。
    """
    return TextMessage(text=text)

async def send_text_message(event, text):
    """
    發送文字訊息給使用者。
    
    Sends a text message to the user.

    Args:
        event: 事件物件，包含回覆token。
        text: 要發送的文字內容。
    """
    await line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=text)]
        )
    )

async def send_audio_message(event, filename, duration):
    """
    發送音訊訊息給使用者。
    
    Sends an audio message to the user.
       Args:
        event: 事件物件，包含回覆token。
        url: 音訊檔案的網址。
    """
    await line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[AudioMessage(originalContentUrl=f'{URL}/templates/{filename}', duration=duration)]
        )
    )

async def progress_message(user_id):
    """
    生成使用者未回答問題的進度訊息。
    
    Generates a progress message for unanswered questions for the user.

    Args:
        user_id: 使用者ID。
    
    Returns:
        TextMessage: 進度訊息物件。
    """
    questions = question_manager.questions  # Assume this function retrieves all categories
    progress: dict[str: list[int]] = {}
    total = 0
    
    for category, question in questions.items():
        if not isEnabled(category):
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
    
    # Create a formatted message
    message = f"您尚未回答 Questions Unanswered ({sum(len(v) for v in progress.values())}):\n"
    for category, subs in progress.items():
        if len(subs) > 0:
            message += f"\n{rich_menu_manager.get_display_name(category)}:\n"
        for i, sub in enumerate(subs):
            message += f"{"\n" if i > 0 else ""} - Q{sub+1}"
    
    return TextMessage(text=message)
    
    
async def result_message(result: SpeechAssessment, category: str, sub: int):
    """
    生成口語評估結果訊息。
    
    Generates a speech assessment result message.

    Args:
        result: 口語評估結果物件。
        unit: 單元編號。
        sub: 子單元編號。
    
    Returns:
        FlexMessage: 口語評估結果訊息物件。
    """
    q = question_manager.get_question(category, sub)
    msg = FlexMessage(
        altText=f'Q{sub+1} 口語練習結果 Result',
        contents=FlexCarousel(
            contents=[
                FlexBubble(
                    size='giga',
                    body=FlexBox(
                        layout='vertical',
                        justifyContent='center',
                        alignItems='center',
                        contents=[
                            FlexText(
                                text=f'Q{sub+1} 練習結果 Result',
                                wrap=True,
                                weight='bold',
                                size='xxl',
                            ),
                            FlexBox(
                                layout='vertical',
                                margin='md',
                                contents=[
                                    FlexText(
                                        text=f'評分 Score: {result.score}/{q.max_score if q.max_score else 10}',
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
                FlexBubble(
                    size='giga',
                    body=FlexBox(
                        layout='vertical',
                        spacing='sm',
                        contents=[
                            FlexText(
                                text='建議 Suggestions',
                                wrap=True,
                                weight='bold',
                                size='xl',
                            ),
                            FlexBox(
                                layout='vertical',
                                margin='md',
                                spacing='sm',
                                contents=[
                                    FlexText(
                                        text=result.chi_suggestion.replace('\\n','\n').strip(),
                                        color='#5b5b5b',
                                        size='sm',
                                        wrap=True,
                                        flex=1,
                                    ),
                                    FlexText(
                                        text=result.eng_suggestion.replace('\\n','\n').strip(),
                                        color='#5b5b5b',
                                        size='sm',
                                        wrap=True,
                                        flex=1,
                                    )
                                ]
                            ),
                        ]
                    )
                ),
                FlexBubble(
                    size='giga',
                    body=FlexBox(
                        layout='vertical',
                        spacing='sm',
                        contents=[
                            FlexText(
                                text='可改善為 Improvements',
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
            ] if isResponse(category) else [
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
                                        text=f'評分 Score: {result.score}/{q.max_score if q.max_score else 10}',
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
        )
    )
    msg.quick_reply = QuickReply(items=[
        QuickReplyItem(action=PostbackAction(label='再次回答 Again',data=f'action=record&sub={sub}')),
        # QuickReplyItem(action=PostbackAction(label='查看單元 Back', data=f'action=unit&unit={unit+1}')),
    ])
    if len(question_manager.get_all_questions(category))-1 > sub:
        msg.quick_reply.items.append(QuickReplyItem(action=PostbackAction(label='下一題 Next', data=f'action=record&sub={sub+1}')))
    return msg

async def chat_message(user_id, sub):
    return TextMessage(text=f'已選擇主題 {sub+1}！\nSelected subject {sub+1}!', quick_reply=QuickReply(items=[
        QuickReplyItem(action=PostbackAction(label='', data=f'action=record&sub={sub}')),]))
    

async def question_message(category, sub):
    """
    生成問題訊息。
    
    Generates a question message.

    Args:
        unit: 單元編號。
        sub: 子單元編號。
    
    Returns:
        FlexMessage: 問題訊息物件。
    """
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
    
    # Add image if present
    if question.image_url:
        contents.insert(1, FlexImage(
            url=f'{URL}{question.image_url}',
            size='full',
            aspect_ratio='1:1',
            aspect_mode='cover',
            margin='md'
        ))
        
    messages.append(FlexBubble(   
            size='giga', 
            body=FlexBox(
                layout='vertical',
                wrap=True,
                contents=contents
            ),
            footer=FlexBox(
                layout='vertical',
                spacing='sm',
                alignItems='center',
                justifyContent='center',
                contents=[
                    FlexText(
                        style='italic',
                        size='md',
                        wrap=True,
                        align='center',
                        text='請按下方按鈕開始錄音回答\nPress record button below to start',
                    )
                ]
            )
        )
    )
    
    if question.extra_info:
        for obj in question.extra_info:
            if isinstance(obj, str):
                obj = [obj]
            messages.append(FlexBubble(
                size='giga',
                body=FlexBox(
                    layout='vertical',
                    spacing='sm',
                    contents=[
                        FlexText(
                            text=i.strip(),
                            wrap=True,
                            size='md',
                        ) if not i.lower().endswith(IMG_EXT) else 
                        FlexImage(
                            url=URL+i,
                            size='full',
                            aspect_ratio='1:1',
                            aspect_mode='fit',
                        )
                        for i in obj
                    ]
                )
            ))
    
    return FlexMessage(
        altText='口語練習',
        contents=FlexCarousel(contents=messages)
    )
    
async def carousel_message(user_id, category, unit):
    """
    生成單元導覽訊息。
    
    Generates a unit navigation message.

    Args:
        user_id: 使用者ID。
        unit: 單元編號。
    
    Returns:
        FlexMessage: 單元導覽訊息物件。
    """
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

CHI_HINT = [
    '請輸入你的上課時段\n1 代表英聽課(建築)\n2 代表英聽課(商設)\n3 代表英國課(1-56)\n4 代表英國課(1-78)',
    '接著，請輸入你的系級\n如：資管一乙\n輸入 "Back" 可返回上一步',
    '接著，請輸入你的學號\n如：11352237\n輸入 "Back" 可返回上一步',
    '接著，請輸入你的姓名\n如：王聰明\n輸入 "Back" 可返回上一步',
]

ENG_HINT =[
    'Enter your class time\n1 for English Listening and Speaking in Lab (Architecture)\n2 for English Listening and Speaking in Lab (Commercial Design)\n3 for British Culture and Lifestyle (1-56)\n4 for British Culture and Lifestyle (1-78)',
    'Next, what is your department?\nFor example: Information Management\nEnter "Back" to previous step.',
    'Next, what is your student ID?\nFor example: 11352237\nEnter "Back" to previous step.',
    'Next, what is your name?\nFor example: Paul Wang\nEnter "Back" to previous step.',
]

async def info_hint_message(index: int):
    """
    生成資料綁定提示訊息。
    
    Generates an information binding hint message.

    Args:
        index: 提示訊息的索引。
    
    Returns:
        FlexMessage: 資料綁定提示訊息物件。
    """
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

async def handle_rich_menu(user_id):
    """
    處理使用者的Rich Menu。
    
    Handles the user's rich menu.

    Args:
        user_id: 使用者ID。
    """
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
    """
    創建Rich Menu。
    
    Creates a rich menu.
    """
    await line_bot_api.set_webhook_endpoint(SetWebhookEndpointRequest(endpoint=f'{URL}/callback'))
    configs = load_rich_menu_configs()
    response = await rich_menu_manager.get_all_rich_menus()
    if len(response) != len(configs['rich_menus'].items()):
        print("Deleting all rich menus...")
        for r in response:
            await rich_menu_manager.delete_rich_menu(r.rich_menu_id)
        clear_rich_menu_id()
    for menu_name, config in configs['rich_menus'].items():
        rich_menu_manager.set_display_name(menu_name, config.get('chat_bar_text'))
        if get_rich_menu_id(menu_name):
            continue
        builder = build_rich_menu_from_config(menu_name, config)
        rich_menu_id = await rich_menu_manager.create_rich_menu(builder)
        image_file = config.get("file")
        if image_file:
            image_path = os.path.join("./templates/richmenu", image_file)
            await rich_menu_manager.upload_rich_menu_image(rich_menu_id, image_path)
        if builder.selected:
            await rich_menu_manager.set_default_rich_menu(rich_menu_id)
        set_rich_menu_id(rich_menu_id, menu_name)
        print(f'Rich Menu {menu_name} created with ID: {rich_menu_id}')
    await save_config()
