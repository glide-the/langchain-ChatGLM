from typing import List

from openai_plugins.adapter.adapter import LLMWorkerInfo
from openai_plugins.controller import ControllerAdapter


class FastChatControllerAdapter(ControllerAdapter):
    def __init__(self, state_dict: dict = None):
        _state_dict = {
            "controller_name": "fastchat",
            "controller_version": "0.0.1",
            "controller_description": "fastchat controller",
            "controller_author": "fastchat"
        }
        if state_dict is not None and _state_dict is not None:
            _state_dict = {**state_dict, **_state_dict}
        else:
            # 处理其中一个或两者都为 None 的情况
            _state_dict = state_dict or _state_dict or {}

        super().__init__(state_dict=_state_dict)

    def list_workers(self) -> List[LLMWorkerInfo]:
        pass

    def stop_worker(self, worker_id):
        pass

    def start_worker(self, worker_id):
        pass

    def get_worker_status(self, worker_id) -> LLMWorkerInfo:
        pass




