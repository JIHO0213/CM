"""
Solar LLM 응답에서 JSON만 안전하게 뽑아내는 공용 유틸.

문제 상황: "JSON으로만 답하라"고 프롬프트에 명시해도, 모델이 가끔
- 코드펜스(```json ... ```)를 붙이거나
- JSON 뒤에 짧은 설명을 덧붙이거나
- 마지막 항목 뒤에 쉼표를 하나 더 붙이는 등(trailing comma) JSON 문법을 살짝 틀리거나
- 스스로 "어 이거 틀렸다"며 중간에 반성 문단을 쓰고, 그 뒤에 수정된 JSON을
  또 하나 붙이는 경우(응답 안에 JSON이 2개 이상 들어있는 경우)가 있습니다.
아래 함수는 이런 경우들을 전부 방어합니다: 문자열 리터럴을 제대로 인식하면서
중괄호/대괄호가 짝이 맞는 JSON 덩어리를 전부 찾아내고, 뒤에 있는 것부터
(자기 수정은 보통 나중에 나오므로) 유효하게 파싱되는 걸 채택합니다.
"""
import json
import re


def _strip_trailing_commas(text: str) -> str:
    """ ',' 뒤에 '}' 또는 ']' 가 바로 오는 경우(trailing comma)를 제거."""
    return re.sub(r",\s*([}\]])", r"\1", text)


def _find_balanced_json_candidates(text: str) -> list[str]:
    """
    문자열 리터럴 안의 중괄호/대괄호는 무시하면서, 최상위 레벨에서 짝이 맞는
    '{...}' 또는 '[...]' 덩어리를 전부 찾아서 순서대로 반환.
    """
    candidates = []
    stack = []
    start = None
    in_string = False
    escape = False

    for i, ch in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            continue

        if ch in "{[":
            if not stack:
                start = i
            stack.append(ch)
        elif ch in "}]":
            if stack:
                stack.pop()
                if not stack and start is not None:
                    candidates.append(text[start : i + 1])
                    start = None

    return candidates


def extract_json(raw: str):
    text = raw.strip()

    # 코드펜스 제거 (```json ... ``` 또는 ``` ... ```)
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text).strip()

    # 1) 바로 파싱 시도 (대부분의 경우 이걸로 충분)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2) 최상위 레벨에서 짝이 맞는 JSON 덩어리를 전부 찾고,
    #    "뒤에 있는 것부터" 시도 (모델이 스스로 수정한 답은 보통 뒤에 나오므로)
    candidates = _find_balanced_json_candidates(text)
    if not candidates:
        raise ValueError(f"응답에서 JSON을 찾을 수 없습니다: {text[:500]}")

    last_error = None
    for snippet in reversed(candidates):
        try:
            return json.loads(snippet)
        except json.JSONDecodeError as e:
            last_error = e
        # trailing comma 복구 후 재시도
        try:
            return json.loads(_strip_trailing_commas(snippet))
        except json.JSONDecodeError as e:
            last_error = e
            continue

    # 여기까지 실패하면 원문을 그대로 에러 메시지에 남겨서, 터미널 로그만 보고도
    # Solar가 정확히 뭘 잘못 줬는지 바로 알 수 있게 함
    raise ValueError(
        f"Solar 응답을 JSON으로 파싱하지 못했습니다 ({last_error}). 원문: {text[:800]}"
    ) from last_error


