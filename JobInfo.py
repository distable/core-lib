import inspect
import types
from typing import Callable

from . import paths
from .paths import split_jid
from .JobArgs import JobArgs
from .printlib import printerr


class JobInfo:
    def __init__(self, jid=None, jfunc: Callable = None, plugin=None, key=None, is_alias=False):
        self.jid = jid
        self.func: Callable = jfunc
        self.plugid = plugin.id
        self.key = key
        self.is_alias = is_alias

    @property
    def short_jid(self):
        plug, job = paths.split_jid(self.jid, True)
        return job

    def get_paramclass(self, directly_under_job=False):
        """
        Get the parameters for a job query
        """
        for p in inspect.signature(self.func).parameters.values():
            if '_empty' not in str(p.annotation):
                ptype = type(p.annotation)
                if ptype == type:
                    if not directly_under_job:
                        return p.annotation
                    else:
                        ancestry = inspect.getmro(p.annotation)
                        # Find the first class that is not JobArgs
                        for c in reversed(ancestry):
                            if c == JobArgs: continue
                            if c == object: continue
                            return c

                elif ptype == types.ModuleType:
                    printerr("Make sure to use the type, not the module, when annotating jobparameters with @plugjob.")
                else:
                    printerr(f"Unknown jobparameter type: {ptype}")

    def find_entry(self, munch):
        """
        Find the entry for a plugin in a list of tuple (id, dict) where id is 'plug.job' or 'job'
        """
        munch = munch if munch else dict()

        jplug, jname = split_jid(self.jid, True)
        if self.plugid in munch:
            v = munch[self.plugid]
            if jname in v:
                return v[jname]
        return dict()

    def new_args(self, kwargs) -> JobArgs:
        """
        Instantiate job parameters for a matching job.
        Args:
            kwargs: The parameters for the JobArgs' constructor.

        Returns: A new JobArgs of the matching type.
        """

        # Bake the job parameters
        for k, v in kwargs.items():
            if callable(v):
                kwargs[k] = v()

        return self.get_paramclass()(**kwargs)

    def get_groupclass(self):
        if self.key is not None:
            return self.key
        else:
            return self.get_paramclass()


    def __repr__(self):
        return f"JobInfo({self.jid}, {self.plugid}->{self.func},alias={self.is_alias})"