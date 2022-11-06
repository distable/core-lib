import sys
import traceback
from beeprint import pp
from munch import Munch

print_timing = True
last_time = False

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


def make_print(module_name):
    def ret(msg, *args, **kwargs):
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


progress_print_out = sys.stdout
