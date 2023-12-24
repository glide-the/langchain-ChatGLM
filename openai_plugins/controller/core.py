from typing import Optional, List
from abc import abstractmethod
from openai_plugins.adapter.adapter import Adapter, LLMWorkerInfo


class ControllerAdapter(Adapter):

    @abstractmethod
    def list_running_models(self) -> List[LLMWorkerInfo]:
        raise NotImplementedError

    @abstractmethod
    def get_model_config(self, model_name) -> LLMWorkerInfo:
        raise NotImplementedError

    @abstractmethod
    def stop(self, model_name: str):
        raise NotImplementedError

    @abstractmethod
    def change(self, model_name: str, new_model_name: str ):
        raise NotImplementedError
