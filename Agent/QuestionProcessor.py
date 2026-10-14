import openai
import re
import config
import AllAgent
import NormalAgent
import CurriculumAgent
import time

class QuestionProcessor:
    def __init__(self, db_connection):
        self.db_connection = db_connection
        self.memory = None
        self.conversation_question = []
        self.failed_directagent = False  # directagent 실패 여부를 저장하는 플래그
        openai.api_key = config.api_key
    async def process_questions(self, question, history):
        start_time = time.time()
        assignment, continuous = self.classify_question(question, history)
        if assignment != '3' and not AllAgent.AllAgent.search_available:
            raise AllAgent.MissingSearchImplementationError(AllAgent.AllAgent.missing_message)
        if assignment == '1':
            async for partial_response in self.directagent(question, continuous, history):
                yield partial_response
            # result = await self.directagent(question, continuous, history)
            end_time = time.time()
            print(f"총 응답 시간: {(end_time - start_time) * 1000:.2f} ms")
        elif assignment == '2':
            async for partial_response in self.searchagent(question, continuous, history):
                yield partial_response
            end_time = time.time()
            print(f"총 응답 시간: {(end_time - start_time) * 1000:.2f} ms")
        elif assignment == '3':
            async for partial_response in self.normalagent(question, continuous, history):
                yield partial_response
            end_time = time.time()
            print(f"총 응답 시간: {(end_time - start_time) * 1000:.2f} ms")
        elif assignment == '4':
            # `curriculumagent`가 여러 개의 결과를 `yield`로 반환
            async for partial_response in self.curriculumagent(question, continuous, history=history):
                yield partial_response
            end_time = time.time()
            print(f"총 응답 시간: {(end_time - start_time) * 1000:.2f} ms")
        elif assignment == '5':
            # `curriculumagent`가 여러 개의 결과를 `yield`로 반환
            async for partial_response in self.dep_curriculumagent(question, continuous, history=history):
                yield partial_response
            end_time = time.time()
            print(f"총 응답 시간: {(end_time - start_time) * 1000:.2f} ms")
        elif assignment == '6':
            # `curriculumagent`가 여러 개의 결과를 `yield`로 반환
            async for partial_response in self.search_curriculumagent(question, continuous, history=history):
                yield partial_response
            end_time = time.time()
            print(f"총 응답 시간: {(end_time - start_time) * 1000:.2f} ms")


    def classify_question(self, question, history, failed=False):
        start_time = time.time()
        # 프롬프트를 작성하여 LLM에 질문을 전달하고 응답을 받음
        if failed == 1:
            return "2",0
        elif failed == 2:
            return "6",0

        # LLM 프롬프트 작성: 이전 대화와 연관성을 평가
        prompt = f"""
        You are an intelligent agent that classifies questions into four categories:
        1. When the question requests a simple data search, or there is any conjunction or directive pronoun (such as '그럼', '그', '이런') appearing in the question. This includes questions asking about departments, professors, or specific courses. (e.g., "컴퓨터인공지능학부 2학년 때 무슨 과목을 들어야할까?", "골프는 언제 개설돼?", "송현제 교수님은 뭘 가르치셔?", "그럼 그 과목을 가르치는 교수님은 누구야?", "동역학은 어느 학과에서 배워?").
        3. Assign to the agent for general or casual questions that do not involve specific department or lecture (e.g., "저녁 추천해줘", "오늘 날씨 어때?", "날씨 좋다", "고마워", "잘헸어!", "졸려", "배고파", "심심해").
        4. Assign questions related to careers or educational curriculum to this agent (e.g., "AI 기계결함 전문가가 되기 위해 2학년부터 커리큘럼을 짜줘" or "과학선생님이 되기 위한 과목을 추천해줘" or "의료인공지능에 대해 공부하고 싶어").
        5. Assign to this agent for questions specifically asking about the curriculum of a particular department, the question must include "커리큘럼" (e.g., "컴퓨터공학부 커리큘럼 알려줘", "기계공학부 커리큘럼은 뭐야?", "경제부 커리큘럼은 어떻게 돼?").

        Classify the issue as category 1, 3, 4, or 5 only. Keep in mind that there is no 2.
        Also, determine if the current question is not relevant with the previous conversation or a new topic comes up, return '1' if it is continuous, otherwise return '0'.

        Question: "{question}"
        Previous conversation: "{history}"


        Return the answer in the following format:
        Category: [classification]
        Continuation: [0 or 1]
        """
        # LLM에게 질문 분류 요청
        response = openai.ChatCompletion.create(
            model=config.chat_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=20,
            n=1,
            stop=None,
            temperature=0
        )

        response_text = response['choices'][0]['message']['content'].strip()
        category_match = re.search(r"Category:\s*([1345])\b", response_text)
        continuation_match = re.search(r"Continuation:\s*([01])\b", response_text)
        classification = category_match.group(1) if category_match else "3"
        continuous = int(continuation_match.group(1)) if continuation_match else 0
        end_time = time.time()
        print(f"에이전트 배정 시간: {(end_time - start_time) * 1000:.2f} ms")
        return classification, continuous

    async def directagent(self, question, continuous, history):
        agent = AllAgent.AllAgent(self.db_connection)
        agent.memory = history  # 히스토리 공유
        agent.conversation_question = self.conversation_question
        result = ""
        async for partial_response in agent.directagent(question, continuous, history):
            result += partial_response
            yield partial_response
        if result == "No result":  # directagent 결과가 없으면 classify_question을 통해 2번으로 유도
            self.failed_directagent = True  # 실패 플래그 설정
            assignment, continuous = self.classify_question(question, history, failed=1)  # 분류에서 2번으로 유도
            if assignment == '2':
                async for partial_response in agent.searchagent(question, continuous, history):
                    yield partial_response

    async def searchagent(self, question, continuous, history):
        agent = AllAgent.AllAgent(self.db_connection)
        agent.memory = history # 히스토리 공유
        agent.conversation_question = self.conversation_question
        async for partial_response in agent.searchagent(question, continuous, history):
            yield partial_response

    async def normalagent(self, question, continuous, history):
        agent = NormalAgent.NormalAgent()
        agent.memory = history  # 히스토리 공유
        agent.conversation_question = self.conversation_question
        async for partial_response in agent.normalagent(question, continuous, history):
            yield partial_response

    async def curriculumagent(self, question, continuous, history):
        agent = CurriculumAgent.CurriculumAgent(self.db_connection)
        agent.memory = history  # 히스토리 공유
        agent.conversation_question = self.conversation_question
        # CurriculumAgent의 `curriculumagent` 메서드에서 `yield`되는 값을 받아서 하나씩 `yield`
        async for partial_response in agent.curriculumagent(question, continuous, history):
            yield partial_response

    async def dep_curriculumagent(self, question, continuous, history):
        agent = CurriculumAgent.CurriculumAgent(self.db_connection)
        agent.memory = history  # 히스토리 공유
        agent.conversation_question = self.conversation_question
        result = ""
        # CurriculumAgent의 `curriculumagent` 메서드에서 `yield`되는 값을 받아서 하나씩 `yield`
        async for partial_response in agent.direct_curriculumagent(question, continuous, history):
            result += partial_response
            yield partial_response
        if result == "No result":  # directagent 결과가 없으면 classify_question을 통해 2번으로 유도
            self.failed_directagent = True  # 실패 플래그 설정
            assignment, continuous = self.classify_question(question, history, failed=2)  # 분류에서 2번으로 유도
            if assignment == '6':
                async for partial_response in agent.dep_curriculumagent(question, continuous, history):
                    result += partial_response
                    yield partial_response
    async def search_curriculumagent(self, question, continuous, history):
        agent = CurriculumAgent.CurriculumAgent(self.db_connection)
        agent.memory = history  # 히스토리 공유
        agent.conversation_question = self.conversation_question
        # CurriculumAgent의 `curriculumagent` 메서드에서 `yield`되는 값을 받아서 하나씩 `yield`
        async for partial_response in agent.dep_curriculumagent(question, continuous, history):
            yield partial_response
