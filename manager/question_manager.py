from utils.models import Question
from typing import List
import aiofiles
import json
import os

class QuestionManager(object):
    """問題管理器
    """
    
    def __init__(self, data_source):
        # 初始化
        self.data_source = data_source
        self.questions = self.load_questions()

    def load_questions(self) -> List[List[List[Question]]]:
        # 載入問題
        questions = []
        for root, dirs, files in os.walk(self.data_source):
            for file in files:
                if not file.endswith('.json'):
                    continue
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    questions.append([[Question(**q) for q in unit] for unit in data['content']])
        self.questions = questions
        return questions
    
    def get_question(self, category, unit, sub) -> Question:
        # 返回指定的問題
        return self.questions[category][unit][sub]
    
    def get_unit(self, category, unit) -> List[Question]:
        # 返回指定的單元
        return self.questions[category][unit]
        
    def get_category(self, category) -> List[List[Question]]:
        # 返回指定的類別
        return self.questions[category]
    
    async def save_questions(self):
        # 儲存問題
        for i, cate in enumerate(self.questions):
            async with aiofiles.open(f'{self.data_source}/{i}.json', 'w', encoding='utf-8') as file:
                await file.write(json.dumps(cate, indent=4))
                print(f"Category {i} saved successfully.")

