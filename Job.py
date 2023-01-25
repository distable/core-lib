import random
import time
import uuid
from datetime import datetime

from .JobArgs import JobArgs


class Job:
    """
    A job as it appears in the
    """

    def __init__(self, jid: str | None, args: JobArgs | None):
        # Job definition
        self.uid = 0#str(random.randint(0, 2**31))
        self.jid = jid  # Jid to execute
        self.session = None
        self.aborting: bool = False
        self.timestamp_post: float = time.time()
        self.timestamp_run: float = None
        self.args: JobArgs = args
        self.queued = False
        self.running = False
        self.thread = None
        self.progress_text: str = ""
        self.progress: float = 0
        self.progress_i: int = 0
        self.progress_max: int = 0
        # self.on_output: None = None  # Handle the job output

    @property
    def done(self):
        return self.progress == 1


    def update_step(self, num=None):
        if num is None:
            num = self.progress_i + 1

        self.progress_i = num
        self.progress = self.progress_i / self.progress_max

    def update_max(self, num):
        self.progress_max = num

    def update_progress(self, progress: float):
        self.progress = progress


    def __repr__(self):
        return f"Job({self.uid}, {self.jid}, {self.state.progress})"

    def __str__(self):
        return self.__repr__()
