from os import remove
from config import line_bot_api, line_bot_api_blob, client, question_manager, rich_menu_manager
import asyncio
from utils.message_utils import (
    handle_rich_menu, info_hint_message, result_message, send_message, send_text_message,
    question_message, carousel_message, SYSTEM_INSTRUCTION, text_message, progress_message,
)
from utils.models import SpeechAssessment
from utils.file_utils import *
import tempfile
import time

async def handle_text_message(event):
    # 獲取使用者傳來的文字訊息並移除前後空白
    message: str = event.message.text.strip()
    # 獲取使用者 ID
    user_id = event.source.user_id

    # 若訊息以「清除」開頭，取消使用者的 rich menu 綁定 using new framework
    if message.startswith('清除'):
        rich_menu_manager.unlink_rich_menu_from_user(user_id)
        return
    
    await handle_rich_menu(user_id)
    
    # 檢查使用者是否登入，若未登入則結束
    if not await check_user_login(event, message):
        return

    # 根據訊息內容執行不同的口語練習
    if message.startswith('口語練習一'):
        await send_message(event, await carousel_message(user_id, 1))
    elif message.startswith('口語練習二'):
        await send_message(event, await carousel_message(user_id, 2))
    elif message.startswith('口語練習三'):
        await send_message(event, await carousel_message(user_id, 3))
    elif message.startswith('答題狀況') or message.startswith('progress') or message.startswith('Progress'):
        await send_message(event, await progress_message(user_id))
    elif message.startswith('/儲存'):
        await save_user_data()
        await send_text_message(event, "儲存成功！\nSaved!")
    elif message.startswith('解除綁定'):
        delData(user_id)
        await send_text_message(event, "已解除綁定！\nUnlinked!")
    elif message.startswith('/更新題目'):
        question_manager.load_questions()
        await send_text_message(event, "已更新題目！\nQuestions updated!")
    elif message.startswith('/魔法'):
        await send_text_message(event, "你已變成管理員\nMagic!")
        await addAdmin(user_id)
        await save_config()

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
            if not message.isdigit():
                await send_text_message(event, "格式錯誤！\nFormat error!")
                return False
            try:
                option = int(message)
                if option < 1 or option > 4:
                    await send_text_message(event, "輸入格式錯誤！\nFormat error!")
                    return False
            except ValueError:
                await send_text_message(event, "輸入格式錯誤！\nFormat error!")
                return False
            except Exception as e:
                await send_text_message(event, "處理時發生錯誤，請稍後再試。\nAn error occurred during processing, please try again later.")
                print(e)
        # 系級
        elif len(info) == 1:
            pass
        # 學號
        elif len(info) == 2:
            if not message.isdigit():
                await send_text_message(event, "學號格式錯誤！\nFormat error!")
                return False
            elif len(message) > 8:
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
    user_state = get_user_state(user_id)
    # 檢查使用者的狀態資料是否存在
    if not user_state:
        return
    
    try:
        # 取得音訊訊息內容並等待處理完成
        result = await line_bot_api_blob.get_message_content_transcoding_by_message_id(event.message.id)
        text = None
        category = user_state.category
        
        if not category or not question_manager.has_question(category):
            return 
        
        # 獲取使用者的練習單元和題目
        sub = user_state.sub
        question = question_manager.get_question(category, sub)
        
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
            transcript = await client.audio.transcriptions.create(
                model="whisper-1",
                file=(f.name, f.read()),
                language="en",
            )
            # 獲取轉錄的文字
            text = transcript.text.strip()
            
            f.close()
        except Exception as e:
            await send_text_message(event, "文字轉錄發生錯誤，請稍後再試。\nAn error occurred, please try again later.")
            print(e)
            return
    
        if not text or len(text) < 1:
            await send_text_message(event, "無法獲取音訊內容，請稍後再試。\nUnable to get audio content, please try again later.")
            print('No text found in audio')
            return
        
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
                    "content": f"<question>{question.text}</question>" \
                               f"{'<standard>'+question.assessment_standard.replace('\n','').strip()+'</standard>' if question.assessment_standard else ''}" \
                               f"<userAnswer>{text}</userAnswer>" \
                               f"{f'<maxScore>{question.max_score}</maxScore>' if question.max_score else ''}",
                }
            ],
        )
        
        # 將分析結果轉換為 SpeechAssessment 物件並儲存歷史紀錄
        result: SpeechAssessment = SpeechAssessment.model_validate_json(completion.choices[0].message.content)
        result.transcript = text
        result.timestamp = time.time()
        
        updateHistory(user_id, f'{category}-{sub}', result)
        
        # 發送評估結果給使用者
        await send_message(event, await result_message(result, category, sub))
    except Exception as e:
        await send_text_message(event, "發生錯誤，請稍後再試。\nAn error occurred, please try again later.")
        print(e)

async def handle_postback(event):
    # 確認使用者登入狀態
    if not await check_user_login(event):
        return
    user_id = event.source.user_id
    
    await handle_rich_menu(user_id)
    
    user_state = get_user_state(user_id)
    # 解析 postback 資料
    data: str = event.postback.data
    vars = {sep.split('=')[0]: sep.split('=')[1] for sep in data.split('&')}
    action = vars.get('action')
    
    # 處理不同的 postback 動作
    if action == 'record':
        # 設定使用者狀態為當前選擇的單元和題目
        category = user_state.category

        if not isEnabled(category):
            await send_text_message(event, "該單元目前不可用。\nCurrently unavailable.")
            return
        sub = int(vars.get('sub', 0))
        user_state.sub = sub
        await send_message(event, await question_message(category, sub))
    # elif action == 'unit':
    #     # 發送特定單元的 carousel 訊息
    #     unit = int(vars.get('unit', 1))
    #     await send_message(event, await carousel_message(user_id, unit))
    elif action == 'result':
        category = int(vars.get('category', user_state.category))
        sub = int(vars.get('sub', 0))
        result = getHistory(user_id, f'{category}-{sub}')
        if not result:
            await send_text_message(event, f'Q{sub+1} 查無紀錄！\nNo history found in Q{sub+1}!')
            return
        await send_message(event, await result_message(result, category, sub))
    elif action == 'switch':
        alias = vars.get('to')
        if alias in ['admin'] and not isAdmin(user_id):
            await send_text_message(event, '無權限！\nNo permission!')
            return
        if alias in ['pretest', 'posttest', 'sheet1', 'sheet2', 'sheet3'] and not isEnabled(alias):
            await send_text_message(event, "該單元目前不可用。\nCurrently unavailable.")
            return
        user_state.category = alias
        await rich_menu_manager.link_rich_menu_to_user(user_id, get_rich_menu_id(alias))
    elif action == 'progress':
        await send_message(event, await progress_message(user_id))
    elif action == 'enabled':
        alias = vars.get('alias')
        if isEnabled(alias):
            removeEnabled(alias)
        else:
            addEnabled(alias)
        await save_config()
        await send_text_message(event, f'已{"啟用" if isEnabled(alias) else "停用"} {alias}！\n{alias} {"enabled" if isEnabled(alias) else "disabled"}!')
        await question_manager.save_category(alias)
    elif action == 'respond':
        alias = vars.get('alias')
        if isResponse(alias):
            removeResponse(alias)
        else:
            addResponse(alias)
        await save_config()
        await send_text_message(event, f'已{"開啟" if isResponse(alias) else "關閉"} {alias} 回饋！\n{alias} feedback {"enabled" if isResponse(alias) else "disabled"}!')
        await question_manager.save_category(alias)
    elif action == 'reload':
        question_manager.load_questions()
        await send_text_message(event, '已重新載入問題！\nQuestions reloaded!')
    elif action == 'save':
        await save_all()
        await send_text_message(event, '儲存成功！\nSave successful!')