from typing import (Dict,
                    Optional, Any, List)

from openai_plugins.deploy.utils import init_openai_plugins
from openai_plugins.publish.core.resource import gather_node_info
import concurrent.futures as futures
import logging
import asyncio
import xoscar as xo
from xoscar import MainActorPoolType

from openai_plugins import openai_plugins_config
import os
import signal

import platform
from openai_plugins.publish.core.deploy_adapter_subscription_actor import DeployAdapterSubscriptionActor
from openai_plugins.utils import json_dumps

logger = logging.getLogger(__name__)
DEFAULT_NODE_HEARTBEAT_INTERVAL = 5


class DeployAdapterSubscribeActor(xo.StatelessActor):
    '''
    Subscribe to the profile endpoint
    '''

    def __init__(
            self,
            publish_address: str,
            main_pool: MainActorPoolType,
    ) -> None:
        super().__init__()
        self._publish_address = publish_address
        self._publish_ref = None
        self._plugins_names = None

        self._main_pool = main_pool
        self._main_pool.recover_sub_pool = self.recover_sub_pool

        # internal states.
        self._plugins_uid_to_adapter: Dict[str, xo.ActorRefType["DeployAdapterSubscriptionActor"]] = {}
        self._plugins_uid_to_adapter_spec: Dict[str, Dict[str, Any]] = {}

        self._plugins_uid_to_adapter_addr: Dict[str, str] = {}
        self._plugins_uid_to_adapter_launch_args: Dict[str, Dict] = {}

    async def recover_sub_pool(self, address):
        """子线程池恢复,TODO 如果开启了多个子线程池，终止一个子线程池，导致这个地址一直重新启动，这里无法判断是否是被删除的子线程池
        所以 create_subscribe_actor_pool 的auto_recover从 auto_recover="process"改为False，不自动恢复
            await xo.create_actor_pool(
                address=address,
                n_process=0,
                auto_recover=False,
                subprocess_start_method=subprocess_start_method,
                logging_conf={"dict": logging_conf},
            )
        """
        # logger.warning("Process %s is down, create adapter.", address)
        # for model_uid, addr in self._plugins_uid_to_adapter_addr.items():
        #     if addr == address:
        #         launch_args = self._plugins_uid_to_adapter_launch_args.get(model_uid)
        #         try:
        #             # 销毁adapter
        #             await self.terminate_adapter(model_uid)
        #         except Exception:
        #             pass
        #         await self.launch_adapters(plugins_name=model_uid, request_limits=launch_args.get("request_limits"))
        #         break

    async def report_status(self):
        """心跳上报"""
        status = await asyncio.to_thread(gather_node_info)
        await self._publish_ref.report_openai_plugin_status(self.address, status)

    async def _periodical_report_status(self):
        """心跳上报"""
        while True:
            try:
                await self.report_status()
            except asyncio.CancelledError:  # pragma: no cover
                break
            except RuntimeError as ex:  # pragma: no cover
                if "cannot schedule new futures" not in str(ex):
                    # when atexit is triggered, the default pool might be shutdown
                    # and to_thread will fail
                    break
            except (
                    Exception
            ) as ex:  # pragma: no cover  # noqa: E722  # nosec  # pylint: disable=bare-except
                logger.error(f"Failed to upload node info: {ex}")
            try:
                await asyncio.sleep(DEFAULT_NODE_HEARTBEAT_INTERVAL)
            except asyncio.CancelledError:  # pragma: no cover
                break

    @classmethod
    def uid(cls) -> str:
        return "subscribe"

    async def __post_create__(self):

        from openai_plugins.publish.core.deploy_adapter_publish_actor import ProfileEndpointPublishActor

        self._publish_ref: xo.ActorRefType["ProfileEndpointPublishActor"] = await xo.actor_ref(
            address=self._publish_address, uid=ProfileEndpointPublishActor.uid()
        )
        await self._publish_ref.add_openai_plugin_subscribe(self.address)
        self._upload_task = asyncio.create_task(self._periodical_report_status())
        logger.info(f"openai_plugins worker {self.address} started")
        #  查询openai_plugins 组件
        plugins_names = openai_plugins_config()
        self._plugins_names = plugins_names
        logger.info(f"openai_plugins worker {self.address} plugins_names: {plugins_names}")
        # 跳过键盘中断，使用xoscar的信号处理
        signal.signal(signal.SIGINT, lambda *_: None)

    async def __pre_destroy__(self):
        _plugins_uid_to_adapter = self._plugins_uid_to_adapter.copy()
        for plugins_name, adapter_ref in _plugins_uid_to_adapter.items():
            try:
                await self.terminate_adapter(plugins_name)
            except Exception:
                pass

        self._upload_task.cancel()
        await self._publish_ref.remove_openai_plugin_subscribe(self.address)

    async def get_adapter_count(self) -> int:
        return len(self._plugins_uid_to_adapter)

    async def get_plugins_names(self) -> List[str]:

        return self._plugins_names

    async def _create_subpool(
            self
    ) -> str:
        env = {}
        if os.name != "nt" and platform.system() != "Darwin":
            # Linux
            start_method = "forkserver"
        else:
            # Windows and macOS
            start_method = "spawn"
        subpool_address = await self._main_pool.append_sub_pool(
            env=env, start_method=start_method
        )
        return subpool_address

    async def launch_adapters(
            self,
            plugins_name: str,
            request_limits: Optional[int] = None,
            **kwargs,
    ):
        launch_args = locals()
        launch_args.pop("self")
        #  查询openai_plugins 组件
        plugins_names = openai_plugins_config()
        # 判断插件是否存在
        if plugins_name not in plugins_names:
            raise ValueError(f"openai_plugins not found in the adapter list, uid: {plugins_name}")

        subpool_address = await self._create_subpool()

        try:
            adapter_ref = await xo.create_actor(
                DeployAdapterSubscriptionActor,
                address=subpool_address,
                uid=plugins_name,
                plugins_name=plugins_name,
                request_limits=request_limits
            )
            await adapter_ref.load()
            # await adapter_ref.start()
            adapter_description = await adapter_ref.adapters_description()
        except Exception as e:
            logger.info(f"Failed to launch adapter {plugins_name}", exc_info=True)
            process = self._main_pool.sub_processes[subpool_address]
            await self._main_pool.stop_sub_pool(address=subpool_address, process=process, force=True)
            raise e

        self._plugins_uid_to_adapter[plugins_name] = adapter_ref
        self._plugins_uid_to_adapter_spec[plugins_name] = adapter_description
        self._plugins_uid_to_adapter_addr[plugins_name] = subpool_address
        self._plugins_uid_to_adapter_launch_args[plugins_name] = launch_args

    async def terminate_adapter(self, plugins_name: str):
        adapter_ref = self._plugins_uid_to_adapter.get(plugins_name, None)
        if adapter_ref is None:
            raise ValueError(f"openai_plugins not found in the adapter list, uid: {plugins_name}")

        try:
            await xo.destroy_actor(adapter_ref)
        except Exception as e:
            logger.debug(
                "Destroy adapter actor failed, adapter uid: %s, error: %s", plugins_name, e
            )
        try:
            subpool_address = self._plugins_uid_to_adapter_addr[plugins_name]
            process = self._main_pool.sub_processes[subpool_address]
            # await self._main_pool.stop_sub_pool(address=subpool_address, process=process)

            try:
                os.kill(process.pid, signal.SIGINT)  # type: ignore
            except OSError:  # pragma: no cover
                pass
            process.terminate()
            wait_pool = futures.ThreadPoolExecutor(1)
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(wait_pool, process.join, 3)
            finally:
                wait_pool.shutdown(False)
            process.kill()
            await asyncio.to_thread(process.join, 5)
            await self._main_pool.remove_sub_pool(subpool_address)
        except Exception as e:
            logger.debug(
                "Stop sub pool failed, adapter uid: %s, error: %s", plugins_name, e
            )
        finally:
            del self._plugins_uid_to_adapter[plugins_name]
            del self._plugins_uid_to_adapter_spec[plugins_name]
            del self._plugins_uid_to_adapter_addr[plugins_name]
            del self._plugins_uid_to_adapter_launch_args[plugins_name]

    async def list_adapters(self) -> Dict[str, Dict[str, Any]]:
        ret = {}

        items = list(self._plugins_uid_to_adapter_spec.items())
        for k, v in items:
            ret[k] = v.copy()
        return ret

    def get_adapter(self, plugins_name: str) -> xo.ActorRefType["DeployAdapterSubscriptionActor"]:
        adapter_ref = self._plugins_uid_to_adapter.get(plugins_name, None)
        if adapter_ref is None:
            raise ValueError(f"openai_plugins not found in the adapter list, uid: {plugins_name}")
        return adapter_ref

    def describe_adapter(self, plugins_name: str) -> Dict[str, Any]:
        adapter_desc = self._plugins_uid_to_adapter_spec.get(plugins_name, None)
        if adapter_desc is None:
            raise ValueError(f"openai_plugins not found in the adapter list, uid: {adapter_desc}")
        return adapter_desc
