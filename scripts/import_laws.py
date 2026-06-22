#!/usr/bin/env python3
"""批量导入 data/laws/ 下的法律文本到资料库。"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.db.database import SessionLocal, init_db
from backend.services.ingestion import import_law_file

LAWS = [
    ("constitution.txt", "中华人民共和国宪法", "2018-03-11"),
    ("criminal_law.txt", "中华人民共和国刑法", "2023-12-29"),
    ("company_law.txt", "中华人民共和国公司法", "2023-12-29"),
    ("tax_law.txt", "中华人民共和国税收征收管理法", "2015-04-24"),
    ("labor_law.txt", "中华人民共和国劳动法", "2018-12-29"),
]


async def main() -> None:
    laws_dir = ROOT / "data" / "laws"
    await init_db()

    async with SessionLocal() as session:
        for filename, law_name, version_date in LAWS:
            file_path = laws_dir / filename
            if not file_path.exists():
                print(f"跳过缺失文件: {file_path}")
                continue
            document = await import_law_file(session, file_path, law_name, version_date)
            print(f"已导入: {document.law_name} ({document.chunk_count} 条)")


if __name__ == "__main__":
    asyncio.run(main())
