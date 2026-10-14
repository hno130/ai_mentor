"""AImentor web entry point with a JSON-based server-sent event protocol."""

import json
import logging

from quart import Quart, Response, jsonify, render_template, request

import config
from AllAgent import MissingSearchImplementationError
from DatabaseConnection import DatabaseConnection
from QuestionProcessor import QuestionProcessor

app = Quart(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024
logger = logging.getLogger(__name__)


def encode_event(event, payload):
    """JSON preserves spaces, newlines and Unicode without HTML injection."""
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.get("/")
async def index():
    return await render_template("index.html")


@app.get("/health")
async def health():
    return jsonify(status="ok", version="recovery", search_available=False)


@app.get("/get-curriculum")
async def get_curriculum():
    question = request.args.get("question", "").strip()
    history_param = request.args.get("history", "[]")
    if not question or len(question) > 2000:
        return jsonify(error="질문은 1~2,000자 사이로 입력해 주세요."), 400
    if len(history_param) > 16000:
        return jsonify(error="대화 기록이 너무 깁니다. 기록을 삭제한 뒤 다시 시도해 주세요."), 400
    try:
        history = json.loads(history_param)
        if not isinstance(history, list):
            raise ValueError
        sanitized_history = []
        for item in history[-5:]:
            if not isinstance(item, dict) or not all(isinstance(item.get(k), str) for k in ("question", "response")):
                raise ValueError
            sanitized_history.append({"question": item["question"][:2000], "response": item["response"][:6000]})
    except (ValueError, TypeError):
        return jsonify(error="대화 기록 형식이 올바르지 않습니다."), 400

    if not config.api_key:
        return jsonify(error="서버의 OPENAI_API_KEY 설정이 필요합니다."), 503

    async def generate():
        # Each stream owns its connection, which stays alive until completion.
        db = DatabaseConnection(config.host, config.port, config.user, config.password, config.database)
        try:
            processor = QuestionProcessor(db)
            async for part in processor.process_questions(question, json.dumps(sanitized_history, ensure_ascii=False)):
                if isinstance(part, list):
                    yield encode_event("courses", part)
                elif part == "curriculum_start":
                    yield encode_event("status", {"curriculum": True})
                else:
                    yield encode_event("text", str(part))
        except MissingSearchImplementationError as exc:
            yield encode_event("error", {"message": str(exc)})
        except Exception:
            logger.exception("AImentor response failed")
            yield encode_event("error", {"message": "응답을 생성하지 못했습니다. 서버 설정을 확인해 주세요."})
        finally:
            db.close()
        yield encode_event("done", {})

    response = Response(generate(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    response.timeout = None
    return response


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(host=config.app_host, port=config.app_port, debug=False)
