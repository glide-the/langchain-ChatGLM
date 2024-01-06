from abc import abstractmethod
from argparse import Namespace
from typing import Optional, List
import multiprocessing as mp
from typing_extensions import Literal, NotRequired, TypedDict


class LLMWorkerInfo(TypedDict):
    worker_id: Optional[str]
    model_name: Optional[str]
    model_description: Optional[str]
    model_extra_info: Optional[str]


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
