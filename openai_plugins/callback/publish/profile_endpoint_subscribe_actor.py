from typing import List

from configs import (logger, log_verbose)

import xoscar as xo

from openai_plugins.callback.core import OpenaiPluginsLoader
from openai_plugins.callback.publish.profile_endpoint_publish_actor import ProfileEndpointPublishActor
from openai_plugins.core.adapter import LLMWorkerInfo


class ProfileEndpointSubscribeActor(xo.StatelessActor):
    '''
    Subscribe to the profile endpoint
    '''
    worker_id: str = None
    openai_plugin_loader: OpenaiPluginsLoader = None

    def __init__(
            self,
            publish_address: str,
            worker_id: str = "worker",
    ) -> None:
        super().__init__()
        self.publish_address = publish_address
        self.worker_id = worker_id
        self._publish_ref: xo.ActorRefType["ProfileEndpointPublishActor"] = None

    async def __post_create__(self):
        self._publish_ref = await xo.actor_ref(address=self.publish_address, uid=ProfileEndpointPublishActor.uid)
        return self._publish_ref

    async def publish_subscription(self, openai_plugin_loader: OpenaiPluginsLoader):
        self.openai_plugin_loader = openai_plugin_loader
        return await self._publish_ref.register_subscription(self.address, self.uid)

    def list_running_models(self) -> List[LLMWorkerInfo]:
        raise NotImplementedError

    def get_model_config(self, model_name) -> LLMWorkerInfo:
        raise NotImplementedError
