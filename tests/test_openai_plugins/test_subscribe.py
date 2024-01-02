
from typing import List, Optional
import multiprocessing as mp
import pytest
import pytest_asyncio
import xoscar as xo
from xoscar import MainActorPoolType, create_actor_pool, get_pool_config
import init_folder_config
from launch_module import launch_utils
import os
import sys
from openai_plugins.core.adapter import ProcessesInfo
from openai_plugins.publish.deploy_adapter_subscribe_actor import (DeployAdapterSubscribeActor)
from openai_plugins import (openai_components_plugins_register,
                            openai_install_plugins_load,
                            openai_plugins_config)
from openai_plugins.callback import (openai_plugin_loader)
# 为了能使用fastchat_wrapper.py中的函数，需要将当前目录加入到sys.path中
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(root_dir)

args = launch_utils.args


class MockDeployAdapterSubscribeActor(DeployAdapterSubscribeActor):
    def __init__(
            self,
            publish_address: str,
            main_pool: MainActorPoolType,
    ):
        super().__init__(publish_address, main_pool)

    async def __post_create__(self):
        pass

    async def __pre_destroy__(self):
        pass

    async def launch_adapters(
            self,
            plugins_name: str,
            request_limits: Optional[int] = None,
            **kwargs,
    ):
        subpool_address = await self._create_subpool()
        self._plugins_uid_to_adapter_addr[plugins_name] = subpool_address

    async def terminate_adapter(self, plugins_name: str):
        sub_pool_addr = self._plugins_uid_to_adapter_addr[plugins_name]
        await self._main_pool.remove_sub_pool(sub_pool_addr)
        del self._plugins_uid_to_adapter_addr[plugins_name]


@pytest_asyncio.fixture
async def setup_pool():
    pool = await create_actor_pool(
        f"test://127.0.0.1:{xo.utils.get_next_port()}", n_process=0
    )
    async with pool:
        yield pool


@pytest.mark.asyncio
async def test_terminate_create_subpool_flag(setup_pool):
    pool = setup_pool
    addr = pool.external_address
    init_folder_config.init_folder_config()
    openai_components_plugins_register()
    openai_install_plugins_load()

    print(openai_plugin_loader.callbacks_controller_adapter)
    print(openai_plugin_loader.callbacks_application_adapter)

    mp.set_start_method("spawn")
    manager = mp.Manager()

    queue = manager.Queue()
    completed_queue = manager.Queue()
    log_level = "INFO"
    #  查询openai_plugins 组件
    plugins_names = openai_plugins_config()
    for plugins_name in plugins_names:
        # openai_plugins 组件加载
        app_adapters = openai_plugin_loader.callbacks_application_adapter.get_callbacks(plugins_name=plugins_name)
        for app_adapter in app_adapters:
            processesInfo = ProcessesInfo(
                model_name=args.model_name,
                controller_address=args.controller_address,
                log_level=log_level,
                queue=queue,
                completed_queue=completed_queue,
                mp_manager=manager,
            )

            app_adapter.init_processes(processesInfo=processesInfo)

        control_adapters = openai_plugin_loader.callbacks_controller_adapter.get_callbacks(plugins_name=plugins_name)
        for control_adapter in control_adapters:
            processesInfo = ProcessesInfo(
                model_name=args.model_name,
                controller_address=args.controller_address,
                log_level=log_level,
                queue=queue,
                completed_queue=completed_queue,
                mp_manager=manager,
            )

            control_adapter.init_processes(processesInfo=processesInfo)
    worker: xo.ActorRefType["MockDeployAdapterSubscribeActor"] = await xo.create_actor(
        MockDeployAdapterSubscribeActor,
        address=addr,
        uid=DeployAdapterSubscribeActor.uid(),
        publish_address="test",
        main_pool=pool,
    )

    await worker.launch_adapters("fastchat")

    pool_config = (await get_pool_config(addr)).as_dict()
    assert len(pool_config["pools"]) == 2

    await worker.terminate_adapter("fastchat")
    assert len(pool_config["pools"]) == 1
