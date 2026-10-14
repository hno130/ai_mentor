"""Regression checks that never call OpenAI or a real database."""

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Agent"))
import main
from AllAgent import AllAgent, MissingSearchImplementationError
from QuestionProcessor import QuestionProcessor


class FakeDatabase:
    instances = []

    def __init__(self, *args):
        self.closed = False
        self.instances.append(self)

    def close(self):
        self.closed = True


class FakeProcessor:
    def __init__(self, db):
        self.db = db

    async def process_questions(self, question, history):
        assert not self.db.closed, "Connection closed before streaming"
        yield "공백  유지\n다음 줄"
        yield [{"교과목명": "가상 과목", "학년": 2, "학기": "1학기"}]
        assert not self.db.closed, "Connection closed while streaming"


class AppTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        FakeDatabase.instances = []
        self.client = main.app.test_client()

    async def request_stream(self, processor=FakeProcessor):
        with patch.object(main.config, "api_key", "test-placeholder"), patch.object(main, "DatabaseConnection", FakeDatabase), patch.object(main, "QuestionProcessor", processor):
            response = await self.client.get("/get-curriculum", query_string={"question": "안녕", "history": "[]"})
            return response, (await response.get_data()).decode()

    async def test_home_and_health_work_without_credentials_or_database(self):
        with patch.object(main.config, "api_key", ""), patch("mysql.connector.connect", side_effect=AssertionError("Unexpected DB connection")):
            home = await self.client.get("/")
            health = await self.client.get("/health")
        self.assertEqual(home.status_code, 200)
        self.assertIn("static/chat.js", (await home.get_data()).decode())
        self.assertFalse((await health.get_json())["search_available"])

    async def test_input_validation(self):
        for query in ({}, {"question": "x" * 2001}, {"question": "hi", "history": "bad-json"}, {"question": "hi", "history": "{}"}, {"question": "hi", "history": '[{"question":null,"response":"x"}]'}):
            response = await self.client.get("/get-curriculum", query_string=query)
            self.assertEqual(response.status_code, 400)

    async def test_missing_key_returns_503_before_processing(self):
        with patch.object(main.config, "api_key", ""), patch.object(main, "QuestionProcessor", side_effect=AssertionError("Should not run")):
            response = await self.client.get("/get-curriculum?question=hello")
        self.assertEqual(response.status_code, 503)

    async def test_sse_preserves_text_and_serializes_courses(self):
        response, body = await self.request_stream()
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.content_type)
        frames = body.strip().split("\n\n")
        self.assertEqual(len(frames), 3)
        self.assertEqual(json.loads(frames[0].split("data: ", 1)[1]), "공백  유지\n다음 줄")
        self.assertEqual(json.loads(frames[1].split("data: ", 1)[1])[0]["교과목명"], "가상 과목")
        self.assertTrue(frames[-1].startswith("event: done\n"))
        self.assertTrue(FakeDatabase.instances[0].closed)

    async def test_request_connections_are_distinct(self):
        await self.request_stream()
        await self.request_stream()
        self.assertEqual(len(FakeDatabase.instances), 2)
        self.assertIsNot(FakeDatabase.instances[0], FakeDatabase.instances[1])
        self.assertTrue(all(db.closed for db in FakeDatabase.instances))

    async def test_stream_error_is_reported_and_connection_closed(self):
        class BrokenProcessor(FakeProcessor):
            async def process_questions(self, question, history):
                yield "partial"
                raise MissingSearchImplementationError("검색 복구 필요")
        _, body = await self.request_stream(BrokenProcessor)
        self.assertIn('event: error\ndata: {"message": "검색 복구 필요"}', body)
        self.assertIn("event: done", body)
        self.assertTrue(FakeDatabase.instances[0].closed)

    async def test_normal_chat_route_uses_mocked_api_only(self):
        completion = {"choices": [{"message": {"content": "Category: 3\nContinuation: 0"}}]}
        chunks = [{"choices": [{"delta": {"content": "안녕  하세요"}}]}]
        with patch.object(main.config, "api_key", "test-placeholder"), patch("openai.ChatCompletion.create", side_effect=[completion, iter(chunks)]), patch("mysql.connector.connect", side_effect=AssertionError("No DB needed for chat")):
            response = await self.client.get("/get-curriculum?question=hello")
            body = (await response.get_data()).decode()
        self.assertNotIn("event: error", body)
        self.assertIn("event: done", body)
        payloads = [json.loads(frame.split("data: ", 1)[1]) for frame in body.strip().split("\n\n") if frame.startswith("event: text")]
        self.assertEqual("".join(payloads), "안녕  하세요")

    async def test_unavailable_search_stops_after_classification(self):
        completion = {"choices": [{"message": {"content": "Category: 4\nContinuation: 0"}}]}
        with patch.object(main.config, "api_key", "test-placeholder"), patch("openai.ChatCompletion.create", return_value=completion) as api:
            response = await self.client.get("/get-curriculum?question=curriculum")
            body = (await response.get_data()).decode()
        self.assertIn("event: error", body)
        self.assertIn("검색 구현", body)
        self.assertEqual(api.call_count, 1)


class ClassifierTests(unittest.TestCase):
    def test_malformed_classifier_response_has_safe_default(self):
        for content in ("Category:", "unexpected response", "Category: 13\nContinuation: 8"):
            with patch("openai.ChatCompletion.create", return_value={"choices": [{"message": {"content": content}}]}):
                self.assertEqual(QuestionProcessor(None).classify_question("hi", "[]"), ("3", 0))

    def test_search_placeholder_is_explicit(self):
        with self.assertRaises(MissingSearchImplementationError):
            AllAgent().search_db("question")


if __name__ == "__main__":
    unittest.main()
