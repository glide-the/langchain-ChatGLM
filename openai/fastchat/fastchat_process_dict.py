from multiprocessing import Process
from typing import Dict

mp_manager = None
processes: Dict[str, Process] = {}
