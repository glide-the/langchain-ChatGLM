import asyncio
import logging
import multiprocessing
import signal
import sys
from typing import Dict, Optional

import xoscar as xo
from xoscar.utils import get_next_port

from configs import HEALTH_CHECK_INTERVAL, HEALTH_CHECK_ATTEMPTS
from .utils import health_check
from openai_plugins.publish.core.deploy_adapter_publish_actor import ProfileEndpointPublishActor

logger = logging.getLogger(__name__)


async def _start_publish(address: str, logging_conf: Optional[Dict] = None):
    logging.config.dictConfig(logging_conf)  # type: ignore

    pool = None
    try:
        pool = await xo.create_actor_pool(
            address=address, n_process=0, logging_conf={"dict": logging_conf}
        )
        await xo.create_actor(
            ProfileEndpointPublishActor, address=address, uid=ProfileEndpointPublishActor.uid()
        )
        await pool.join()
    except asyncio.exceptions.CancelledError:
        if pool is not None:
            await pool.stop()


def run(address: str, logging_conf: Optional[Dict] = None):
    def sigterm_handler(signum, frame):
        sys.exit(0)

    signal.signal(signal.SIGTERM, sigterm_handler)

    loop = asyncio.get_event_loop()
    task = loop.create_task(
        _start_publish(address=address, logging_conf=logging_conf)
    )
    loop.run_until_complete(task)


def run_in_subprocess(
    address: str, logging_conf: Optional[Dict] = None
) -> multiprocessing.Process:
    p = multiprocessing.Process(target=run, args=(address, logging_conf))
    p.start()
    return p


def main(
    host: str,
    port: int,
    publish_port: Optional[int],
    logging_conf: Optional[Dict] = None,
):
    publish_address = f"{host}:{publish_port or get_next_port()}"
    local_cluster = run_in_subprocess(publish_address, logging_conf)

    if not health_check(
        address=publish_address,
        max_attempts=HEALTH_CHECK_ATTEMPTS,
        sleep_interval=HEALTH_CHECK_INTERVAL,
    ):
        raise RuntimeError("publish is not available after multiple attempts")

    try:
        from openai_plugins.publish import openai_plugins_bootstrap_web

        openai_plugins_bootstrap_web.run(
            publish_address=publish_address,
            host=host,
            port=port,
            logging_conf=logging_conf,
        )
    finally:
        local_cluster.terminate()
