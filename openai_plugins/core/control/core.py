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

    def start_model(self, pid: str, new_model_name: str):
        self.start_model(new_model_name=new_model_name)

        self.processesInfo.completed_queue.put([new_model_name, "started", None, pid])

    @abstractmethod
    def stop_model(self, model_name: str):
        raise NotImplementedError

    def stop_model(self, pid: str, model_name: str):
        self.stop_model(model_name=model_name)

        self.processesInfo.completed_queue.put([model_name, "stopped", None, pid])

    @abstractmethod
    def replace_model(self, model_name: str, new_model_name: str):
        raise NotImplementedError

    def replace_model(self, pid: str, model_name: str, new_model_name: str):
        self.replace_model(model_name=model_name, new_model_name=new_model_name)

        self.processesInfo.completed_queue.put([model_name, "replaced", new_model_name, pid])
