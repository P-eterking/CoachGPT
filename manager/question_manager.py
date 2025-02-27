from utils.models import Question
from typing import List
import aiofiles
import asyncio
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
                    if 'content' not in data:
                        continue
                    category_questions = [([Question(**q) for q in unit] if isinstance(unit, list) else Question(**unit)) for unit in data['content']]
                    questions.append(category_questions)
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
    
    async def _save_category(self, index: int, category) -> None:
        file_path = os.path.join(self.data_source, f'{index}.json')
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as file:
            await file.write(json.dumps(category, indent=4))
        print(f"Category {index} saved successfully.")
    
    async def save_questions(self):
        # 儲存問題
        tasks = [self._save_category(i, cate) for i, cate in enumerate(self.questions)]
        await asyncio.gather(*tasks)

