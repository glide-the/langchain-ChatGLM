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
            q: mp.Queue = None,
            started_event: mp.Event = None,
    ):
        self.model_name = model_name
        self.controller_address = controller_address
        self.log_level = log_level
        self.q = q
        self.started_event = started_event

    def to_dict(self):
        return {
            "model_name": self.model_name,
            "controller_address": self.controller_address,
            "log_level": self.log_level,
            "q": self.q,
            "started_event": self.started_event
        }


class Adapter:

    def __init__(self, state_dict: dict):
        self.state_dict = state_dict
