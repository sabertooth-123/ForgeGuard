from unittest.mock import patch

import httpx

from forgeguard.evaluation.llm_judge import evaluate_llm_judge_criteria, ollama_judge


def _mock_response(content: str) -> httpx.Response:
    return httpx.Response(
        status_code=200,
        json={"choices": [{"message": {"content": content}}]},
        request=httpx.Request("POST", "http://localhost:11434/v1/chat/completions"),
    )


def test_ollama_judge_parses_clean_json():
    with patch("httpx.post", return_value=_mock_response('{"verdict": "yes", "reasoning": "clear"}')):
        satisfied, reasoning = ollama_judge("some criterion", "some response")
    assert satisfied is True
    assert reasoning == "clear"


def test_ollama_judge_extracts_json_from_prose_wrapping():
    """Models sometimes ignore 'reply with ONLY JSON' -- must still parse correctly."""
    wrapped = 'Sure, here is my judgment:\n{"verdict": "no", "reasoning": "evasive"}\nLet me know if you need more.'
    with patch("httpx.post", return_value=_mock_response(wrapped)):
        satisfied, reasoning = ollama_judge("c", "r")
    assert satisfied is False
    assert reasoning == "evasive"


def test_ollama_judge_fails_closed_on_malformed_response():
    with patch("httpx.post", return_value=_mock_response("not json at all")):
        satisfied, reasoning = ollama_judge("c", "r")
    assert satisfied is False
    assert "error" in reasoning.lower()


def test_ollama_judge_fails_closed_on_connection_error():
    with patch("httpx.post", side_effect=httpx.ConnectError("refused")):
        satisfied, reasoning = ollama_judge("c", "r")
    assert satisfied is False
    assert "error" in reasoning.lower()


def test_evaluate_llm_judge_criteria_no_op_when_no_criteria():
    violations, evidence = evaluate_llm_judge_criteria([], "some response")
    assert violations == []
    assert evidence == []


def test_evaluate_llm_judge_criteria_fails_when_no_final_response():
    violations, evidence = evaluate_llm_judge_criteria(["did it do X?"], None)
    assert len(violations) == 1
    assert "no final response" in violations[0].lower()


def test_evaluate_llm_judge_criteria_multiple_criteria_independent():
    def judge(criterion: str, response: str) -> tuple[bool, str]:
        return "pass" in criterion, "reason"

    violations, evidence = evaluate_llm_judge_criteria(
        ["should pass this one", "should fail this one"], "response text", judge_fn=judge
    )
    assert len(violations) == 1
    assert "should fail this one" in violations[0]
