import asyncio
from typing import Dict

SSE_TABLET_CONNECTIONS: Dict[str, asyncio.Queue] = {}
SSE_TEACHER_CONNECTIONS: Dict[int, asyncio.Queue] = {}
