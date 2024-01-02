import asyncio
import logging
from typing import Any, Optional

import xoscar as xo
from xoscar import MainActorPoolType


from openai_plugins.publish.core.deploy_adapter_subscribe_actor import DeployAdapterSubscribeActor


logger = logging.getLogger(__name__)


async def start_subscribe_components(
    address: str, publish_address: str, main_pool: MainActorPoolType
):
     await xo.create_actor(
        DeployAdapterSubscribeActor,
        address=address,
        uid=DeployAdapterSubscribeActor.uid(),
        publish_address=publish_address,
        main_pool=main_pool
    )


async def _start_subscribe(
    address: str, publish_address: str, logging_conf: Any = None
):
    from openai_plugins.deploy.utils import create_subscribe_actor_pool

    pool = await create_subscribe_actor_pool(address=address, logging_conf=logging_conf)
    await start_subscribe_components(
        address=address, publish_address=publish_address, main_pool=pool
    )
    await pool.join()


def main(address: str, publish_address: str, logging_conf: Optional[dict] = None):
    loop = asyncio.get_event_loop()
    task = loop.create_task(_start_subscribe(address, publish_address, logging_conf))

    try:
        loop.run_until_complete(task)
    except KeyboardInterrupt:
        task.cancel()
        loop.run_until_complete(task)
        # avoid displaying exception-unhandled warnings
        task.exception()
