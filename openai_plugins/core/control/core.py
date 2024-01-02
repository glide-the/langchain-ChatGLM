from typing import List
from abc import abstractmethod
from openai_plugins.core.adapter.adapter import Adapter, LLMWorkerInfo, ProcessesInfo


class ControlAdapter(Adapter):
    processesInfo: ProcessesInfo = None

    def init_processes(self, processesInfo: ProcessesInfo):
        self.processesInfo = processesInfo

    @abstractmethod
    def start_model(self, new_model_name: str):
        raise NotImplementedError

    @abstractmethod
    def stop_model(self, model_name: str):
        raise NotImplementedError

    @abstractmethod
    def replace_model(self, model_name: str, new_model_name: str):
        raise NotImplementedError
