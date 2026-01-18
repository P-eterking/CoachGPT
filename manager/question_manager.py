from utils.models import Question, QuestionCategory
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
        self.questions: dict[str, QuestionCategory]
        self.load_questions()

    def load_questions(self) -> dict[str, QuestionCategory]:
        # 載入問題
        questions = {}
        for root, _, files in os.walk(self.data_source):
            for file in files:
                if not file.endswith('.json') or file.startswith('-'):
                    continue
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'content' not in data:
                        continue
                    category_questions = QuestionCategory(**data)
                    questions[file.split('.')[0]] = category_questions
        self.questions = questions
    
    def get_question(self, category: str, sub: str) -> Question:
        # 返回指定的問題
        return self.questions[category].content[sub]
    
    def has_question(self, category: str) -> bool:
        # 是否有問題
        return category in self.questions
    
    def get_all_questions(self, category: str) -> List[Question]:
        # 返回所有問題
        return self.questions[category].content
    
    def get_category(self, category) -> QuestionCategory | None:
        # 返回指定的類別
        return self.questions.get(category)
    
    def get_unit(self, category: str, unit: int = 0) -> List[Question]:
        """
        獲取指定類別和單元（分頁）的問題列表。
        假設每個單元顯示 10 個問題。
        """
        if category not in self.questions:
            return []
        
        all_questions = self.questions[category].content
        start_index = unit * 10
        end_index = start_index + 10
        
        # 如果超出範圍，返回空列表或剩餘問題
        if start_index >= len(all_questions):
            return []
            
        return all_questions[start_index:end_index]

    async def _save_category(self, category: str, value: QuestionCategory) -> None:
        file_path = os.path.join(self.data_source, f'{category}.json')
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as file:
            # Convert value to dict for JSON serialization
            await file.write(json.dumps(value.to_dict(), indent=4, ensure_ascii=False))
        print(f"Category {category} saved successfully.")

    async def save_category(self, category: str) -> None:
        # 儲存類別（僅對已載入的題目類別進行儲存）
        value = self.questions.get(category)
        if value is None:
            # 若該類別不存在於題庫（例如 chat 等純功能性類別），則不進行儲存
            print(f"Category {category} not found in questions, skip saving.")
            return
        await self._save_category(category, value)

    async def save_questions(self) -> None:
        # 儲存問題
        tasks = [self._save_category(cate, value) for cate, value in self.questions.items()]
        await asyncio.gather(*tasks)