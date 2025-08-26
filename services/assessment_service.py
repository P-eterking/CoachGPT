"""
Assessment service for handling speech evaluation and scoring.
"""
from typing import Optional
from openai import AsyncOpenAI

from utils.models import SpeechAssessment, Question
from interfaces.services import IAssessmentService
from constants import (
    ASSESSMENT_MODEL, ASSESSMENT_MAX_COMPLETION_TOKENS, 
    ASSESSMENT_TEMPERATURE, ASSESSMENT_MIN_SCORE, ASSESSMENT_MAX_SCORE
)


class AssessmentService(IAssessmentService):
    """Service for handling speech assessment operations."""
    
    def __init__(self, openai_client: AsyncOpenAI, system_instruction: str) -> None:
        self.client = openai_client
        self.system_instruction = system_instruction
    
    async def assess_speech(
        self, 
        question: Question, 
        user_answer: str
    ) -> Optional[SpeechAssessment]:
        """
        Assess user's speech response using OpenAI GPT model.
        
        Args:
            question: The question object containing text and assessment criteria
            user_answer: The user's transcribed response
            
        Returns:
            SpeechAssessment object or None if assessment failed
        """
        try:
            content = f"<question>{question.text}</question>"
            
            if question.assessment_standard:
                content += f"<standard>{question.assessment_standard.replace('\n','').strip()}</standard>"
            
            content += f"<userAnswer>{user_answer}</userAnswer>"
            
            if question.max_score:
                content += f"<maxScore>{question.max_score}</maxScore>"
            
            completion = await self.client.beta.chat.completions.parse(
                model=ASSESSMENT_MODEL,
                response_format=SpeechAssessment,
                max_completion_tokens=ASSESSMENT_MAX_COMPLETION_TOKENS,
                temperature=ASSESSMENT_TEMPERATURE,
                messages=[
                    {
                        "role": "system",
                        "content": self.system_instruction,
                    },
                    {
                        "role": "user",
                        "content": content,
                    }
                ]
            )
            
            return completion.choices[0].message.parsed
            
        except Exception as e:
            print(f"Error assessing speech: {e}")
            return None
    
    def validate_assessment(self, assessment: SpeechAssessment) -> bool:
        """
        Validate assessment results.
        
        Args:
            assessment: The assessment to validate
            
        Returns:
            True if assessment is valid, False otherwise
        """
        if not assessment:
            return False
            
        # Check required fields
        if not assessment.transcript or len(assessment.transcript.strip()) < 1:
            return False
            
        # Check score bounds
        if assessment.score < ASSESSMENT_MIN_SCORE or assessment.score > ASSESSMENT_MAX_SCORE:
            return False
            
        return True