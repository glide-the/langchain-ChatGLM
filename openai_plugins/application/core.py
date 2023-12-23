from typing import Optional, List
from abc import abstractmethod
from openai_plugins.adapter.adapter import Adapter, LLMWorkerInfo, ProcessesInfo


class ApplicationAdapter(Adapter):

    def __init__(self, state_dict: dict):
        super().__init__(state_dict)

    @abstractmethod
    def init_processes(self, processesInfo: ProcessesInfo):
        raise NotImplementedError

    @abstractmethod
    def start(self):
        raise NotImplementedError

    @abstractmethod
    def stop(self):
        raise NotImplementedError
