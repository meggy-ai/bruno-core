"""
Text processing utilities for bruno-core.

Provides text manipulation and processing helpers.
"""

import re
from typing import List, Optional


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text

    Example:
        >>> truncate_text("Hello world", 8)
        'Hello...'
    """
    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix


def clean_whitespace(text: str) -> str:
    """
    Clean excessive whitespace from text.

    - Removes leading/trailing whitespace
    - Replaces multiple spaces with single space
    - Replaces multiple newlines with single newline

    Args:
        text: Text to clean

    Returns:
        Cleaned text

    Example:
        >>> clean_whitespace("Hello   world\\n\\n\\ntest")
        'Hello world\\ntest'
    """
    # Replace multiple spaces with single space
    text = re.sub(r" +", " ", text)

    # Replace multiple newlines with single newline
    text = re.sub(r"\n+", "\n", text)

    # Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split("\n")]

    return "\n".join(line for line in lines if line)


def extract_keywords(text: str, min_length: int = 3) -> List[str]:
    """
    Extract keywords from text.

    Simple extraction based on word frequency.

    Args:
        text: Text to extract keywords from
        min_length: Minimum keyword length

    Returns:
        List of keywords

    Example:
        >>> extract_keywords("Python is a programming language")
        ['python', 'programming', 'language']
    """
    # Convert to lowercase and split into words
    words = re.findall(r"\b\w+\b", text.lower())

    # Filter by length and remove common words
    common_words = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
    }

    keywords = [
        word for word in words if len(word) >= min_length and word not in common_words
    ]

    # Remove duplicates while preserving order
    seen = set()
    unique_keywords = []
    for keyword in keywords:
        if keyword not in seen:
            seen.add(keyword)
            unique_keywords.append(keyword)

    return unique_keywords


def highlight_text(text: str, query: str, tag: str = "**") -> str:
    """
    Highlight query matches in text.

    Args:
        text: Text to highlight in
        query: Query to highlight
        tag: Tag to wrap matches with

    Returns:
        Text with highlights

    Example:
        >>> highlight_text("Hello world", "world")
        'Hello **world**'
    """
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    return pattern.sub(f"{tag}\\g<0>{tag}", text)


def count_words(text: str) -> int:
    """
    Count words in text.

    Args:
        text: Text to count words in

    Returns:
        Word count

    Example:
        >>> count_words("Hello world")
        2
    """
    return len(re.findall(r"\b\w+\b", text))


def count_tokens_estimate(text: str) -> int:
    """
    Estimate token count.

    Rough estimation: 1 token ≈ 4 characters (for English).

    Args:
        text: Text to estimate tokens for

    Returns:
        Estimated token count

    Example:
        >>> count_tokens_estimate("Hello world")
        3
    """
    return len(text) // 4


def format_duration(seconds: int) -> str:
    """
    Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string

    Example:
        >>> format_duration(3665)
        '1h 1m 5s'
    """
    if seconds < 60:
        return f"{seconds}s"

    minutes = seconds // 60
    seconds = seconds % 60

    if minutes < 60:
        if seconds > 0:
            return f"{minutes}m {seconds}s"
        return f"{minutes}m"

    hours = minutes // 60
    minutes = minutes % 60

    parts = [f"{hours}h"]
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0:
        parts.append(f"{seconds}s")

    return " ".join(parts)


def parse_duration(text: str) -> Optional[int]:
    """
    Parse duration string to seconds.

    Supports formats like: "5m", "1h 30m", "2h", "90s"

    Args:
        text: Duration text to parse

    Returns:
        Duration in seconds, or None if invalid

    Example:
        >>> parse_duration("1h 30m")
        5400
    """
    text = text.lower().strip()
    total_seconds = 0

    # Extract hours
    hours_match = re.search(r"(\d+)\s*h", text)
    if hours_match:
        total_seconds += int(hours_match.group(1)) * 3600

    # Extract minutes
    minutes_match = re.search(r"(\d+)\s*m", text)
    if minutes_match:
        total_seconds += int(minutes_match.group(1)) * 60

    # Extract seconds
    seconds_match = re.search(r"(\d+)\s*s", text)
    if seconds_match:
        total_seconds += int(seconds_match.group(1))

    return total_seconds if total_seconds > 0 else None
