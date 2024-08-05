from typing import Callable, Any, Dict, Optional, Type, Union
from abc import ABC, abstractmethod

__all__ = ["regist_graph", "InputHandler", "EventHandler"]

_GRAPHS_REGISTRY: Dict[str, Dict[str, Any]] = {}


class InputHandler(ABC):
    @abstractmethod
    def create_inputs(self, query: str, metadata: dict) -> Dict[str, Any]:
        pass


class EventHandler(ABC):
    @abstractmethod
    def handle_event(self, event: Dict[str, Any]) -> str:
        pass


def regist_graph(name: str, input_handler: Type[InputHandler], event_handler: Type[EventHandler]) -> Callable:
    """
    装饰器, 用于注册 graph 到注册表中
    :param name: 图的名称
    :param input_handler: 输入数据结构
    :param event_handler: 输出数据结构
    :return: 被装饰的函数
    """
    def wrapper(func: Callable) -> Callable:
        _GRAPHS_REGISTRY[name] = {
            "func": func,
            "input_handler": input_handler,
            "event_handler": event_handler
        }
        return func
    return wrapper
