import orjson
from pydantic import BaseModel

import xoscar as xo


def json_dumps(o):
    def _default(obj):
        if isinstance(obj, BaseModel):
            return obj.dict()
        raise TypeError

    return orjson.dumps(o, default=_default)


async def create_worker_actor_pool(
        address: str, logging_conf: Optional[dict] = None
) -> "MainActorPoolType":
    subprocess_start_method = "forkserver" if os.name != "nt" else "spawn"

    return await xo.create_actor_pool(
        address=address,
        n_process=0,
        auto_recover="process",
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
                from openai_plugins.publish.deploy_adapter_publish_actor import ProfileEndpointPublishActor

                supervisor_ref: xo.ActorRefType[ProfileEndpointPublishActor] = await xo.actor_ref(
                    address=address, uid=ProfileEndpointPublishActor.uid()
                )

                await supervisor_ref.get_status()
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

    from ..isolation import Isolation

    isolation = Isolation(asyncio.new_event_loop(), threaded=True)
    isolation.start()
    available = isolation.call(health_check_internal())
    isolation.stop()
    return available


def get_timestamp_ms():
    t = time.time()
    return int(round(t * 1000))
