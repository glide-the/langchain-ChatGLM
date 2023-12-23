import inspect
import os
from collections import namedtuple
from typing import Optional, Any, List, TypeVar, Type

from openai_plugins.adapter.adapter import Adapter
from openai_plugins.application import ApplicationAdapter
from openai_plugins.controller import ControllerAdapter


# 使用注册回调适配器
class CallbackAdapter:

    def get_callbacks(self) -> List[Adapter]:
        raise NotImplementedError

    def add_callback(self, callback_adapter: Adapter):
        raise NotImplementedError

    def clear(self):
        raise NotImplementedError

    def remove(self, callback_adapter: Adapter):
        raise NotImplementedError


class ControllerCallbackAdapter(CallbackAdapter):
    def __init__(self, callback_adapter: List[ControllerAdapter] = []):
        super().__init__()
        self._adapters = callback_adapter

    def get_callbacks(self) -> List[ControllerAdapter]:
        return self._adapters

    def add_callback(self, callback_adapter: ControllerAdapter):
        self._adapters.append(callback_adapter)

    def clear(self):
        self._adapters.clear()

    def remove(self, callback_adapter: ControllerAdapter):
        self._adapters.remove(callback_adapter)


class ApplicationCallbackAdapter(CallbackAdapter):
    def __init__(self, callback_adapter: List[ApplicationAdapter] = []):
        super().__init__()
        self._adapters = callback_adapter

    def get_callbacks(self) -> List[ApplicationAdapter]:
        return self._adapters

    def add_callback(self, callback_adapter: ApplicationAdapter):
        self._adapters.append(callback_adapter)

    def clear(self):
        self._adapters.clear()

    def remove(self, callback_adapter: ApplicationAdapter):
        self._adapters.remove(callback_adapter)


class CallbackLoader:
    callbacks_controller_adapter: ControllerCallbackAdapter = ControllerCallbackAdapter(callback_adapter=[])
    callbacks_application_adapter: ApplicationCallbackAdapter = ApplicationCallbackAdapter(callback_adapter=[])


callback_map = CallbackLoader()


def clear_callbacks():
    callback_map.callbacks_controller_adapter.clear()
    callback_map.callbacks_application_adapter.clear()


def add_callback(callbacks: CallbackAdapter, adapter: Adapter):
    callbacks.add_callback(adapter)


def remove_callback(callbacks: CallbackAdapter, adapter: Adapter):
    callbacks.remove(adapter)


def remove_controller_callbacks_adapter(adapter: ControllerAdapter):
    remove_callback(callback_map.callbacks_controller_adapter, adapter)


def register_controller_adapter(adapter: ControllerAdapter):
    add_callback(callback_map.callbacks_controller_adapter, adapter)


def remove_application_callbacks_adapter(adapter: ControllerAdapter):
    remove_callback(callback_map.callbacks_application_adapter, adapter)


def register_application_adapter(adapter: ControllerAdapter):
    add_callback(callback_map.callbacks_application_adapter, adapter)
