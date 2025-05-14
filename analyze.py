import json
from pathlib import Path
from manager.question_manager import QuestionManager
from utils.models import User, SpeechAssessment, Question
from datetime import datetime
from zoneinfo import ZoneInfo  # Import ZoneInfo for timezone handling
import os

# Helper function to parse different history key formats
def parse_history_key(key: str) -> tuple[str, str] | None:
    """Parses keys like 'ex1-0', 'pretest-3' into (category_name, question_idx)."""
    parts = key.split('-')
    if len(parts) == 2:
        category_name, q_idx_str = parts
        # Check if the first part is a known category prefix and the second is a digit
        if category_name in ['ex1', 'ex2', 'ex3', 'pretest', 'posttest'] and q_idx_str.isdigit():
            return (category_name, q_idx_str)
            
    # Handle potential old numeric keys 'c-u-q' by mapping them back to names
    # This adds robustness but might need adjustment based on actual data mix
    elif len(parts) == 3 and all(p.isdigit() for p in parts):
         cat_idx, unit_idx, q_idx = parts
         if cat_idx == '0':
             if unit_idx == '0': return ('ex1', q_idx)
             elif unit_idx == '1': return ('ex2', q_idx)
             elif unit_idx == '2': return ('ex3', q_idx)
         elif cat_idx == '1' and unit_idx == '0': return ('pretest', q_idx)
         elif cat_idx == '2' and unit_idx == '0': return ('posttest', q_idx)
            
    # If none of the above formats match
    return None

def load_user_data(file_path: str) -> list[User]:
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return [User(**value) for key, value in data.items()]

def analyze_by_question(users: list[User], question_manager: QuestionManager):
    category_scores = {} # Renamed, keyed by category_name
    user_count = len(users)
    users_completed_category = {} # Renamed, keyed by category_name
    
    # Define the mapping from category name to QM indices and the category names list
    category_name_map = {
        'ex1': (0, 0),
        'ex2': (0, 1),
        'ex3': (0, 2),
        'pretest': (1, 0),
        'posttest': (2, 0)
    }
    category_names = list(category_name_map.keys())
    
    # --- Initialize data structures using category names --- 
    for name in category_names:
        category_scores[name] = {
            'total_score': 0,
            'count': 0,
            'max_score': float('-inf')
        }
        users_completed_category[name] = 0
    # --- End Initialization ---
    
    # --- Store expected lengths --- 
    expected_lengths = {}
    for name in category_names:
        try:
            category = question_manager.get_category(name)
            if category is not None:
                expected_lengths[name] = len(category.content)
            else:
                expected_lengths[name] = 0
                print(f"Warning: Category '{name}' not found in QuestionManager.")
        except Exception as e:
            print(f"Error getting length for category '{name}': {str(e)}")
            expected_lengths[name] = 0
    # ----------------------------

    # Collect all assessment histories (using new parser)
    all_histories = []
    for user in users:
        for question_number, assessment_list in user.history.items():
            if not assessment_list:
                continue
            
            parsed_key = parse_history_key(question_number)
            if parsed_key is None:
                # print(f"Warning: Skipping unparseable history key '{question_number}' for user {user.id}")
                continue 
                
            category_name, question_idx = parsed_key
            
            # Add to history list (no unit concept needed here)
            for assessment in assessment_list:
                if isinstance(assessment.timestamp, (int, float)):
                    dt = datetime.fromtimestamp(assessment.timestamp, tz=ZoneInfo('Asia/Taipei'))
                else:
                    dt = assessment.timestamp # Assuming already datetime object (handle potential errors?)
                
                dt_gmt8 = dt.astimezone(ZoneInfo('Asia/Taipei'))
                formatted_timestamp = dt_gmt8.strftime("%Y-%m-%d %H:%M:%S")
                
                all_histories.append({
                    "category": category_name, # Use the name
                    "question": question_idx,
                    "score": assessment.score,
                    "user_id": user.id,
                    "name": user.name,
                    "class_time": user.class_time,
                    "timestamp": formatted_timestamp
                })

    # Sort histories by timestamp descending and select top 10
    latest_histories = sorted(all_histories, key=lambda x: x['timestamp'], reverse=True)[:10]

    # Analyze user data
    for user in users:
        # Track completed categories (using parsed keys and expected lengths)
        user_category_completion = {} # Tracks attempted q_indices per category_name for this user
        user_samples = {} # Track number of attempts per category for this user

        for q_key in user.history.keys():
            parsed = parse_history_key(q_key)
            if parsed:
                cat_name_parsed, q_idx_parsed = parsed
                if cat_name_parsed not in user_category_completion:
                    user_category_completion[cat_name_parsed] = set()
                    user_samples[cat_name_parsed] = 0
                user_category_completion[cat_name_parsed].add(q_idx_parsed)
                # Count total attempts for this question
                user_samples[cat_name_parsed] += len(user.history[q_key])

        # Check completion against expected lengths
        for name in category_names:
            num_expected = expected_lengths.get(name, 0)
            if num_expected > 0:
                attempted_set = user_category_completion.get(name, set())
                if len(attempted_set) >= num_expected:
                    if name in users_completed_category:
                         users_completed_category[name] += 1

        # Process assessment data (aggregation by category_name)
        for question_number, assessment_list in user.history.items():
            if not assessment_list:
                continue
            
            parsed_key = parse_history_key(question_number)
            if parsed_key is None:
                 continue 
                 
            category_name, _ = parsed_key 
            
            # Aggregate scores into the correct category_name bucket
            if category_name in category_scores:
                for assessment in assessment_list:
                    category_scores[category_name]['total_score'] += assessment.score
                    category_scores[category_name]['count'] += 1
                    if assessment.score > category_scores[category_name]['max_score']:
                        category_scores[category_name]['max_score'] = assessment.score
            # else: # Should not happen if initialization covers all parseable names
                 # print(f"Warning: Category '{category_name}' from history key {question_number} not found in initialized scores. User: {user.id}")

    # Compute samples per user statistics
    samples_per_user = {}
    for name in category_names:
        samples_per_user[name] = {
            'min_samples': float('inf'),
            'max_samples': 0,
            'avg_samples': 0,
            'total_samples': 0,
            'users_with_attempts': 0
        }

    for user in users:
        user_samples = {}
        for q_key, assessment_list in user.history.items():
            parsed = parse_history_key(q_key)
            if parsed:
                cat_name, _ = parsed
                if cat_name not in user_samples:
                    user_samples[cat_name] = 0
                user_samples[cat_name] += len(assessment_list)

        for name in category_names:
            samples = user_samples.get(name, 0)
            if samples > 0:
                samples_per_user[name]['users_with_attempts'] += 1
                samples_per_user[name]['total_samples'] += samples
                samples_per_user[name]['min_samples'] = min(samples_per_user[name]['min_samples'], samples)
                samples_per_user[name]['max_samples'] = max(samples_per_user[name]['max_samples'], samples)

    # Calculate averages
    for name in category_names:
        if samples_per_user[name]['users_with_attempts'] > 0:
            samples_per_user[name]['avg_samples'] = samples_per_user[name]['total_samples'] / samples_per_user[name]['users_with_attempts']
        if samples_per_user[name]['min_samples'] == float('inf'):
            samples_per_user[name]['min_samples'] = 0

    # Prepare category-wise analysis data (keyed by category_name)
    category_analysis = []
    for name, data in category_scores.items():
        if data['count'] > 0:
            average_score = data['total_score'] / data['count']
            completed_count = users_completed_category.get(name, 0)
            
            completion_rate_percent = 0
            if user_count > 0:
                completion_rate_percent = (completed_count / user_count) * 100
            
            category_analysis.append({
                "category_name": name,
                "average_score": average_score,
                "max_score": data['max_score'],
                "total_samples": data['count'],
                "users_completed": completed_count,
                "completion_rate_percent": completion_rate_percent,
                "samples_per_user": {
                    "min": samples_per_user[name]['min_samples'],
                    "max": samples_per_user[name]['max_samples'],
                    "avg": round(samples_per_user[name]['avg_samples'], 2),
                    "users_with_attempts": samples_per_user[name]['users_with_attempts']
                }
            })
        # else: Handle categories with no attempts if needed
            # category_analysis.append({
            #     "category_name": name,
            #     "average_score": 0,
            #     "max_score": float('-inf'),
            #     "total_samples": 0,
            #     "users_completed": 0,
            #     "completion_rate_percent": 0.0
            # })
            
    # Sort analysis results alphabetically by category name for consistent output
    category_analysis.sort(key=lambda x: x['category_name'])

    return {
        "category_analysis": category_analysis,
        "user_count": user_count,
        "latest_histories": latest_histories 
    }

def bonus(users: list[User], question_manager: QuestionManager):
    print("Warning: The 'bonus' function needs refactoring to align with the new category name structure.")
    # ... (existing complex logic needs update based on names like 'ex1', 'pretest') ...
    # Example of fetching expected length for 'ex1':
    # ex1_len = 0
    # try:
    #     ex1_len = len(question_manager.get_unit(0, 0)) # Assuming ex1 maps to (0,0)
    # except IndexError: pass
    # ... (rest of logic needs updating)
    pass # Prevent execution for now

def score_print(users, question_manager: QuestionManager):
    print("Warning: The 'score_print' function might need header adjustments for category names.")
    import csv
    classes : dict[str, list[User]]= {}
    for user in users:
        classes.setdefault(user.class_time, []).append(user)
        
    for class_time, subs in classes.items():
        if not os.path.exists(class_time):
            os.mkdir(class_time)
        with open(f'{class_time}/score.csv', 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            header = ['學號', '姓名', '系所']
            for category in range(3):
                for unit in range(len(question_manager.get_category(category))):
                    for question in range(len(question_manager.get_unit(category, unit))):
                        header.append(f'{category}-{unit}-{question}')
            writer.writerow(header)
            for user in subs:
                row = [user.id.strip(), user.name.strip(), user.dep.strip()]
                for category in range(3):
                    for unit in range(len(question_manager.get_category(category))):
                        for question in range(len(question_manager.get_unit(category, unit))):
                            key = f'{category}-{unit}-{question}'
                            if key in user.history:
                                assessment_list = user.history[key]
                                if assessment_list:  # Check if the list is not empty
                                    # Sort by timestamp to get the latest assessment's score
                                    latest_assessment = sorted(assessment_list, key=lambda sa: sa.timestamp, reverse=True)[0]
                                    row.append(latest_assessment.score)
                                else:
                                    row.append('') # Key exists but list is empty
                            else:
                                row.append('')
                writer.writerow(row)
                
def answer_print(users, question_manager: QuestionManager):
    print("Warning: The 'answer_print' function needs changes to generate 'question.csv' correctly.")
    import csv
    classes : dict[str, list[User]]= {}
    for user in users:
        classes.setdefault(user.class_time, []).append(user)
    
    for class_time, subs in classes.items():
        if not os.path.exists(class_time):
            os.mkdir(class_time)
        subs = sorted(subs, key=lambda x: x.id)
        with open(f'{class_time}/answers.csv', 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['學號', '題號', '分數', '學生答案'])
            for user in subs:
                # Sort history items by question key (k: "cat-unit-q_idx")
                sorted_history_items = sorted(user.history.items(), key=lambda item: item[0])
                for k, v_list in sorted_history_items: # v_list is list[SpeechAssessment]
                    if v_list:
                        # Sort assessments for this specific question by timestamp (chronological)
                        sorted_assessments_for_question = sorted(v_list, key=lambda sa: sa.timestamp)
                        for assessment_item in sorted_assessments_for_question:
                            writer.writerow([user.id, k, assessment_item.score, assessment_item.transcript])
        with open(f'{class_time}/idtostu.csv', 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['學號', '姓名', '系所'])
            for user in sorted(subs, key=lambda x: x.id):
                writer.writerow([user.id, user.name, user.dep])
    
    # 題號對問題的對照表 - This needs to be generated differently
    # Cannot simply iterate range(3) anymore.
    # Needs to iterate through category_names, get QM indices, get questions.
    pass # Prevent execution for now
    
if __name__ == "__main__":
    user_data_path = Path("user_data2.json")
    users = load_user_data(user_data_path)
    question_manager = QuestionManager('./category')
    
    # bonus(users, question_manager)    
    # score_print(users, question_manager)
    # answer_print(users,question_manager)
    analysis_result = analyze_by_question(users, question_manager)
    print(json.dumps(analysis_result, indent=2))
