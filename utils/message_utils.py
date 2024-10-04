from config import line_bot_api, line_bot_api_blob, DOMAIN
from linebot.v3.messaging import ReplyMessageRequest, TextMessage, PostbackAction, RichMenuRequest, RichMenuSize, RichMenuArea, RichMenuBounds, FlexMessage, FlexCarousel, FlexBubble, FlexImage, FlexText, FlexBox, FlexButton

url  = f'https://{DOMAIN}'
qs = [
        [
            "**What does 'inexpensive' mean, and can you name something that is inexpensive?**\n - 什麼是「便宜」的意思？你能舉出一個「便宜」的例子嗎？",
            "**How would you describe 'portable'? Mention a portable item you use.**\n - 「便攜的」應該怎麼解釋？提到一個你使用「便攜的」物品。",
            "**What is the role of 'management' in a company?**\n - 在公司中，「管理」有什麼作用？",
            "**Define 'manual' and give an example of a manual task.**\n - 定義「手動」並給出一個關於「手動」任務的例子。",
            "**Can you make a sentence using 'export' and 'recently'?**\n - 你能使用「出口」和「最近」造一個句子嗎？",
            "**Describe a situation where you might need to 'replace' something because it is 'inexpensive'.**\n - 描述一個你可能需要因為物品是「便宜」而「取代」它的情境。",
            "**How would you tell someone to 'decrease' the volume using polite language?**\n - 你會如何用禮貌的語言告訴某人「減少」音量？",
            "**Write a sentence where you explain to a friend why something is 'comfortable'.**\n - 寫一個句子解釋給朋友聽為什麼某物是「舒服的」。"
        ],
        [
            "**Meet the Deadline:**\n- Can you describe a time when you had to meet a tight deadline?\n- 你能描述一次你必須在截止日期前完成任務的情況嗎？",
            "**Apply for the Job:**\n- What kind of job do you want to apply for?\n- 你想申請什麼樣的工作？",
            "**Keep in Touch with Someone:**\n- Talk about a friend or family member you try to keep in touch with regularly.\n- 談談你努力與朋友或家人保持聯繫的情況。",
            "**Offer a Discount:**\n- Please create a situation where you purchased an item because it was discounted.\n- 請創造一個你因為商品打折而購買的情況。",
            "**Register In:**\n- Pretend you are a student, use 'register in' to make a sentence.\n- 假設你是一名學生，用“註冊”一詞造一個句子。",
            "**Make an Appointment:**\n- Can you recall a time when you had to make an appointment for an important meeting or event?\n- 你能回憶起你曾經為一次重要的會議或活動預約的時候嗎？",
            "**Remain a Concern:**\n- What things make you remain a concern?\n- 有什麼事情讓你一直擔心嗎？",
            "**Book a Ticket:**\n- Describe a situation in which you would need to book a ticket by yourself.\n- 描述您需要自己訂票的情況",
        ],
        [
            "**Beginning**: Introduce the main character and setting.\nA hare was making fun of a tortoise for moving so slowly. The tortoise got tired of the hare making fun of how slow he was. So, he asked the hare to have a race.\n**開始**：介紹主要角色和場景。\n一隻野兔正在嘲笑一隻行動緩慢的烏龜。烏龜厭倦了野兔嘲笑牠動作慢的樣子。於是牠要求野兔和他進行一場比賽。",
            "**Then**: Introduce obstacles and challenges main character encounters.\nWhen the race started, the hare bounded off in front, making good progress. He was so far ahead of the tortoise that he decided he could afford to stop and have a rest.\n**然後**：介紹主要角色遇到的障礙和挑戰。\n比賽一開始，野兔就飛奔而出，並且進展迅速。遠遠地把烏龜甩在後面，牠覺得自己可以停下來休息一下。",
            "**After**: Reach the climax or turning point of the story, where the main character confronts the central conflict head-on.\nHowever, the hare fell fast asleep, and as he lay sleeping, the tortoise continued to plod along at his slow pace. In time, he reached the finish-line and won the race.\n**之後**：到達故事的高潮或轉折點，主角正面對抗主要衝突。\n然而，野兔很快就睡著了，當牠在睡覺時，烏龜以緩慢的步伐繼續向前爬行。最終，烏龜到達了終點線，贏得了比賽。",
            "**Ending**: Resolve the conflict and provide closure for the story. Show how the main character has changed. \nWhen the hare woke up, he was annoyed at himself for falling asleep. So he ran off towards the finish-line as fast as his legs would carry him, but it was too late, as the tortoise had already won.\n**結尾**：解決衝突並為故事提供結局。展示主角的變化。\n當野兔醒來時，他對自己睡著了感到懊惱。於是牠全力奔向終點線，但為時已晚，烏龜已經贏得了比賽。"
        ]]

richMenuId : str = None

async def send_message(event, msg):
    await line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=msg
        )
    )

async def send_text_message(event, text):
    await line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=text)]
        )
    )

async def question_message(unit, sub):
    return FlexMessage(
            altText='口語練習',
            contents=FlexBubble(   
                size='giga', 
                body=FlexBox(
                    layout='vertical',
                    contents=[
                        FlexText(
                            text=f'題目 {unit+1}-{sub+1}',
                            wrap=True,
                            weight='bold',
                            size='xl',
                        ),
                        FlexBox(
                            layout='baseline',
                            margin='md',
                            contents=[
                                FlexText(
                                    text=qs[unit][sub],
                                    color='#5b5b5b',
                                    size='sm',
                                    margin='md',
                                    wrap=True,
                                    flex=1,
                                ),
                            ]
                        ),
                    ],
                ),
                footer=FlexBox(
                    layout='vertical',
                    spacing='sm',
                    alignItems='center',
                    justifyContent='center',
                    contents=[
                        FlexText(
                            style='italic',
                            size='xs',
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

async def create_rich_menu():
    richMenu = await line_bot_api.create_rich_menu(
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
    
    richMenuId = richMenu.to_dict()['richMenuId']

    await line_bot_api_blob.set_rich_menu_image_with_http_info(rich_menu_id=richMenuId, body='templates/richmenu.png',_headers={"Content-Type": "image/png"},async_req=True).get()
    # await line_bot_api.link_rich_menu_id_to_user(user_id=user_id, rich_menu_id=richMenuId,async_req=True).get()
    await line_bot_api.set_default_rich_menu(richMenuId,async_req=True).get()