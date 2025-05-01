import asyncio
import time
import uuid
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.compose import router

app = FastAPI()
app.include_router(router)

@pytest.mark.asyncio
async def test_concurrent_article_generation_load():
    """Simulate concurrent article generation requests and report performance metrics."""
    NUM_REQUESTS = 20
    CONCURRENCY = 5
    TEST_TOPIC = "Performance Testing AI"
    TEST_STYLE_GUIDE = "Write in a 1920s newspaper style"

    async def make_request(client, topic, style_guide):
        start = time.perf_counter()
        response = client.post(
            "/api/compose",
            json={"topic": topic, "style_guide": style_guide},
        )
        elapsed = time.perf_counter() - start
        return response.status_code, elapsed

    results = []
    with TestClient(app) as client:
        sem = asyncio.Semaphore(CONCURRENCY)

        async def worker():
            async with sem:
                return await make_request(client, TEST_TOPIC, TEST_STYLE_GUIDE)

        tasks = [worker() for _ in range(NUM_REQUESTS)]
        results = await asyncio.gather(*tasks)

    response_times = [r[1] for r in results if r[0] == 200]
    print(f"\n--- Load Test Results ---")
    print(f"Total requests: {NUM_REQUESTS}")
    print(f"Successful: {len(response_times)}")
    print(f"Failed: {NUM_REQUESTS - len(response_times)}")
    if response_times:
        print(f"Avg response time: {sum(response_times)/len(response_times):.3f}s")
        print(f"Min response time: {min(response_times):.3f}s")
        print(f"Max response time: {max(response_times):.3f}s")
    print(f"------------------------\n") 