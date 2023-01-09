class JobArgs:
    """
    Parameters for a job
    """

    def __init__(self,
                 prompt: str = None,
                 p: str = None,
                 w: int = None,
                 h: int = None,
                 __getdefaults__=False, **kwargs):
        self.__dict__.update(kwargs)
        self.prompt = p or prompt or ''
        self.w = int(w) if w else None
        self.h = int(h) if h else None

        self.job_repeats = 1
        if 'n' in kwargs: self.job_repeats = int(kwargs['n'])
        elif 'repeats' in kwargs: self.job_repeats = int(kwargs['repeats'])

        if not __getdefaults__:
            self.defaults = self.__class__(__getdefaults__=True)

        self.job: 'Job' = None
        self.ctx: 'PipeData' = None
        self.session: 'Session' = None

    def __str__(self):
        # Print the values that have changed from the defaults
        s = ''
        for k, v in self.__dict__.items():
            if k == 'defaults': continue
            if k == 'job': continue
            if k == 'kwargs': continue
            if v != self.defaults.__dict__.get(k, None):
                s += f'{k}={v} '
        return s
