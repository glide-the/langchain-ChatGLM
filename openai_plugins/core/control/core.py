from typing import List
from abc import abstractmethod
from openai_plugins.core.adapter.adapter import Adapter, LLMWorkerInfo, ProcessesInfo


class ControlAdapter(Adapter):
    processesInfo: ProcessesInfo = None

    def init_processes(self, processesInfo: ProcessesInfo):
        self.processesInfo = processesInfo

    @abstractmethod
    def start(self, new_model_name: str):
        raise NotImplementedError

    def start(self, pid: str, new_model_name: str):
        self.start(new_model_name=new_model_name)

        self.processesInfo.completed_queue.put([new_model_name, "started", None, pid])

    @abstractmethod
    def stop(self, model_name: str):
        raise NotImplementedError

    def stop(self, pid: str, model_name: str):
        self.stop(model_name=model_name)

        self.processesInfo.completed_queue.put([model_name, "stopped", None, pid])

    @abstractmethod
    def replace(self, model_name: str, new_model_name: str):
        raise NotImplementedError

    def replace(self, pid: str, model_name: str, new_model_name: str):
        self.replace(model_name=model_name, new_model_name=new_model_name)

        self.processesInfo.completed_queue.put([model_name, "replaced", new_model_name, pid])
