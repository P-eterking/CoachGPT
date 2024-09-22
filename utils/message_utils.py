from config import line_bot_api
from linebot.v3.messaging import ReplyMessageRequest, TextMessage, TemplateMessage, CarouselTemplate, CarouselColumn, PostbackAction

async def send_text_message(event, text):
    await line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=text)]
        )
    )

async def send_carousel_message(event):
    msg = TemplateMessage(
        altText='單元導覽',
        template=CarouselTemplate(columns=[
            CarouselColumn(
                thumbnailImageUrl='https://developers.line.biz/assets/images/services/bot-designer-icon.png',
                title='點我',
                text='你好',
                actions=[PostbackAction(label='點我', data='action=buy&itemid=111')],
            ),
        ])
    )
    await line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[msg]
        )
    )