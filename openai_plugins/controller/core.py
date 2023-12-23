from typing import Optional, List
from abc import abstractmethod
from openai_plugins.adapter.adapter import Adapter, LLMWorkerInfo


class ControllerAdapter(Adapter):

    def __init__(self, state_dict: dict):
        super().__init__(state_dict)

    @abstractmethod
    def list_workers(self) -> List[LLMWorkerInfo]:
        raise NotImplementedError

    @abstractmethod
    def stop_worker(self, worker_id):
        raise NotImplementedError

    @abstractmethod
    def start_worker(self, worker_id):
        raise NotImplementedError

    @abstractmethod
    def get_worker_status(self, worker_id) -> LLMWorkerInfo:
        raise NotImplementedError
