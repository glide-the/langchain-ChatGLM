from abc import abstractmethod, ABC
from typing import List, Dict, TypeVar, Generic, Type, Optional, Set

from openai_plugins.core.adapter import Adapter
from openai_plugins.core.application import ApplicationAdapter
from openai_plugins.core.control import ControlAdapter
from openai_plugins.core.profile_endpoint import ProfileEndpointAdapter

A = TypeVar("A", bound=Adapter)


# 使用注册回调适配器
class CallbackAdapter(Generic[A], ABC):
    adapters_cls: Type[A]
    _adapters: Optional[Dict[str, List[A]]] = None

    def __init__(self, adapters: Optional[Dict[str, List[A]]] = None):
        if adapters is None:
            self._adapters = self._build()
        else:
            self._adapters = adapters

    @abstractmethod
    def _build(self) -> Dict[str, List[A]]:
        """Build the adapters."""

    def get_callbacks(self, plugins_name: str) -> List[A]:
        return self._adapters.get(plugins_name, [])

    def add_callback(self, plugins_name: str, callback_adapter: A):
        if plugins_name in self._adapters:
            self._adapters[plugins_name].append(callback_adapter)
        else:
            self._adapters[plugins_name] = [callback_adapter]

    def clear(self, plugins_name: str):
        if plugins_name in self._adapters:
            self._adapters[plugins_name].clear()
        else:
            self._adapters[plugins_name] = []

    def remove(self, plugins_name: str, adapter_class_name: str):
        if plugins_name in self._adapters:
            for adapter in self._adapters[plugins_name]:
                if adapter.class_name() == adapter_class_name:
                    self._adapters[plugins_name].remove(adapter)


class ControllerCallbackAdapter(CallbackAdapter[ControlAdapter]):
    adapters_cls: Type[A] = ControlAdapter

    def _build(self) -> Dict[str, List[ControlAdapter]]:
        return {}


class ApplicationCallbackAdapter(CallbackAdapter[ApplicationAdapter]):
    adapters_cls: Type[A] = ApplicationAdapter

    def _build(self) -> Dict[str, List[ApplicationAdapter]]:
        return {}


class ProfileEndpointCallbackAdapter(CallbackAdapter[ProfileEndpointAdapter]):
    adapters_cls: Type[A] = ProfileEndpointAdapter

    def _build(self) -> Dict[str, List[ProfileEndpointAdapter]]:
        return {}


class OpenaiPluginsLoader:
    # openai_plugins 组件加载,不重复加载
    plugins_name: Set[str] = set()
    callbacks_controller_adapter: ControllerCallbackAdapter = ControllerCallbackAdapter(adapters={})
    callbacks_application_adapter: ApplicationCallbackAdapter = ApplicationCallbackAdapter(adapters={})
    callbacks_profile_endpoint_adapter: ProfileEndpointCallbackAdapter = ProfileEndpointCallbackAdapter(adapters={})


openai_plugin_loader = OpenaiPluginsLoader()


# 以下是对外接口, 函数式编程

def clear_callbacks(plugins_name: str):
    openai_plugin_loader.callbacks_controller_adapter.clear(plugins_name=plugins_name)
    openai_plugin_loader.callbacks_application_adapter.clear(plugins_name=plugins_name)
    openai_plugin_loader.callbacks_profile_endpoint_adapter.clear(plugins_name=plugins_name)
    openai_plugin_loader.plugins_name.remove(plugins_name)


def remove_controller_callbacks_adapter(plugin_name: str, adapter_class_name: str):
    openai_plugin_loader.callbacks_controller_adapter.remove(plugins_name=plugin_name,
                                                             adapter_class_name=adapter_class_name)
    if len(openai_plugin_loader.callbacks_controller_adapter.get_callbacks(plugins_name=plugin_name)) == 0:
        openai_plugin_loader.plugins_name.remove(plugin_name)


def register_controller_adapter(plugins_name: str, adapter: ControlAdapter):
    openai_plugin_loader.callbacks_controller_adapter.add_callback(plugins_name=plugins_name,
                                                                   callback_adapter=adapter)
    openai_plugin_loader.plugins_name.add(plugins_name)


def remove_application_callbacks_adapter(plugin_name: str, adapter_class_name: str):
    openai_plugin_loader.callbacks_application_adapter.remove(plugins_name=plugin_name,
                                                              adapter_class_name=adapter_class_name)
    if len(openai_plugin_loader.callbacks_application_adapter.get_callbacks(plugins_name=plugin_name)) == 0:
        openai_plugin_loader.plugins_name.remove(plugin_name)


def register_application_adapter(plugins_name: str, adapter: ApplicationAdapter):
    openai_plugin_loader.callbacks_application_adapter.add_callback(plugins_name=plugins_name,
                                                                    callback_adapter=adapter)
    openai_plugin_loader.plugins_name.add(plugins_name)


def remove_profile_endpoint_callbacks_adapter(plugin_name: str, adapter_class_name: str):
    openai_plugin_loader.callbacks_profile_endpoint_adapter.remove(plugins_name=plugin_name,
                                                                   adapter_class_name=adapter_class_name)
    if len(openai_plugin_loader.callbacks_profile_endpoint_adapter.get_callbacks(plugins_name=plugin_name)) == 0:
        openai_plugin_loader.plugins_name.remove(plugin_name)


def register_profile_endpoint_adapter(plugins_name: str, adapter: ProfileEndpointAdapter):
    openai_plugin_loader.callbacks_profile_endpoint_adapter.add_callback(plugins_name=plugins_name,
                                                                         callback_adapter=adapter)
    openai_plugin_loader.plugins_name.add(plugins_name)
