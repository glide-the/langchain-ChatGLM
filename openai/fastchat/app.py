from openai_plugins.adapter.adapter import ProcessesInfo
from openai_plugins.application import ApplicationAdapter


class FastChatApplicationAdapter(ApplicationAdapter):
    def __init__(self, state_dict: dict = None):
        _state_dict = {
            "application_name": "fastchat",
            "application_version": "0.0.1",
            "application_description": "fastchat application",
            "application_author": "fastchat"
        }
        if state_dict is not None and _state_dict is not None:
            _state_dict = {**state_dict, **_state_dict}
        else:
            # 处理其中一个或两者都为 None 的情况
            _state_dict = state_dict or _state_dict or {}

        super().__init__(state_dict=_state_dict)

    def init_processes(self, processesInfo: ProcessesInfo):
        pass

    def start(self):
        pass

    def stop(self):
        pass


