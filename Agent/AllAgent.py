"""Explicit recovery boundary for the search agent missing from the archive.

The recovered AllAgent.py was a duplicate of Agent.py and did not define
AllAgent or any search methods. Do not substitute invented search results.
"""

from Agent import Agent


class MissingSearchImplementationError(RuntimeError):
    pass


class AllAgent(Agent):
    search_available = False

    def __init__(self, db_connection=None):
        super().__init__()
        self.db_connection = db_connection

    missing_message = (
        "이 복구본에는 학과·강의 검색 구현이 포함되어 있지 않습니다. "
        "README의 기능 복구 안내를 확인해 주세요."
    )

    def search_db(self, question, continuous=0, history=None):
        raise MissingSearchImplementationError(self.missing_message)

    async def directagent(self, question, continuous=0, history=None):
        raise MissingSearchImplementationError(self.missing_message)
        yield  # Preserve the async generator contract of QuestionProcessor.

    async def searchagent(self, question, continuous=0, history=None):
        raise MissingSearchImplementationError(self.missing_message)
        yield

    async def recommend_relevant_department(self, question, key_skills):
        raise MissingSearchImplementationError(self.missing_message)
        yield

    def recommend_relevant_department_all(self, question, key_skills=None):
        raise MissingSearchImplementationError(self.missing_message)
