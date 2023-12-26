
import multiprocessing as mp

# 信号队列，用于模型控制，包含如下信号：start, stop, replace
shared_queue: mp.Queue = None
# 信号队列，模型控制完成后，向该队列发送信号,包含如下信号：started, stopped, replaced
shared_completed_queue: mp.Queue = None
