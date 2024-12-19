import json
from pathlib import Path
from manager.question_manager import QuestionManager
from utils.models import User, SpeechAssessment, Question
from datetime import datetime
from zoneinfo import ZoneInfo  # Import ZoneInfo for timezone handling

def load_user_data(file_path: str) -> list[User]:
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return [User(**value) for key, value in data.items()]

def analyze_by_question(users: list[User], question_manager: QuestionManager):
    category_unit_scores = {}
    user_count = len(users)
    users_completed_units = {}
    
    # Initialize data structures for all categories and units
    for category_idx, category in enumerate(question_manager.questions):
        category_str = str(category_idx)
        category_unit_scores[category_str] = {}
        users_completed_units[category_str] = {}
        for unit_idx, unit in enumerate(category):
            unit_str = str(unit_idx)
            category_unit_scores[category_str][unit_str] = {
                'total_score': 0,
                'count': 0,
                'max_score': float('-inf')  # Initialize max_score
            }
            users_completed_units[category_str][unit_str] = 0

    # Collect all assessment histories
    all_histories = []
    for user in users:
        for question_number, assessment in user.history.items():
            category, unit, question = question_number.split('-')  # Split into separate fields
            
            # Convert timestamp to GMT+8
            if isinstance(assessment.timestamp, (int, float)):
                # If timestamp is a float or int, assume it's a Unix timestamp
                dt = datetime.fromtimestamp(assessment.timestamp, tz=ZoneInfo('UTC'))
            else:
                dt = assessment.timestamp  # Assume it's already a datetime object
            
            dt_gmt8 = dt.astimezone(ZoneInfo('Asia/Taipei'))  # Convert to GMT+8
            formatted_timestamp = dt_gmt8.strftime("%Y-%m-%d %H:%M:%S")  # Format datetime
            
            all_histories.append({
                "category": category,          # Updated field
                "unit": unit,                  # Updated field
                "question": question,          # Updated field
                "score": assessment.score,
                "user_id": user.id,
                "name": user.name,
                "class_time": user.class_time,
                "timestamp": formatted_timestamp  # Formatted timestamp
            })

    # Sort histories by timestamp descending and select top 10
    latest_histories = sorted(all_histories, key=lambda x: x['timestamp'], reverse=True)[:10]

    # Analyze user data
    for user in users:

        # Track completed units
        for category_idx, category in enumerate(question_manager.questions):
            category_str = str(category_idx)
            for unit_idx, unit in enumerate(category):
                unit_str = str(unit_idx)
                unit_questions = sum(1 for q in user.history.keys() 
                                     if q.startswith(f'{category_idx}-{unit_idx}-'))
                if unit_questions == len(unit):
                    users_completed_units[category_str][unit_str] += 1

        # Process assessment data
        for question_number, assessment in user.history.items():
            category, unit, _ = question_number.split('-')
            category_unit_scores[category][unit]['total_score'] += assessment.score
            category_unit_scores[category][unit]['count'] += 1
            if assessment.score > category_unit_scores[category][unit]['max_score']:
                category_unit_scores[category][unit]['max_score'] = assessment.score  # Update max_score

    # Prepare category-wise analysis data
    category_analysis = []
    for category, units_data in category_unit_scores.items():
        category_data = {
            "category": category,
            "units": []
        }
        for unit, data in units_data.items():
            if data['count'] > 0:
                average_unit_score = data['total_score'] / data['count']
                category_data["units"].append({
                    "unit": unit,
                    "average_score": average_unit_score,
                    "max_score": data['max_score'],  # Include max_score
                    "total_samples": data['count'],
                    "users_completed": users_completed_units[category][unit]
                })
        category_analysis.append(category_data)

    return {
        "category_analysis": category_analysis,
        "user_count": user_count,  # Already existing
        "latest_histories": latest_histories  # Added latest_histories
    }

if __name__ == "__main__":
    user_data_path = Path("user_data2.json")
    users = load_user_data(user_data_path)
    question_manager = QuestionManager('./category')
    
    analysis_result = analyze_by_question(users, question_manager)
    print(json.dumps(analysis_result, indent=2))
