# manager/game_manager.py
import json
import os
from utils.models import User
from utils.file_utils import updateHistory, get_rag_context_v2, config
from linebot.v3.messaging import FlexMessage, FlexBubble, FlexBox, FlexText, FlexButton, FlexImage, FlexVideo, VideoMessage, PostbackAction

class GameManager:
    def __init__(self, script_path='./category/game_script.json'):
        self.script_path = script_path
        self.scripts = {}
        self.load_scripts()

    def load_scripts(self):
        if os.path.exists(self.script_path):
            with open(self.script_path, 'r', encoding='utf-8') as f:
                self.scripts = json.load(f)
        else:
            print("Game script not found!")

    def get_user_level(self, user: User, theme_id: str) -> int:
        return user.game_progress.themes.get(theme_id, 0)

    def get_level_data(self, theme_id: str, level_index: int):
        theme = self.scripts.get(theme_id)
        if not theme or level_index >= len(theme['levels']):
            return None
        return theme['levels'][level_index]

    # 生成關卡介面 (影片 + 題目 + NPC選單)
    def generate_level_message(self, theme_id, level_index):
        level_data = self.get_level_data(theme_id, level_index)
        if not level_data:
            return TextMessage(text="恭喜！你已完成此主題的所有關卡！")

        # 1. 影片訊息 (若 Line 支援，或用連結)
        # 這裡示範用 Flex Message 組合
        bubbles = []
        
        # 關卡標題與影片卡片
        bubbles.append(FlexBubble(
            size='mega',
            hero=FlexImage(
                url=level_data['preview_image'],
                size='full',
                aspect_ratio='16:9',
                aspect_mode='cover',
                action=URIAction(label="Watch Video", uri=level_data['video_url']) # 點擊看影片
            ),
            body=FlexBox(
                layout='vertical',
                contents=[
                    FlexText(text=level_data['title'], weight='bold', size='xl'),
                    FlexText(text="請觀看影片後，與下方 NPC 對話並回答問題。", wrap=True, size='sm', color='#666666')
                ]
            )
        ))

        # NPC 選擇卡片
        npc_buttons = []
        for npc_id, npc_info in level_data['npcs'].items():
            npc_buttons.append(FlexButton(
                style='secondary',
                action=PostbackAction(
                    label=f"與 {npc_info['name']} 對話",
                    data=f"action=game_chat&theme={theme_id}&npc={npc_id}"
                )
            ))
        
        bubbles.append(FlexBubble(
            size='mega',
            header=FlexBox(layout='vertical', contents=[FlexText(text="選擇調查對象", weight='bold')]),
            body=FlexBox(layout='vertical', spacing='sm', contents=npc_buttons)
        ))

        # 題目卡片
        for q in level_data['questions']:
            bubbles.append(FlexBubble(
                size='mega',
                body=FlexBox(
                    layout='vertical',
                    contents=[
                        FlexText(text=f"任務 {q['id']+1}", weight='bold', color='#1DB446'),
                        FlexText(text=q['text'], wrap=True, size='md', margin='md'),
                        FlexButton(
                            style='primary',
                            margin='md',
                            action=PostbackAction(
                                label="我要回答此題",
                                data=f"action=game_answer&theme={theme_id}&qid={q['id']}"
                            )
                        )
                    ]
                )
            ))

        return FlexMessage(altText=f"關卡：{level_data['title']}", contents=FlexCarousel(contents=bubbles))

    # 驗證答案邏輯
    def validate_answer(self, theme_id, level_index, q_id, user_text):
        level_data = self.get_level_data(theme_id, level_index)
        question = next((q for q in level_data['questions'] if q['id'] == q_id), None)
        
        if not question:
            return False
        
        # 簡單關鍵字比對 (或是這一步可以 call LLM 判斷語意)
        for keyword in question['keywords']:
            if keyword.lower() in user_text.lower():
                return True
        return False

# 初始化實例
game_manager = GameManager()