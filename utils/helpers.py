"""Shared utility helpers."""


def truncate(text: str, max_length: int = 60000) -> str:
    """Truncate text to fit within GitHub comment limits.
    
    GitHub issue comments have a max length of ~65536 characters.
    We leave some room for safety.
    
    Args:
        text: The text to truncate
        max_length: Maximum allowed length (default 60000)
        
    Returns:
        The truncated text with suffix if truncation occurred
    """
    if len(text) <= max_length:
        return text
    suffix = "[TRUNCATED]"
    return text[:max_length] + "\n\n... " + suffix
