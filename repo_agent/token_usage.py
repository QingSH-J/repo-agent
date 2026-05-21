def empty_token_usage():
    return {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0
    }


"""
add_token_usage takes two token usage dicts and returns a new dict with the values added together.
"""
def add_token_usage(
    left: dict[str, int],
    right: dict[str, int]
) -> dict[str, int]:
    return {
        "prompt_tokens": left.get("prompt_tokens", 0) + right.get("prompt_tokens", 0),
        "completion_tokens": left.get("completion_tokens", 0) + right.get("completion_tokens", 0),
        "total_tokens": left.get("total_tokens", 0) + right.get("total_tokens", 0),
    }

def extract_message_token(message: object) -> dict[str, int]:
    usage = getattr(message, "token_usage", None)

    if usage:
        return {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        }
    
    response_metadata = getattr(message, "response_metadata", {}) or {}
    token_usage = response_metadata.get("token_usage", {}) or {}

    return {
        "input_tokens": int(token_usage.get("prompt_tokens", 0)),
        "output_tokens": int(token_usage.get("completion_tokens", 0)),
        "total_tokens": int(token_usage.get("total_tokens", 0)),
    }

def extract_agent_usage(result: dict) -> dict[str, int]:
    messages = result.get("messages", [])
    total_usage = empty_token_usage()

    for message in messages:
        message_usage = extract_message_token(message)
        total_usage = add_token_usage(total_usage, message_usage)

    return total_usage


