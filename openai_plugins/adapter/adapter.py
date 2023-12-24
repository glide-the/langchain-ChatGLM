from typing import Optional, List
import multiprocessing as mp


class LLMWorkerInfo:
    def __init__(
            self,
            worker_id: Optional[str],
            model_name: Optional[str],
            model_description: Optional[str]
    ):
        self.worker_id = worker_id
        self.model_name = model_name
        self.model_description = model_description

    def to_dict(self):
        return {
            "worker_id": self.worker_id,
            "model_name": self.model_name,
            "model_description": self.model_description
        }


class ProcessesInfo:
    def __init__(
            self,
            model_name: Optional[str],
            controller_address: Optional[str],
            log_level: str = "INFO",
            queue: mp.Queue = None,
            mp_manager=None,
    ):
        """

        :param model_name: 模型 name
        :param controller_address: 接口地址
        :param log_level: 日志级别
        :param q: 信号队列
        :param mp_manager:  进程管理器
        """
        self.model_name = model_name
        self.controller_address = controller_address
        self.log_level = log_level
        self.queue = queue
        self.mp_manager = mp_manager

    def to_dict(self):
        return {
            "model_name": self.model_name,
            "controller_address": self.controller_address,
            "log_level": self.log_level,
            "queue": self.queue,
            "mp_manager": self.mp_manager
        }


class Adapter:
    state_dict: dict = {}

    def __init__(self, state_dict: dict):
        self.state_dict = state_dict

    @classmethod
    def from_config(cls, cfg=None):
        return cls()
