"""
Keyword extraction module using jieba TF-IDF algorithm.

This module extracts keywords from transcription text for automatic tagging.
"""

from typing import List

import jieba.analyse


def extract_keywords(text: str, top_k: int = 5) -> List[str]:
    """
    Extract keywords from transcription text using TF-IDF algorithm.

    Args:
        text: The transcription text to analyze
        top_k: Number of keywords to extract (default: 5)

    Returns:
        List of extracted keywords, ordered by relevance
    """
    if not text or not text.strip():
        return []

    # Use jieba's built-in TF-IDF algorithm
    # This is optimized for Chinese text but works with mixed content
    keywords = jieba.analyse.extract_tags(text, topK=top_k)
    return list(keywords)


def extract_keywords_with_weight(text: str, top_k: int = 5) -> List[tuple]:
    """
    Extract keywords with their TF-IDF weights.

    Args:
        text: The transcription text to analyze
        top_k: Number of keywords to extract (default: 5)

    Returns:
        List of (keyword, weight) tuples, ordered by weight descending
    """
    if not text or not text.strip():
        return []

    keywords = jieba.analyse.extract_tags(text, topK=top_k, withWeight=True)
    return list(keywords)
