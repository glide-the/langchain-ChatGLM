
import asyncio
import logging
import multiprocessing
import signal
import sys
from typing import Dict, Optional

import xoscar as xo
from xoscar.utils import get_next_port

from configs import HEALTH_CHECK_ATTEMPTS, HEALTH_CHECK_INTERVAL, LOG_BACKUP_COUNT, LOG_MAX_BYTES
from openai_plugins.deploy.subscribe import start_subscribe_components
from openai_plugins.deploy.utils import health_check, get_timestamp_ms, get_log_file, get_config_dict, \
    init_openai_plugins
from openai_plugins.publish.core.deploy_adapter_publish_actor import ProfileEndpointPublishActor

logger = logging.getLogger(__name__)


async def _start_local_cluster(
    address: str,
    logging_conf: Optional[Dict] = None,
):
    from openai_plugins.deploy.utils import create_subscribe_actor_pool

    logging.config.dictConfig(logging_conf)  # type: ignore

    pool = None
    publish_ref = None
    subscribe_ref = None
    try:

        pool = await create_subscribe_actor_pool(
            address=address, logging_conf=logging_conf
        )
        publish_ref = await xo.create_actor(
            ProfileEndpointPublishActor, address=address, uid=ProfileEndpointPublishActor.uid()
        )
        subscribe_ref = await start_subscribe_components(
            address=address, publish_address=address, main_pool=pool
        )
        await pool.join()
    except asyncio.CancelledError:
        if pool is not None:

            try:
                await xo.destroy_actor(publish_ref)
            except Exception as e:
                logger.debug(
                    "Destroy publish actor failed,  error: %s",  e
                )

            try:
                await xo.destroy_actor(subscribe_ref)
            except Exception as e:
                logger.debug(
                    "Destroy subscribe actor failed,  error: %s",  e
                )
            await pool.stop()


def run(address: str, logging_conf: Optional[Dict] = None):

    def sigterm_handler(signum, frame):
        sys.exit(0)

    signal.signal(signal.SIGTERM, sigterm_handler)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    task = loop.create_task(
        _start_local_cluster(address=address, logging_conf=logging_conf)
    )
    loop.run_until_complete(task)


def run_in_subprocess(
    address: str, logging_conf: Optional[Dict] = None
) -> multiprocessing.Process:
    # prevent re-init cuda error.
    multiprocessing.set_start_method(method="spawn", force=True)
    p = multiprocessing.Process(target=run, args=(address, logging_conf))
    p.start()
    return p


def main(host: str, port: int, logging_conf: Optional[Dict] = None):
    publish_address = f"{host}:{get_next_port()}"
    local_cluster = run_in_subprocess(publish_address, logging_conf)

    if not health_check(
        address=publish_address,
        max_attempts=HEALTH_CHECK_ATTEMPTS,
        sleep_interval=HEALTH_CHECK_INTERVAL,
    ):
        raise RuntimeError("Cluster is not available after multiple attempts")

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


if __name__ == "__main__":

    dict_config = get_config_dict(
        "DEBUG",
        get_log_file(f"local_{get_timestamp_ms()}"),
        LOG_BACKUP_COUNT,
        LOG_MAX_BYTES,
    )
    logging.config.dictConfig(dict_config)  # type: ignore
    main(host="127.0.0.1", port=8000, logging_conf=dict_config)
