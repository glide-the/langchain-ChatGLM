from asyncio import sleep

from openai_plugins.fixture_test import setup_publish
import pytest
import pytest_asyncio


@pytest.mark.asyncio
async def test_create_setup_publish_api(setup_publish):
    endpoint, _ = setup_publish

    while True:
        try:
            print(endpoint)
            await sleep(100)
        except Exception:
            pass
