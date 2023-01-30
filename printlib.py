import sys
import time
import traceback
from contextlib import contextmanager
from time import perf_counter

import numpy as np
import torch

print_timing = False
print_trace = False
print_gputrace = False

last_time = time.time()

# Set default decimal precision for printing
torch.set_printoptions(precision=2)
np.set_printoptions(precision=2, suppress=True)


# stdout = sys.stdout
# sys.stdout = None

# _print = print

# def print(*kargs, **kwargs):
#     _print(*kargs, file=stdout, **kwargs)

def run(code, task):
    try:
        code()
    except Exception as e:
        print(f"{task}: {type(e).__name__}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)


_print = print


def print(*args, **kwargs):
    from beeprint import pp
    from munch import Munch
    if isinstance(args[0], dict) or isinstance(args[0], Munch):
        pp(*args, **kwargs)
    else:
        _print(*args, **kwargs)


def print_bp(msg, *args, **kwargs):
    print(f' - {msg}', *args, **kwargs)


def printerr(msg, *args, **kwargs):
    import sys
    print(msg, *args, **kwargs)


def printerr_bp(msg, *args, **kwargs):
    print(f' - {msg}', *args, **kwargs)


def pct(f: float):
    """
    Get a constant percentage string, e.g. 23% instead of 0.23, 04% instead of 0.04
    """
    if np.isnan(f):
        return 'nan%'

    return f'{int(f * 100):02d}%'


def make_print(module_name):
    def ret(msg, *args, **kwargs):
        from yachalk import chalk
        # Wrap all args[1:] in chalk.grey
        # if len(args) > 1:
        #     args = [args[0]] + [chalk.grey(str(a)) for a in args[1:]]
        # if len(kwargs) > 1:
        #     # key in red
        #     kwargs = {chalk.white(k): chalk.dim(str(v)) for k, v in kwargs.items()}

        if not print_timing:
            print(f"[{module_name}] {msg}", *args, **kwargs)
        else:
            # Print the elapsed time since the last call to this function
            import time
            global last_time
            if last_time and print_timing:
                print(f"[{module_name}] ({time.time() - last_time:.2f}s) {msg}", *args, **kwargs)
            else:
                print(f"[{module_name}] {msg}", *args, **kwargs)
            last_time = time.time()

    return ret


def make_printerr(module_name):
    def ret(msg, *args, **kwargs):
        printerr(f"[{module_name}] {msg}", *args, **kwargs)

    return ret


@contextmanager
def trace(name) -> float:
    start = perf_counter()
    yield lambda: perf_counter() - start

    seconds = perf_counter() - start
    if seconds >= 1:
        s = f'({seconds:.3f}s) {name}'
    else:
        s = f'({int(seconds*1000)}ms) {name}'
    from yachalk import chalk
    if print_trace:
        print(chalk.grey(s))


@contextmanager
def gputrace(name, vram_dt=False) -> float:
    vram = 0
    if vram_dt:
        vram = torch.cuda.memory_allocated()
    start = perf_counter()
    yield lambda: perf_counter() - start
    s = f'{name}: {perf_counter() - start:.3f}s'
    if vram_dt:
        vram = (torch.cuda.memory_allocated() - vram) / 1024 / 1024 / 1024
        s += f' {vram:.3f}GB / {torch.cuda.memory_allocated() / 1024 / 1024 / 1024:.3f}GB'
    from yachalk import chalk
    if print_gputrace:
        print(chalk.grey(s))


@contextmanager
def cpuprofile(enable=True) -> float:
    if not enable:
        yield None
        return

    import yappi
    yappi.clear_stats()
    yappi.set_clock_type('cpu')
    yappi.start()

    yield None

    columns = {
        0: ("name", 80),
        1: ("ncall", 5),
        2: ("tsub", 8),
        3: ("ttot", 8),
        4: ("tavg", 8)
    }
    # Print and limit the number of functions to 100
    yappi.get_func_stats().print_all(columns=columns)
    yappi.stop()
    input("Press Enter to continue...")

def trace_decorator(func):
    def wrapper(*args, **kwargs):
        s = ', '.join([str(a) for a in args] + [f'{k}={v}' for k, v in kwargs.items()])
        with trace(f'{func.__name__}({s})'):
            return func(*args, **kwargs)

    return wrapper

# Override str method and return "PIL(w, h)" for PIL.Image.Image, otherwise regular str
regstr = str


def str(obj):
    from PIL import Image
    # Simplified PIL image
    if isinstance(obj, Image.Image):
        return f"PIL({obj.width}x{obj.height}, {obj.mode})"
    # Limit floats to 2 decimals
    if isinstance(obj, float):
        return f"{obj:.2f}"

    return regstr(obj)


progress_print_out = sys.stdout
