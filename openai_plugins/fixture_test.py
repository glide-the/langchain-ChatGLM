import asyncio
import logging
import multiprocessing
import signal
import sys
from typing import Dict, Optional
import init_folder_config
import pytest_asyncio
import xoscar as xo
from openai_plugins.core.adapter import ProcessesInfo
from openai_plugins import (openai_components_plugins_register,
                            openai_install_plugins_load,
                            openai_plugins_config)
from openai_plugins.callback import (openai_plugin_loader)
from openai_plugins.deploy.subscribe import start_subscribe_components
from openai_plugins.deploy.utils import create_subscribe_actor_pool, get_timestamp_ms, get_log_file, init_openai_plugins
from openai_plugins.publish.core.deploy_adapter_publish_actor import ProfileEndpointPublishActor
import multiprocessing as mp
from launch_module import launch_utils
from openai_plugins.deploy.utils import get_config_dict
from configs import LOG_BACKUP_COUNT, LOG_MAX_BYTES

args = launch_utils.args
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def api_health_check(endpoint: str, max_attempts: int, sleep_interval: int = 3):
    import time

    import requests

    attempts = 0
    while attempts < max_attempts:
        time.sleep(sleep_interval)
        try:
            response = requests.get(f"{endpoint}/status")
            if response.status_code == 200:
                return True
        except requests.RequestException as e:
            logger.info(f"Error while checking endpoint: {e}")

        attempts += 1
        if attempts < max_attempts:
            logger.info(
                f"Endpoint not available, will try {max_attempts - attempts} more times"
            )

    return False


async def _start_test_cluster(
        address: str,
        logging_conf: Optional[Dict] = None,
):
    logging.config.dictConfig(logging_conf)  # type: ignore

    pool = None
    try:
        pool = await create_subscribe_actor_pool(
            address=f"test://{address}", logging_conf=logging_conf
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


def run_test_cluster(address: str, logging_conf: Optional[Dict] = None):
    init_openai_plugins()

    def sigterm_handler(signum, frame):
        sys.exit(0)

    signal.signal(signal.SIGTERM, sigterm_handler)

    loop = asyncio.get_event_loop()
    task = loop.create_task(
        _start_test_cluster(address=address, logging_conf=logging_conf)
    )
    loop.run_until_complete(task)


def run_test_cluster_in_subprocess(
        address: str, logging_conf: Optional[Dict] = None
) -> multiprocessing.Process:
    # prevent re-init cuda error.
    multiprocessing.set_start_method(method="spawn", force=True)

    p = multiprocessing.Process(target=run_test_cluster, args=(address, logging_conf))
    p.start()
    return p


@pytest_asyncio.fixture
def setup_publish():
    from openai_plugins.deploy.utils import health_check as cluster_health_check
    from openai_plugins.publish import run_in_subprocess as run_restful_api

    dict_config = get_config_dict(
        "DEBUG",
        get_log_file(f"local_{get_timestamp_ms()}"),
        LOG_BACKUP_COUNT,
        LOG_MAX_BYTES,
    )
    logging.config.dictConfig(dict_config)  # type: ignore
    publish_address = f"localhost:{xo.utils.get_next_port()}"
    local_cluster_proc = run_test_cluster_in_subprocess(
        publish_address, dict_config
    )
    if not cluster_health_check(publish_address, max_attempts=10, sleep_interval=3):
        raise RuntimeError("Cluster is not available after multiple attempts")

    port = xo.utils.get_next_port()
    restful_api_proc = run_restful_api(
        publish_address,
        host="localhost",
        port=port,
        logging_conf=dict_config,
    )
    endpoint = f"http://localhost:{port}"
    if not api_health_check(endpoint, max_attempts=10, sleep_interval=5):
        raise RuntimeError("Endpoint is not available after multiple attempts")

    yield f"http://localhost:{port}", publish_address
    local_cluster_proc.terminate()
    restful_api_proc.terminate()
