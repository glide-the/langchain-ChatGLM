from typing import Optional, List
from abc import abstractmethod
from openai_plugins.adapter.adapter import Adapter, LLMWorkerInfo, ProcessesInfo


class ControllerAdapter(Adapter):
    processesInfo: ProcessesInfo = None

    def init_processes(self, processesInfo: ProcessesInfo):
        self.processesInfo = processesInfo

    @abstractmethod
    def list_running_models(self) -> List[LLMWorkerInfo]:
        raise NotImplementedError

    @abstractmethod
    def get_model_config(self, model_name) -> LLMWorkerInfo:
        raise NotImplementedError

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
