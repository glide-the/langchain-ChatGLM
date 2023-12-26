from typing import Optional, List
from abc import abstractmethod
from openai_plugins.adapter.adapter import Adapter, LLMWorkerInfo, ProcessesInfo


class ControllerAdapter(Adapter):
    @abstractmethod
    def init_processes(self, processesInfo: ProcessesInfo):
        raise NotImplementedError

    @abstractmethod
    def list_running_models(self) -> List[LLMWorkerInfo]:
        raise NotImplementedError

    @abstractmethod
    def get_model_config(self, model_name) -> LLMWorkerInfo:
        raise NotImplementedError

    @abstractmethod
    def start(self, pid: str, new_model_name: str):
        raise NotImplementedError

    @abstractmethod
    def stop(self, pid: str, model_name: str):
        raise NotImplementedError

    @abstractmethod
    def replace(self, pid: str, model_name: str, new_model_name: str):
        raise NotImplementedError
