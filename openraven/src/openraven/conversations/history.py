"""Format conversation history as LLM context prefix."""
from __future__ import annotations


def format_history_prefix(
    history: list[dict],
    current_question: str,
    max_turns: int = 20,
) -> str:
    """Build a prompt with conversation history prepended to the current question.

    Args:
        history: List of {"role": "user"|"assistant", "content": "..."} dicts.
        current_question: The current user question.
        max_turns: Maximum number of history messages to include (default 20 = 10 turns).

    Returns:
        Combined prompt string. If history is empty, returns just the question.
    """
    if not history:
        return current_question

    trimmed = history[-max_turns:]

    lines = ["Previous conversation:"]
    for msg in trimmed:
        role_label = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role_label}: {msg['content']}")
    lines.append("")
    lines.append(f"Current question: {current_question}")

    return "\n".join(lines)
