import math
import re
from pathlib import Path
from typing import Tuple

root = Path(__file__).resolve().parent.parent.parent  # TODO this isn't very robust

scripts_name = 'scripts'
userconf_name = 'user_conf.py'
plug_res_name = 'plug-res'

# Code for the core
code_core = root / 'src_core'  # conflict with package names, must be prefixed differently here

# Downloaded plugin source code
code_plugins = root / 'src_plugins'  # conflict with package names, must be prefixed differently here

# Contains the user's downloaded plugins (cloned from github)
plugins = root / 'src_plugins'

# User project scripts to run
scripts = root / 'scripts'

# Contains the resources for each plugin, categorized by plugin id
plug_res = root / plug_res_name

# Contains the logs output by each plugin, categorized by plugin id
plug_logs = root / 'plug-logs'

# Contains the repositories cloned by each plugin, categorized by plugin id
plug_repos = root / 'plug-repos'

# Image outputs are divied up into 'sessions'
# Session logic can be customized in different ways:
#   - One session per client connect
#   - Global session on a timeout
#   - Started manually by the user
sessions = root / 'sessions'

session_timestamp_format = '%Y-%m-%d_%Hh%M'

plug_res.mkdir(exist_ok=True)
plug_logs.mkdir(exist_ok=True)
plug_repos.mkdir(exist_ok=True)
sessions.mkdir(exist_ok=True)

# These suffixes will be stripped from the plugin IDs for simplicity
plugin_suffixes = ['_plugin']

video_exts = ['.mp4', '.mov', '.avi', '.mkv']

leadnum_zpad = 8


# sys.path.insert(0, root.as_posix())


def short_pid(pid):
    """
    Convert 'user/my-repository' to 'my_repository'
    """
    if isinstance(pid, Path):
        pid = pid.as_posix()

    if '/' in pid:
        pid = pid.split('/')[-1]

    # Strip suffixes
    for suffix in plugin_suffixes:
        if pid.endswith(suffix):
            pid = pid[:-len(suffix)]

    # Replace all dashes with underscores
    pid = pid.replace('-', '_')

    return pid


def split_jid(jid, allow_jobonly=False) -> Tuple[str:None, str]:
    """
    Split a plugin jid into a tuple of (plug, job)
    """
    if '.' in jid:
        s = jid.split('.')
        return s[0], s[1]

    if allow_jobonly:
        return None, jid

    raise ValueError(f"Invalid plugin jid: {jid}")


def is_session(v):
    v = str(v)
    return sessions / v in sessions.iterdir()


def parse_frames(name, frames):
    """
    parse_frames('example', '1:5') -> ('example_1_5', 1, 5)
    parse_frames('example', ':5') -> ('example_5', None, 5)
    parse_frames('example', '1:') -> ('example_1', 1, None)
    parse_frames("banner", None) -> ("banner", None, None)
    """
    if frames is not None:
        sides = frames.split(':')
        lo = sides[0]
        hi = sides[1]
        if frames.endswith(':'):
            lo = int(lo)
            return f'{name}_{lo}', lo, None
        elif frames.startswith(':'):
            hi = int(hi)
            return f'{name}_{hi}', None, hi
        else:
            lo = int(lo)
            hi = int(hi)
            return f'{name}_{lo}_{hi}', lo, hi
    else:
        return name, None, None

# region Leadnums
def get_leadnum_zpad(iterator=None, separator='', directory=None):
    """
    Find the amount of leading zeroes for the 'leading numbers' in the directory names and return it
    e.g.:
    0003123 -> 7
    00023 -> 5
    023 -> 3
    23 -> 2
    23_session -> 2
    48123_session -> 5
    """
    iterator = get_dir_iter(iterator, directory)
    if iterator is None:
        return 0

    biggest = 0
    smallest = math.inf
    for path in iterator:
        if not Path(path).is_dir():
            match = re.match(r"^(\d+)" + separator, Path(path).name)
            if match is not None:
                num = match.group(1)
                biggest = max(biggest, len(num))
                smallest = min(smallest, len(num))

    if smallest != biggest:
        return smallest
    return biggest


def is_leadnum_zpadded(iterator=None, separator='', directory=None):
    return get_leadnum_zpad(iterator, separator, directory) >= 2


def get_next_leadnum(iterator=None, separator='', directory=None):
    return get_max_leadnum(iterator, separator, directory) + 1


def get_max_leadnum(iterator=None, separator='', directory=None):
    lo, hi = get_leadnum(iterator, separator, directory)
    return hi


def get_min_leadnum(iterator=None, separator='', directory=None):
    lo, hi = get_leadnum(iterator, separator, directory)
    return lo


def get_leadnum(iterator=None, separator='', directory=None):
    """
    Find the largest 'leading number' in the directory names and return it
    e.g.:
    23_session
    24_session
    28_session
    23_session

    return value is 28
    """
    iterator = get_dir_iter(iterator, directory)
    if iterator is None:
        return 0, 0

    smallest = math.inf
    biggest = 0
    for path in iterator:
        if not Path(path).is_dir():
            match = re.match(r"^(\d+)" + separator, Path(path).name)
            if match is not None:
                num = int(match.group(1))
                if match:
                    smallest = min(smallest, num)
                    biggest = max(biggest, num)

    return smallest, biggest


# endregion


# region Utilities
def get_dir_iter(iterator, directory):
    iterator = iterator if iterator is not None else directory.iterdir()
    if isinstance(iterator, str):
        iterator = Path(iterator)
    if isinstance(iterator, Path):
        if not iterator.exists():
            iterator = None
        iterator = iterator.iterdir()
    return iterator


# endregion

def get_first_match(path: str | Path, suffix: str | None = None, name: str | None = None):
    path = Path(path)
    if not path.exists():
        return None

    for p in path.iterdir():
        if suffix is not None and p.suffix == suffix: return p
        if name is not None and p.name == name: return p
        pass

    return None

# region Scripts
def script_exists(name):
    return get_script_file_path(name).exists()


def parse_action_script(s, default=None):
    if s is None:
        return None, None

    v = s.split(':')

    action = v[0]
    script = None

    if script_exists(v[0]):
        action = v[1] if len(v) > 1 else default
        script = v[0]

    return action, script


def get_script_file_path(name):
    return Path(scripts / name).with_suffix(".py")


def get_script_module_path(name=None):
    modpath = get_script_file_path(name)
    return f'{scripts.name}.{modpath.relative_to(scripts).with_suffix("").as_posix().replace("/", ".")}'
# endregion
