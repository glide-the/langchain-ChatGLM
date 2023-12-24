from typing import List

from openai_plugins.adapter.adapter import LLMWorkerInfo
from openai_plugins.controller import ControllerAdapter


class FastChatControllerAdapter(ControllerAdapter):
    def __init__(self, state_dict: dict = None):
        super().__init__(state_dict=state_dict)

    def list_running_models(self) -> List[LLMWorkerInfo]:
        pass

    def get_model_config(self, model_name) -> LLMWorkerInfo:
        pass

    def stop(self, model_name: str):
        pass

    def change(self, model_name: str, new_model_name: str):
        pass

    @classmethod
    def from_config(cls, cfg=None):
        _state_dict = {
            "controller_name": "fastchat",
            "controller_version": "0.0.1",
            "controller_description": "fastchat controller",
            "controller_author": "fastchat"
        }
        state_dict = cfg.get("state_dict", {})
        if state_dict is not None and _state_dict is not None:
            _state_dict = {**state_dict, **_state_dict}
        else:
            # 处理其中一个或两者都为 None 的情况
            _state_dict = state_dict or _state_dict or {}

        return cls(state_dict=_state_dict)




