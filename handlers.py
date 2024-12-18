from calendar import c
from config import line_bot_api, line_bot_api_blob, client, question_manager
import asyncio
from utils.message_utils import (
    create_rich_menu, data_message, info_hint_message, result_message, send_message, send_text_message,
    question_message, carousel_message, handle_rich_menu, SYSTEM_INSTRUCTION, text_message
)
from utils.models import SpeechAssessment
from utils.file_utils import (
    get_answerable, get_test_mode, save_config, switch_answerable, user_state, save_user_data, hasData,
    updateHistory, getHistory, initData, delData, switch_test_mode, get_category, set_category
)
import tempfile
import time

async def handle_text_message(event):
    # 獲取使用者傳來的文字訊息並移除前後空白
    message: str = event.message.text.strip()
    # 獲取使用者 ID
    user_id = event.source.user_id

    # 若訊息以「清除」開頭，取消使用者的 rich menu 綁定
    if message.startswith('清除'):
        await line_bot_api.unlink_rich_menu_id_from_user(user_id)
        return
    
    # 處理使用者的 rich menu
    await handle_rich_menu(user_id)
    
    # 檢查使用者是否登入，若未登入則結束
    if not await check_user_login(event, message):
        return

    # 根據訊息內容執行不同的口語練習
    if message.startswith('口語練習一'):
        await send_message(event, await carousel_message(user_id,1))
    elif message.startswith('口語練習二'):
        await send_message(event, await carousel_message(user_id,2))
    elif message.startswith('口語練習三'):
        await send_message(event, await carousel_message(user_id,3))
    elif message.startswith('/儲存'):
        await save_user_data()
        await send_text_message(event, "儲存成功！\nSaved!")
    elif message.startswith('解除綁定'):
        delData(user_id)
        await send_text_message(event, "已解除綁定！\nUnlinked!")
    elif message.startswith('/測驗模式'):
        if switch_test_mode():
            await send_text_message(event, "已進入測驗模式！\nTest mode activated!")
        else:
            await send_text_message(event, "已退出測驗模式！\nTest mode deactivated!")
        await save_config()
    elif message.startswith('/切換'):
        if not switch_answerable():
            await send_text_message(event, "已切換為不可回答模式！\nAnswerable mode deactivated!")
        else:
            await send_text_message(event, "已切換為可回答模式！\nAnswerable mode activated!")
        await save_config()
    elif message.startswith('/數據'):
        await send_message(event, await data_message())
    elif message.startswith('/測驗類別'):
        if ' ' not in message:
            await send_text_message(event, "輸入格式錯誤！記得要加空格！\nFormat error! Don't forget the space!")
            return
        category = int(message.split(' ')[1])
        set_category(category)
        await create_rich_menu()
        await save_config()
        await send_text_message(event, f"已設定測驗類別為{category}！\nCategory set to {category}!")
    elif message.startswith('/更新題目'):
        question_manager.load_questions()
        await send_text_message(event, "已更新題目！\nQuestions updated!")

user_data_enter = {}

async def check_user_login(event, message: str = None) -> bool:
    # 檢查使用者是否已登入或已存有資料
    user_id = event.source.user_id
    
    if not hasData(user_id):
        # 若無使用者資料，開始進行資料綁定流程
        info = user_data_enter.get(user_id, [])
        if message is None:
            # 若沒有訊息，提示使用者提供所需資料
            await send_message(event, await info_hint_message(len(info)))
            return False
        
        # 以下依序確認使用者輸入格式
        # 上課時段
        if len(info) == 0:
            if '-' not in message:
                await send_text_message(event, "輸入格式錯誤！\nFormat error!")
                return False
        # 系級
        elif len(info) == 1:
            pass
        # 學號
        elif len(info) == 2:
            if not message.isdigit():
                await send_text_message(event, "學號格式錯誤！\nFormat error!")
                return False
        # 姓名
        else:
            # 綁定完成後儲存資料並提示使用者綁定成功
            info.append(message)
            initData(user_id, info[0], info[1], info[2], info[3])
            del user_data_enter[user_id]
            await send_message(event, [
                await text_message(f"綁定完成 你好! {message}\nSuccess! Hello, {message} !"), 
                await carousel_message(user_id,1)
            ])
            return True

        # 保存目前階段的資料以繼續下一步
        info.append(message)
        user_data_enter[user_id] = info
        await send_message(event, await info_hint_message(len(info)))
    
    return True

async def handle_audio_message(event):
    # 確認使用者登入狀態，若未登入則結束
    if not await check_user_login(event):
        return
    
    user_id = event.source.user_id
    
    # 檢查使用者的狀態資料是否存在
    if user_state.get(user_id) is None:
        return
    
    try:
        # 取得音訊訊息內容並等待處理完成
        result = await line_bot_api_blob.get_message_content_transcoding_by_message_id(event.message.id)
        text = None
        
        # 獲取使用者的練習單元和題目
        unit = user_state[user_id]['unit']
        sub = user_state[user_id]['sub']
        question = question_manager.get_question(get_category(), unit, sub)
        
        try:
            while result.status == 'processing':
                result = await line_bot_api_blob.get_message_content_transcoding_by_message_id(event.message.id)
                await asyncio.sleep(1)

            # 取得音訊檔案內容
            message_content = await line_bot_api_blob.get_message_content(event.message.id)
            
            # 檢查音訊內容是否成功獲取
            if not message_content:
                await send_text_message(event, "無法獲取音訊內容，請稍後再試。\nUnable to get audio content, please try again later.")
                return
            
            # 使用暫存檔儲存音訊內容
            f = tempfile.NamedTemporaryFile(suffix=".m4a", delete=True)
            f.write(message_content)
            f.seek(0)
            f.flush()
                
            # 使用 Whisper 進行音訊轉錄
            # transcript = await groq.audio.transcriptions.create(
            #     model="whisper-large-v3",
            #     file=(f.name,f.read()),
            #     language="en",
            # )
            transcript = await client.audio.transcriptions.create(
                model="whisper-1",
                file=(f.name, f.read()),
                language="en",
            )
            # 獲取轉錄的文字
            text = transcript.text.strip()
            
            f.close()
            # text = base64.b64encode(message_content).decode('utf-8')
        except Exception as e:
            await send_text_message(event, "文字轉錄發生錯誤，請稍後再試。\nAn error occurred, please try again later.")
            print(e)
            return
    
        if not text or len(text) < 1:
            await send_text_message(event, "無法獲取音訊內容，請稍後再試。\nUnable to get audio content, please try again later.")
            print('No text found in audio')
            return
         
        # 使用 GPT 模型進行回應分析與評估
        completion = await client.beta.chat.completions.parse(
            model="gpt-4o",
            response_format=SpeechAssessment,
            max_completion_tokens=2048,
            temperature=1,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_INSTRUCTION,
                },
                {
                    "role": "user",
                    "content": f"<question>{question.text}</question>{"<standard>"+question.assessment_standard.replace('\n','').strip()+"</standard>" if question.assessment_standard else ""}<userAnswer>{text}</userAnswer>",
                }
            ],
        )
        # completion = await client.beta.chat.completions.parse(
        #     model="gpt-4o-audio-preview",
        #     # response_format={ "type": "json_object" },
        #     # response_format=SpeechAssessment,
        #     modalities=["text"],
        #     max_completion_tokens=2048,
        #     temperature=1.1,
        #     messages=[
        #         {
        #             "role": "system",
        #             "content": SYSTEM_INSTRUCTION,
        #         },
        #         {
        #             'role': 'user',
        #             'content': [
        #                 { 'type': "text", 'text': f"<question>{question['text']}</question>{"<standard>"+question['assessment_standard'].replace('\n','').strip()+"</standard>" if question.get('assessment_standard') else ""}"},
        #                 { 'type': "input_audio", 'input_audio': { 'data': text, 'format': "mp3" }}      
        #             ],
        #         },
        #     ],
        # )
        
        # 將分析結果轉換為 SpeechAssessment 物件並儲存歷史紀錄
        result: SpeechAssessment = SpeechAssessment.model_validate_json(completion.choices[0].message.content)
        result.transcript = text
        result.timestamp = time.time()
        
        updateHistory(user_id, f'{get_category()}-{unit}-{sub}', result)
        
        # 發送評估結果給使用者
        await send_message(event, await result_message(result, unit, sub))
    except Exception as e:
        await send_text_message(event, "發生錯誤，請稍後再試。\nAn error occurred, please try again later.")
        print(e)

async def handle_postback(event):
    # 確認使用者登入狀態
    if not await check_user_login(event):
        return
    user_id = event.source.user_id
    
    await handle_rich_menu(user_id)
    
    # 解析 postback 資料
    data: str = event.postback.data
    vars = {sep.split('=')[0]: sep.split('=')[1] for sep in data.split('&')}
    action = vars.get('action')
    
    # 處理不同的 postback 動作
    if action == 'record':
        if not get_answerable():
            await send_text_message(event, '目前不接受測驗！\nCurrently not available!')
            return
        # 設定使用者狀態為當前選擇的單元和題目
        unit = int(vars.get('unit', 0))
        sub = int(vars.get('sub', 0))
        user_state[user_id] = {'unit': unit, 'sub': sub}
        await send_message(event, await question_message(unit, sub))
    elif action == 'unit':
        # 發送特定單元的 carousel 訊息
        unit = int(vars.get('unit', 1))
        await send_message(event, await carousel_message(user_id, unit))
    elif action == 'result':
        if get_test_mode():
            return
        unit = int(vars.get('unit', 0))
        sub = int(vars.get('sub', 0))
        result = getHistory(user_id, f'{get_category()}-{unit}-{sub}')
        if not result:
            await send_text_message(event, '查無紀錄！\nNo history found!')
        await send_message(event, await result_message(result, unit, sub))