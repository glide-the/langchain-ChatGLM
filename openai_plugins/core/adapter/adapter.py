from abc import abstractmethod
from argparse import Namespace
from typing import Optional, List
import multiprocessing as mp


class LLMWorkerInfo:
    def __init__(
            self,
            worker_id: Optional[str],
            model_name: Optional[str],
            model_description: Optional[str],
            model_extra_info: Optional[str],
    ):
        self.worker_id = worker_id
        self.model_name = model_name
        self.model_description = model_description
        self.model_extra_info = model_extra_info

    def to_dict(self):
        return {
            "worker_id": self.worker_id,
            "model_name": self.model_name,
            "model_description": self.model_description,
            "model_extra_info": self.model_extra_info
        }


class ProcessesInfo:
    def __init__(
            self,
            log_level: str = "INFO",
    ):
        """
        :param args: args
        :param log_level: 日志级别
        """
        self.log_level = log_level

    def to_dict(self):
        return {
            "log_level": self.log_level
        }


class Adapter:
    state_dict: dict = {}

    def __init__(self, state_dict: dict):
        self.state_dict = state_dict

    @classmethod
    def from_config(cls, cfg=None):
        return cls()

    @classmethod
    @abstractmethod
    def class_name(cls) -> str:
        """Get class name."""
