from typing import Optional, List
from abc import abstractmethod
from openai_plugins.adapter.adapter import Adapter, LLMWorkerInfo, ProcessesInfo


class ApplicationAdapter(Adapter):

    @abstractmethod
    def init_processes(self, processesInfo: ProcessesInfo):
        raise NotImplementedError

    @abstractmethod
    def start(self):
        raise NotImplementedError

    @abstractmethod
    def stop(self):
        raise NotImplementedError
