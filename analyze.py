import json
from pathlib import Path
from manager.question_manager import QuestionManager
from utils.models import User, SpeechAssessment, Question
from datetime import datetime
from zoneinfo import ZoneInfo  # Import ZoneInfo for timezone handling
import os

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

def bonus(users: list[User], question_manager: QuestionManager):
    from collections import defaultdict
    import csv

    # Initialize finished user lists per class_time
    finished_per_class = defaultdict(lambda: {
        "pre_test": [],
        "ex_finished": [],
        "ex_1_finished": [],
        "ex_2_finished": [],
        "ex_3_finished": [[], [], []],
        "post_test": []
    })
    
    category_lengths = {
        0: sum(len(unit) for unit in question_manager.get_category(0)),
        1: sum(len(unit) for unit in question_manager.get_category(1)),
        2: sum(len(unit) for unit in question_manager.get_category(2))
    }

    unit_lengths = {
        (0,0): len(question_manager.get_unit(0,0)),
        (0,1): len(question_manager.get_unit(0,1))
    }

    # Initialize bonus points dictionary
    bonus_points = defaultdict(int)

    for user in users:
        class_time = user.class_time
        counts = defaultdict(int)
        ex_parts = defaultdict(int)

        for history in user.history:
            parts = history.split('-')
            if parts[0] == '0':
                counts['ex'] += 1
                if parts[1] == '0':
                    counts['ex1'] += 1
                elif parts[1] == '1':
                    counts['ex2'] += 1
                if parts[2] == '0':
                    ex_parts['ex3_1'] += 1
                elif parts[2] == '1':
                    ex_parts['ex3_2'] += 1
                elif parts[2] == '2':
                    ex_parts['ex3_3'] += 1
            elif parts[0] == '1':
                counts['pre_test'] += 1
            elif parts[0] == '2':
                counts['post_test'] += 1

        # Check completion criteria
        if counts['ex'] >= category_lengths[0]:
            finished_per_class[class_time]["ex_finished"].append(user)
            bonus_points[user.id] += 0  # No bonus for ex_finished
        if counts['ex1'] >= unit_lengths.get((0,0), 0):
            finished_per_class[class_time]["ex_1_finished"].append(user)
            bonus_points[user.id] += 10
        if counts['ex2'] >= unit_lengths.get((0,1), 0):
            finished_per_class[class_time]["ex_2_finished"].append(user)
            bonus_points[user.id] += 10
        if ex_parts['ex3_1'] >= 1:
            finished_per_class[class_time]["ex_3_finished"][0].append(user)
            bonus_points[user.id] += 10
        if ex_parts['ex3_2'] >= 1:
            finished_per_class[class_time]["ex_3_finished"][1].append(user)
            bonus_points[user.id] += 10
        if ex_parts['ex3_3'] >= 1:
            finished_per_class[class_time]["ex_3_finished"][2].append(user)
            bonus_points[user.id] += 10
        if counts['pre_test'] >= category_lengths[1]:
            finished_per_class[class_time]["pre_test"].append(user)
            bonus_points[user.id] += 15
        if counts['post_test'] >= category_lengths[2]:
            finished_per_class[class_time]["post_test"].append(user)
            bonus_points[user.id] += 15
        if (counts['post_test'] >= category_lengths[2] and
            any(user.name == ex_user.name for ex_user in finished_per_class[class_time]["ex_finished"])):
            bonus_points[user.id] += 10
        if (counts['pre_test'] >= category_lengths[1] and
            any(user.name == ex_user.name for ex_user in finished_per_class[class_time]["ex_finished"])):
            bonus_points[user.id] += 10

    # Union of pre_test_finished and ex_finished per class_time
    postEx_per_class = {}
    preEx_per_class = {}
    for class_time, finished in finished_per_class.items():
        postEx_per_class[class_time] = [user for user in finished["post_test"]
                                       if any(user.name == ex_user.name for ex_user in finished["ex_finished"])]
        preEx_per_class[class_time] = [user for user in finished["pre_test"] if any(user.name == ex_user.name for ex_user in finished["ex_finished"])]

    def write_csv(filename, headers, users):
        with open(filename, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for user in users:
                row = [user.id.strip(), user.name.strip(), user.dep, user.class_time]
                writer.writerow(row)

    for class_time, finished in finished_per_class.items():
        if not os.path.exists(class_time):
            os.mkdir(class_time)

        # Write CSV files for each class_time
        write_csv(f'{class_time}/pretest.csv', ['學號', '姓名', '系所', '上課時段'], finished["pre_test"])
        write_csv(f'{class_time}/ex1.csv', ['學號', '姓名', '系所', '上課時段'], finished["ex_1_finished"])
        write_csv(f'{class_time}/ex2.csv', ['學號', '姓名', '系所', '上課時段'], finished["ex_2_finished"])

        for i in range(1, 4):
            write_csv(f'{class_time}/ex3-{i}.csv', ['學號', '姓名', '系所', '上課時段'], finished["ex_3_finished"][i-1])

        write_csv(f'{class_time}/posttest.csv', ['學號', '姓名', '系所', '上課時段'], finished["post_test"])
        write_csv(f'{class_time}/post+ex.csv', ['學號', '姓名', '系所', '上課時段'], postEx_per_class[class_time])
        write_csv(f'{class_time}/pre+ex.csv', ['學號', '姓名', '系所', '上課時段'], preEx_per_class[class_time])

        with open(f'{class_time}/bonus.csv', 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['學號', '姓名', '系所', 'Total', 'EX1', 'EX2', 'EX3-1', 'EX3-2', 'EX3-3', 'Pre-test', 'Post-test', 'Pre+EX', 'Post+EX'])
            for user in users:
                if user.id in bonus_points and user.class_time == class_time:
                    row = [user.id.strip(), user.name.strip(), user.dep, bonus_points[user.id], user in finished_per_class[class_time]["ex_1_finished"], 
                        user in finished_per_class[class_time]["ex_2_finished"], user in finished_per_class[class_time]["ex_3_finished"][0],
                        user in finished_per_class[class_time]["ex_3_finished"][1], user in finished_per_class[class_time]["ex_3_finished"][2],
                        user in finished_per_class[class_time]["pre_test"], user in finished_per_class[class_time]["post_test"],
                        user in preEx_per_class[class_time], user in postEx_per_class[class_time]
                        ]
                    writer.writerow(row)

if __name__ == "__main__":
    user_data_path = Path("user_data.json")
    users = load_user_data(user_data_path)
    question_manager = QuestionManager('./category')
    
    bonus(users, question_manager)    
    # analysis_result = analyze_by_question(users, question_manager)
    # print(json.dumps(analysis_result, indent=2))
