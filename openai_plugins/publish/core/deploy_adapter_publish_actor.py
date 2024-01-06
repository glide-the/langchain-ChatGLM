from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Iterator, Optional, List

from openai_plugins.publish.core.resource import ResourceStatus
import xoscar as xo
import time
import logging
import asyncio
if TYPE_CHECKING:
    from openai_plugins.publish.core.deploy_adapter_subscribe_actor import DeployAdapterSubscribeActor
    from openai_plugins.publish.core.deploy_adapter_subscription_actor import DeployAdapterSubscriptionActor


logger = logging.getLogger(__name__)


@dataclass
class SubscribeStatus:
    update_time: float
    status: Dict[str, ResourceStatus]


class ProfileEndpointPublishActor(xo.StatelessActor):
    """
    openai profile endpoint actor
    """

    def __init__(
            self,
    ) -> None:
        super().__init__()
        self._subscribe_address_to_plugins_subscribe: Dict[str, xo.ActorRefType["DeployAdapterSubscribeActor"]] = {}
        self._subscribe_status: Dict[str, SubscribeStatus] = {}
        self._plugins_name_to_subscribe: Dict[
            str, xo.ActorRefType["DeployAdapterSubscribeActor"]
        ] = {}
        # TODO launch_subscribe时，需要加锁，防止多个请求同时创建同一个模型
        self._locks = {}
        self._uptime = None

    @classmethod
    def uid(cls) -> str:
        return "publish"

    async def __post_create__(self):
        self._uptime = time.time()
        logger.info(f"publish {self.address} started")

    async def _choose_subscribe(self, plugins_name: str) -> xo.ActorRefType["DeployAdapterSubscribeActor"]:
        # TODO: 不同的订阅提供者可能提供的资源不同,此处需要根据资源情况选择一个订阅提供者，
        min_running_adapter_count = None
        target_subscribe = None

        subscribes = list(self._subscribe_address_to_plugins_subscribe.values())
        for subscribe in subscribes:
            running_adapter_count = await subscribe.get_adapter_count()
            if (
                    min_running_adapter_count is None
                    or running_adapter_count < min_running_adapter_count
            ):
                min_running_adapter_count = running_adapter_count
                plugins_names = await subscribe.get_plugins_names()
                if plugins_name in plugins_names:
                    target_subscribe = subscribe

        if target_subscribe:
            return target_subscribe

        raise RuntimeError("No available subscribe found")

    def get_status(self) -> Dict:
        return {
            "uptime": int(time.time() - self._uptime),
            "workers": self._subscribe_status,
        }

    async def list_plugins(self) -> List[str]:
        # 获取所有的插件
        return list(self._plugins_name_to_subscribe.keys())

    async def launch_subscribe(
            self,
            plugins_name: str,
            request_limits: Optional[int] = None,
            **kwargs,
    ) -> str:
        logger.debug(
            f"Enter launch_builtin_model, request_limits: {request_limits},  "
        )

        async def _launch_one_subscribe(_plugins_name):
            if _plugins_name in self._plugins_name_to_subscribe:
                raise ValueError(
                    f"Adapter is already in the Subscribe list, plugins_name: {_plugins_name}"
                )
            subscribe_ref = await self._choose_subscribe(plugins_name=_plugins_name)

            await subscribe_ref.launch_adapters(
                plugins_name=_plugins_name,
                request_limits=request_limits,
                **kwargs,
            )
            self._plugins_name_to_subscribe[_plugins_name] = subscribe_ref

        if request_limits is not None and request_limits < 0:
            raise ValueError(
                "The `request_limits` parameter must be greater or equal than 0."
            )

        try:
            await _launch_one_subscribe(plugins_name)
        except Exception as e:
            # terminate_model will remove the replica info.
            logger.error(f"Failed to launch subscribe {plugins_name}", exc_info=True)
            await self.terminate_subscribe(plugins_name, suppress_exception=True)
            raise e
        return plugins_name

    async def terminate_subscribe(self, plugins_name: str, suppress_exception=False):
        async def _terminate_one_subscribe(_plugins_name):
            subscribe_ref = self._plugins_name_to_subscribe.get(_plugins_name, None)

            if subscribe_ref is None:
                raise ValueError(
                    f"Adapter not found in the Subscribe, plugins_name: {_plugins_name}"
                )
            await subscribe_ref.terminate_adapter(plugins_name=plugins_name)
            del self._plugins_name_to_subscribe[_plugins_name]

        subscribe_info = self._plugins_name_to_subscribe.get(plugins_name, None)
        if subscribe_info is None:
            raise ValueError(f"Adapter not found in the Subscribe list, plugins_name: {plugins_name}")

        try:
            await _terminate_one_subscribe(plugins_name)
        except Exception as e:
            if not suppress_exception:
                raise e

        self._plugins_name_to_subscribe.pop(plugins_name, None)

    async def get_subscribe(self, plugins_name: str) -> xo.ActorRefType["DeployAdapterSubscribeActor"]:

        return self._plugins_name_to_subscribe.get(plugins_name, None)

    async def get_adapter(self, plugins_name: str) -> xo.ActorRefType["DeployAdapterSubscriptionActor"]:
        subscribe_ref = self._plugins_name_to_subscribe.get(plugins_name, None)
        if subscribe_ref is None:
            raise ValueError(f"Adapter not found in the Subscribe list, plugins_name: {plugins_name}")

        return await subscribe_ref.get_adapter(plugins_name=plugins_name)

    async def describe_adapter(self, plugins_name: str) -> str:
        subscribe_ref = self._plugins_name_to_subscribe.get(plugins_name, None)
        if subscribe_ref is None:
            raise ValueError(f"Adapter not found in the Subscribe list, plugins_name: {plugins_name}")

        return await subscribe_ref.describe_adapter(plugins_name=plugins_name)

    async def add_openai_plugin_subscribe(self, subscribe_address: str):
        """ register subscribe to openai_plugins"""
        from openai_plugins.publish.core.deploy_adapter_subscribe_actor import DeployAdapterSubscribeActor

        assert (
                subscribe_address not in self._subscribe_address_to_plugins_subscribe
        ), f"Subscribe {subscribe_address} exists"

        worker_ref = await xo.actor_ref(address=subscribe_address, uid=DeployAdapterSubscribeActor.uid())
        self._subscribe_address_to_plugins_subscribe[subscribe_address] = worker_ref
        logger.debug("Subscribe %s has been added successfully", subscribe_address)

    async def remove_openai_plugin_subscribe(self, subscribe_address: str):
        if subscribe_address in self._subscribe_address_to_plugins_subscribe:
            del self._subscribe_address_to_plugins_subscribe[subscribe_address]
            logger.debug("Subscribe %s has been removed successfully", subscribe_address)
        else:
            logger.warning(
                f"Subscribe {subscribe_address} cannot be removed since it is not registered to publish."
            )

    async def report_openai_plugin_status(
            self, subscribe_address: str, status: Dict[str, ResourceStatus]
    ):
        if subscribe_address not in self._subscribe_status:
            logger.debug("Subscribe %s resources: %s", subscribe_address, status)
        self._subscribe_status[subscribe_address] = SubscribeStatus(
            update_time=time.time(), status=status
        )
