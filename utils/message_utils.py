from config import line_bot_api, line_bot_api_blob, DOMAIN, question_manager
from linebot.v3.messaging import (
    ReplyMessageRequest, TextMessage, PostbackAction, QuickReply,
    QuickReplyItem, RichMenuRequest, RichMenuSize, RichMenuArea,
    RichMenuBounds, FlexMessage, FlexCarousel, FlexBubble, FlexImage,
    FlexText, FlexBox, FlexButton
)
from linebot.v3.messaging.exceptions import ApiException
from linebot.v3.messaging.models import SetWebhookEndpointRequest
from utils.models import SpeechAssessment
import json
from PIL import Image
from utils.file_utils import (
    get_test_mode, getData, get_category, getHistory, get_rich_menu_id, set_rich_menu_id, save_config,
    get_category
)
# 設定主網址和分類變數
URL = f'https://{DOMAIN}'
IMG_EXT = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')

# 系統評估提示語，指導如何進行回答分析
SYSTEM_INSTRUCTION = f"""
        你是一個專業英語口說評量助手，擅長根據學生的回答提供改進建議和改善後之文本。
        
        userAnswer 代表使用者的口說回答
        question 代表題目
        standard 代表評量標準
        
        Sample Question #1: Based on the vocabulary provided, explain the meaning of the word "Brochure".
        Sample Question #2: <An image shows a scene inside a bank or a similar service center. Several people are lined up in a queue, waiting at counters, likely to speak with tellers or staff behind glass or plastic dividers.>
        
        10分 優異表達者
        表達清晰度：能清楚表達意見或完整描述，回應詳細且準確。
        主題相關性：回應與主題高度相關，能深入探討主題的各個面向，展現出對主題的全面理解，並能有效地連結相關概念。
        語法使用：熟練使用基本及複雜的文法，無明顯錯誤。
        字彙量：詞彙使用豐富且精準，能靈活運用各種詞彙。
        回應複雜度：能對詞彙解釋、圖片描述及段落構建給出完整且有深度的回應。
        Answer #1: A brochure is a printed material designed to provide detailed information about a
        product, service, or event, often including eye-catching images and persuasive text to attract potential customers.
        Answer #2: The picture shows people standing in line at a bank counter, each waiting patiently 
        for their turn. The setting appears orderly, and the individuals are maintaining a 
        proper distance.
        
        9分 優良表達者
        表達清晰度：能有效表達意見或描述圖片，內容清楚。 
        主題關聯性：回應與主題相關，雖然可能未能完全深入探討所有面向，但能夠有效地涵蓋主要的主題要素，展現出對主題的基本理解。
        語法使用：能使用複雜語法，偶有小錯誤但不影響理解。 
        字彙量：詞彙豐富但有少量不精確的使用。 
        回應複雜度：能有效回應並詳細解釋詞彙，描述圖片清楚。 
        Answer #1: A brochure is a printed document that gives information about a specific product 
        or service, usually featuring attractive images and descriptions to engage the reader.
        Answer #2: Several people are standing in line at a bank. They are waiting for their turn at the 
        counter in an organized manner. 
        
        8分 良好表達者
        表達清晰度：能清楚表達大部分意見，描述圖片時可能有些許不清晰之處。
        主題關聯性：回應與主題有一定的關聯性，能表達出主題的部分要素，但可能在深度和廣度上有所欠缺，影響整體的主題呈現。
        語法使用：能使用較複雜的語法，但存在一些錯誤。 
        字彙量：詞彙量足夠，但在精確性上有所欠缺。 
        回應複雜度：能回應詞彙解釋和圖片描述，但不總是完全準確。 
        Answer #1: A brochure is a type of printed material that explains a product or service, often 
        with pictures and text to help people understand what is being offered.
        Answer #2: The image shows people waiting in line at a bank counter. They are standing one 
        behind another. 
        
        7分 基礎表達者 
        表達清晰度：能夠基本描述圖片，但表達的清晰度不穩定。
        主題關聯性：回應的主題關聯性不穩定，能提供基本的主題訊息，但對於主題的理解和闡述顯得淺薄，可能未能完整呈現主題內容。
        語法使用：基本語法使用正確，但在使用較複雜語法時有明顯錯誤。
        字彙量：詞彙量有限，影響表達的完整性。 
        回應複雜度：能提供基本回應，但深度和連貫性不足。 
        Answer #1: A brochure is a printed piece that tells about a product or service, usually with 
        some images and information.
        Answer #2: People are lined up at a counter. It looks like they are at a bank, waiting for service.
        
        6分 有限表達者 
        表達清晰度：在解釋詞彙和描述圖片時，表達不清晰，可能影響理解。
        主題關聯性：回應與主題的關聯性較弱，內容可能偏離主題，影響理解的完整性和準確性，未能提供有意義的主題解釋。
        語法使用：主要使用簡單語法，複雜語法的使用常出錯。
        字彙量：詞彙量有限，常常無法找到適當的詞彙。
        回應複雜度：回應缺乏詳細性和深度。
        Answer #1: A brochure is a paper that has information about something, often with pictures.
        Answer #2: There are people waiting in line at what seems to be a bank. 
        
        5分 簡單表達者 
        表達清晰度：回應中存在不連貫的部分，圖片描述或詞彙解釋可能無法理解。
        主題關聯性：回應與主題的關聯性非常有限，內容多為簡單陳述，未能有效地表達主題的關鍵概念，導致聽眾難以理解主題。
        語法使用：主要使用基本語法，錯誤頻繁。
        字彙量：詞彙量非常有限，表達受限。
        回應複雜度：回應多為簡單句，缺乏深入性。 
        Answer #1: A brochure is a small booklet that gives information.
        Answer #2: People are standing in line at a counter. It looks like a bank. 
        
        4分 有限互動能力者 
        表達清晰度：無法完整描述圖片，回應詞彙解釋時表達不清。 
        主題關聯性：回應基本無法與主題相關聯，內容不清，無法有效地表達主題的意義，影響整體的表達效果。
        語法使用：語法錯誤頻繁，影響理解。 
        字彙量：詞彙量極少，無法有效表達意見。
        回應複雜度：無法給出複雜回應，多為不完整句子。 
        Answer #1: A brochure is paper that shows products.
        Answer #2: People are waiting at a counter in a bank. 
        
        3分 極度有限的表達者 
        表達清晰度：多數時間無法完成句子，描述圖片時困難重重。
        主題關聯性：回應與主題幾乎無關，表達能力極為不足，無法提供有意義的主題內容，影響聽眾的理解。
        語法使用：無法正確使用基本語法，錯誤頻繁且嚴重。
        字彙量：詞彙量極度有限，無法進行有效表達。 
        回應複雜度：無法給出有效回應。 
        Answer #1: A brochure is for information. 
        Answer #2: People are standing in line. It looks like a bank. 
        
        2分 極低表達能力者 
        表達清晰度：只能使用簡單詞語或片語，無法形成完整句子。
        主題關聯性：無法理解主題，回應內容完全無法與主題相連結，幾乎無法表達任何訊息。
        語法使用：無法使用基本語法。
        字彙量：詞彙極少，無法有效傳達訊息。 
        回應複雜度：無法回應基本問題。 
        Answer #1: A brochure is a book.
        Answer #2: People are at a bank.
        
        1分 無表達能力者 
        表達清晰度：無法作答或表達。 
        主題關聯性：完全無法進行主題相關的表達或回應，無法提供任何訊息。
        語法使用：無法使用任何語法。 
        字彙量：無可使用詞彙。 
        回應複雜度：無回應能力。 
        Answer #1: <Not speaking, nonsense, or not knowing> 
        Answer #2: <Not speaking, nonsense, or not knowing>
        
        你需要以4個步驟執行任務，Think step by step:
        1. 針對以下評估面向給予分析和建議：表達清晰度、語法使用、詞彙量、回應複雜度、主題相關性進行思考評估。
        2. 根據提供之評分標準，為學生的口說回答評分(It's okay to give out a full marks)。
        3. 給予具體分析和建議，如糾正語法錯誤、建議使用更自然的語句或增加詞彙量，以台灣繁體中文與英文回傳。
        4. 依照學生回答文本，延伸或改進其回答，以英文回覆。
        
        The JSON object must use the schema: {json.dumps(SpeechAssessment.model_json_schema(), indent=2)}
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

async def result_message(result: SpeechAssessment, unit, sub):
    return FlexMessage(
        altText=f'{unit+1}-{sub+1} 口語練習結果',
        quickReply=QuickReply(items=[
            QuickReplyItem(action=PostbackAction(label='再次回答 Again',data=f'action=record&unit={unit}&sub={sub}')),
            QuickReplyItem(action=PostbackAction(label='下一題 Next', data=f'action=unit&unit={unit+1}' if len(question_manager.get_unit(get_category(),unit))-1 == sub else f'action=record&unit={unit}&sub={sub+1}')),
            QuickReplyItem(action=PostbackAction(label='查看單元 Back', data=f'action=unit&unit={unit+1}')),
        ]),
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
                                text=f'Q{unit+1}-{sub+1} 練習結果 Result',
                                wrap=True,
                                weight='bold',
                                size='xxl',
                            ),
                            FlexBox(
                                layout='vertical',
                                margin='md',
                                contents=[
                                    FlexText(
                                        text=f'評分 Score: {result.score}/{question_manager.get_question(get_category(),unit,sub).get("max_score",10)}',
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
            ] if not get_test_mode() else [
                FlexBubble(
                    size='giga',
                    body=FlexBox(
                        layout='vertical',
                        justifyContent='center',
                        alignItems='center',
                        contents=[
                            FlexText(
                                text=f'Q{unit+1}-{sub+1} 作答完成 Complete',
                                wrap=True,
                                weight='bold',
                                size='xxl',
                            ),
                        ],
                    ),
                ),
            ]
        )
    )

async def question_message(unit, sub):
    messages = []
    question = question_manager.get_question(get_category(), unit, sub)
    contents = [
        FlexText(
            text=f'Q{unit+1}-{sub+1}',
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
    
async def carousel_message(user_id, unit):
    if len(question_manager.get_category(get_category())) < unit:
        return None
    cols = []
    for sub,j in enumerate(question_manager.get_unit(get_category(),unit-1)):
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
        if getHistory(user_id, f'{get_category()}-{unit-1}-{sub}'):
            body.contents.append(
                FlexButton(
                    action=PostbackAction(
                        label='查看結果 Result',
                        data=f'action=result&unit={unit-1}&sub={sub}'
                    ),
                    height='sm',
                    style='secondary',
                )
            )
        cols.append(FlexBubble(
            hero=FlexImage(
                url=f'{URL}/templates/{get_category()}/cover{unit}-{sub+1}.jpg',
                size='full',
                aspect_ratio='20:13',
                aspect_mode='cover',
            ),
            body=body
        ))
    if len(question_manager.get_category(get_category())) > unit:
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
    '請輸入你的上課時段\n如：1-34',
    '接著，請輸入你的系級\n如：資管一乙',
    '接著，請輸入你的學號\n如：11352237',
    '接著，請輸入你的姓名\n如：王聰明',
]

ENG_HINT =[
    'What is your class period?\nFor example: 1-34',
    'Next, what is your department?\nFor example: Information Management',
    'Next, what is your student ID?\nFor example: 11352237',
    'Next, what is your name?\nFor example: Paul Wang',
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

async def data_message():
    user_data = getData()

    user_count = len(user_data)
    total_history_score = 0
    total_history_count = 0
    max_score = float('-inf')
    min_score = float('inf')
    users_with_history = 0
    users_with_all = 0

    total_questions = sum([len(i) for i in question_manager.get_category(get_category())])
    
    for user in user_data.values():
        user_history = [key.startswith(f'{get_category()}-') for key in user.history.keys()]
        if user.history and len(user_history) > 0:
            users_with_history += 1
            if len(user_history) >= total_questions:
                users_with_all += 1
        for str, assessment in user.history.items():
            if not str.startswith(f'{get_category()}-'):
                continue
            total_history_score += assessment.score
            total_history_count += 1
            if assessment.score > max_score:
                max_score = assessment.score
            if assessment.score < min_score:
                min_score = assessment.score

    average_history_score = total_history_score / total_history_count if total_history_count > 0 else 0
    average_history_per_user = total_history_count / users_with_history if users_with_history > 0 else 0

    return FlexMessage(
        altText="User data analysis",
        contents=FlexBubble(
            size='mega',
            body=FlexBox(
                layout='vertical',
                spacing='lg',
                contents=[
                    FlexText(
                        text=f"用戶總數: {user_count}\n有歷史紀錄的用戶數: {users_with_history}\n答完題目的用戶數: {users_with_all}\n每個用戶平均歷史紀錄數: {average_history_per_user:.2f}\n歷史紀錄平均分數: {average_history_score:.2f}\n歷史紀錄最高分: {max_score}\n歷史紀錄最低分: {min_score}",
                        wrap=True,
                        size='md',
                     ),
                ],
            ),
        )
    )

async def handle_rich_menu(user_id):
    rich_menu_id = get_rich_menu_id(get_category())
    try:
        oldId = await line_bot_api.get_rich_menu_id_of_user(user_id, async_req=True).get()
        if oldId.rich_menu_id is not rich_menu_id:
            await line_bot_api.link_rich_menu_id_to_user(user_id, rich_menu_id=rich_menu_id, async_req=True).get()
    except ApiException as e:
        await line_bot_api.link_rich_menu_id_to_user(user_id, rich_menu_id=rich_menu_id, async_req=True).get()

async def create_rich_menu():
    rich_menu_id = get_rich_menu_id(get_category())
    await line_bot_api.set_webhook_endpoint(SetWebhookEndpointRequest(endpoint=f'{URL}/callback'))
    if not rich_menu_id:
        # Load image and get dimensions
        path = f'templates/richmenu-{get_category()}.png'
        width, height = Image.open(path).size

        # Calculate rows and columns
        rows = height // 843
        cols = width // 3
        area_height = height // rows

        # Create RichMenuRequest with areas
        request = RichMenuRequest(
            size=RichMenuSize(width=width, height=height),
            name="Menu",
            chatBarText="CoachGPT",
            selected=True,
            areas=[
                RichMenuArea(
                    bounds=RichMenuBounds(
                        x=(i % 3) * cols,
                        y=(i // 3) * area_height,
                        width=cols,
                        height=area_height
                    ),
                    action=PostbackAction(label=f'Ex {i+1}', data=f'action=unit&unit={i+1}')
                )
                for i in range(3 * rows)
            ]
        )
        rich_menu = await line_bot_api.create_rich_menu(
            rich_menu_request=request,
            async_req=True
        ).get()

        rich_menu_id = rich_menu.to_dict().get('richMenuId')
        set_rich_menu_id(rich_menu_id, get_category())
        await save_config()
        
        await line_bot_api_blob.set_rich_menu_image_with_http_info(
            rich_menu_id=rich_menu_id,
            body=path,
            _headers={"Content-Type": "image/png"},
            async_req=True
        ).get()
        await line_bot_api.set_default_rich_menu_with_http_info(
            rich_menu_id=rich_menu_id,
            async_req=True
        ).get()
        
    print(f'Rich Menu ID: {rich_menu_id}')
