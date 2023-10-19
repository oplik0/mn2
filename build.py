import python_minifier
import stickytape
import sys
import base64

def build():
    
    output = stickytape.script(
        "mn2/cli.py",
        python_binary=sys.executable,
    )
    # output = python_minifier.minify(output,
    #                                 filename='cli.py',
    #                                 remove_literal_statements=True,
    #                                 remove_annotations=True,
    #                                 remove_pass=True,
    #                                 combine_imports=True,
    #                                 hoist_literals=False,
    #                                 rename_globals=False,
    #                                 rename_locals=False,
    #                                 remove_asserts=True,
    #                                 remove_debug=True,
    #                                 remove_explicit_return_none=True,
    #                                 preserve_shebang=False,
    #                                 )
    
    encoded = base64.b85encode(output.encode('utf-8'))

    target_script = f'px if not "is_mn2" in globals() or not is_mn2:from base64 import b85decode;exec(b85decode("{encoded.decode("utf-8")}"), globals(), locals()) '
    with open("dist/mn2", "w", encoding="utf-8") as f:
        f.write(target_script)
if __name__ == "__main__":
    build()