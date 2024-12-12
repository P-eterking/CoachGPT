from config import line_bot_api, line_bot_api_blob, DOMAIN
from linebot.v3.messaging import (
    ReplyMessageRequest, TextMessage, PostbackAction, QuickReply,
    QuickReplyItem, RichMenuRequest, RichMenuSize, RichMenuArea,
    RichMenuBounds, FlexMessage, FlexCarousel, FlexBubble, FlexImage,
    FlexText, FlexBox, FlexButton
)
from linebot.v3.messaging.exceptions import ApiException
from linebot.v3.messaging.models import SetWebhookEndpointRequest
from utils.models import SpeechAssessment
import json
from PIL import Image
from utils.file_utils import (
    get_test_mode, getData, get_category, getHistory, get_rich_menu_id, set_rich_menu_id, save_config,
    get_category
)
# 設定主網址和分類變數
URL = f'https://{DOMAIN}'
IMG_EXT = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')

# 定義問題集合
qs = {
    0:[
        [
            {
                "text": "What is 'access' and how do you use it in your daily life?\n - 「使用權」是什麼？在日常生活中你會怎麼用到它？",
                "assessment_standard": """
                            10	Access refers to the ability or permission to use, enter, or retrieve something. For example, having access to a restricted area means being allowed to enter it. In the digital world, access often involves obtaining data or using online services, such as accessing a website or a cloud storage platform. The term is widely used in contexts like technology, transportation, and security.
                            9	Access means the ability to use, enter, or reach something. For instance, having access to a computer allows you to use its programs and files. It can also mean permission to go to a place or obtain specific information, such as accessing private data.
                            8	Access is the ability to use or enter something, like going into a building or opening a file on a computer. It can also refer to permission to get information or resources.
                            7	Access means being able to go to a place or use something, like entering a room or opening a computer file. It helps people get what they need.
                            6	Access is when you can use something or go to somewhere. For example, you have access to a computer or a door to enter.
                            5	Access is when you can use or go into something, like a room or a computer.
                            4	Access is when you can go in or use. It has something to do with doors or computers.
                            3	Access is something you can use. It means go.
                            2	Access is something. It can go.
                            1	(No response or attempt to answer.)
                        """
            },
            {
                "text": "What is 'negotiation'? Tell us about a time when you might need to negotiate.\n - 什麼是「談判」？說說什麼時候你可能需要談判。",
                "assessment_standard": """
                            10	Negotiation is the process of discussing and reaching an agreement between two or more parties, often to resolve a conflict or finalize a deal. It involves clear communication, compromise, and decision-making to achieve mutual benefits. Negotiations can occur in various contexts, such as business transactions, legal disputes, or personal arrangements, and often require strategic thinking and interpersonal skills.
                            9	Negotiation refers to a discussion between two or more people to settle a disagreement or make an agreement. It is commonly used in business deals or problem-solving situations. The goal is to find a solution that benefits everyone involved.
                            8	Negotiation is when people talk to each other to solve a problem or make a deal. It happens in places like businesses, and both sides try to agree on something.
                            7	Negotiation means talking to someone to agree on something. For example, people negotiate prices when buying or selling things.
                            6	Negotiation is when people talk about a problem to find a solution. It can happen in a business or between friends.
                            5	Negotiation is talking to solve a problem or make a deal.
                            4	Negotiation is when people talk about something and want to agree.
                            3	Negotiation is people talking. They want to make a deal.
                            2	Negotiation is talking about something.
                            1	(No response or attempt to answer.)
                        """
            },
            {
                "text": "What is a 'warranty'? Why do we care about it when buying things?\n - 「保固」是什麼？我們買東西時為什麼要在意它？",
                "assessment_standard": """
                            10	Warranty is a written guarantee provided by a manufacturer or seller, assuring the buyer that a product will meet specific quality standards or perform as promised. If the product fails within a certain period, the warranty allows the buyer to request a repair, replacement, or refund. Warranties are often included with appliances, electronics, and vehicles, serving as a form of consumer protection and building trust between businesses and customers.
                            9	Warranty refers to a promise made by a company to fix or replace a product if it does not work as expected within a certain time. It is often provided for items like electronics or cars to ensure customer satisfaction and trust.
                            8	Warranty is a guarantee from a seller or maker that a product will work well. If the product breaks within a set time, the company will fix or replace it. It is common for products like phones or cars.
                            7	Warranty means a promise that if something you buy breaks, the company will fix it for free. It is usually for things like machines or gadgets.
                            6	Warranty is when a company promises to fix something if it stops working. It is for products like a phone or a car.
                            5	Warranty is a promise that a company will fix something if it breaks.
                            4	Warranty is a promise to fix or change something if it doesn't work.
                            3	Warranty is a promise. It fixes things.
                            2	Warranty is fixing something.
                            1	(No response or attempt to answer.)
                        """
            },
            {
                "text": "What is 'insurance'? Give an example of when it comes in handy.\n - 「保險」是什麼？舉個例子說明什麼時候它會派上用場。",
                "assessment_standard": """
                            10	Insurance is a financial arrangement in which an individual or organization pays regular premiums to an insurance company in exchange for protection against potential losses or damages. It provides coverage for various risks, such as accidents, health issues, or property damage. If an insured event occurs, the insurance company compensates the policyholder based on the terms of the agreement, offering financial security and peace of mind.
                            9	Insurance is a service where people pay money to a company regularly so that the company will cover costs if something bad happens, like an accident or illness. It is a way to protect yourself from financial losses.
                            8	Insurance is an agreement where you pay money to a company, and they help you if you lose something or have an accident. It can protect your car, house, or health.
                            7	Insurance means paying money to a company so they will pay you back if something bad happens, like a car crash or a fire.
                            6	Insurance is when you pay money to a company, and they help you if something bad happens, like a car accident.
                            5	Insurance is paying money to a company, and they pay you if something happens.
                            4	Insurance is something you pay for, and it helps if something bad happens.
                            3	Insurance is something you buy. It helps with problems.
                            2	Insurance is money for something bad.
                            1	(No response or attempt to answer.)
                        """
            },
            {
                "text": "What is a 'quarter'? How do we use it in business and daily life?\n - 「四分之一」是什麼？我們在商業和日常生活中怎麼用它？",
                "assessment_standard": """
                            10	Quarter has multiple meanings depending on the context. It can refer to one-fourth of something, such as a quarter of an hour (15 minutes) or a quarter of a dollar (25 cents in US currency). In business, it represents a three-month period used for financial reporting. Additionally, it can describe a specific area or district within a city, such as the French Quarter in New Orleans.
                            9	Quarter means one-fourth of something, like 15 minutes in an hour or 25 cents in US money. In business, it also refers to a three-month period, like the first quarter of the year. It can also mean a section of a city, such as a historical area.
                            8	Quarter is one-fourth of something. For example, it can mean 15 minutes, 25 cents, or a three-month period in business. It can also describe a part of a city.
                            7	Quarter means a part that is one-fourth of something, like 15 minutes or 25 cents. It can also mean three months of a year.
                            6	Quarter is one-fourth of something. It can mean a small amount of money or a short period of time.
                            5	Quarter is one-fourth of something, like time or money.
                            4	Quarter is one-fourth. It can mean time or money.
                            3	Quarter is one-fourth. It's small.
                            2	Quarter is part of something.
                            1	(No response or attempt to answer.)
                        """
            },
            {
                "text": "What does a 'technician' do at work?\n - 「技術人員」在工作時都做些什麼？",
                "assessment_standard": """
                            10	A technician is a skilled professional who specializes in a specific technical field, such as engineering, electronics, or medical equipment. They are responsible for maintaining, repairing, and operating complex systems or machinery. Technicians often work alongside engineers or other professionals, applying their expertise to ensure that equipment and processes function efficiently and safely.
                            9	A technician is someone with specialized skills who works in areas like machines, computers, or medical equipment. Their job is to fix, maintain, or operate these systems, helping things run smoothly. They often work closely with engineers or other experts.
                            8	A technician is a person trained to work with machines or equipment. They repair, check, or operate things like computers or medical tools.
                            7	A technician is someone who works with machines or equipment. They help fix and make sure things work properly.
                            6	A technician is a person who fixes or works with machines, like computers or tools.
                            5	A technician is someone who works with machines and fixes them.
                            4	A technician is a person who fixes machines or equipment.
                            3	A technician is someone who fixes things.
                            2	A technician is a person for machines.
                            1	(No response or attempt to answer.)
                        """
            },
            {
                "text": "What does it mean to 'provide'? What kind of things do you often provide to others?\n - 「提供」是什麼意思？你常常提供什麼給別人？",
                "assessment_standard": """
                            10	Provide means to supply or make something available that is needed or wanted. For example, parents provide food, shelter, and education for their children, while companies provide services or products to customers. It is commonly used in various contexts, such as offering assistance, resources, or opportunities.
                            9	Provide means to give or supply something that people need or ask for. For example, a teacher provides knowledge to students, or a business provides goods to its customers. It is an essential action in everyday life.
                            8	Provide means to give something that is needed. For instance, a company provides products, or a school provides education for children.
                            7	Provide means to give something that people need, like food, help, or information.
                            6	Provide is when you give something to someone, like help or things they need.
                            5	Provide means to give something, like food or help.
                            4	Provide is to give things to people, like food or help.
                            3	Provide is to give something to people.
                            2	Provide is giving.
                            1	(No response or attempt to answer.)
                        """
            },
            {
                "text": "What happens in a 'seminar'? What topic would you like to learn about in one?\n - 「研討會」會做些什麼？你想在研討會上學什麼主題？",
                "assessment_standard": """
                            10	A seminar is a formal meeting or educational session where a small group of people discuss specific topics, often led by an expert or presenter. Seminars are commonly held in academic, professional, or corporate settings to share knowledge, exchange ideas, or provide training. For example, a marketing seminar may teach participants strategies to improve brand visibility.
                            9	A seminar is a meeting or class where people learn about a specific topic. It is usually guided by a speaker or expert. For example, a seminar on business might include presentations and discussions about improving sales.
                            8	A seminar is a meeting or class where people discuss and learn about a topic. It is often led by someone knowledgeable, like a teacher or professional.
                            7	A seminar is a meeting where people talk about a topic and learn from a teacher or expert.
                            6	A seminar is a small meeting where people learn about something from a speaker.
                            5	A seminar is a meeting to learn about something.
                            4	A seminar is a meeting for learning or talking.
                            3	A seminar is a meeting to talk.
                            2	A seminar is a meeting.
                            1	(No response or attempt to answer.)
                        """
            },
            {
                "text": "What is a 'reservation'? Why is it helpful when planning events?\n - 「預約」是什麼？在規劃活動時為什麼有幫助？",
                "assessment_standard": """
                            10	A reservation is an arrangement made in advance to secure a place, service, or item, such as booking a table at a restaurant, a seat on a flight, or a hotel room. It ensures that the requested service will be available at a specific time. Additionally, the term can also refer to a doubt or hesitation about something, often used in discussions or agreements.
                            9	A reservation is an advance booking for something, like a table at a restaurant, a hotel room, or a ticket for a flight. It helps secure a spot or service. It can also mean feeling unsure about something in a conversation.
                            8	A reservation is when you book something in advance, like a hotel room or a table at a restaurant. It makes sure you have a spot or service ready.
                            7	A reservation means booking something ahead of time, like a seat, a room, or a table.
                            6	A reservation is when you save a spot, like a table at a restaurant or a hotel room.
                            5	A reservation is booking a place like a hotel or restaurant.
                            4	A reservation is when you book or save a place for later.
                            3	A reservation is booking or saving a spot.
                            2	A reservation is saving something.
                            1	(No response or attempt to answer.)
                        """
            },
            {
                "text": "What does 'previous' mean? Can you share an important experience from your past?\n - 「先前的」是什麼意思？能分享一個你過去重要的經驗嗎？",
                "assessment_standard": """
                            10	Previous means something that happened, existed, or occurred before a particular time or event. For example, a previous meeting refers to a meeting that took place earlier. It is often used to describe earlier experiences, events, or versions of something. In context, it might be said, "The previous version of this report was less detailed than the current one."
                            9	Previous refers to something that came before another in time or order. For instance, the previous week is the one before the current week, or a previous job refers to a job you had earlier.
                            8	Previous means something that happened earlier. For example, a previous meeting or event refers to one that happened before now.
                            7	Previous means something that was before now, like a meeting or a time that happened earlier.
                            6	Previous is when something happened before, like last week or last time.
                            5	Previous means before something, like last week.
                            4	Previous is something before, like last time.
                            3	Previous is before now.
                            2	Previous is before.
                            1	(No response or attempt to answer.)
                        """
            }
        ],
        [
            {
                "text": "請先閱讀右方情境說明再答題 Read the scenario instructions on the right before answering.\nCan you describe what the team might be discussing during this meeting?\n- 你能描述這個會議中團隊可能在討論什麼嗎？",
                "image_url": f"{URL}/templates/0/cover2-1.jpg",
                "assessment_standard": """
                    10	The team might be discussing the causes of the company’s declining quarterly performance, and analyzing financial trends such as reduced sales or increased costs. They could be focusing on identifying issues and proposing solutions to improve performance, like reallocating budgets or revising strategies.
                    9	The team might be reviewing the company’s performance data, identifying reasons for the decline, and brainstorming possible solutions, such as adjusting budgets or improving operations.
                    8	The team is analyzing performance charts to find out why results declined. They are discussing possible strategies, like cutting costs or improving sales efforts.
                    7	The team is looking at charts to understand why the performance is worse. They are talking about ways to fix the problem.
                    6	The team is talking about bad numbers. They are trying to find what caused it and how to fix it.
                    5	The team talks about bad results and fixing them.
                    4	Talk about numbers going down.
                    3	Bad numbers. Fix them.
                    2	Bad charts.
                    1	(Incomprehensible reply.)
                    0	(No response.)
                """,
                "extra_info": [[
                    "You are attending a meeting as the team’s note-taker. The team is discussing the company’s declining quarterly performance. The team leader is reviewing financial charts and data trends with the standing colleague, who is explaining potential causes. Discussions focus on identifying problem areas, such as reduced sales or rising costs, and brainstorming solutions. Negotiations might involve reallocating budgets, setting new priorities, or agreeing on next steps to improve performance.",
                    "您正在參加一場會議，並擔任團隊的會議紀錄員。團隊正在討論公司季度業績下滑的問題。團隊領導正在檢視財務圖表和數據趨勢，而站著的同事正在說明可能的原因。討論的重點是識別問題區域，例如銷售下降或成本上升，並集思廣益提出解決方案。協商內容可能包括重新分配預算、設定新優先事項或商定改善績效的下一步行動。"
                ]]
            },
            {
                "text": "請先閱讀右方情境說明再答題 Read the scenario instructions on the right before answering.\nWhat kind of negotiation might take place in this meeting?\n- 會議中可能會進行哪種類型的談判？",
                "image_url": f"{URL}/templates/0/cover2-1.jpg",
                "assessment_standard": """
                    10	The negotiation might involve deciding how to reallocate budgets to focus on profitable areas or agreeing on adjustments to marketing and operational strategies. Team members may also discuss setting realistic performance goals and timelines to address the quarterly decline effectively.
                    9	The team might negotiate reallocating budgets or deciding on priorities for upcoming projects. They could also discuss changes to strategies for improving performance.
                    8	The team can talk about shifting money to important areas or changing plans to improve results. They could also decide on new goals.
                    7	The team is discussing where to spend money and what changes to make to fix the problem.
                    6	The team is talking about budgets and plans to improve performance.
                    5	The team talks about budgets and changes.
                    4	Talk about spending and fixing problems.
                    3	Budget meeting.
                    2	Money plans.
                    1	(Incomprehensible reply.)
                    0	(No response.)
                """,
                "extra_info": [[
                    "You are attending a meeting as the team’s note-taker. The team is discussing the company’s declining quarterly performance. The team leader is reviewing financial charts and data trends with the standing colleague, who is explaining potential causes. Discussions focus on identifying problem areas, such as reduced sales or rising costs, and brainstorming solutions. Negotiations might involve reallocating budgets, setting new priorities, or agreeing on next steps to improve performance.",
                    "您正在參加一場會議，並擔任團隊的會議紀錄員。團隊正在討論公司季度業績下滑的問題。團隊領導正在檢視財務圖表和數據趨勢，而站著的同事正在說明可能的原因。討論的重點是識別問題區域，例如銷售下降或成本上升，並集思廣益提出解決方案。協商內容可能包括重新分配預算、設定新優先事項或商定改善績效的下一步行動。"
                ]]
            },
            {
                "text": "請先閱讀右方情境說明再答題 Read the scenario instructions on the right before answering.\nWhat concerns might travelers have about their plans, and how can these be addressed at the airport?\n- 旅客可能對他們的計劃有哪些擔憂，這些擔憂可以在機場如何解決？",
                "image_url": f'{URL}/templates/0/cover2-3.jpg',
                'assessment_standard': """
                    10	Travelers may be concerned about flight delays, cancellations, lost luggage, or unexpected travel restrictions. These concerns can be addressed by utilizing airport services such as real-time updates on flight boards, luggage assistance desks, and travel insurance counters for last-minute coverage.
                    9	Travelers might worry about delays, missing their connections, or baggage issues. The airport can assist with information boards, customer service desks, and insurance kiosks for last-minute needs.
                    8	Some passengers may worry about delayed flights or lost luggage. The airport staff and service desks can help address these problems.
                    7	They might worry about late flights or losing their bags. Staff at the airport can help solve these problems.
                    6	They are worried about their flights or bags. They can ask for help.
                    5	They worry about flights and bags.
                    4	Worry about flight, ask staff help.
                    3	Flight bad. Help.
                    2	Flight.
                    1	(Incomprehensible reply.)
                    0	(No response.)
                """,
                "extra_info": [[
                    "You are observing activities in a busy airport terminal. Passengers are checking in or exchanging currency, and some are considering buying insurance for their travel plans.",
                    "您正在觀察繁忙的機場航廈內的活動。乘客正在辦理登機手續或兌換貨幣，有些人正在考慮為旅行計劃購買保險。",
                ]]
            },
            {
                "text": "請先閱讀右方情境說明再答題 Read the scenario instructions on the right before answering.\now might passengers be preparing for their flights at the check-in counters?\n- 旅客可能會如何在登機櫃檯為航班做準備？",
                "image_url": f'{URL}/templates/0/cover2-3.jpg',
                'assessment_standard': """
                    10	Passengers might confirm their travel documents, check in their luggage, select seats, and verify any special requests, such as meal preferences or additional assistance. They may also inquire about flight updates or connecting flights.
                    9	Passengers may be preparing for their flights by checking their tickets, dropping off luggage, and confirming their seats. They might also ask about meal preferences or travel details.
                    8	Passengers could check in their bags, show their tickets, and talk to staff about their flights.
                    7	They check tickets and bags and ask questions at the counter.
                    6	They prepare tickets and bags for their flight.
                    5	They check bags and tickets.
                    4	Check bags and tickets.
                    3	Bag check.
                    2	Ticket.
                    1	(Incomprehensible reply.)
                    0	(No response.)
                """,
                "extra_info": [[
                    "You are observing activities in a busy airport terminal. Passengers are checking in or exchanging currency, and some are considering buying insurance for their travel plans.",
                    "您正在觀察繁忙的機場航廈內的活動。乘客正在辦理登機手續或兌換貨幣，有些人正在考慮為旅行計劃購買保險。",
                ]]
            },
            {
                "text": "請先閱讀右方情境說明再答題 Read the scenario instructions on the right before answering.\nWhat information might the guests be providing to the front desk staff during check-in?\n- 客人在辦理入住手續時可能向前台人員提供什麼資訊？",
                "image_url": f"{URL}/templates/0/cover2-5.jpg",
                "assessment_standard": """
                    10	The guests might be providing their reservation details, valid IDs, and payment information. They may also confirm the duration of their stay, specify room preferences, and mention any special needs, such as early check-in or accessibility requirements.
                    9	The guests might share their reservation confirmation, ID, and payment details. They may also indicate specific room preferences or mention their length of stay.
                    8	The guests provide their reservation number, ID, and payment. They might also mention their check-in and check-out dates.
                    7	The guests give their ID and booking information and tell how long they are staying.
                    6	The guests give their name and ID for check-in.
                    5	The guests give their name and booking.
                    4	Give name, booking
                    3	Name.
                    2	ID.
                    1	(Incomprehensible reply.)
                    0	(No response.)
                """,
                "extra_info": [[
                    "You are observing interactions at the front desk of a busy hotel. Guests are checking in and asking for additional services during their stay.",
                    "您正在觀察一家繁忙飯店前台的互動。客人正在辦理入住手續並詢問住宿期間的其他服務。",
                ]]
            },
            {
                "text": "請先閱讀右方情境說明再答題 Read the scenario instructions on the right before answering.\nWhat additional services might guests request during their stay?\n- 客人在住宿期間可能會要求哪些額外服務？",
                "image_url": f"{URL}/templates/0/cover2-5.jpg",
                "assessment_standard": """
                    10	Guests might request room service, access to the gym or spa, laundry services, or assistance with booking local tours and transportation. They may also inquire about late check-out or upgrading their room.
                    9	The guests might ask for room service, laundry, or help with booking transportation and tours. They might also request late check-out or room upgrades.
                    8	The guests might ask for room service, access to the gym, or help with tours.
                    7	The guests ask for food in their room or help with transportation.
                    6	They ask for room service or help with booking.
                    5	They want room service and help.
                    4	Ask for food, help.
                    3	Food.
                    2	Room.
                    1	(Incomprehensible reply.)
                    0	(No response.)
                """,
                "extra_info": [[
                    "You are observing interactions at the front desk of a busy hotel. Guests are checking in and asking for additional services during their stay.",
                    "您正在觀察一家繁忙飯店前台的互動。客人正在辦理入住手續並詢問住宿期間的其他服務。",
                ]]
            },
        ],  
        # [
        #     {
        #         "text": "Beginning: Introduce the main character and setting.\nA hare was making fun of a tortoise for moving so slowly. The tortoise got tired of the hare making fun of how slow he was. So, he asked the hare to have a race.\n開始：介紹主要角色和場景。\n一隻野兔正在嘲笑一隻行動緩慢的烏龜。烏龜厭倦了野兔嘲笑牠動作慢的樣子。於是牠要求野兔和他進行一場比賽。",
        #     },
        #     {
        #         "text": "Then: Introduce obstacles and challenges main character encounters.\nWhen the race started, the hare bounded off in front, making good progress. He was so far ahead of the tortoise that he decided he could afford to stop and have a rest.\n然後：介紹主要角色遇到的障礙和挑戰。\n比賽一開始，野兔就飛奔而出，並且進展迅速。遠遠地把烏龜甩在後面，牠覺得自己可以停下來休息一下。",
        #     },
        #     {
        #         "text": "After: Reach the climax or turning point of the story, where the main character confronts the central conflict head-on.\nHowever, the hare fell fast asleep, and as he lay sleeping, the tortoise continued to plod along at his slow pace. In time, he reached the finish-line and won the race.\n之後：到達故事的高潮或轉折點，主角正面對抗主要衝突。\n然而，野兔很快就睡著了，當牠在睡覺時，烏龜以緩慢的步伐繼續向前爬行。最終，烏龜到達了終點線，贏得了比賽。",
        #     },
        #     {
        #         "text": "Ending: Resolve the conflict and provide closure for the story. Show how the main character has changed. \nWhen the hare woke up, he was annoyed at himself for falling asleep. So he ran off towards the finish-line as fast as his legs would carry him, but it was too late, as the tortoise had already won.\n結尾：解決衝突並為故事提供結局。展示主角的變化。\n當野兔醒來時，他對自己睡著了感到懊惱。於是牠全力奔向終點線，但為時已晚，烏龜已經贏得了比賽。",
        #     }
        # ]
    ],
    1: [
        [
            {
                "text": "What is a 'brochure'? Could you provide an example and explain it?\n - 什麼是「宣傳冊」？試著舉一個例子解釋",
                "assessment_standard": """
                10 優異表達者
                A brochure is a printed document that provides detailed information about a specific topic, product, or service. It is often used for marketing purposes to attract potential customers by highlighting key features and benefits. Brochures can be found in various formats, including tri-folds and booklets, and are designed to be visually appealing to engage readers effectively.
                9 優良表達者
                A brochure is a promotional document that offers information about a product, service, or event. It typically includes attractive images and concise text to inform potential customers. Brochures are commonly distributed at conventions or events to provide attendees with valuable details about what is being offered.
                8 良好表達者
                A brochure is a type of printed material that gives information about something, such as a service or a place. It often has pictures and a layout designed to catch people’s attention. Brochures are used by businesses and organizations to promote their offerings.
                7 基礎表達者
                A brochure is a small booklet that contains information. It can be about a place or a service, and it usually has some pictures. People use brochures to learn more about different things.
                6 有限表達者
                A brochure is a paper that tells about something. It has some words and pictures to help people understand. It is used by companies to share information.
                5 簡單表達者
                A brochure is a paper with information. It shows pictures and tells about things. It helps people know more about products.
                4 有限互動能力者
                A brochure is a type of paper with stuff on it. It has pictures. It gives some information, but it is not clear.
                3 極度有限的表達者
                A brochure is paper. It has pictures. I don’t know much more.
                2 極低表達能力者
                A brochure is paper. It has something.
                1 無表達能力者
                (No response or attempt to answer.)
                """,
            },
            {
                "text": "Explain 'convention' and what are its main functions?\n - 「會議」是什麼？它的主要功能是什麼？",
                "assessment_standard": """
                10 優異表達者
                A convention is a formal gathering or meeting of individuals who share a common interest or profession. These events often include presentations, workshops, and discussions aimed at exchanging knowledge, networking, and addressing issues relevant to the group. Conventions can be organized around specific themes, such as education, technology, or health, and typically attract participants from various regions or fields.
                9 優良表達者
                A convention is a large meeting where people with similar interests come together to discuss topics and share ideas. These gatherings usually include speakers, workshops, and networking opportunities. Conventions are common in various fields, such as science, business, and arts, and provide a platform for collaboration.
                8 良好表達者
                A convention is a meeting of a group of people who come together to talk about certain topics. It often includes presentations and activities related to a specific theme. Conventions allow attendees to learn and network with others in their field.
                7 基礎表達者
                A convention is a big meeting. People come together to talk about something important. They have speakers and discussions.
                6 有限表達者
                A convention is a place where people meet. They talk about things and share information. It can be big.
                5 簡單表達者
                A convention is a meeting. People go there to talk and learn.
                4 有限互動能力者
                A convention is a type of meeting. People gather, but I don’t know what they do.
                3 極度有限的表達者
                A convention is a meeting. People are there.
                2 極低表達能力者
                A convention is a meeting of people.
                1 無表達能力者
                (No response or attempt to answer.)
                """,
            },
        ],
        [
            {
                "text": "Describe the picture in as much detail as you can\n根據圖片，詳細描述圖片中的人物、場景及所發生的事。",
                "image_url": f"{URL}/templates/1/cover2-1.jpg",
                "assessment_standard": """
                10 優異表達者
                This picture shows a business meeting in a modern office with large windows overlooking the city. There are several professionals around a polished wooden table, engaged in discussion. Some are looking at reports, while one person is taking notes. The atmosphere feels serious, indicating important decisions are being made.
                9 優良表達者
                The image depicts a business meeting happening in a high-rise office. People are sitting around a table, reviewing documents and charts. One person is writing notes, and the others are discussing strategies. The setting looks professional and focused.
                8 良好表達者
                This image features a meeting in an office. There are several people at a table with papers and charts. One person is writing while others seem to be talking about important topics.
                7 基礎表達者
                The picture shows a meeting in an office. People are gathered around a table with documents. It looks like they are discussing something serious.
                6 有限表達者
                This image has a group of people in a meeting. They have papers on the table, and one person is writing. It seems important.
                5 簡單表達者
                There are people in a meeting. They are looking at papers.
                4 有限互動能力者
                Meeting. People with papers. They look serious.
                3 極度有限的表達者
                Meeting with papers. People are there.
                2 極低表達能力者
                Meeting. Not clear.
                1 無表達能力者
                (No response or attempt to answer.)
                """
            },
            {
                "text": "Describe the picture in as much detail as you can\n根據圖片，詳細描述圖片中的人物、場景及所發生的事。",
                "image_url": f"{URL}/templates/1/cover2-2.jpg",
                "assessment_standard": """
                10 優異表達者
                This image shows a busy train station with lots of people waiting for trains. The station is modern, with tall ceilings and clear signs. A train is arriving, and everyone looks ready to travel. The scene captures the excitement of commuting in a big city.
                9 優良表達者
                The picture depicts a crowded train station. There are many people waiting for trains, and a train is at the platform. The place looks lively and organized.
                8 良好表達者
                This image features a train station with many passengers. A train is arriving, and it looks busy with people moving around.
                7 基礎表達者
                The picture shows a train station. There are lots of people, and a train is there.
                6 有限表達者
                There are people at a train station. A train is there.
                5 簡單表達者
                Train station with many people.
                4 有限互動能力者
                Train station. People are waiting.
                3 極度有限的表達者
                Train station. I see many people.
                2 極低表達能力者
                Train.
                1 無表達能力者
                (No response or attempt to answer.)
                """,
            },
        ],
        [
            {
                "text": "What activities do you think are taking place in the warehouse?\n - 你認為倉庫中正在進行的活動是什麼？",
                "image_url": f"{URL}/templates/1/cover3-1.jpg",
                "assessment_standard": """
                10 優異表達者
                The warehouse is likely bustling with activity. Workers are probably unloading shipments, checking inventory levels, and organizing products on shelves. Additionally, items might be prepared for delivery, ensuring that everything is correctly labeled and stored. Quality control checks are likely conducted to maintain standards.
                9 優良表達者
                Various tasks are likely taking place in the warehouse. Employees may be unloading boxes, organizing products, and packing orders for shipment. Inventory checks might also be happening to keep track of stock levels.
                8 良好表達者
                People in the warehouse seem to be involved in packing and sorting items. They may also be checking what products are available and getting them ready to send out.
                7 基礎表達者
                Activities in the warehouse probably include packing boxes and organizing items. Inventory checks may also take place to see what is in stock.
                6 有限表達者
                Workers seem to be packing and moving items around in the warehouse. They might be checking some products, but it’s not clear.
                5 簡單表達者
                There are workers in the warehouse packing items and moving boxes. It looks busy, but not much detail is available.
                4 有限互動能力者
                It seems like people are working in the warehouse. They might be packing and moving items, but it’s difficult to know exactly what they are doing.
                3 極度有限的表達者
                Some workers are busy moving things in the warehouse. Packing might be happening, but it’s not very clear.
                2 極低表達能力者
                There are people working. Boxes are being moved around, and maybe some packing is happening.
                1 無表達能力者
                (No response or attempt to answer.)
                """
            },
            {
                "text": "What considerations should hikers keep in mind to ensure a safe and enjoyable outing\n - 登山者應該考慮哪些因素，以確保安全且愉快的郊遊？",
                "image_url": f"{URL}/templates/1/cover3-2.jpg",
                "assessment_standard": """
                10 優異表達者
                Hikers should prioritize safety by planning their routes carefully and ensuring they are well-prepared for theterrain. This includes checking weather conditions and dressing appropriately for the climate. Carrying
                essential gear, such as a first aid kit, sufficient water, and nutritious snacks, is crucial. Additionally, informing someone about their hiking plans and estimated return time can enhance safety. Practicing Leave No
                Trace principles also helps preserve the environment for future hikers.
                9 優良表達者
                To ensure a safe and enjoyable hiking experience, it's important for hikers to choose suitable trails that match their skill levels. They should check the weather
                forecast and pack necessary items like water, snacks, and a map. Wearing appropriate footwear and clothing can also prevent injuries and discomfort. It’s a good idea to hike with a friend and let someone know the planned route and return time for added safety.
                8 良好表達者
                Hikers should consider planning their hike based on the trail difficulty and checking the weather. Bringing enough water and snacks is important to stay energized.
                Wearing the right shoes and clothes can help prevent injuries, and it’s better to hike with others for safety.
                7 基礎表達者
                When hiking, it’s good to pick a trail that is not too hard. Checking the weather and bringing water and snacks can make the hike better. Wearing proper shoes is also important for safety.
                6 有限表達者
                Hikers need to think about the trail they choose and check the weather. Bringing water and snacks is important to stay safe.
                5 簡單表達者
                Hiking safely means picking the right trail and bringing enough water. Wearing good shoes helps too.
                4 有限互動能力者
                Hikers should remember to check the weather and bring supplies. It seems like knowing the trail is important for safety.
                3 極度有限的表達者
                Safety is important when hiking, but it’s hard to say what to do exactly.
                2 極低表達能力者
                Um... just be careful? Bring water?
                1 無表達能力者
                (No response or attempt to answer.)
                """
            }
        ],
        [
            {
                "text": "What time does Bandaid Band perform?\n - Bandaid Band 是在哪一個時間表演?",
                "image_url": f"{URL}/templates/1/cover4-1.jpg",
                "max_score": 4,
                "assessment_standard": """
                為使評分標準更具指導性，可以根據每個分數提供具體的反饋。例如：
                3分：鼓勵學生繼續保持正確性和流利度。
                2分：指導學生在句子結構或細節準確性上進行改善。
                1分：提供更基礎的建議，幫助他們增強語法和句子結構的理解。
                
                4 回答完整且正確
                • 使用完整句子，且回答內容完全正確，無語法或內容錯誤。
                • 例子：學生完整且正確地表達所要求的資訊，語法與用詞準確。
                3 回答部分正確或語法不完整，但仍表達主要資訊
                • 情況1：回答內容大部分正確，但有些小錯誤或不完整，影響回答的全面性。
                • 情況2：回答為完整句子，但內容部分不正確。
                • 例子：學生表達了主要資訊，但在細節或語法上 存在小錯誤。
                2 回答不完整且不正確
                • 回答內容部分不正確且未使用完整句子，或只表達非常有限的資訊。
                • 例子：學生的回答僅包含少量正確資訊，且句子不完整或語法錯誤嚴重。
                1 (No response or attempt to answer.)
                
                4:
                - Bandaid Band performs at 1:00 PM on Stage B.
                - Bandaid Band is scheduled to play at 1:00 PM.
                - Bandaid Band plays at 1:00 PM.
                - Bandaid Band is on at 1 PM.
                
                3:
                - Bandaid Band performs at 1.
                - Bandaid Band is at 1 PM.
                - Bandaid Band plays at 1.

                2:
                - Bandaid Band at 1.
                - 1 PM.
                
                1: (No response.)
                """
            },
            {
                "text": "How much does the Beach Getaway to Cancun cost?\n - Cancun 海灘度假的費用是多少？",
                "image_url": f"{URL}/templates/1/cover4-2.jpg",
                "max_score": 4,
                "assessment_standard": """
                為使評分標準更具指導性，可以根據每個分數提供具體的反饋。例如：
                3分：鼓勵學生繼續保持正確性和流利度。
                2分：指導學生在句子結構或細節準確性上進行改善。
                1分：提供更基礎的建議，幫助他們增強語法和句子結構的理解。
                
                4 回答完整且正確
                • 使用完整句子，且回答內容完全正確，無語法或內容錯誤。
                • 例子：學生完整且正確地表達所要求的資訊，語法與用詞準確。
                3 回答部分正確或語法不完整，但仍表達主要資訊
                • 情況1：回答內容大部分正確，但有些小錯誤或不完整，影響回答的全面性。
                • 情況2：回答為完整句子，但內容部分不正確。
                • 例子：學生表達了主要資訊，但在細節或語法上 存在小錯誤。
                2 回答不完整且不正確
                • 回答內容部分不正確且未使用完整句子，或只表達非常有限的資訊。
                • 例子：學生的回答僅包含少量正確資訊，且句子不完整或語法錯誤嚴重。
                1 (No response or attempt to answer.)
                
                4:
                - The 7-day trip to Cancun costs $999.
                - The price for the 7-day Cancun trip is $999.
                - The 7-day Cancun trip is priced at $999.
                - A 7-day trip to Cancun costs $999.
                3:
                - It is $999 for Cancun.
                - The Cancun trip is $999.
                - Cancun is $999.
                2:
                - $999.
                - Cancun $999.
                1: (No response.)
                """
            },
        ],
        [
            {
                "text": "Do you agree that people should limit their use of social media to improve their mental health?\n - 你認為人們是否需限制社交媒體使用時間，以改善心裡健康？",
                "assessment_standard": """
                10 優異表達者
                "Yes, I strongly agree that limiting social media use can significantly benefit mental health. Studies show that excessive social media use can lead to issues such as anxiety, depression, and low self-esteem, particularly among young people. Constant comparison with others' seemingly perfect lives creates unrealistic expectations and promotes negative self-image. By reducing time on social platforms, individuals can shift focus to real-life interactions, fostering genuine connections and reducing anxiety. Moreover, decreased social media use allows for increased productivity and personal development, as people can invest time in hobbies, exercise, or mindfulness practices, which all contribute positively to mental health."
                9 優良表達者 
                "Yes, I agree that people should limit social media usage for better mental health. Many studies highlight that too much time on social media can lead to issues like anxiety and feeling inadequate. Social media often shows only the highlights of people’s lives, which makes others feel they are not doing enough. By cutting down on social media, people can focus more on their personal lives and relationships, reducing stress and negativity. Also, using less social media can increase time for other meaningful activities, such as spending time with friends, exercising, or learning new skills."
                8 良好表達者 
                "Yes, I think people should try to reduce their use of social media for mental health. Many people feel anxious or stressed after looking at social media because they compare themselves to others. When people spend too much time online, it can make them feel bad about themselves. By spending less time on social media, they might feel happier and can focus on things they enjoy in real life. Also, it could give people more time to be with friends or family, which is also good for mental health."
                7 基礎表達者
                "I think it is a good idea for people to use less social media to feel better. Social media can sometimes make people feel bad because they compare their lives to others. If they don’t use it so much, they might feel happier and focus on other things like family or hobbies. Also, they can spend more time outside or with friends, which is good for health."
                6 有限表達者 
                "I think people should use social media less. It makes people feel bad because they look at other people’s lives. When they don’t use it so much, they can feel better. They can spend more time with family or do fun things."
                5 簡單表達者
                "People should not use too much social media. It is not good. They feel sad because they look at others. If they use less, they can be happier and do other things."
                4 有限互動能力者
                "Social media is not good for people. They feel bad. Less is better."
                3 極度有限的表達者 
                "Social media… not good. People feel sad. Less… better."
                2 極低表達能力者 
                "Social media… not… good. People… sad."
                1 無表達能力者 
                (No response or attempt to answer.)
                """
            },
            {
                "text": "Do you agree that animal testing should be banned in all cases?\n - 你是否認為動物實驗應該被全面禁止？",
                "assessment_standard": """
                10 優異表達者
                "Yes, I believe animal testing should be banned in all cases. While it has contributed to scientific and medical advancements, the harm and suffering inflicted on animals is unacceptable. With the development of alternative methods, such as computer modeling and cell cultures, we now have other ways to test the safety and effectiveness of products. Banning animal testing would encourage innovation in developing cruelty-free methods, ultimately leading to a more humane approach in science and technology. Although some argue that animal testing is necessary for complex studies, I believe modern technology can replace these practices."
                9 優良表達者
                "Yes, I think animal testing should be banned because it causes unnecessary suffering. Many new technologies, like computer simulations, offer alternative ways to test products safely. If we stop animal testing, it will push scientists to find more humane methods. While some believe animal testing is still needed, I think we can find other solutions."
                8 良好表達者
                "I agree that animal testing should be banned. Testing causes animals pain, and now we have other ways to do research, like using computers. If we stop testing on animals, we can find kinder ways to do research. Some people think it’s needed, but I think there are other options."
                7 基礎表達者
                "I think animal testing should be banned. Testing causes animals to suffer, which isn’t fair. We have other options for testing, like using computers, so animal testing isn’t needed anymore."
                6 有限表達者
                "Yes, I think animal testing should stop because it hurts animals. We can use other ways to test products now, like computer models, which are better."
                5 簡單表達者
                "Animal testing is bad because it hurts animals. We can use other methods instead of testing on animals."
                4 有限互動能力者
                "Animal testing is not good because it causes pain. We should use different ways to test things."
                3 極度有限的表達者
                "Animal testing is bad. We should find other ways."
                2極低表達能力者
                "Animal testing is bad. Use other ways."
                1 無表達能力者 
                (No response or attempt to answer.)
                """
            },
        ],
    ],
    2: [
        [
            {
                "text": "What is a 'brochure'? Could you provide an example and explain it?\n - 什麼是「宣傳冊」？試著舉一個例子解釋",
                "assessment_standard": """
                10 優異表達者
                A brochure is a printed document that provides detailed information about a specific topic, product, or service. It is often used for marketing purposes to attract potential customers by highlighting key features and benefits. Brochures can be found in various formats, including tri-folds and booklets, and are designed to be visually appealing to engage readers effectively.
                9 優良表達者
                A brochure is a promotional document that offers information about a product, service, or event. It typically includes attractive images and concise text to inform potential customers. Brochures are commonly distributed at conventions or events to provide attendees with valuable details about what is being offered.
                8 良好表達者
                A brochure is a type of printed material that gives information about something, such as a service or a place. It often has pictures and a layout designed to catch people’s attention. Brochures are used by businesses and organizations to promote their offerings.
                7 基礎表達者
                A brochure is a small booklet that contains information. It can be about a place or a service, and it usually has some pictures. People use brochures to learn more about different things.
                6 有限表達者
                A brochure is a paper that tells about something. It has some words and pictures to help people understand. It is used by companies to share information.
                5 簡單表達者
                A brochure is a paper with information. It shows pictures and tells about things. It helps people know more about products.
                4 有限互動能力者
                A brochure is a type of paper with stuff on it. It has pictures. It gives some information, but it is not clear.
                3 極度有限的表達者
                A brochure is paper. It has pictures. I don’t know much more.
                2 極低表達能力者
                A brochure is paper. It has something.
                1 無表達能力者
                (No response or attempt to answer.)
                """,
            },
            {
                "text": "Explain 'convention' and what are its main functions?\n - 「會議」是什麼？它的主要功能是什麼？",
                "assessment_standard": """
                10 優異表達者
                A convention is a formal gathering or meeting of individuals who share a common interest or profession. These events often include presentations, workshops, and discussions aimed at exchanging knowledge, networking, and addressing issues relevant to the group. Conventions can be organized around specific themes, such as education, technology, or health, and typically attract participants from various regions or fields.
                9 優良表達者
                A convention is a large meeting where people with similar interests come together to discuss topics and share ideas. These gatherings usually include speakers, workshops, and networking opportunities. Conventions are common in various fields, such as science, business, and arts, and provide a platform for collaboration.
                8 良好表達者
                A convention is a meeting of a group of people who come together to talk about certain topics. It often includes presentations and activities related to a specific theme. Conventions allow attendees to learn and network with others in their field.
                7 基礎表達者
                A convention is a big meeting. People come together to talk about something important. They have speakers and discussions.
                6 有限表達者
                A convention is a place where people meet. They talk about things and share information. It can be big.
                5 簡單表達者
                A convention is a meeting. People go there to talk and learn.
                4 有限互動能力者
                A convention is a type of meeting. People gather, but I don’t know what they do.
                3 極度有限的表達者
                A convention is a meeting. People are there.
                2 極低表達能力者
                A convention is a meeting of people.
                1 無表達能力者
                (No response or attempt to answer.)
                """,
            },
        ],
        [
            {
                "text": "Describe the picture in as much detail as you can\n根據圖片，詳細描述圖片中的人物、場景及所發生的事。",
                "image_url": f"{URL}/templates/1/cover2-1.jpg",
                "assessment_standard": """
                10 優異表達者
                This picture shows a business meeting in a modern office with large windows overlooking the city. There are several professionals around a polished wooden table, engaged in discussion. Some are looking at reports, while one person is taking notes. The atmosphere feels serious, indicating important decisions are being made.
                9 優良表達者
                The image depicts a business meeting happening in a high-rise office. People are sitting around a table, reviewing documents and charts. One person is writing notes, and the others are discussing strategies. The setting looks professional and focused.
                8 良好表達者
                This image features a meeting in an office. There are several people at a table with papers and charts. One person is writing while others seem to be talking about important topics.
                7 基礎表達者
                The picture shows a meeting in an office. People are gathered around a table with documents. It looks like they are discussing something serious.
                6 有限表達者
                This image has a group of people in a meeting. They have papers on the table, and one person is writing. It seems important.
                5 簡單表達者
                There are people in a meeting. They are looking at papers.
                4 有限互動能力者
                Meeting. People with papers. They look serious.
                3 極度有限的表達者
                Meeting with papers. People are there.
                2 極低表達能力者
                Meeting. Not clear.
                1 無表達能力者
                (No response or attempt to answer.)
                """
            },
            {
                "text": "Describe the picture in as much detail as you can\n根據圖片，詳細描述圖片中的人物、場景及所發生的事。",
                "image_url": f"{URL}/templates/1/cover2-2.jpg",
                "assessment_standard": """
                10 優異表達者
                This image shows a busy train station with lots of people waiting for trains. The station is modern, with tall ceilings and clear signs. A train is arriving, and everyone looks ready to travel. The scene captures the excitement of commuting in a big city.
                9 優良表達者
                The picture depicts a crowded train station. There are many people waiting for trains, and a train is at the platform. The place looks lively and organized.
                8 良好表達者
                This image features a train station with many passengers. A train is arriving, and it looks busy with people moving around.
                7 基礎表達者
                The picture shows a train station. There are lots of people, and a train is there.
                6 有限表達者
                There are people at a train station. A train is there.
                5 簡單表達者
                Train station with many people.
                4 有限互動能力者
                Train station. People are waiting.
                3 極度有限的表達者
                Train station. I see many people.
                2 極低表達能力者
                Train.
                1 無表達能力者
                (No response or attempt to answer.)
                """,
            },
        ],
        [
            {
                "text": "What activities do you think are taking place in the warehouse?\n - 你認為倉庫中正在進行的活動是什麼？",
                "image_url": f"{URL}/templates/1/cover3-1.jpg",
                "assessment_standard": """
                10優異表達者
                The warehouse is likely bustling with activity. Workers are probably unloading shipments, checking inventory levels, and organizing products on shelves. Additionally, items might be prepared for delivery, ensuring that everything is correctly labeled and stored. Quality control checks are likely conducted to maintain standards.
                9優良表達者
                Various tasks are likely taking place in the warehouse. Employees may be unloading boxes, organizing products, and packing orders for shipment. Inventory checks might also be happening to keep track of stock levels.
                8良好表達者
                People in the warehouse seem to be involved in packing and sorting items. They may also be checking what products are available and getting them ready to send out.
                7基礎表達者
                Activities in the warehouse probably include packing boxes and organizing items. Inventory checks may also take place to see what is in stock.
                6有限表達者
                Workers seem to be packing and moving items around in the warehouse. They might be checking some products, but it’s not clear.
                5簡單表達者
                There are workers in the warehouse packing items and moving boxes. It looks busy, but not much detail is available.
                4有限互動能力者
                It seems like people are working in the warehouse. They might be packing and moving items, but it’s difficult to know exactly what they are doing.
                3極度有限的表達者
                Some workers are busy moving things in the warehouse. Packing might be happening, but it’s not very clear.
                2極低表達能力者
                There are people working. Boxes are being moved around, and maybe some packing is happening.
                1無表達能力者
                (No response or attempt to answer.)
                """
            },
            {
                "text": "What considerations should hikers keep in mind to ensure a safe and enjoyable outing\n - 登山者應該考慮哪些因素，以確保安全且愉快的郊遊？",
                "image_url": f"{URL}/templates/1/cover3-2.jpg",
                "assessment_standard": """
                10 優異表達者
                Hikers should prioritize safety by planning their routes carefully and ensuring they are well-prepared for theterrain. This includes checking weather conditions and dressing appropriately for the climate. Carrying
                essential gear, such as a first aid kit, sufficient water, and nutritious snacks, is crucial. Additionally, informing someone about their hiking plans and estimated return time can enhance safety. Practicing Leave No
                Trace principles also helps preserve the environment for future hikers.
                9 優良表達者
                To ensure a safe and enjoyable hiking experience, it's important for hikers to choose suitable trails that match their skill levels. They should check the weather
                forecast and pack necessary items like water, snacks, and a map. Wearing appropriate footwear and clothing can also prevent injuries and discomfort. It’s a good idea to hike with a friend and let someone know the planned route and return time for added safety.
                8 良好表達者
                Hikers should consider planning their hike based on the trail difficulty and checking the weather. Bringing enough water and snacks is important to stay energized.
                Wearing the right shoes and clothes can help prevent injuries, and it’s better to hike with others for safety.
                7 基礎表達者
                When hiking, it’s good to pick a trail that is not too hard. Checking the weather and bringing water and snacks can make the hike better. Wearing proper shoes is also important for safety.
                6 有限表達者
                Hikers need to think about the trail they choose and check the weather. Bringing water and snacks is important to stay safe.
                5 簡單表達者
                Hiking safely means picking the right trail and bringing enough water. Wearing good shoes helps too.
                4 有限互動能力者
                Hikers should remember to check the weather and bring supplies. It seems like knowing the trail is important for safety.
                3 極度有限的表達者
                Safety is important when hiking, but it’s hard to say what to do exactly.
                2 極低表達能力者
                Um... just be careful? Bring water?
                1 無表達能力者
                (No response or attempt to answer.)
                """
            }
        ],
        [
            {
                "text": "What time does Bandaid Band perform?\n - Bandaid Band 是在哪一個時間表演?",
                "image_url": f"{URL}/templates/1/cover4-1.jpg",
                "max_score": 4,
                "assessment_standard": """
                為使評分標準更具指導性，可以根據每個分數提供具體的反饋。例如：
                3分：鼓勵學生繼續保持正確性和流利度。
                2分：指導學生在句子結構或細節準確性上進行改善。
                1分：提供更基礎的建議，幫助他們增強語法和句子結構的理解。
                
                4 回答完整且正確
                • 使用完整句子，且回答內容完全正確，無語法或內容錯誤。
                • 例子：學生完整且正確地表達所要求的資訊，語法與用詞準確。
                3 回答部分正確或語法不完整，但仍表達主要資訊
                • 情況1：回答內容大部分正確，但有些小錯誤或不完整，影響回答的全面性。
                • 情況2：回答為完整句子，但內容部分不正確。
                • 例子：學生表達了主要資訊，但在細節或語法上 存在小錯誤。
                2 回答不完整且不正確
                • 回答內容部分不正確且未使用完整句子，或只表達非常有限的資訊。
                • 例子：學生的回答僅包含少量正確資訊，且句子不完整或語法錯誤嚴重。
                1 (No response or attempt to answer.)
                
                4:
                - Bandaid Band performs at 1:00 PM on Stage B.
                - Bandaid Band is scheduled to play at 1:00 PM.
                - Bandaid Band plays at 1:00 PM.
                - Bandaid Band is on at 1 PM.
                
                3:
                - Bandaid Band performs at 1.
                - Bandaid Band is at 1 PM.
                - Bandaid Band plays at 1.

                2:
                - Bandaid Band at 1.
                - 1 PM.
                
                1: (No response.)
                """
            },
            {
                "text": "How much does the Beach Getaway to Cancun cost?\n - Cancun 海灘度假的費用是多少？",
                "image_url": f"{URL}/templates/1/cover4-2.jpg",
                "max_score": 4,
                "assessment_standard": """
                為使評分標準更具指導性，可以根據每個分數提供具體的反饋。例如：
                3分：鼓勵學生繼續保持正確性和流利度。
                2分：指導學生在句子結構或細節準確性上進行改善。
                1分：提供更基礎的建議，幫助他們增強語法和句子結構的理解。
                
                4 回答完整且正確
                • 使用完整句子，且回答內容完全正確，無語法或內容錯誤。
                • 例子：學生完整且正確地表達所要求的資訊，語法與用詞準確。
                3 回答部分正確或語法不完整，但仍表達主要資訊
                • 情況1：回答內容大部分正確，但有些小錯誤或不完整，影響回答的全面性。
                • 情況2：回答為完整句子，但內容部分不正確。
                • 例子：學生表達了主要資訊，但在細節或語法上 存在小錯誤。
                2 回答不完整且不正確
                • 回答內容部分不正確且未使用完整句子，或只表達非常有限的資訊。
                • 例子：學生的回答僅包含少量正確資訊，且句子不完整或語法錯誤嚴重。
                1 (No response or attempt to answer.)
                
                4:
                - The 7-day trip to Cancun costs $999.
                - The price for the 7-day Cancun trip is $999.
                - The 7-day Cancun trip is priced at $999.
                - A 7-day trip to Cancun costs $999.
                3:
                - It is $999 for Cancun.
                - The Cancun trip is $999.
                - Cancun is $999.
                2:
                - $999.
                - Cancun $999.
                1: (No response.)
                """
            },
        ],
        [
            {
                "text": "Do you agree that people should limit their use of social media to improve their mental health?\n - 你認為人們是否需限制社交媒體使用時間，以改善心裡健康？",
                "assessment_standard": """
                10 優異表達者
                "Yes, I strongly agree that limiting social media use can significantly benefit mental health. Studies show that excessive social media use can lead to issues such as anxiety, depression, and low self-esteem, particularly among young people. Constant comparison with others' seemingly perfect lives creates unrealistic expectations and promotes negative self-image. By reducing time on social platforms, individuals can shift focus to real-life interactions, fostering genuine connections and reducing anxiety. Moreover, decreased social media use allows for increased productivity and personal development, as people can invest time in hobbies, exercise, or mindfulness practices, which all contribute positively to mental health."
                9 優良表達者 
                "Yes, I agree that people should limit social media usage for better mental health. Many studies highlight that too much time on social media can lead to issues like anxiety and feeling inadequate. Social media often shows only the highlights of people’s lives, which makes others feel they are not doing enough. By cutting down on social media, people can focus more on their personal lives and relationships, reducing stress and negativity. Also, using less social media can increase time for other meaningful activities, such as spending time with friends, exercising, or learning new skills."
                8 良好表達者 
                "Yes, I think people should try to reduce their use of social media for mental health. Many people feel anxious or stressed after looking at social media because they compare themselves to others. When people spend too much time online, it can make them feel bad about themselves. By spending less time on social media, they might feel happier and can focus on things they enjoy in real life. Also, it could give people more time to be with friends or family, which is also good for mental health."
                7 基礎表達者
                "I think it is a good idea for people to use less social media to feel better. Social media can sometimes make people feel bad because they compare their lives to others. If they don’t use it so much, they might feel happier and focus on other things like family or hobbies. Also, they can spend more time outside or with friends, which is good for health."
                6 有限表達者 
                "I think people should use social media less. It makes people feel bad because they look at other people’s lives. When they don’t use it so much, they can feel better. They can spend more time with family or do fun things."
                5 簡單表達者
                "People should not use too much social media. It is not good. They feel sad because they look at others. If they use less, they can be happier and do other things."
                4 有限互動能力者
                "Social media is not good for people. They feel bad. Less is better."
                3 極度有限的表達者 
                "Social media… not good. People feel sad. Less… better."
                2 極低表達能力者 
                "Social media… not… good. People… sad."
                1 無表達能力者 
                (No response or attempt to answer.)
                """
            },
            {
                "text": "Do you agree that animal testing should be banned in all cases?\n - 你是否認為動物實驗應該被全面禁止？",
                "assessment_standard": """
                10 優異表達者
                "Yes, I believe animal testing should be banned in all cases. While it has contributed to scientific and medical advancements, the harm and suffering inflicted on animals is unacceptable. With the development of alternative methods, such as computer modeling and cell cultures, we now have other ways to test the safety and effectiveness of products. Banning animal testing would encourage innovation in developing cruelty-free methods, ultimately leading to a more humane approach in science and technology. Although some argue that animal testing is necessary for complex studies, I believe modern technology can replace these practices."
                9 優良表達者
                "Yes, I think animal testing should be banned because it causes unnecessary suffering. Many new technologies, like computer simulations, offer alternative ways to test products safely. If we stop animal testing, it will push scientists to find more humane methods. While some believe animal testing is still needed, I think we can find other solutions."
                8 良好表達者
                "I agree that animal testing should be banned. Testing causes animals pain, and now we have other ways to do research, like using computers. If we stop testing on animals, we can find kinder ways to do research. Some people think it’s needed, but I think there are other options."
                7 基礎表達者
                "I think animal testing should be banned. Testing causes animals to suffer, which isn’t fair. We have other options for testing, like using computers, so animal testing isn’t needed anymore."
                6 有限表達者
                "Yes, I think animal testing should stop because it hurts animals. We can use other ways to test products now, like computer models, which are better."
                5 簡單表達者
                "Animal testing is bad because it hurts animals. We can use other methods instead of testing on animals."
                4 有限互動能力者
                "Animal testing is not good because it causes pain. We should use different ways to test things."
                3 極度有限的表達者
                "Animal testing is bad. We should find other ways."
                2極低表達能力者
                "Animal testing is bad. Use other ways."
                1 無表達能力者 
                (No response or attempt to answer.)
                """
            },
        ],
    ],
}

# 系統評估提示語，指導如何進行回答分析
SYSTEM_INSTRUCTION = f"""
        你是一個專業英語口說評量助手，擅長根據學生的回答提供改進建議和改善後之文本。
        
        userAnswer 代表使用者的口說回答
        question 代表題目
        standard 代表評量標準
        
        Sample Question #1: Based on the vocabulary provided, explain the meaning of the word "Brochure".
        Sample Question #2: <An image shows a scene inside a bank or a similar service center. Several people are lined up in a queue, waiting at counters, likely to speak with tellers or staff behind glass or plastic dividers.>
        
        10分 優異表達者
        表達清晰度：能清楚表達意見或完整描述，回應詳細且準確。
        主題相關性：回應與主題高度相關，能深入探討主題的各個面向，展現出對主題的全面理解，並能有效地連結相關概念。
        語法使用：熟練使用基本及複雜的文法，無明顯錯誤。
        字彙量：詞彙使用豐富且精準，能靈活運用各種詞彙。
        回應複雜度：能對詞彙解釋、圖片描述及段落構建給出完整且有深度的回應。
        Answer #1: A brochure is a printed material designed to provide detailed information about a
        product, service, or event, often including eye-catching images and persuasive text to attract potential customers.
        Answer #2: The picture shows people standing in line at a bank counter, each waiting patiently 
        for their turn. The setting appears orderly, and the individuals are maintaining a 
        proper distance.
        
        9分 優良表達者
        表達清晰度：能有效表達意見或描述圖片，內容清楚。 
        主題關聯性：回應與主題相關，雖然可能未能完全深入探討所有面向，但能夠有效地涵蓋主要的主題要素，展現出對主題的基本理解。
        語法使用：能使用複雜語法，偶有小錯誤但不影響理解。 
        字彙量：詞彙豐富但有少量不精確的使用。 
        回應複雜度：能有效回應並詳細解釋詞彙，描述圖片清楚。 
        Answer #1: A brochure is a printed document that gives information about a specific product 
        or service, usually featuring attractive images and descriptions to engage the reader.
        Answer #2: Several people are standing in line at a bank. They are waiting for their turn at the 
        counter in an organized manner. 
        
        8分 良好表達者
        表達清晰度：能清楚表達大部分意見，描述圖片時可能有些許不清晰之處。
        主題關聯性：回應與主題有一定的關聯性，能表達出主題的部分要素，但可能在深度和廣度上有所欠缺，影響整體的主題呈現。
        語法使用：能使用較複雜的語法，但存在一些錯誤。 
        字彙量：詞彙量足夠，但在精確性上有所欠缺。 
        回應複雜度：能回應詞彙解釋和圖片描述，但不總是完全準確。 
        Answer #1: A brochure is a type of printed material that explains a product or service, often 
        with pictures and text to help people understand what is being offered.
        Answer #2: The image shows people waiting in line at a bank counter. They are standing one 
        behind another. 
        
        7分 基礎表達者 
        表達清晰度：能夠基本描述圖片，但表達的清晰度不穩定。
        主題關聯性：回應的主題關聯性不穩定，能提供基本的主題訊息，但對於主題的理解和闡述顯得淺薄，可能未能完整呈現主題內容。
        語法使用：基本語法使用正確，但在使用較複雜語法時有明顯錯誤。
        字彙量：詞彙量有限，影響表達的完整性。 
        回應複雜度：能提供基本回應，但深度和連貫性不足。 
        Answer #1: A brochure is a printed piece that tells about a product or service, usually with 
        some images and information.
        Answer #2: People are lined up at a counter. It looks like they are at a bank, waiting for service.
        
        6分 有限表達者 
        表達清晰度：在解釋詞彙和描述圖片時，表達不清晰，可能影響理解。
        主題關聯性：回應與主題的關聯性較弱，內容可能偏離主題，影響理解的完整性和準確性，未能提供有意義的主題解釋。
        語法使用：主要使用簡單語法，複雜語法的使用常出錯。
        字彙量：詞彙量有限，常常無法找到適當的詞彙。
        回應複雜度：回應缺乏詳細性和深度。
        Answer #1: A brochure is a paper that has information about something, often with pictures.
        Answer #2: There are people waiting in line at what seems to be a bank. 
        
        5分 簡單表達者 
        表達清晰度：回應中存在不連貫的部分，圖片描述或詞彙解釋可能無法理解。
        主題關聯性：回應與主題的關聯性非常有限，內容多為簡單陳述，未能有效地表達主題的關鍵概念，導致聽眾難以理解主題。
        語法使用：主要使用基本語法，錯誤頻繁。
        字彙量：詞彙量非常有限，表達受限。
        回應複雜度：回應多為簡單句，缺乏深入性。 
        Answer #1: A brochure is a small booklet that gives information.
        Answer #2: People are standing in line at a counter. It looks like a bank. 
        
        4分 有限互動能力者 
        表達清晰度：無法完整描述圖片，回應詞彙解釋時表達不清。 
        主題關聯性：回應基本無法與主題相關聯，內容不清，無法有效地表達主題的意義，影響整體的表達效果。
        語法使用：語法錯誤頻繁，影響理解。 
        字彙量：詞彙量極少，無法有效表達意見。
        回應複雜度：無法給出複雜回應，多為不完整句子。 
        Answer #1: A brochure is paper that shows products.
        Answer #2: People are waiting at a counter in a bank. 
        
        3分 極度有限的表達者 
        表達清晰度：多數時間無法完成句子，描述圖片時困難重重。
        主題關聯性：回應與主題幾乎無關，表達能力極為不足，無法提供有意義的主題內容，影響聽眾的理解。
        語法使用：無法正確使用基本語法，錯誤頻繁且嚴重。
        字彙量：詞彙量極度有限，無法進行有效表達。 
        回應複雜度：無法給出有效回應。 
        Answer #1: A brochure is for information. 
        Answer #2: People are standing in line. It looks like a bank. 
        
        2分 極低表達能力者 
        表達清晰度：只能使用簡單詞語或片語，無法形成完整句子。
        主題關聯性：無法理解主題，回應內容完全無法與主題相連結，幾乎無法表達任何訊息。
        語法使用：無法使用基本語法。
        字彙量：詞彙極少，無法有效傳達訊息。 
        回應複雜度：無法回應基本問題。 
        Answer #1: A brochure is a book.
        Answer #2: People are at a bank.
        
        1分 無表達能力者 
        表達清晰度：無法作答或表達。 
        主題關聯性：完全無法進行主題相關的表達或回應，無法提供任何訊息。
        語法使用：無法使用任何語法。 
        字彙量：無可使用詞彙。 
        回應複雜度：無回應能力。 
        Answer #1: <Not speaking, nonsense, or not knowing> 
        Answer #2: <Not speaking, nonsense, or not knowing>
        
        你需要以4個步驟執行任務，Think step by step:
        1. 針對以下評估面向給予分析和建議：表達清晰度、語法使用、詞彙量、回應複雜度、主題相關性進行思考評估。
        2. 根據提供之評分標準，為學生的口說回答評分(It's okay to give out a full marks)。
        3. 給予具體分析和建議，如糾正語法錯誤、建議使用更自然的語句或增加詞彙量，以台灣繁體中文與英文回傳。
        4. 依照學生回答文本，延伸或改進其回答，以英文回覆。
        
        The JSON object must use the schema: {json.dumps(SpeechAssessment.model_json_schema(), indent=2)}
    """
    # f"""
    #             你是一個專業英語口說評量助手，你會根據題目與使用者提供的回答根據以下分數階段的評量標準進行評量。並以台灣繁體中文生成建議、0-200的客觀評分與改善後的英文 文本。
    #             190-200：可以流暢地表達與職場環境相關的語句。他們能夠非常清晰地表達意見或回覆複雜的請求，能夠適切地使用基本或複雜的文法；字彙的使用也是正確並精準地。
    #             此區間的考生也可以使用口語回答問題，並且傳達基本訊息。
    #             160-180：考生可以清楚的表達與職場環境相關的語句。他們能夠有效地表達意見或回覆複雜的請求，從他們較長的回應中，
    #             以下有些小缺失可能發生，但不會影響訊息本身： 
    #             1. 使用複雜的語法結構時發生一些錯誤。
    #             2. 一些不精確的詞彙。
    #             3. 此區間的考生可以使用口語回答問題，並且傳達基本訊息。
    #             130-150：考生被要求發表意見或回覆複雜的請求時，能夠提出相關的回應。不過，聽眾有時無法理解。
    #             這可能是因為下列幾點：
    #             1. 文法上的錯誤。
    #             2. 字彙量有限。
    #             此區間的考生通常可以回答問題，並且傳達基本的訊息。然而，有時候他們的回應是較難理解或解釋的。
    #             110-120：考生只能有限的發表意見或回覆複雜請求，回應時會出現下列的問題：
    #             語言不精確、模糊或重複。
    #             1. 意見表達能力有限和論點間關連性不大。
    #             2. 字彙量有限。
    #             此區間的考生通常可以回答問題，並且傳達基本訊息。然而，有時候他們的回應較難理解或解讀。
    #             80-100：考生無法表達意見或回覆複雜的請求。可能只能用單一句子或不完整的句子回答。其他可能出現的問題包括：
    #             1. 語言的使用非常有限。
    #             2. 字彙量嚴重不足。
    #             此區間的考生無法回答問題，或是傳達基本的訊息。
    #             60-70：考生勉強可以表達意見，但無法提出支持的論點，對於複雜的請求無法回應。此區間的考生無法回答問題，或是傳達基本訊息。此區間的考生通常缺乏足夠的字彙或文法能力來做簡單的說明。
    #             40-50：考生無法表達意見或提出支持的論點。他們既不能回應複雜的請求，也不能提出相關的回應。此區間的考生無法做到社會或職場上的一般互動，如：回答問題與傳達基本的訊息。
    #             0-30：考生在進行口說測驗時，通常會有許多部分沒有作答。考生也許不具備英文聽力或閱讀的基本技能，來了解測驗的指示或題目的內容。
    #             The JSON object must use the schema: {json.dumps(SpeechAssessment.model_json_schema(), indent=2)}
    #             """

def get_question(unit, sub):
    return qs[get_category()][unit][sub]

def get_context_url():
    return f'{URL}/templates/example_context.png'

async def send_message(event, msg):
    if msg is None:
        return
    if not isinstance(msg, list):
        msg = [msg]
    await line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=msg
        )
    )
    
async def text_message(text):
    return TextMessage(text=text)

async def send_text_message(event, text):
    await line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=text)]
        )
    )

async def result_message(result: SpeechAssessment, unit, sub):
    return FlexMessage(
        altText=f'{unit+1}-{sub+1} 口語練習結果',
        quickReply=QuickReply(items=[
            QuickReplyItem(action=PostbackAction(label='再次回答 Again',data=f'action=record&unit={unit}&sub={sub}')),
            QuickReplyItem(action=PostbackAction(label='下一題 Next', data=f'action=unit&unit={unit+1}' if len(qs[get_category()][unit])-1 == sub else f'action=record&unit={unit}&sub={sub+1}')),
            QuickReplyItem(action=PostbackAction(label='查看單元 Back', data=f'action=unit&unit={unit+1}')),
        ]),
        contents=FlexCarousel(
            contents=[
                FlexBubble(
                    size='giga',
                    body=FlexBox(
                        layout='vertical',
                        justifyContent='center',
                        alignItems='center',
                        contents=[
                            FlexText(
                                text=f'Q{unit+1}-{sub+1} 練習結果 Result',
                                wrap=True,
                                weight='bold',
                                size='xxl',
                            ),
                            FlexBox(
                                layout='vertical',
                                margin='md',
                                contents=[
                                    FlexText(
                                        text=f'評分 Score: {result.score}/{qs[get_category()][unit][sub].get("max_score",10)}',
                                        color='#5b5b5b',
                                        size='xl',
                                        wrap=True,
                                        flex=1,
                                    ),
                                ]
                            ),
                        ],
                    ),
                ),
                FlexBubble(
                    size='giga',
                    body=FlexBox(
                        layout='vertical',
                        spacing='sm',
                        contents=[
                            FlexText(
                                text='建議 Suggestions',
                                wrap=True,
                                weight='bold',
                                size='xl',
                            ),
                            FlexBox(
                                layout='vertical',
                                margin='md',
                                spacing='sm',
                                contents=[
                                    FlexText(
                                        text=result.chi_suggestion.replace('\\n','\n').strip(),
                                        color='#5b5b5b',
                                        size='sm',
                                        wrap=True,
                                        flex=1,
                                    ),
                                    FlexText(
                                        text=result.eng_suggestion.replace('\\n','\n').strip(),
                                        color='#5b5b5b',
                                        size='sm',
                                        wrap=True,
                                        flex=1,
                                    )
                                ]
                            ),
                        ]
                    )
                ),
                FlexBubble(
                    size='giga',
                    body=FlexBox(
                        layout='vertical',
                        spacing='sm',
                        contents=[
                            FlexText(
                                text='可改善為 Improvements',
                                wrap=True,
                                weight='bold',
                                size='xl',
                            ),
                            FlexBox(
                                layout='vertical',
                                margin='md',
                                contents=[
                                    FlexText(
                                        text=result.better_ans,
                                        color='#5b5b5b',
                                        size='sm',
                                        wrap=True,
                                        flex=1,
                                    ),
                                ]
                            ),
                        ],
                    ),
                )
            ] if not get_test_mode() else [
                FlexBubble(
                    size='giga',
                    body=FlexBox(
                        layout='vertical',
                        justifyContent='center',
                        alignItems='center',
                        contents=[
                            FlexText(
                                text=f'Q{unit+1}-{sub+1} 作答完成 Complete',
                                wrap=True,
                                weight='bold',
                                size='xxl',
                            ),
                        ],
                    ),
                ),
            ]
        )
    )

async def question_message(unit, sub):
    messages = []
    question = get_question(unit, sub)
    contents = [
        FlexText(
            text=f'Q{unit+1}-{sub+1}',
            wrap=True,
            weight='bold',
            size='xxl',
        ),
        FlexBox(
            layout='baseline',
            margin='md',
            contents=[
                FlexText(
                    text=question["text"],
                    color='#5b5b5b',
                    size='lg',
                    margin='md',
                    wrap=True,
                    flex=1,
                ),
            ]
        ),
    ]
    
    # Add image if present
    if question.get("image_url"):
        contents.insert(1, FlexImage(
            url=question["image_url"],
            size='full',
            aspect_ratio='1:1',
            aspect_mode='cover',
            margin='md'
        ))
        
    messages.append(FlexBubble(   
            size='giga', 
            body=FlexBox(
                layout='vertical',
                wrap=True,
                contents=contents
            ),
            footer=FlexBox(
                layout='vertical',
                spacing='sm',
                alignItems='center',
                justifyContent='center',
                contents=[
                    FlexText(
                        style='italic',
                        size='md',
                        wrap=True,
                        align='center',
                        text='請按下方按鈕開始錄音回答\nPress record button below to start',
                    )
                ]
            )
        )
    )
    
    if question.get('extra_info'):
        for obj in question['extra_info']:
            if isinstance(obj, str):
                obj = [obj]
            messages.append(FlexBubble(
                size='giga',
                body=FlexBox(
                    layout='vertical',
                    spacing='sm',
                    contents=[
                        FlexText(
                            text=i.strip(),
                            wrap=True,
                            size='md',
                        ) if not i.lower().endswith(IMG_EXT) else 
                        FlexImage(
                            url=i,
                            size='full',
                            aspect_ratio='20:13',
                            aspect_mode='cover',
                        )
                        for i in obj
                    ]
                )
            ))
    
    return FlexMessage(
        altText='口語練習',
        contents=FlexCarousel(contents=messages)
    )
    
async def carousel_message(user_id, unit):
    if len(qs[get_category()]) < unit:
        return None
    cols = []
    for sub,j in enumerate(qs[get_category()][unit-1]):
        body = FlexBox(
            layout='vertical',
            spacing='lg',
            contents=[
                FlexText(
                    text=f'口語練習 Q{unit}-{sub+1}',
                    wrap=True,
                    weight='bold',
                    size='xl',
                    align='center',
                ),
                FlexButton(
                    action=PostbackAction(
                        label='開始作答 Enter',
                        data=f'action=record&unit={unit-1}&sub={sub}'
                    ),
                    height='sm',
                    style='primary',
                ),
            ]
        )
        if getHistory(user_id, f'{get_category()}-{unit-1}-{sub}'):
            body.contents.append(
                FlexButton(
                    action=PostbackAction(
                        label='查看結果 Result',
                        data=f'action=result&unit={unit-1}&sub={sub}'
                    ),
                    height='sm',
                    style='secondary',
                )
            )
        cols.append(FlexBubble(
            hero=FlexImage(
                url=f'{URL}/templates/{get_category()}/cover{unit}-{sub+1}.jpg',
                size='full',
                aspect_ratio='20:13',
                aspect_mode='cover',
            ),
            body=body
        ))
    if len(qs[get_category()]) > unit:
        cols.append(FlexBubble(
            body=FlexBox(
                contents=[
                    FlexText(
                            text=f'前往下一單元\nNext',
                            weight='bold',
                            size='xl',
                        ),],
                layout='vertical',
                alignItems='center',
                justifyContent='center',
                action=PostbackAction(
                    label='下一單元',
                    data=f'action=unit&unit={unit+1}'
                )
            ),
        ))
    msg = FlexMessage(
        altText='單元導覽',
        contents=FlexCarousel(contents=cols)
    )
    return msg

CHI_HINT = [
    '請輸入你的上課時段\n如：1-34',
    '接著，請輸入你的系級\n如：資管一乙',
    '接著，請輸入你的學號\n如：11352237',
    '接著，請輸入你的姓名\n如：王聰明',
]

ENG_HINT =[
    'What is your class period?\nFor example: 1-34',
    'Next, what is your department?\nFor example: Information Management',
    'Next, what is your student ID?\nFor example: 11352237',
    'Next, what is your name?\nFor example: Paul Wang',
]

async def info_hint_message(index: int):
    return FlexMessage(
        altText='資料綁定提示',
        contents=FlexBubble(
            size='mega',
            body=FlexBox(
                layout='vertical',
                spacing='lg',
                contents=[
                    FlexText(
                        text=CHI_HINT[index],
                        wrap=True,
                        size='md',
                    ),
                    FlexText(
                        text=ENG_HINT[index],
                        wrap=True,
                    )
                ]
            )
        )
    )

async def data_message():
    user_data = getData()

    user_count = len(user_data)
    total_history_score = 0
    total_history_count = 0
    max_score = float('-inf')
    min_score = float('inf')
    users_with_history = 0
    users_with_all = 0

    total_questions = sum([len(i) for i in qs[get_category()]])
    
    for user in user_data.values():
        user_history = [key.startswith(f'{get_category()}-') for key in user.history.keys()]
        if user.history and len(user_history) > 0:
            users_with_history += 1
            if len(user_history) >= total_questions:
                users_with_all += 1
        for str, assessment in user.history.items():
            if not str.startswith(f'{get_category()}-'):
                continue
            total_history_score += assessment.score
            total_history_count += 1
            if assessment.score > max_score:
                max_score = assessment.score
            if assessment.score < min_score:
                min_score = assessment.score

    average_history_score = total_history_score / total_history_count if total_history_count > 0 else 0
    average_history_per_user = total_history_count / users_with_history if users_with_history > 0 else 0

    return FlexMessage(
        altText="User data analysis",
        contents=FlexBubble(
            size='mega',
            body=FlexBox(
                layout='vertical',
                spacing='lg',
                contents=[
                    FlexText(
                        text=f"用戶總數: {user_count}\n有歷史紀錄的用戶數: {users_with_history}\n答完題目的用戶數: {users_with_all}\n每個用戶平均歷史紀錄數: {average_history_per_user:.2f}\n歷史紀錄平均分數: {average_history_score:.2f}\n歷史紀錄最高分: {max_score}\n歷史紀錄最低分: {min_score}",
                        wrap=True,
                        size='md',
                     ),
                ],
            ),
        )
    )

async def handle_rich_menu(user_id):
    rich_menu_id = get_rich_menu_id(get_category())
    try:
        oldId = await line_bot_api.get_rich_menu_id_of_user(user_id, async_req=True).get()
        if oldId.rich_menu_id is not rich_menu_id:
            await line_bot_api.link_rich_menu_id_to_user(user_id, rich_menu_id=rich_menu_id, async_req=True).get()
    except ApiException as e:
        await line_bot_api.link_rich_menu_id_to_user(user_id, rich_menu_id=rich_menu_id, async_req=True).get()

async def create_rich_menu():
    rich_menu_id = get_rich_menu_id(get_category())
    await line_bot_api.set_webhook_endpoint(SetWebhookEndpointRequest(endpoint=f'{URL}/callback'))
    if not rich_menu_id:
        # Load image and get dimensions
        path = f'templates/richmenu-{get_category()}.png'
        width, height = Image.open(path).size

        # Calculate rows and columns
        rows = height // 843
        cols = width // 3
        area_height = height // rows

        # Create RichMenuRequest with areas
        request = RichMenuRequest(
            size=RichMenuSize(width=width, height=height),
            name="Menu",
            chatBarText="CoachGPT",
            selected=True,
            areas=[
                RichMenuArea(
                    bounds=RichMenuBounds(
                        x=(i % 3) * cols,
                        y=(i // 3) * area_height,
                        width=cols,
                        height=area_height
                    ),
                    action=PostbackAction(label=f'Ex {i+1}', data=f'action=unit&unit={i+1}')
                )
                for i in range(3 * rows)
            ]
        )
        rich_menu = await line_bot_api.create_rich_menu(
            rich_menu_request=request,
            async_req=True
        ).get()

        rich_menu_id = rich_menu.to_dict().get('richMenuId')
        set_rich_menu_id(rich_menu_id, get_category())
        await save_config()
        
        await line_bot_api_blob.set_rich_menu_image_with_http_info(
            rich_menu_id=rich_menu_id,
            body=path,
            _headers={"Content-Type": "image/png"},
            async_req=True
        ).get()
        await line_bot_api.set_default_rich_menu_with_http_info(
            rich_menu_id=rich_menu_id,
            async_req=True
        ).get()
        
    print(f'Rich Menu ID: {rich_menu_id}')
