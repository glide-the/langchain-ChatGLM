
from typing import Optional
import multiprocessing as mp
import pytest
import pytest_asyncio
import xoscar as xo
from xoscar import MainActorPoolType, create_actor_pool, get_pool_config
import init_folder_config
from launch_module import launch_utils
from openai_plugins.core.adapter import ProcessesInfo
from openai_plugins.deploy.utils import init_openai_plugins
from openai_plugins.publish.core.deploy_adapter_subscribe_actor import (DeployAdapterSubscribeActor)
from openai_plugins import (openai_components_plugins_register,
                            openai_install_plugins_load,
                            openai_plugins_config)
from openai_plugins.callback import (openai_plugin_loader)

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

    mp.set_start_method("spawn")

    log_level = "INFO"
    init_openai_plugins(plugins_name="fastchat", log_level=log_level)
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
