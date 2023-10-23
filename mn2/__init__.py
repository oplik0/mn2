
from mn2.cli import start_mn2


if __name__ == "mininet.cli":
    global is_mn2
    initial_globals = globals().copy()
    initial_locals = locals().copy()
    is_mn2 = True
    try:
        start_mn2( net )
    except Exception as e:
        print(e)
        import traceback
        traceback.print_exc()
    finally:
        is_mn2 = False
        globals().update(initial_globals)
        locals().update(initial_locals)