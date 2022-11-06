import os
import signal


def extract_dict(obj, *names):
    return {x: getattr(obj, x) for x in names}




def setup_ctrl_c(func=None):
    def sigint_handler(sig, frame):
        print(f'Interrupted with signal {sig} in {frame}')
        if func:
            func()
        else:
            os._exit(0)

    # CTRL-C handler
    signal.signal(signal.SIGINT, sigint_handler)
