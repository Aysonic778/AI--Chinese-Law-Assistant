from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class LawChunk:
    law_name: str
    article_number: str
    chapter: str
    content: str
    version_date: str


ARTICLE_PATTERN = re.compile(
    r"(?m)^(?:第[一二三四五六七八九十百零〇\d]+章[^\n]*\n)?第[一二三四五六七八九十百零〇\d]+条"
)
CHAPTER_PATTERN = re.compile(r"^第[一二三四五六七八九十百零〇\d]+章[^\n]*")
ARTICLE_NUM_PATTERN = re.compile(r"^第[一二三四五六七八九十百零〇\d]+条")


def split_law_text(
    text: str,
    law_name: str,
    version_date: str = "",
) -> list[LawChunk]:
    text = text.strip()
    if not text:
        return []

    matches = list(ARTICLE_PATTERN.finditer(text))
    if not matches:
        return [
            LawChunk(
                law_name=law_name,
                article_number="",
                chapter="",
                content=text,
                version_date=version_date,
            )
        ]

    chunks: list[LawChunk] = []
    current_chapter = ""

    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[start:end].strip()

        chapter_match = CHAPTER_PATTERN.match(block)
        if chapter_match:
            current_chapter = chapter_match.group(0).strip()

        article_match = ARTICLE_NUM_PATTERN.match(block)
        article_number = article_match.group(0).strip() if article_match else ""

        chunks.append(
            LawChunk(
                law_name=law_name,
                article_number=article_number,
                chapter=current_chapter,
                content=block,
                version_date=version_date,
            )
        )

    return chunks
