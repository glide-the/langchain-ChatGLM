from typing import List
from abc import abstractmethod
from openai_plugins.core.adapter.adapter import Adapter, LLMWorkerInfo


class ProfileEndpointAdapter(Adapter):
    """Adapter for the profile endpoint."""

    @abstractmethod
    def list_running_models(self) -> List[LLMWorkerInfo]:
        raise NotImplementedError

    @abstractmethod
    def get_model_config(self, model_name) -> LLMWorkerInfo:
        raise NotImplementedError
