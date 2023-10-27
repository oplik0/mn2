
import os
from select import POLLIN
import signal
import sys
import time
from typing import List, Optional
import contextlib

def isReadable( poller ):
        "Check whether a Poll object has a readable fd."
        for fdmask in poller.poll( 0 ):
            mask = fdmask[ 1 ]
            if mask & POLLIN:
                return True
            return False
def is_atty():
    "Check whether stdin is a tty."
    return os.isatty( sys.stdin.fileno() )


def wait_listening(client, server:str="127.0.0.1", port: int=80, timeout: int = None):
    """Wait until server is listening on given port."""
    start_time = time.time()
    client.cmd(f"{'timeout ' + timeout +' ' if timeout else ''}sh -c 'until nc -z {server} {port} > /dev/null; do sleep 0.2; done'")
    if timeout and time.time() - start_time > timeout:
        return False
    return True

def bit_convert(bits: int, ps: bool = False, precision: int = 2, format = None):
    bytes = False
    if format in ["B", "K", "M", "G", "A"]:
        bytes = True
        format = format.lower()
        bits = bits // 8
    unit_scale = bits.bit_length() // 10
    if format=="b" or unit_scale == 0:
        return f"{bits} {'B' if bytes else 'b'}{'ps' if ps else ''}"
    elif format == "k" or unit_scale == 1:
        return f"{round(bits / (2**10), precision)} K{'B' if bytes else 'b'}{'ps' if ps else ''}"
    elif format == "g" or unit_scale == 2:
        return f"{round(bits / (2**20), precision)} M{'B' if bytes else 'b'}{'ps' if ps else ''}"
    elif unit_scale == 3:
        return f"{round(bits / (2**30), precision)} G{'B' if bytes else 'b'}{'ps' if ps else ''}"
    
def optional_list(value: Optional[List[str]]) -> List[str]:
    return value if value else []



class timeout(contextlib.ContextDecorator):
    def __init__(self, seconds, *, suppress_timeout_errors=False):
        self.seconds = int(seconds)
        self.suppress = bool(suppress_timeout_errors)

    def _timeout_handler(self, signum, frame):
        raise TimeoutError()

    def __enter__(self):
        signal.signal(signal.SIGALRM, self._timeout_handler)
        signal.alarm(self.seconds)

    def __exit__(self, exc_type, exc_val, exc_tb):
        signal.alarm(0)
        if self.suppress and exc_type is TimeoutError:
            return True