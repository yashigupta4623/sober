import os, asyncio, pathlib

os.environ.setdefault("ENABLE_BACKEND_ACCESS_CONTROL", "false")
from dotenv import load_dotenv

BASE = pathlib.Path(__file__).parent
load_dotenv(BASE / ".env")

import cognee
from cognee import SearchType

cognee.config.data_root_directory(str(BASE / ".cognee_data"))
cognee.config.system_root_directory(str(BASE / ".cognee_system"))


async def main():
    await cognee.remember(
        ["My dog's name is Pixel and he is a beagle."], dataset_name="sober_memory"
    )
    res = await cognee.recall(
        query_text="What is my dog's name and breed?",
        query_type=SearchType.GRAPH_COMPLETION,
        datasets=["sober_memory"],
    )
    print("\n>>> RECALL RESULT:", str(res[0])[:300] if res else "(empty)")


asyncio.run(main())
