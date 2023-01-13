import sys
import traceback
from contextlib import contextmanager
from time import perf_counter

import torch

print_timing = True
print_trace = True
print_gputrace = True

last_time = False

# Set default decimal precision for printing
torch.set_printoptions(precision=2)


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
    s = f'{name}: {perf_counter() - start:.3f}s'
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
