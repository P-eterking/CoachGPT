from typing import Annotated
from config import line_bot_api, line_bot_api_blob, DOMAIN
from linebot.v3.messaging import (
    ReplyMessageRequest, TextMessage, PostbackAction, QuickReply,
    QuickReplyItem, RichMenuRequest, RichMenuSize, RichMenuArea,
    RichMenuBounds, FlexMessage, FlexCarousel, FlexBubble, FlexImage,
    FlexText, FlexBox, FlexButton
)
from linebot.v3.messaging.exceptions import ApiException
from pydantic import BaseModel
import json
import asyncio

url  = f'https://{DOMAIN}'
qs = [
    [
        {
            "text": "**What does 'inexpensive' mean, and can you name something that is inexpensive?**\n - 什麼是「便宜」的意思？你能舉出一個「便宜」的例子嗎？",
            "image_url": None
        },
        {
            "text": "**Look at the image and describe what you see in the store.**\n - 看著圖片，描述你在商店裡看到什麼。",
            "image_url": f"{url}/templates/store.jpg"
        },
        {
            "text": "**How would you describe 'portable'? Mention a portable item you use.**\n - 「便攜的」應該怎麼解釋？提到一個你使用「便攜的」物品。",
            "image_url": None
        },
        {
            "text": "**What is the role of 'management' in a company?**\n - 在公司中，「管理」有什麼作用？",
            "image_url": None
        },
        {
            "text": "**Define 'manual' and give an example of a manual task.**\n - 定義「手動」並給出一個關於「手動」任務的例子。",
            "image_url": None
        },
        {
            "text": "**Can you make a sentence using 'export' and 'recently'?**\n - 你能使用「出口」和「最近」造一個句子嗎？",
            "image_url": None
        },
        {
            "text": "**Describe a situation where you might need to 'replace' something because it is 'inexpensive'.**\n - 描述一個你可能需要因為物品是「便宜」而「取代」它的情境。",
            "image_url": None
        },
        {
            "text": "**How would you tell someone to 'decrease' the volume using polite language?**\n - 你會如何用禮貌的語言告訴某人「減少」音量？",
            "image_url": None
        },
        {
            "text": "**Write a sentence where you explain to a friend why something is 'comfortable'.**\n - 寫一個句子解釋給朋友聽為什麼某物是「舒服的」。",
            "image_url": None
        }
    ],
    [
        {
            "text": "**Meet the Deadline:**\n- Can you describe a time when you had to meet a tight deadline?\n- 你能描述一次你必須在截止日期前完成任務的情況嗎？",
            "image_url": None
        },
        {
            "text": "**Apply for the Job:**\n- What kind of job do you want to apply for?\n- 你想申請什麼樣的工作？",
            "image_url": None
        },
        {
            "text": "**Keep in Touch with Someone:**\n- Talk about a friend or family member you try to keep in touch with regularly.\n- 談談你努力與朋友或家人保持聯繫的情況。",
            "image_url": None
        },
        {
            "text": "**Offer a Discount:**\n- Please create a situation where you purchased an item because it was discounted.\n- 請創造一個你因為商品打折而購買的情況。",
            "image_url": None
        },
        {
            "text": "**Register In:**\n- Pretend you are a student, use 'register in' to make a sentence.\n- 假設你是一名學生，用“註冊”一詞造一個句子。",
            "image_url": None
        },
        {
            "text": "**Make an Appointment:**\n- Can you recall a time when you had to make an appointment for an important meeting or event?\n- 你能回憶起你曾經為一次重要的會議或活動預約的時候嗎？",
            "image_url": None
        },
        {
            "text": "**Remain a Concern:**\n- What things make you remain a concern?\n- 有什麼事情讓你一直擔心嗎？",
            "image_url": None
        },
        {
            "text": "**Book a Ticket:**\n- Describe a situation in which you would need to book a ticket by yourself.\n- 描述您需要自己訂票的情況",
            "image_url": None
        }
    ],
    [
        {
            "text": "**Beginning**: Introduce the main character and setting.\nA hare was making fun of a tortoise for moving so slowly. The tortoise got tired of the hare making fun of how slow he was. So, he asked the hare to have a race.\n**開始**：介紹主要角色和場景。\n一隻野兔正在嘲笑一隻行動緩慢的烏龜。烏龜厭倦了野兔嘲笑牠動作慢的樣子。於是牠要求野兔和他進行一場比賽。",
            "image_url": None
        },
        {
            "text": "**Then**: Introduce obstacles and challenges main character encounters.\nWhen the race started, the hare bounded off in front, making good progress. He was so far ahead of the tortoise that he decided he could afford to stop and have a rest.\n**然後**：介紹主要角色遇到的障礙和挑戰。\n比賽一開始，野兔就飛奔而出，並且進展迅速。遠遠地把烏龜甩在後面，牠覺得自己可以停下來休息一下。",
            "image_url": None
        },
        {
            "text": "**After**: Reach the climax or turning point of the story, where the main character confronts the central conflict head-on.\nHowever, the hare fell fast asleep, and as he lay sleeping, the tortoise continued to plod along at his slow pace. In time, he reached the finish-line and won the race.\n**之後**：到達故事的高潮或轉折點，主角正面對抗主要衝突。\n然而，野兔很快就睡著了，當牠在睡覺時，烏龜以緩慢的步伐繼續向前爬行。最終，烏龜到達了終點線，贏得了比賽。",
            "image_url": None
        },
        {
            "text": "**Ending**: Resolve the conflict and provide closure for the story. Show how the main character has changed. \nWhen the hare woke up, he was annoyed at himself for falling asleep. So he ran off towards the finish-line as fast as his legs would carry him, but it was too late, as the tortoise had already won.\n**結尾**：解決衝突並為故事提供結局。展示主角的變化。\n當野兔醒來時，他對自己睡著了感到懊惱。於是牠全力奔向終點線，但為時已晚，烏龜已經贏得了比賽。",
            "image_url": None
        }
    ]
]

class SpeechAssessment(BaseModel):
    suggestion: Annotated[str, '給予之中文建議']
    score: Annotated[int, '評量分數']
    transcript: Annotated[str, '轉錄後文本']
    better_ans: Annotated[str, '改善後文本']
    
    def to_dict(self) -> dict:
        return self.model_dump()
    
SYSTEM_INSTRUCTION = f"""
        你是一個專業英語口說評量助手，請根據學生的回答內容提供之台灣繁體中文具體改進建議和改善後之英文文本。
        請針對以下評估面向給予分析和建議：流暢度、表達清晰度、語法使用、詞彙量、回應複雜度、主題相關性、自信與互動性
        同時，提供具體的改進方式，如糾正語法錯誤、建議使用更自然的語句或增加詞彙量。
        
        Context #1: Based on the vocabulary provided, explain the meaning of the word "Brochure".
        Context #2: <An image shows a scene inside a bank or a similar service center. Several people are lined up in a queue, waiting at counters, likely to speak with tellers or staff behind glass or plastic dividers.>
        
        90-100分 優異表達者
        流暢度：非常流暢，無明顯停頓，能自信地解釋詞彙、描述圖片。
        表達清晰度：能清楚表達意見或完整描述，回應詳細且準確。
        語法使用：熟練使用基本及複雜的文法，無明顯錯誤。
        字彙量：詞彙使用豐富且精準，能靈活運用各種詞彙。
        回應複雜度：能對詞彙解釋、圖片描述及段落構建給出完整且有深度的回應。
        Answer #1: A brochure is a printed material designed to provide detailed information about a
        product, service, or event, often including eye-catching images and persuasive text to attract potential customers.
        Answer #2: The picture shows people standing in line at a bank counter, each waiting patiently 
        for their turn. The setting appears orderly, and the individuals are maintaining a 
        proper distance.
        
        80-89分 優良表達者
        流暢度：流暢，有少量停頓，但不影響整體表達。 
        表達清晰度：能有效表達意見或描述圖片，內容清楚。 
        語法使用：能使用複雜語法，偶有小錯誤但不影響理解。 
        字彙量：詞彙豐富但有少量不精確的使用。 
        回應複雜度：能有效回應並詳細解釋詞彙，描述圖片清楚。 
        Answer #1: A brochure is a printed document that gives information about a specific product 
        or service, usually featuring attractive images and descriptions to engage the reader.
        Answer #2: Several people are standing in line at a bank. They are waiting for their turn at the 
        counter in an organized manner. 
        
        70-79分 良好表達者
        流暢度：表達流暢，但有時會停頓。 
        表達清晰度：能清楚表達大部分意見，描述圖片時可能有些許不清晰之處。 
        語法使用：能使用較複雜的語法，但存在一些錯誤。 
        字彙量：詞彙量足夠，但在精確性上有所欠缺。 
        回應複雜度：能回應詞彙解釋和圖片描述，但不總是完全準確。 
        Answer #1: A brochure is a type of printed material that explains a product or service, often 
        with pictures and text to help people understand what is being offered.
        Answer #2: The image shows people waiting in line at a bank counter. They are standing one 
        behind another. 
        
        60-69分 基礎表達者 
        流暢度：表達時有明顯停頓，流暢度有限。 
        表達清晰度：能夠基本描述圖片，但表達的清晰度不穩定。 
        語法使用：基本語法使用正確，但在使用較複雜語法時有明顯錯誤。 
        字彙量：詞彙量有限，影響表達的完整性。 
        回應複雜度：能提供基本回應，但深度和連貫性不足。 
        Answer #1: A brochure is a printed piece that tells about a product or service, usually with 
        some images and information.
        Answer #2: People are lined up at a counter. It looks like they are at a bank, waiting for service.
        
        50-59分 有限表達者 
        流暢度：頻繁出現停頓和遲疑。 
        表達清晰度：在解釋詞彙和描述圖片時，表達不清晰，可能影響理解。 
        語法使用：主要使用簡單語法，複雜語法的使用常出錯。 
        字彙量：詞彙量有限，常常無法找到適當的詞彙。 
        回應複雜度：回應缺乏詳細性和深度。 
        Answer #1: A brochure is a paper that has information about something, often with pictures.
        Answer #2: There are people waiting in line at what seems to be a bank. 
        
        40-49分 簡單表達者 
        流暢度：表達中出現長時間停頓，語速較慢。 
        表達清晰度：回應中存在不連貫的部分，圖片描述或詞彙解釋可能無法理解。 
        語法使用：主要使用基本語法，錯誤頻繁。 
        字彙量：詞彙量非常有限，表達受限。 
        回應複雜度：回應多為簡單句，缺乏深入性。 
        Answer #1: A brochure is a small booklet that gives information.
        Answer #2: People are standing in line at a counter. It looks like a bank. 
        
        30-39分 有限互動能力者 
        流暢度：表達中有明顯且頻繁的停頓。 
        表達清晰度：無法完整描述圖片，回應詞彙解釋時表達不清。 
        語法使用：語法錯誤頻繁，影響理解。 
        字彙量：詞彙量極少，無法有效表達意見。
        回應複雜度：無法給出複雜回應，多為不完整句子。 
        Answer #1: A brochure is paper that shows products.
        Answer #2: People are waiting at a counter in a bank. 
        
        20-29分 極度有限的表達者 
        流暢度：表達中多數時間有長時間停頓，無法連貫。 
        表達清晰度：多數時間無法完成句子，描述圖片時困難重重。 
        語法使用：無法正確使用基本語法，錯誤頻繁且嚴重。 
        字彙量：詞彙量極度有限，無法進行有效表達。 
        回應複雜度：無法給出有效回應。 
        Answer #1: A brochure is for information. 
        Answer #2: People are standing in line. It looks like a bank. 
        
        10-19分 極低表達能力者 
        流暢度：幾乎無法進行持續表達。 
        表達清晰度：只能使用簡單詞語或片語，無法形成完整句子。 
        語法使用：無法使用基本語法。 
        字彙量：詞彙極少，無法有效傳達訊息。 
        回應複雜度：無法回應基本問題。 
        Answer #1: A brochure is a book.
        Answer #2: People are at a bank.
        
        0-9分 無表達能力者 
        流暢度：無法進行表達。 
        表達清晰度：無法作答或表達。 
        語法使用：無法使用任何語法。 
        字彙量：無可使用詞彙。 
        回應複雜度：無回應能力。 
        Answer #1: <Not speaking, nonsense, or not knowing> 
        Answer #2: Queue at the bank.
        
        你需要以3個步驟執行任務:
        1. 根據以上評分標準為學生回答評分。
        2. 思考並給予具體的改進建議，以繁體中文回覆。
        3. 依照學生回答文本，延伸或改進其回答，並以英文回覆。
        
        The JSON object must use the schema: {json.dumps(SpeechAssessment.model_json_schema(), indent=2)}
    """
    # f"""
    #             你是一個專業英語口說評量助手，你會根據題目與使用者提供的回答根據以下分數階段的評量標準進行評量。並以台灣繁體中文生成建議、0-200的客觀評分與改善後的英文 文本。
    #             190-200：可以流暢地表達與職場環境相關的語句。他們能夠非常清晰地表達意見或回覆複雜的請求，能夠適切地使用基本或複雜的文法；字彙的使用也是正確並精準地。
    #             此區間的考生也可以使用口語回答問題，並且傳達基本訊息。
    #             160-180：考生可以清楚的表達與職場環境相關的語句。他們能夠有效地表達意見或回覆複雜的請求，從他們較長的回應中，
    #             以下有些小缺失可能發生，但不會影響訊息本身： 
    #             1. 使用複雜的語法結構時發生一些錯誤。
    #             2. 一些不精確的詞彙。
    #             3. 此區間的考生可以使用口語回答問題，並且傳達基本訊息。
    #             130-150：考生被要求發表意見或回覆複雜的請求時，能夠提出相關的回應。不過，聽眾有時無法理解。
    #             這可能是因為下列幾點：
    #             1. 文法上的錯誤。
    #             2. 字彙量有限。
    #             此區間的考生通常可以回答問題，並且傳達基本的訊息。然而，有時候他們的回應是較難理解或解釋的。
    #             110-120：考生只能有限的發表意見或回覆複雜請求，回應時會出現下列的問題：
    #             語言不精確、模糊或重複。
    #             1. 意見表達能力有限和論點間關連性不大。
    #             2. 字彙量有限。
    #             此區間的考生通常可以回答問題，並且傳達基本訊息。然而，有時候他們的回應較難理解或解讀。
    #             80-100：考生無法表達意見或回覆複雜的請求。可能只能用單一句子或不完整的句子回答。其他可能出現的問題包括：
    #             1. 語言的使用非常有限。
    #             2. 字彙量嚴重不足。
    #             此區間的考生無法回答問題，或是傳達基本的訊息。
    #             60-70：考生勉強可以表達意見，但無法提出支持的論點，對於複雜的請求無法回應。此區間的考生無法回答問題，或是傳達基本訊息。此區間的考生通常缺乏足夠的字彙或文法能力來做簡單的說明。
    #             40-50：考生無法表達意見或提出支持的論點。他們既不能回應複雜的請求，也不能提出相關的回應。此區間的考生無法做到社會或職場上的一般互動，如：回答問題與傳達基本的訊息。
    #             0-30：考生在進行口說測驗時，通常會有許多部分沒有作答。考生也許不具備英文聽力或閱讀的基本技能，來了解測驗的指示或題目的內容。
    #             The JSON object must use the schema: {json.dumps(SpeechAssessment.model_json_schema(), indent=2)}
    #             """

rich_menu_id : str = None

def get_question(unit, sub):
    return qs[unit][sub]

def get_context_url():
    return f'{url}/templates/example_context.png'

async def send_message(event, msg):
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
            QuickReplyItem(action=PostbackAction(label='再次回答',data=f'action=record&unit={unit}&sub={sub}')),
            QuickReplyItem(action=PostbackAction(label='下一題', data=f'action=unit&unit={unit+1}' if len(qs[unit])-1 == sub else f'action=record&unit={unit}&sub={sub+1}')),
            QuickReplyItem(action=PostbackAction(label='查看單元', data=f'action=unit&unit={unit+1}')),
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
                                text=f'{unit+1}-{sub+1} 口語練習結果',
                                wrap=True,
                                weight='bold',
                                size='3xl',
                            ),
                            FlexBox(
                                layout='vertical',
                                margin='md',
                                contents=[
                                    FlexText(
                                        text=f'評分: {result.score}/100',
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
                                text='建議',
                                wrap=True,
                                weight='bold',
                                size='xl',
                            ),
                            FlexBox(
                                layout='vertical',
                                margin='md',
                                contents=[
                                    FlexText(
                                        text=result.suggestion,
                                        color='#5b5b5b',
                                        size='sm',
                                        wrap=True,
                                        flex=1,
                                    ),
                                ]
                            ),
                            FlexText(
                                text='可改善為',
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
            ]
        )
    )

async def question_message(unit, sub):
    question = get_question(unit, sub)
    contents = [
        FlexText(
            text=f'題目 {unit+1}-{sub+1}',
            wrap=True,
            weight='bold',
            size='xxl',
        ),
        FlexBox(
            layout='baseline',
            margin='md',
            contents=[
                FlexText(
                    text=question["text"],
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
    if question.get("image_url"):
        contents.insert(1, FlexImage(
            url=question["image_url"],
            size='full',
            aspect_ratio='20:13',
            aspect_mode='cover',
            margin='md'
        ))

    return FlexMessage(
        altText='口語練習',
        contents=FlexBubble(   
            size='giga', 
            body=FlexBox(
                layout='vertical',
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
                        text='用語音回答問題，請按下方按鈕開始錄音',
                    )
                ]
            )
        )
    )
    
async def carousel_message(unit):
    cols = []
    for sub,j in enumerate(qs[unit-1]):
        cols.append(FlexBubble(
            hero=FlexImage(
                url=f'{url}/templates/cover{unit}-{sub+1}.jpg',
                size='full',
                aspect_ratio='20:13',
                aspect_mode='cover',
            ),
            body=FlexBox(
                layout='vertical',
                spacing='lg',
                contents=[
                    FlexText(
                        text=f'口語練習 {unit}-{sub+1}',
                        wrap=True,
                        weight='bold',
                        size='xl',
                        align='center',
                    ),
                    FlexButton(
                        action=PostbackAction(
                            label='開始作答',
                            data=f'action=record&unit={unit-1}&sub={sub}'
                        ),
                        height='sm',
                        style='primary',
                    )
                ]
            )
        ))
    if len(qs) > unit:
        cols.append(FlexBubble(
            body=FlexBox(
                contents=[
                    FlexText(
                            text=f'前往下一單元',
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

async def handle_rich_menu(user_id):
    global rich_menu_id
    try:
        await line_bot_api.get_rich_menu_id_of_user(user_id, async_req=True).get()
    except ApiException as e:
        await line_bot_api.link_rich_menu_id_to_user(user_id, rich_menu_id=rich_menu_id, async_req=True).get()

async def create_rich_menu():
    global rich_menu_id
    rich_menu = await line_bot_api.create_rich_menu(
        rich_menu_request=RichMenuRequest(
            size=RichMenuSize(width=2500, height=843),
            name="Menu",
            chatBarText="Exercises 1~3",
            selected=True,
            areas=[
                RichMenuArea(
                    bounds=RichMenuBounds(x=0, y=0, width=833, height=843),
                    action=PostbackAction(label='Unit 1', data='action=unit&unit=1')
                ),
                RichMenuArea(
                    bounds=RichMenuBounds(x=833, y=0, width=833, height=843),
                    action=PostbackAction(label='Unit 2', data='action=unit&unit=2')
                ),
                RichMenuArea(
                    bounds=RichMenuBounds(x=1666, y=0, width=833, height=843),
                    action=PostbackAction(label='Unit 3', data='action=unit&unit=3')
                ),
            ]
        ),
        async_req=True
    ).get()

    rich_menu_id = rich_menu.to_dict().get('richMenuId')
        
    print(f'Rich Menu ID: {rich_menu_id}')
    
    await line_bot_api_blob.set_rich_menu_image_with_http_info(
        rich_menu_id=rich_menu_id,
        body='templates/richmenu.png',
        _headers={"Content-Type": "image/png"},
        async_req=True
    ).get()
    await line_bot_api.set_default_rich_menu_with_http_info(
        rich_menu_id=rich_menu_id,
        async_req=True
    ).get()
