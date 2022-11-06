from datetime import datetime
from pathlib import Path

from PIL.Image import Image

from . import paths
from .JobInfo import JobInfo
from .PipeData import PipeData
from .paths import get_next_leadnum
from .logs import logsession, logsession_err


class Session:
    def __init__(self, name=None, path: Path | str = None, **kwargs):
        self.context = PipeData()
        self.jobs = []
        self.args = dict()
        self.autosave = True

        if name is not None:
            self.name = name
            self.path = (paths.sessions / name).as_posix()
        elif path is not None:
            self.path = Path(path)
            self.name = Path(path).stem
        else:
            self.valid = False
            logsession_err("Cannot create session! No name or path given!")
            return

        if Path(self.path).exists():
            self.load_if_exists()
        else:
            logsession("New session:", self.name)

    @staticmethod
    def now(prefix='', **kwargs):
        """
        Returns: A new session which is timestamped to now
        """
        return Session(prefix + paths.format_session_id(datetime.now().strftime(paths.session_timestamp_format), **kwargs))

    @staticmethod
    def now_or_recent(recent_window=60 * 5, **kwargs):
        """
        Returns: A new session which is timestamped
        """
        now = datetime.now()

        # Check with pathlib and lstat
        for p in paths.sessions.iterdir():
            if p.is_dir():
                if (now - datetime.fromtimestamp(p.stat().st_mtime)).seconds < recent_window:
                    return Session(path=p, **kwargs)

        return Session.now()

    def load_if_exists(self):
        if self.path.exists():
            # Set the context to the most recent file in the session directory
            recent = self.path / max(self.path.iterdir(), key=lambda p: p.stat().st_mtime)
            self.context = PipeData.file(recent)
            logsession(f"Load session {self.name}")
            # TODO load a session metadata file

    def save_next(self, dat: PipeData = None):
        if dat is None:
            dat = self.context

        path = self.path / str(get_next_leadnum(self.path, ''))
        self.save(dat, path)

        if self.context.file is str:
            p = Path(self.path / self.context.file)
            p = p.with_name(get_next_leadnum(Path(self.context.file).stem))
            p = p.relative_to(self.path)
            self.context.file = p

    def save(self, dat: PipeData, path):
        dat.save(path)

    def add_job(self, j):
        self.jobs.append(j)

    def rem_job(self, j):
        self.jobs.remove(j)

    def add_kwargs(self, ifo: JobInfo, kwargs):
        key = ifo.get_groupclass()
        if key in self.args:
            self.args[key].update(kwargs)
        else:
            self.args[key] = {**kwargs}

    def get_kwargs(self, ifo: JobInfo):
        key = ifo.get_groupclass()
        if key in self.args:
            return self.args[key]
        else:
            return {}

    # def run(self, query: JobArgs | str | None = None, **kwargs):
    #     """
    #     Run a job in the current session context, meaning the output JobState data will be saved to disk
    #     """
    #     ret = plugins.run(query, print=logsession, **kwargs)
    #     current.save_next(ret)
    #     print("")
