from openai_plugins.callback.core import OpenaiPluginsLoader
from openai_plugins.callback.publish.profile_endpoint_publish_actor import ProfileEndpointPublishActor
from configs import (logger, log_verbose)

from openai_plugins.callback.bootstrap import Bootstrap
import asyncio
import multiprocessing as mp
import signal
import sys

import xoscar as xo

import threading

from openai_plugins.callback.publish.profile_endpoint_subscribe_actor import ProfileEndpointSubscribeActor


class OpenaiPluginsBootstrapBaseWeb(Bootstrap):
    """
    Bootstrap Server Lifecycle
    """
    publish_thread: threading
    subscribe_thread: threading
    openai_plugin_loader: OpenaiPluginsLoader = None

    def __init__(self, publish_address: str, subscription_address: str):
        super().__init__()

        self.publish_address = publish_address
        self.subscription_address = subscription_address

    @classmethod
    def from_config(cls, cfg=None):
        publish_address = cfg.get("publish_address")
        subscription_address = cfg.get("subscription_address")
        return cls(publish_address=publish_address, subscription_address=subscription_address)

    def set_openai_plugin_loader(self, openai_plugin_loader: OpenaiPluginsLoader):
        self.openai_plugin_loader = openai_plugin_loader

    async def run_publish_thread(self):
        def sigterm_handler(signum, frame):
            sys.exit(0)

        async def _start_publish(address: str):
            pool = None
            try:
                pool = await xo.create_actor_pool(
                    address=address, n_process=0
                )
                await xo.create_actor(
                    ProfileEndpointPublishActor, address=address, uid=ProfileEndpointPublishActor.uid
                )
                await pool.join()
            except asyncio.exceptions.CancelledError:
                if pool is not None:
                    await pool.stop()

        signal.signal(signal.SIGTERM, sigterm_handler)

        self.publish_thread = threading.Thread(target=_start_publish,
                                               kwargs={"address": self.publish_address})
        self.publish_thread.start()

    async def run_subscribe_thread(self):
        def sigterm_handler(signum, frame):
            sys.exit(0)

        async def _start_subscribe(publish_address: str, subscription_address: str):
            async def heart_beat():
                while True:
                    try:
                        await subscription_worker.register_to_controller()
                    except Exception as e:
                        logger.error(e)
                    finally:
                        await asyncio.sleep(5)

            pool = None
            try:
                pool = await xo.create_actor_pool(
                    address=worker_addr, n_process=0
                )
                # TODO 此处暂不支持多个
                subscription_worker: ProfileEndpointSubscribeActor = await xo.create_actor(
                    ProfileEndpointSubscribeActor,
                    address=subscription_address,
                    uid=ProfileEndpointSubscribeActor.uid,
                    controller_addr=publish_address,
                )
                await subscription_worker.publish_subscription(self.openai_plugin_loader)
                asyncio.create_task(heart_beat())
                await pool.join()
            except asyncio.exceptions.CancelledError:
                if pool is not None:
                    await pool.stop()

        signal.signal(signal.SIGTERM, sigterm_handler)

        self.publish_thread = threading.Thread(target=_start_subscribe,
                                               kwargs={"address": self.host + ":" + str(self.port)})
        self.publish_thread.start()

    async def destroy(self):
        subscribe_thread = self.subscribe_thread
        subscribe_thread.join()  # 等待服务器线程结束
        publish_thread = self.publish_thread
        publish_thread.join()  # 等待服务器线程结束
