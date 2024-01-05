import asyncio
import logging
import multiprocessing
import signal
import sys
import os
from typing import Dict, Optional, TYPE_CHECKING

import xoscar as xo
from xoscar.utils import get_next_port

from configs import HEALTH_CHECK_ATTEMPTS, HEALTH_CHECK_INTERVAL, LOG_BACKUP_COUNT, LOG_MAX_BYTES
from openai_plugins.deploy.subscribe import start_subscribe_components
from openai_plugins.deploy.utils import health_check, get_timestamp_ms, get_log_file, get_config_dict
from openai_plugins.publish.core.deploy_adapter_publish_actor import ProfileEndpointPublishActor
from openai_plugins.publish.core.deploy_adapter_subscribe_actor import DeployAdapterSubscribeActor

logger = logging.getLogger(__name__)


async def _start_local_cluster(
        address: str,
        logging_conf: Optional[Dict] = None,
):
    from openai_plugins.deploy.utils import create_subscribe_actor_pool

    logging.config.dictConfig(logging_conf)  # type: ignore
    # 跳过键盘中断，使用xoscar的信号处理
    signal.signal(signal.SIGINT, lambda *_: None)
    pool = None
    try:

        pool = await create_subscribe_actor_pool(
            address=address, logging_conf=logging_conf
        )
        await xo.create_actor(
            ProfileEndpointPublishActor, address=address, uid=ProfileEndpointPublishActor.uid()
        )
        await start_subscribe_components(
            address=address, publish_address=address, main_pool=pool
        )
        await pool.join()
    except asyncio.CancelledError:
        if pool is not None:
            await pool.stop()


def run(address: str, logging_conf: Optional[Dict] = None):
    # 跳过键盘中断，使用xoscar的信号处理
    signal.signal(signal.SIGINT, lambda *_: None)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    task = loop.create_task(
        _start_local_cluster(address=address, logging_conf=logging_conf)
    )
    loop.run_until_complete(task)


def run_in_subprocess(
        address: str, logging_conf: Optional[Dict] = None
):
    # prevent re-init cuda error.
    multiprocessing.set_start_method(method="spawn", force=True)
    p = multiprocessing.Process(target=run, args=(address, logging_conf))
    p.start()


def main(host: str, port: int, logging_conf: Optional[Dict] = None):
    publish_address = f"{host}:{get_next_port()}"

    def handler(signalname):
        """
        Python 3.9 has `signal.strsignal(signalnum)` so this closure would not be needed.
        Also, 3.8 includes `signal.valid_signals()` that can be used to create a mapping for the same purpose.
        """

        def f(signal_received, frame):
            raise KeyboardInterrupt(f"{signalname} received")

        return f

    # This will be inherited by the child process if it is forked (not spawned)
    signal.signal(signal.SIGINT, handler("SIGINT"))
    signal.signal(signal.SIGTERM, handler("SIGTERM"))
    try:
        run_in_subprocess(publish_address, logging_conf)

        if not health_check(
                address=publish_address,
                max_attempts=HEALTH_CHECK_ATTEMPTS,
                sleep_interval=HEALTH_CHECK_INTERVAL,
        ):
            raise RuntimeError("Cluster is not available after multiple attempts")

        from openai_plugins.publish import openai_plugins_bootstrap_web

        api_run = openai_plugins_bootstrap_web.run(
            publish_address=publish_address,
            host=host,
            port=port,
            logging_conf=logging_conf,
        )

        async def pool_join_thread():
            await api_run.join()

        asyncio.run(pool_join_thread())
    except Exception as e:
        logger.error(e)
        logger.warning("Caught KeyboardInterrupt! Setting stop event...")
    finally:

        logger.warning("Stopping all processes...")

        async def stop_local_cluster():
            publish_ref: xo.ActorRefType["ProfileEndpointPublishActor"] = await xo.actor_ref(
                address=publish_address, uid=ProfileEndpointPublishActor.uid()
            )
            subscribe_ref: xo.ActorRefType["DeployAdapterSubscribeActor"] = await xo.actor_ref(
                address=publish_address, uid=DeployAdapterSubscribeActor.uid()
            )
            # # 获取所有适配器
            # adapters = await subscribe_ref.list_adapters()
            # for adapter in adapters:
            #     await subscribe_ref.terminate_adapter(adapter)
            await xo.destroy_actor(subscribe_ref)
            await asyncio.sleep(1)
            await xo.destroy_actor(publish_ref)
            logger.warning("All processes stopped")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        task = loop.create_task(
            stop_local_cluster()
        )
        loop.run_until_complete(task)


if __name__ == "__main__":

    if sys.version_info < (3, 10):
        loop = asyncio.get_event_loop()
    else:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()

        asyncio.set_event_loop(loop)

    dict_config = get_config_dict(
        "DEBUG",
        get_log_file(f"local_{get_timestamp_ms()}"),
        LOG_BACKUP_COUNT,
        LOG_MAX_BYTES,
    )
    logging.config.dictConfig(dict_config)  # type: ignore

    # 同步调用协程代码
    loop.run_until_complete(main(host="127.0.0.1", port=8000, logging_conf=dict_config))
