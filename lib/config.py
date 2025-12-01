DEBUG = False
VERBOSE = False

def is_verbose() -> bool:
    return VERBOSE

def set_verbose(verbose: bool):
    global VERBOSE
    VERBOSE = verbose

def is_debug() -> bool:
    return DEBUG

def set_debug(debug: bool):
    global DEBUG
    DEBUG = debug
