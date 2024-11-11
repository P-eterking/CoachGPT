from typing import Annotated
from config import line_bot_api, line_bot_api_blob, DOMAIN
from linebot.v3.messaging import (
    ReplyMessageRequest, TextMessage, PostbackAction, QuickReply,
    QuickReplyItem, RichMenuRequest, RichMenuSize, RichMenuArea,
    RichMenuBounds, FlexMessage, FlexCarousel, FlexBubble, FlexImage,
    FlexText, FlexBox, FlexButton
)
from linebot.v3.messaging.exceptions import ApiException
from pydantic import BaseModel
import json

from utils.file_utils import get_test_mode

# 設定主網址和分類變數
url  = f'https://{DOMAIN}'
category = 1

# 定義問題集合
qs = {
    0:[
        [
            {
                "text": "**What does 'inexpensive' mean, and can you name something that is inexpensive?**\n - 什麼是「便宜」的意思？你能舉出一個「便宜」的例子嗎？",
            },
            {
                "text": "**How would you describe 'portable'? Mention a portable item you use.**\n - 「便攜的」應該怎麼解釋？提到一個你使用「便攜的」物品。",
            },
            {
                "text": "**What is the role of 'management' in a company?**\n - 在公司中，「管理」有什麼作用？",
            },
            {
                "text": "**Define 'manual' and give an example of a manual task.**\n - 定義「手動」並給出一個關於「手動」任務的例子。",
            },
            {
                "text": "**Can you make a sentence using 'export' and 'recently'?**\n - 你能使用「出口」和「最近」造一個句子嗎？",
            },
            {
                "text": "**Describe a situation where you might need to 'replace' something because it is 'inexpensive'.**\n - 描述一個你可能需要因為物品是「便宜」而「取代」它的情境。",
            },
            {
                "text": "**How would you tell someone to 'decrease' the volume using polite language?**\n - 你會如何用禮貌的語言告訴某人「減少」音量？",
            },
            {
                "text": "**Write a sentence where you explain to a friend why something is 'comfortable'.**\n - 寫一個句子解釋給朋友聽為什麼某物是「舒服的」。",
            }
        ],
        [
            {
                "text": "**Meet the Deadline:**\n- Can you describe a time when you had to meet a tight deadline?\n- 你能描述一次你必須在截止日期前完成任務的情況嗎？",
                "image_url": None
            },
            {
                "text": "**Apply for the Job:**\n- What kind of job do you want to apply for?\n- 你想申請什麼樣的工作？",
                "image_url": None
            },
            {
                "text": "**Keep in Touch with Someone:**\n- Talk about a friend or family member you try to keep in touch with regularly.\n- 談談你努力與朋友或家人保持聯繫的情況。",
                "image_url": None
            },
            {
                "text": "**Offer a Discount:**\n- Please create a situation where you purchased an item because it was discounted.\n- 請創造一個你因為商品打折而購買的情況。",
                "image_url": None
            },
            {
                "text": "**Register In:**\n- Pretend you are a student, use 'register in' to make a sentence.\n- 假設你是一名學生，用“註冊”一詞造一個句子。",
                "image_url": None
            },
            {
                "text": "**Make an Appointment:**\n- Can you recall a time when you had to make an appointment for an important meeting or event?\n- 你能回憶起你曾經為一次重要的會議或活動預約的時候嗎？",
                "image_url": None
            },
            {
                "text": "**Remain a Concern:**\n- What things make you remain a concern?\n- 有什麼事情讓你一直擔心嗎？",
                "image_url": None
            },
            {
                "text": "**Book a Ticket:**\n- Describe a situation in which you would need to book a ticket by yourself.\n- 描述您需要自己訂票的情況。",
                "image_url": None
            }
        ],
        [
            {
                "text": "**Beginning**: Introduce the main character and setting.\nA hare was making fun of a tortoise for moving so slowly. The tortoise got tired of the hare making fun of how slow he was. So, he asked the hare to have a race.\n**開始**：介紹主要角色和場景。\n一隻野兔正在嘲笑一隻行動緩慢的烏龜。烏龜厭倦了野兔嘲笑牠動作慢的樣子。於是牠要求野兔和他進行一場比賽。",
                "image_url": None
            },
            {
                "text": "**Then**: Introduce obstacles and challenges main character encounters.\nWhen the race started, the hare bounded off in front, making good progress. He was so far ahead of the tortoise that he decided he could afford to stop and have a rest.\n**然後**：介紹主要角色遇到的障礙和挑戰。\n比賽一開始，野兔就飛奔而出，並且進展迅速。遠遠地把烏龜甩在後面，牠覺得自己可以停下來休息一下。",
                "image_url": None
            },
            {
                "text": "**After**: Reach the climax or turning point of the story, where the main character confronts the central conflict head-on.\nHowever, the hare fell fast asleep, and as he lay sleeping, the tortoise continued to plod along at his slow pace. In time, he reached the finish-line and won the race.\n**之後**：到達故事的高潮或轉折點，主角正面對抗主要衝突。\n然而，野兔很快就睡著了，當牠在睡覺時，烏龜以緩慢的步伐繼續向前爬行。最終，烏龜到達了終點線，贏得了比賽。",
                "image_url": None
            },
            {
                "text": "**Ending**: Resolve the conflict and provide closure for the story. Show how the main character has changed. \nWhen the hare woke up, he was annoyed at himself for falling asleep. So he ran off towards the finish-line as fast as his legs would carry him, but it was too late, as the tortoise had already won.\n**結尾**：解決衝突並為故事提供結局。展示主角的變化。\n當野兔醒來時，他對自己睡著了感到懊惱。於是牠全力奔向終點線，但為時已晚，烏龜已經贏得了比賽。",
                "image_url": None
            }
        ]
    ],
    1: [
        [
            {
                "text": "How would you describe 'brochure'? How does it works?\n - 「宣傳冊」應該怎麼解釋？它是如何運作的？",
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
                "text": "Describe the picture in as much detail as you can\n根據螢幕上的照片，詳細描述其中出現的人物、場景與所發生的事，細節越詳細越好。",
                "image_url": f"{url}/templates/1/cover2-1.jpg",
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
                "text": "Describe the picture in as much detail as you can\n根據螢幕上的照片，詳細描述其中出現的人物、場景與所發生的事，細節越詳細越好。",
                "image_url": f"{url}/templates/1/cover2-2.jpg",
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
                "image_url": f"{url}/templates/1/cover3-1.jpg",
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
                "text": "How can efficient logistics management improve a company's supply chain?\n - 有效的物流管理如何改善公司的供應鏈？",
                "image_url": f"{url}/templates/1/cover3-1.jpg",
                "assessment_standard": """
                10優異表達者
                Efficient logistics management plays a crucial role in optimizing a company's supply chain. By streamlining processes like inventory management and transportation, companies can reduce costs and improve delivery times. This efficiency not only enhances customer satisfaction but also helps the company respond quickly to market changes and demands, ultimately leading to increased competitiveness.
                9優良表達者
                Good logistics management can significantly enhance a company’s supply chain. When processes are organized efficiently, it reduces delays and lowers operational costs. This means products can be delivered faster and more reliably, which is important for keeping customers happy and maintaining a good reputation.
                8良好表達者
                Efficient logistics helps companies manage their supply chains better. For example, if inventory levels are tracked accurately, it can prevent overstocking or stockouts, ensuring that products are available when needed. This can lead to smoother operations and satisfied customers.
                7基礎表達者 
                Managing logistics well can improve the supply chain by making sure that products are delivered on time. When things are organized, it helps reduce costs and avoid delays, which is important for business success.
                6有限表達者
                Good logistics management can help a company by making sure things are delivered faster. It might also save money, but it’s not clear how much impact it has overall.
                5簡單表達者
                Logistics management helps companies deliver products on time. If it’s organized well, it can save money and time.
                4有限互動能力者
                Efficient logistics seems to help with delivery times. It probably makes things easier for companies, but it’s not entirely clear how it works.
                3極度有限的表達者
                Logistics helps in some way, but it’s hard to say how exactly. It might make deliveries better.
                2極低表達能力者
                Um... logistics helps? Deliveries... maybe faster?
                1無表達能力者
                (No response or attempt to answer.)
                """
            },
            {
                "text": "What safety precautions should be considered in a warehouse setting?\n - 在倉庫環境中應考慮哪些安全預防措施？",
                "image_url": f"{url}/templates/1/cover3-1.jpg",
                "assessment_standard": """
                10優異表達者
                Safety precautions in a warehouse are critical for protecting workers and maintaining a safe environment. Comprehensive training on equipment operation, especially for machinery like forklifts, is essential. Regular safety audits should be conducted to identify potential hazards. Additionally, proper labeling of hazardous materials and ensuring that personal protective equipment, such as gloves, helmets, and safety shoes, is always worn are crucial steps to prevent accidents and injuries.
                9優良表達者
                In a warehouse, safety is very important. Workers should receive thorough training on how to operate equipment safely. Regular inspections for hazards, such as spills or blocked pathways, can help prevent accidents. It's also vital for employees to wear appropriate personal protective equipment, like hard hats and safety glasses, to reduce the risk of injury.
                8良好表達者
                Important safety precautions include training workers on the proper use of machinery and following safety guidelines. Regular checks for potential hazards, like wet floors or improperly stored items, can help avoid accidents. Wearing safety gear, such as gloves and helmets, is also necessary to protect workers.
                7基礎表達者
                Safety is important in a warehouse setting. Workers should be trained to use machines correctly, and the area should be kept clean to prevent accidents. Wearing protective gear, such as gloves and hard hats, is necessary to ensure safety.
                6有限表達者
                Safety rules are essential in a warehouse. Workers need training on how to use equipment properly, and they should pay attention to their surroundings. Keeping the area tidy and using safety gear can help prevent injuries.
                5簡單表達者
                Workers should be careful in a warehouse. They need to learn how to use tools safely and keep the area organized to avoid accidents. Using safety gear is also important.
                4有限互動能力者
                Safety in the warehouse is important. Training might help workers know how to avoid accidents, and cleaning up seems like a good idea to keep things safe.
                3極度有限的表達者
                Safety matters, but it's hard to explain. It seems like training and wearing protective gear are important.
                2極低表達能力者
                Um... being careful is good? Using safety gear might help.
                1無表達能力者
                (No response or attempt to answer.)
                """
            },
            {
                "text": "What emotions or thoughts might visitors experience while viewing the artwork?\n - 參觀者在觀看藝術作品時可能會經歷哪些情感或想法？",
                "image_url": f"{url}/templates/1/cover3-2.jpg",
                "assessment_standard": """
                10優異表達者
                Visitors in the gallery may experience a wide range of emotions, such as awe, inspiration, and nostalgia. Engaging with the artwork can evoke deep reflections on personal experiences or cultural themes. The use of color, composition, and subject matter can provoke meaningful discussions and inspire visitors to think critically about the artwork’s message and its relevance to society.
                9優良表達者
                While viewing the artwork, visitors are likely to feel inspired and moved. The different pieces might spark thoughts about personal memories or evoke emotions related to the themes depicted in the art. Engaging with the artwork can encourage visitors to reflect on their own experiences and feelings.
                8良好表達者
                People in the gallery might feel a sense of wonder or curiosity when looking at the artwork. Some pieces could remind them of personal experiences or make them think about different ideas and emotions.
                7 基礎表達者
                Visitors probably experience various emotions while looking at the art. They might feel happy or thoughtful, depending on what the artwork represents. Some pieces may resonate with their own life experiences.
                6 有限表達者
                People might feel different things while viewing the art. Some might feel happy, while others could be confused or unsure about what they see.
                5 簡單表達者
                Visitors see art and might feel something like happiness or confusion. It depends on the piece they are looking at.
                4 有限互動能力者
                There are likely different feelings when people look at the art. Some might like it, but others might not understand it well.
                3 極度有限的表達者
                People are looking at art and might feel something, but it’s hard to say what exactly.
                2 極低表達能力者
                Um... people look at art. They might feel something, maybe good?
                1 無表達能力者
                (No response or attempt to answer.)
                """
            },
            {
                "text": "How does the layout of the gallery enhance the visitor experience?\n - 畫廊的佈局如何提升參觀者的體驗？",
                "image_url": f"{url}/templates/1/cover3-2.jpg",
                "assessment_standard": """
                10 優異表達者
                The layout of the gallery plays a crucial role in enhancing the visitor experience by creating a logical flow that guides viewers through the space. Well-planned pathways allow visitors to engage with each piece of artwork without feeling rushed. Open spaces and strategic lighting draw attention to specific pieces, making it easier for visitors to appreciate details and context. Additionally, thematic groupings of artworks can provoke deeper connections and reflections among the visitors.
                9 優良表達者
                A thoughtfully designed layout significantly enhances the visitor experience. By organizing artworks in a way that flows naturally, visitors can move comfortably from one piece to another. Clear sightlines and appropriate lighting help highlight important works, allowing for better appreciation. The grouping of related artworks can also encourage visitors to draw connections and think more critically about the themes presented.
                8 良好表達者
                The gallery layout helps visitors navigate the space more easily. A good arrangement means people can see the artworks clearly without obstruction. Proper lighting and spacing allow viewers to appreciate the details of each piece, making the experience more enjoyable.
                7 基礎表達者
                The layout of the gallery is important because it helps people find their way around. When the artworks are spaced out well, it makes it easier for visitors to see and enjoy each piece.
                6 有限表達者
                The gallery layout probably helps visitors see the art better. If everything is organized, it should make it easier to walk around and look at the pieces.
                5 簡單表達者
                A good layout in the gallery helps people look at the art. If things are organized, it makes it easier to walk around.
                4 有限互動能力者
                The layout seems to matter because it helps people find their way. It could make looking at art a bit easier, but it’s hard to say how.
                3 極度有限的表達者
                Layout helps, but not sure how exactly. It seems like it makes things easier to see.
                2 極低表達能力者
                Um... the layout is good? Maybe it helps people see art?
                1 無表達能力者
                (No response or attempt to answer.)
                """
            },
            {
                "text": "In what ways can art galleries contribute to cultural awareness in society?\n - 藝術畫廊可以通過哪些方式促進社會的文化意識？",
                "image_url": f"{url}/templates/1/cover3-2.jpg",
                "assessment_standard": """
                10 優異表達者
                Art galleries play a vital role in promoting cultural awareness by showcasing diverse artists and their work. They provide a platform for underrepresented voices and perspectives, fostering dialogue about social issues and cultural identity. Through exhibitions and educational programs, galleries can encourage visitors to explore different cultures, challenge stereotypes, and appreciate the richness of global art. This engagement not only broadens understanding but also cultivates empathy among individuals from varied backgrounds.
                9 優良表達者
                Galleries contribute to cultural awareness by displaying art from different cultures and communities. They can host exhibitions that highlight important social issues and encourage discussions among visitors. Educational programs and guided tours can also help people learn about the cultural significance of the artworks, deepening their understanding of various traditions and histories.
                8 良好表達者
                Art galleries help raise cultural awareness by showing a variety of artworks from different cultures. They can educate visitors about the history and significance of the art, which helps people understand and appreciate different perspectives.
                7 基礎表達者
                Art galleries play a role in showing art from different cultures. This helps visitors learn about other people's backgrounds and traditions.
                6 有限表達者
                Galleries show art that can help people learn about different cultures. It might make them think more about other ways of life.
                5 簡單表達者
                Art galleries display different types of art that can help people know about other cultures. This might make them more interested in learning about those cultures.
                4 有限互動能力者
                Art galleries seem to help people understand other cultures, but it’s not entirely clear how that happens. Seeing different art might give some ideas about other ways of life.
                3 極度有限的表達者
                Galleries show art, and that could help people learn about different cultures, but the details are unclear.
                2 極低表達能力者
                Um... galleries show art? Maybe it helps with cultures?
                1 無表達能力者
                (No response or attempt to answer.)
                """
            },
        ],
        # [
        #     {
        #         "text": "**What time does Band A perform?**\n - 哪一個時間段，Band A 會進行活動？",
        #         "image_url": f"{url}/templates/1/cover4-1.jpg"
        #     },
        #     {
        #         "text": "**How much does the Beach Getaway to Cancun cost?**\n - Cancun 海灘度假遊戲費用多少？",
        #         "image_url": f"{url}/templates/1/cover4-2.jpg"
        #     },
        # ],
        [
            {
                "text": "**Do you agree that people should limit their use of social media to improve their mental health?**\n - 你認為社交媒體應該被限制在改善心理健康的使用？",
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
                "text": "**Do you agree that animal testing should be banned in all cases?**\n - 你是否認為動物檢測應該被全面禁止？",
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
    ]
}

# 定義評估模型的格式
class SpeechAssessment(BaseModel):
    chi_suggestion: Annotated[str, 'Traditional Chinese suggestion']  # 中文建議
    eng_suggestion: Annotated[str, 'English suggestion']  # 英文建議
    score: Annotated[int, '評量分數']  # 分數
    transcript: Annotated[str, '轉錄後文本']  # 使用者回答的轉錄文本
    better_ans: Annotated[str, '改善後文本']  # 改進的回覆範例
    
    def to_dict(self) -> dict:
        return self.model_dump()

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

rich_menu_id : str = None

def get_question(unit, sub):
    return qs[category][unit][sub]

def get_context_url():
    return f'{url}/templates/example_context.png'

async def send_message(event, msg):
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
            QuickReplyItem(action=PostbackAction(label='下一題 Next', data=f'action=unit&unit={unit+1}' if len(qs[category][unit])-1 == sub else f'action=record&unit={unit}&sub={sub+1}')),
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
                                        text=f'評分 Score: {result.score}/{qs[category][unit][sub].get("max_score",10)}',
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

    return FlexMessage(
        altText='口語練習',
        contents=FlexBubble(   
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
    
async def carousel_message(unit):
    cols = []
    for sub,j in enumerate(qs[category][unit-1]):
        cols.append(FlexBubble(
            hero=FlexImage(
                url=f'{url}/templates/{category}/cover{unit}-{sub+1}.jpg',
                size='full',
                aspect_ratio='20:13',
                aspect_mode='cover',
            ),
            body=FlexBox(
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
                    )
                ]
            )
        ))
    if len(qs[category]) > unit:
        cols.append(FlexBubble(
            body=FlexBox(
                contents=[
                    FlexText(
                            text=f'前往下一單元\nNext Unit',
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
                        size='md',
                    )
                ]
            )
        )
    )

async def handle_rich_menu(user_id):
    global rich_menu_id
    try:
        await line_bot_api.get_rich_menu_id_of_user(user_id, async_req=True).get()
    except ApiException as e:
        await line_bot_api.link_rich_menu_id_to_user(user_id, rich_menu_id=rich_menu_id, async_req=True).get()

async def create_rich_menu():
    global rich_menu_id
    rich_menu = await line_bot_api.create_rich_menu(
        rich_menu_request=RichMenuRequest(
            size=RichMenuSize(width=2500, height=843),
            name="Menu",
            chatBarText="Exercises 1~3",
            selected=True,
            areas=[
                RichMenuArea(
                    bounds=RichMenuBounds(x=0, y=0, width=833, height=843),
                    action=PostbackAction(label='Unit 1', data='action=unit&unit=1')
                ),
                RichMenuArea(
                    bounds=RichMenuBounds(x=833, y=0, width=833, height=843),
                    action=PostbackAction(label='Unit 2', data='action=unit&unit=2')
                ),
                RichMenuArea(
                    bounds=RichMenuBounds(x=1666, y=0, width=833, height=843),
                    action=PostbackAction(label='Unit 3', data='action=unit&unit=3')
                ),
            ]
        ),
        async_req=True
    ).get()

    rich_menu_id = rich_menu.to_dict().get('richMenuId')
        
    print(f'Rich Menu ID: {rich_menu_id}')
    
    await line_bot_api_blob.set_rich_menu_image_with_http_info(
        rich_menu_id=rich_menu_id,
        body='templates/richmenu.png',
        _headers={"Content-Type": "image/png"},
        async_req=True
    ).get()
    await line_bot_api.set_default_rich_menu_with_http_info(
        rich_menu_id=rich_menu_id,
        async_req=True
    ).get()
