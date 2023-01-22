import random
import time
import uuid
from datetime import datetime

from .JobArgs import JobArgs


class JobState:
    """
    Run-state of the job.
    We separate this from the Job itself so we can optimize our
    networking and send just this chunk of data when necessary.
    """

    def __init__(self):
        self.state_text: str = ""
        self.progress_norm: float = 0
        self.progress_i: int = 0
        self.progress_max: int = 0


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
        self.state = JobState()
        self.queued = False
        self.running = False
        self.thread = None
        # self.on_output: None = None  # Handle the job output

    @property
    def done(self):
        return self.progress_norm == 1


    def update_step(self, num=None):
        if num is None:
            num = self.state.progress_i + 1

        self.progress_i = num
        self.progress_norm = self.progress_i / self.state.progress_max

        # tqdm_total.update()
        # if opts.show_progress_every_n_steps > 0:

    def __repr__(self):
        return f"Job({self.uid}, {self.jid}, {self.state.progress_norm})"

    def __str__(self):
        return self.__repr__()
