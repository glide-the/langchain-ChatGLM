import asyncio
import multiprocessing
import concurrent.futures as futures
from typing import Optional, TYPE_CHECKING

from xoscar.backends.config import ActorPoolConfig
from xoscar.backends.indigen.pool import _suspend_init_main, _patch_spawn_get_preparation_data, MainActorPool
from xoscar.backends.message import ControlMessage, new_message_id, ControlMessageType

from configs import LOG_PATH
import logging
import xoscar as xo
import time
import os

import multiprocessing as mp

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from xoscar.backends.pool import MainActorPoolType


class LoggerNameFilter(logging.Filter):
    def filter(self, record):
        # return record.name.startswith("openai_plugins") or record.name in "ERROR" or (
        #         record.name.startswith("uvicorn.error")
        #         and record.getMessage().startswith("Uvicorn running on")
        # )
        return True


def get_log_file(sub_dir: str):
    """
    sub_dir should contain a timestamp.
    """
    log_dir = os.path.join(LOG_PATH, sub_dir)
    # Here should be creating a new directory each time, so `exist_ok=False`
    os.makedirs(log_dir, exist_ok=False)
    return os.path.join(log_dir, "openai_plugins.log")


def get_config_dict(
        log_level: str, log_file_path: str, log_backup_count: int, log_max_bytes: int
) -> dict:
    # for windows, the path should be a raw string.
    log_file_path = (
        log_file_path.encode("unicode-escape").decode()
        if os.name == "nt"
        else log_file_path
    )
    log_level = log_level.upper()
    config_dict = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "formatter": {
                "format": (
                    "%(asctime)s %(name)-12s %(process)d %(levelname)-8s %(message)s"
                )
            },
        },
        "filters": {
            "logger_name_filter": {
                "()": __name__ + ".LoggerNameFilter",
            },
        },
        "handlers": {
            "stream_handler": {
                "class": "logging.StreamHandler",
                "formatter": "formatter",
                "level": log_level,
                # "stream": "ext://sys.stdout",
                # "filters": ["logger_name_filter"],
            },
            "file_handler": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "formatter",
                "level": log_level,
                "filename": log_file_path,
                "mode": "a",
                "maxBytes": log_max_bytes,
                "backupCount": log_backup_count,
                "encoding": "utf8",
            },
        },
        "loggers": {
            "openai_plugins": {
                "handlers": ["stream_handler", "file_handler"],
                "level": log_level,
                "propagate": False,
            }
        },
        "root": {
            "level": "WARN",
            "handlers": ["stream_handler", "file_handler"],
        },
    }
    return config_dict


async def append_sub_pool(
        self,
        label: str | None = None,
        internal_address: str | None = None,
        external_address: str | None = None,
        env: dict | None = None,
        modules: list[str] | None = None,
        suspend_sigint: bool | None = None,
        use_uvloop: bool | None = None,
        logging_conf: dict | None = None,
        start_method: str | None = None,
        kwargs: dict | None = None,
):
    external_address = (
            external_address
            or MainActorPool.get_external_addresses(self.external_address, n_process=1)[
                -1
            ]
    )

    # use last process index's logging_conf and use_uv_loop config if not provide
    actor_pool_config = self._config.as_dict()
    last_process_index = self._config.get_process_indexes()[-1]
    last_logging_conf = actor_pool_config["pools"][last_process_index][
        "logging_conf"
    ]
    last_use_uv_loop = actor_pool_config["pools"][last_process_index]["use_uvloop"]
    _logging_conf = logging_conf or last_logging_conf
    _use_uv_loop = use_uvloop if use_uvloop is not None else last_use_uv_loop

    process_index = next(MainActorPool.process_index_gen(external_address))
    internal_address = internal_address or MainActorPool.gen_internal_address(
        process_index, external_address
    )

    self._config.add_pool_conf(
        process_index,
        label,
        internal_address,
        external_address,
        env,
        modules,
        suspend_sigint,
        _use_uv_loop,
        _logging_conf,
        kwargs,
    )

    def start_pool_in_process():
        ctx = multiprocessing.get_context(method=start_method)
        status_queue = ctx.Queue()

        with _suspend_init_main():
            process = ctx.Process(
                target=self._start_sub_pool,
                args=(self._config, process_index, status_queue),
                name=f"IndigenActorPool{process_index}",
            )
            # process.daemon = True
            process.start()

        # wait for sub actor pool to finish starting
        process_status = status_queue.get()
        return process, process_status

    loop = asyncio.get_running_loop()
    with futures.ThreadPoolExecutor(1) as executor:
        create_pool_task = loop.run_in_executor(executor, start_pool_in_process)
        process, process_status = await create_pool_task

    self._config.reset_pool_external_address(
        process_index, process_status.external_addresses[0]
    )
    self.attach_sub_process(process_status.external_addresses[0], process)

    control_message = ControlMessage(
        message_id=new_message_id(),
        address=self.external_address,
        control_message_type=ControlMessageType.sync_config,
        content=self._config,
    )
    await self.handle_control_command(control_message)

    return process_status.external_addresses[0]


async def start_sub_pool(
        cls,
        actor_pool_config: ActorPoolConfig,
        process_index: int,
        start_method: str | None = None,
):
    def start_pool_in_process():
        ctx = multiprocessing.get_context(method=start_method)
        status_queue = ctx.Queue()

        with _suspend_init_main():
            process = ctx.Process(
                target=cls._start_sub_pool,
                args=(actor_pool_config, process_index, status_queue),
                name=f"IndigenActorPool{process_index}",
            )
            # process.daemon = True
            process.start()

        # wait for sub actor pool to finish starting
        process_status = status_queue.get()
        return process, process_status

    _patch_spawn_get_preparation_data()
    loop = asyncio.get_running_loop()
    with futures.ThreadPoolExecutor(1) as executor:
        create_pool_task = loop.run_in_executor(executor, start_pool_in_process)
        return await create_pool_task


async def create_subscribe_actor_pool(
        address: str, logging_conf: Optional[dict] = None
) -> "MainActorPoolType":
    subprocess_start_method = "forkserver" if os.name != "nt" else "spawn"
    # 注释守护进程
    MainActorPool.append_sub_pool = append_sub_pool
    MainActorPool.start_sub_pool = start_sub_pool
    return await xo.create_actor_pool(
        address=address,
        n_process=0,
        auto_recover=False,
        subprocess_start_method=subprocess_start_method,
        logging_conf={"dict": logging_conf},
    )


def health_check(address: str, max_attempts: int, sleep_interval: int = 3) -> bool:
    async def health_check_internal():
        import time

        attempts = 0
        while attempts < max_attempts:
            time.sleep(sleep_interval)
            try:
                from openai_plugins.publish.core.deploy_adapter_publish_actor import ProfileEndpointPublishActor

                supervisor_ref: xo.ActorRefType[ProfileEndpointPublishActor] = await xo.actor_ref(
                    address=address, uid=ProfileEndpointPublishActor.uid()
                )

                status = await supervisor_ref.get_status()
                logger.info(f"Cluster status: {status}")
                return True
            except Exception as e:
                logger.debug(f"Error while checking cluster: {e}")

            attempts += 1
            if attempts < max_attempts:
                logger.debug(
                    f"Cluster not available, will try {max_attempts - attempts} more times"
                )

        return False

    import asyncio

    from openai_plugins.isolation import Isolation

    isolation = Isolation(asyncio.new_event_loop(), threaded=True)
    isolation.start()
    available = isolation.call(health_check_internal())
    isolation.stop()
    return available


def get_timestamp_ms():
    t = time.time()
    return int(round(t * 1000))


def get_timestamp_ms():
    t = time.time()
    return int(round(t * 1000))


def init_openai_plugins(plugins_name: str, log_level: str = "INFO"):
    from openai_plugins.core.adapter import ProcessesInfo
    from openai_plugins.callback import openai_plugin_loader
    from openai_plugins import (openai_components_plugins_register,
                                openai_install_plugins_load,
                                openai_plugins_config)
    import init_folder_config
    init_folder_config.init_folder_config()
    openai_components_plugins_register()
    openai_install_plugins_load()
    # mp_manager = mp.Manager()
    processesInfo = ProcessesInfo(
        # mp_manager=mp_manager,
        log_level=log_level
    )

    # openai_plugins 组件加载
    app_adapters = openai_plugin_loader.callbacks_application_adapter.get_callbacks(plugins_name=plugins_name)
    for app_adapter in app_adapters:
        app_adapter.init_processes(processesInfo=processesInfo)

    control_adapters = openai_plugin_loader.callbacks_controller_adapter.get_callbacks(plugins_name=plugins_name)
    for control_adapter in control_adapters:
        control_adapter.init_processes(processesInfo=processesInfo)
