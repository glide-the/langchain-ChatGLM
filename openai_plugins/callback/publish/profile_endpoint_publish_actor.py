from configs import (logger, log_verbose)

import xoscar as xo


class ProfileEndpointPublishActor(xo.StatelessActor):
    """
    openai profile endpoint actor
    """
    uid = "controller"

    def __init__(
            self,
    ) -> None:
        super().__init__()
        self._worker_refs = {}

    async def register_subscription(
            self,
            worker_addr: str,
            worker_id: str
    ) -> bool:
        """
        register subscription to profile endpoint
        :param worker_addr:
        :param worker_id:
        :return:
        """

        key = (worker_addr, worker_id)
        logger.info(f"worker registered: {key}")
        self._worker_refs[key] = await xo.actor_ref(address=worker_addr, uid=worker_id)
        return True

    async def choose_worker(self) -> xo.ActorRefType["ProfileEndpointSubscribeActor"]:
        return list(self._worker_refs.values())[0]
