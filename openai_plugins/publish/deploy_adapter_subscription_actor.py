import xoscar as xo
import asyncio
import inspect
import os
from typing import (
    TYPE_CHECKING, Optional, Callable,
)

if TYPE_CHECKING:
    from openai_plugins.callback.core import ApplicationAdapter
    from openai_plugins.callback.core import ControlAdapter
    from openai_plugins.callback.core import ProfileEndpointAdapter
from configs import logger
from openai_plugins.utils import json_dumps

try:
    from torch.cuda import OutOfMemoryError
except ImportError:

    class _OutOfMemoryError(Exception):
        pass


    OutOfMemoryError = _OutOfMemoryError


def request_limit(fn):
    """
    Used by ModelActor.
    As a decorator, added to a ModelActor method to control
    how many requests are accessing that method at the same time.
    """

    async def wrapped_func(self, *args, **kwargs):
        logger.debug(
            f"Request {fn.__name__}, current serve request count: {self._serve_count}, request limit:"
            f" {self._request_limits} for the model {self.model_uid()}"
        )
        if self._request_limits is not None:
            if 1 + self._serve_count <= self._request_limits:
                self._serve_count += 1
            else:
                raise RuntimeError(
                    f"Rate limit reached for the model. Request limit {self._request_limits} "
                    f"for the model: {self.plugins_name()}"
                )
        try:
            ret = await fn(self, *args, **kwargs)
        finally:
            if self._request_limits is not None:
                self._serve_count -= 1
            logger.debug(
                f"After request {fn.__name__}, current serve request count: {self._serve_count}"
                f" for the model {self.plugins_name()}"
            )
        return ret

    return wrapped_func


class DeployAdapterSubscriptionActor(xo.StatelessActor):

    def __init__(self,
                 plugins_name: str,
                 app_adapter: "ApplicationAdapter",
                 control_adapter: "ControlAdapter",
                 profile_endpoint_adapter: "ProfileEndpointAdapter",
                 request_limits: Optional[int] = None):
        super().__init__()
        self._plugins_name = plugins_name
        self._app_adapter = app_adapter
        self._control_adapter = control_adapter
        self._profile_endpoint_adapter = profile_endpoint_adapter
        self._request_limits = request_limits
        self._lock = (
            None
            if isinstance(self._app_adapter, ApplicationAdapter) or

               isinstance(self._control_adapter, ControlAdapter) or

               isinstance(self._profile_endpoint_adapter,
                          ProfileEndpointAdapter)

            else asyncio.locks.Lock()
        )
        self._serve_count = 0

    def plugins_name(self) -> str:
        return (
            self._plugins_name
            if self._plugins_name is not None
            else (
                None
            )
        )

    async def _call_wrapper(self, _wrapper: Callable):
        try:
            assert not (
                    inspect.iscoroutinefunction(_wrapper)
                    or inspect.isasyncgenfunction(_wrapper)
            )
            if self._lock is None:
                return await asyncio.to_thread(_wrapper)
            else:
                async with self._lock:
                    return await asyncio.to_thread(_wrapper)
        except OutOfMemoryError:
            logger.exception(
                "Model actor is out of memory, model id: %s", self.plugins_name()
            )
            os._exit(1)

    async def _call_async_wrapper(self, _wrapper: Callable):
        try:
            return await asyncio.create_task(_wrapper())
        except OutOfMemoryError:
            logger.exception(
                "Model actor is out of memory, model id: %s", self.plugins_name()
            )
            os._exit(1)

    @request_limit
    async def start(self):
        if not hasattr(self._app_adapter, "start"):
            raise AttributeError(f"Adapter {self._app_adapter.class_name()} is not for start.")

        def _wrapper():
            getattr(self._app_adapter, "start")()
            return None

        return await self._call_wrapper(_wrapper)

    @request_limit
    async def stop(self):
        if not hasattr(self._app_adapter, "stop"):
            raise AttributeError(f"Adapter {self._app_adapter.class_name()} is not for stop.")

        def _wrapper():
            getattr(self._app_adapter, "stop")()
            return None

        return await self._call_wrapper(_wrapper)

    @request_limit
    async def start_model(self, pid: str, new_model_name: str):
        if not hasattr(self._control_adapter, "start_model"):
            raise AttributeError(f"Adapter {self._control_adapter.class_name()} is not for start_model.")

        def _wrapper():
            getattr(self._control_adapter, "start_model")(pid=pid, new_model_name=new_model_name)
            return None

        return await self._call_wrapper(_wrapper)

    @request_limit
    async def stop_model(self, pid: str, model_name: str):
        if not hasattr(self._control_adapter, "stop_model"):
            raise AttributeError(f"Adapter {self._control_adapter.class_name()} is not for stop_model.")

        def _wrapper():
            getattr(self._control_adapter, "stop_model")(pid=pid, model_name=model_name)
            return None

        return await self._call_wrapper(_wrapper)

    @request_limit
    async def replace_model(self, pid: str, model_name: str, new_model_name: str):
        if not hasattr(self._control_adapter, "replace_model"):
            raise AttributeError(f"Adapter {self._control_adapter.class_name()} is not for replace_model.")

        def _wrapper():
            getattr(self._control_adapter, "replace_model")(pid=pid, model_name=model_name,
                                                            new_model_name=new_model_name)
            return None

        return await self._call_wrapper(_wrapper)

    @request_limit
    def list_running_models(self):
        if not hasattr(self._profile_endpoint_adapter, "list_running_models"):
            raise AttributeError(f"Adapter {self._profile_endpoint_adapter.class_name()} is not for list_running_models.")

        def _wrapper():
            data = getattr(self._profile_endpoint_adapter, "list_running_models")()
            return json_dumps(data)

        return self._call_wrapper(_wrapper)

    @request_limit
    def get_model_config(self, model_name):
        if not hasattr(self._profile_endpoint_adapter, "get_model_config"):
            raise AttributeError(f"Adapter {self._profile_endpoint_adapter.class_name()} is not for get_model_config.")

        def _wrapper():
            data = getattr(self._profile_endpoint_adapter, "get_model_config")(model_name=model_name)
            return json_dumps(data)

        return self._call_wrapper(_wrapper)
