from .JobArgs import JobArgs


class prompt_job(JobArgs):
    def __init__(self, prompt: str = None, p: str = None, **kwargs):
        super().__init__(**kwargs)
        self.prompt = prompt or p or ''