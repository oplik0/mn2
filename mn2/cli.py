


from curses import noecho
from hashlib import sha1
from os import wait
from select import poll
import select
import sys
from typing import Any


def start_mn2( mn ):
    from prompt_toolkit import PromptSession
    from prompt_toolkit.document import Document
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.completion import CompleteEvent, Completer, Completion, merge_completers
    import typer
    from typer.rich_utils import rich_format_error
    from typing import List, Optional, Any
    from typing_extensions import Annotated
    from pathlib import Path
    from click.parser import split_arg_string
    from click.shell_completion import CompletionItem
    import re
    from rich import print
    from rich.console import Console
    from rich.table import Table
    from rich.tree import Tree
    from rich.traceback import Traceback
    from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
    from subprocess import call
    from enum import Enum
    import csv
    from os import environ
    import time
    sleep = time.sleep
    from mininet.node import Node
    
    stderr = Console(stderr=True)

    import locale
    if locale.getpreferredencoding() != "UTF-8":
        print("Warning: your locale is not set to UTF-8, this may cause issues with mn2. Trying to override it...", console=stderr)
        try:
            locale.setlocale(locale.getlocale()[0], "UTF-8")
            print("Locale overriden successfully", console=stderr)
        except locale.Error:
            print("Warning: failed to override locale", console=stderr)
    

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
    def mn_node(value: str):
        try:
            return mn[value]
        except KeyError as e:
            raise typer.BadParameter(f"Host {value} not found in topology")
    app = typer.Typer(name="mn2>", 
                      rich_markup_mode="rich", 
                      pretty_exceptions_enable=True, 
                      add_completion=False, 
                      help="mn2 is an improved version of the Mininet CLI. It is based on Typer and Prompt Toolkit, and provides a more user-friendly and complete interface to Mininet.",
                      context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
                      )
    @app.command(hidden=True, help="", context_settings={"ignore_unknown_options": True})
    def default(ctx: typer.Context, host: Annotated[Node, typer.Argument(help="Host to run the command on", parser=mn_node)], cmd: Annotated[List[str], typer.Argument(help="Commands to run on the host", shell_complete=False)]):
        cmd_string = " ".join(cmd)
        node = host
        hostRegex = re.compile(f"(?:$|(?<=[\s\$/:]))(?P<host>h1|h2|s1|c0)(?=[\s:\.]|$)")
        final_cmd = hostRegex.sub(lambda match: mn[match.group("host")].defaultIntf().updateIP() or match.group("host"), cmd_string)
        node.sendCmd(final_cmd)

        nodePoller = poll()
        nodePoller.register(node.stdout)
        bothPoller = poll()
        bothPoller.register(node.stdout)
        bothPoller.register(sys.stdin)
        inPoller = poll()
        inPoller.register(sys.stdin)
        if is_atty():
            quietRun('stty -icanon min 1')
        while True:
            try:
                bothPoller.poll()

                if isReadable(inPoller):
                    node.write(sys.stdin.read(1))
                if isReadable(nodePoller):
                    data = node.monitor()
                    print(data)
                if not node.waiting:
                    break
            except KeyboardInterrupt:
                node.sendInt()
            except select.error as e:
                errno_, errmsg = e.args
                if errno_ != errno.EINTR:
                    node.sendInt()
                    raise


    @app.command()
    def help(ctx: typer.Context, command: Annotated[Optional[str], typer.Argument()] = None):
        """Get help on the CLI or a single command."""
        print("\n Type 'command --help' or 'help <command>' for help on a specific command.")
        if not command:
            ctx.parent.get_help()
            return
        ctx.parent.command.get_command(ctx, command).get_help(ctx)
    
    @app.command(rich_help_panel="Topology")
    def nodes(no_ip: Annotated[bool, typer.Option("--no-ip", help="Don't show IP addresses")]=False):
        """List all nodes in the topology."""
        table = Table(title="Available nodes", expand=True)
        table.add_column("Node", justify="left", style="cyan")
        if not no_ip:
            table.add_column("IP", justify="left", style="green")
        for node in sorted(mn):
            additional_info = []
            if not no_ip:
                additional_info.append(mn[node].IP())
            table.add_row(node, *additional_info)
        print(table)
    
    @app.command(rich_help_panel="Topology")
    def ports():
        """List ports and interfaces for each switch"""
        tree = Tree("Switches")
        for switch in sorted(mn.switches):
            sw_tree = tree.add(str(switch), style="cyan")
            for intf in switch.intfList():
                port = switch.ports[intf]
                sw_tree.add(f"{intf}:{port}", style="green")
        print(tree)
    
    @app.command(rich_help_panel="Topology")
    def net():
        """Dump connections from/to nodes"""
        dumpNodeConnections(mn.values())
    
    @app.command(rich_help_panel="Topology")
    def intfs():
        """List interfaces for each node"""
        tree = Tree("Interfaces")
        for node in sorted(mn):
            node_tree = tree.add(str(node), style="cyan")
            for intf in mn[node].intfNames():
                node_tree.add(intf, style="green")
        print(tree)
    @app.command(rich_help_panel="Topology")
    def dump():
        """Dump node info"""
        for node in mn.values():
            print(repr(node))
    
    @app.command(rich_help_panel="Topology")
    def links():
        """List links"""
        for link in mn.links:
            print(link)
    
    class LinkStatus(str, Enum):
        up = "up"
        down = "down"

    @app.command(rich_help_panel="Topology")
    def link(end1: Annotated[str, typer.Argument(help="First node")], end2: Annotated[str, typer.Argument(help="Second node")], status: Annotated[LinkStatus, typer.Argument(help="Set link status")]):
        """Change the status of links between nodes"""
        mn.configLinkStatus(end1, end2, status)
    
    class SwitchAction(str, Enum):
        start = "start"
        stop = "stop"
        restart = "restart"

    @app.command(rich_help_panel="Topology")
    def switch(switch: Annotated[Node, typer.Argument(help="Switch to run the command on", parser=mn_node)], action: Annotated[SwitchAction, typer.Argument(help="What to do with the switch", shell_complete=False)]):
        sw = str(switch)
        if mn[sw] not in mn.switches:
            raise typer.BadParameter(f"Node {sw} is not a switch")
        if action == SwitchAction.start:
            mn[sw].start(mn.controllers)
        elif action == SwitchAction.stop:
            mn[sw].stop(deleteIntfs=False)
        elif action == SwitchAction.restart:
            mn[sw].stop(deleteIntfs=False)
            mn[sw].start(mn.controllers)

    @app.command(rich_help_panel="Scripting")
    def sh(cmd: Annotated[List[str], typer.Argument(help="Commands to run on the host", shell_complete=False)]):
        """Run an external shell command"""
        call(cmd, shell=True)
    
    @app.command(rich_help_panel="Scripting")
    def py(expr: Annotated[List[str], typer.Argument(help="Expression to evaluate", shell_complete=False)]):
        try:
            result = eval(" ".join(expr), globals(), mn)
            if result is None:
                return
            print(result)
        except Exception as e:
            stderr.print_exception(e)

    @app.command(rich_help_panel="Scripting")
    def px(expr: Annotated[List[str], typer.Argument(help="Expression to evaluate", shell_complete=False)]):
        try:
            exec(" ".join(expr), globals(), mn)
        except Exception as e:
            stderr.print_exception(e)

    @app.command(rich_help_panel="Scripting")
    def source(script: Annotated[typer.FileText, typer.Argument(help="Script to run")]):
        """Run a script file"""
        for line in script.readlines():
            process_command(line)

    @app.command(rich_help_panel="Testing utilities")
    def pingall(all: Annotated[bool, typer.Option("--all", "-a", help="Return all ping results")]=False):
        """Ping between all hosts."""
        if all:
            mn.pingAllFull()
        else:
            mn.pingAll()
    
    @app.command(rich_help_panel="Testing utilities")
    def pingpair(all: Annotated[bool, typer.Option("--all", "-a", help="Return all ping results")]=False):
        """Ping between first two hosts, useful for testing."""
        if all:
            mn.pingPairFull()
        else:
            mn.pingPair()
    
    @app.command(rich_help_panel="Testing utilities")
    def pingallfull():
        """Ping between all hosts returning all results, useful for testing."""
        mn.pingAllFull()
    
    @app.command(rich_help_panel="Testing utilities")
    def pingpairfull():
        """Ping between first two hosts returning all results, useful for testing."""
        mn.pingPairFull()
    
    @app.command(rich_help_panel="Testing utilities")
    def ping(
        hosts: Annotated[List[str], typer.Argument(help="Hosts to ping (at least two)")], 
        timeout: Annotated[int, typer.Option("--timeout", "-t", help="Time to wait for a response, in seconds")] = 30
        ):
        """Run a ping between hosts."""
        if len(hosts) < 2:
            raise typer.BadParameter("At least two hosts are needed to run a ping test")
        if any(host not in mn for host in hosts):
            invalid_hosts = [host for host in hosts if host not in mn]
            raise typer.BadParameter(f"Hosts must be in the topology - missing hosts: {str(invalid_hosts)[1:-1]}")
        mn.ping([mn[host] for host in hosts], timeout)
    
    class TOS(str, Enum):
        IPTOS_LOWDELAY = str(0x10)
        IPTOS_THROUGHPUT = str(0x08)
        IPTOS_RELIABILITY = str(0x04)
        IPTOS_MINCOST = str(0x02)
        def __int__(self):
            return self.score

    def wait_listening(client, server:str="127.0.0.1", port: int=80, timeout: int = None):
        """Wait until server is listening on given port."""
        start_time = time.time()
        client.cmd(f"{'timeout ' + timeout +' ' if timeout else ''}sh -c 'until nc -z {server} {port} > /dev/null; do sleep 0.2; done'")
        if timeout and time.time() - start_time > timeout:
            return False
        return True
    
    def bit_convert(bits: int, ps: bool = False, precision: int = 2):
        unit_scale = bits.bit_length() // 10
        if unit_scale == 0:
            return f"{bits} bps"
        elif unit_scale == 1:
            return f"{round(bits / (2**10), precision)} kb{'ps' if ps else ''}"
        elif unit_scale == 2:
            return f"{round(bits / (2**20), precision)} Mb{'ps' if ps else ''}"
        elif unit_scale == 3:
            return f"{round(bits / (2**30), precision)} Gb{'ps' if ps else ''}"
    def run_iperf(
            server: Node,
            clients: List[Node],
            port: int,
            format: str,
            length: int,
            udp: bool,
            window: int,
            mss: int,
            nodelay: bool,
            time: int,
            bandwidth: str,
            dualtest: bool,
            num: int,
            tradeoff: bool,
            tos: int,
            ttl: int,
            file: Path,
            precision: int
    ):
        if server.waiting:
            server.sendInt()
            server.monitor(timeoutms=100)
        server.cmd("killall -9 iperf")
        iperf_server_cmd = f"iperf -y C -s -p {port} --len {length}{' -u' if udp else ''} &"
        iperf_client_cmd = f"iperf -y C -c {server.IP()} -p {port} -t {time} --len {length} {'-u' if udp else ''} {'--window ' + window if window else ''} {'--mss ' + mss if mss else ''} {'--nodelay' if nodelay else ''} {'--bandwidth ' + bandwidth if bandwidth else ''} {'--dualtest' if dualtest else ''} {'--num ' + str(num) if num else ''} {'--tradeoff' if tradeoff else ''} {'--tos' + hex(tos) if tos else ''} {'--ttl ' + str(ttl) if ttl else ''} {'-F ' + file.absolute() if file else ''}"
        
        table = Table(title="iperf results", expand=True)
        table.add_column("Client", justify="left", style="cyan")
        table.add_column("Client IP", justify="left", style="green")
        table.add_column("Server IP", justify="left", style="green")
        table.add_column("Interval", justify="left", style="cyan")
        table.add_column("Sent", justify="left", style="cyan")
        table.add_column("Rate (server)", justify="left", style="green")
        table.add_column("Rate (client)", justify="left", style="green")

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), TimeElapsedColumn(), transient=True) as progress:
            server_progress = progress.add_task("Starting iperf server", total=True)
            server.sendCmd(iperf_server_cmd)

            for client in clients:
                if not udp and not wait_listening(client, server.IP(), port):
                    raise Exception("iperf server failed to start")
                progress.update(server_progress, completed=True, description=f"Started iperf server on {server.name}")
                client_progress = progress.add_task(f"Running iperf client on {client.name}", total=True)
                cliout = client.cmd(iperf_client_cmd)
                client_csv = [line for line in cliout.strip().split("\n") if line.count(",")>=4]
                iperf_fieldnames = ["date", "client_ip", "client_port", "server_ip", "server_port", "ip_version", "interval", "sent", "rate"]
                client_reader = csv.DictReader(client_csv, fieldnames=iperf_fieldnames)
                client_values = [row for row in client_reader]
                while True:
                    serverout = server.monitor( timeoutms=5000 )
                    server_csv = [line for line in serverout.strip().split("\n") if line.count(",")>=4]
                    server_reader = csv.DictReader(server_csv, fieldnames=iperf_fieldnames)
                    server_values = [row for row in server_reader]
                    for value in server_values:
                        if value["client_ip"] == server.IP():
                            value["client_ip"], value["server_ip"] = value["server_ip"], value["client_ip"]
                            value["client_port"], value["server_port"] = value["server_port"], value["client_port"]
                    if len(server_values) and int(server_values[-1]["rate"]) > 0:
                        break
                table.add_row(client.name, client.IP(), server.IP(), server_values[-1]["interval"], bit_convert(int(client_values[-1]["sent"])), bit_convert(int(server_values[-1]["rate"]), True), bit_convert(int(client_values[-1]["rate"]), True))
                progress.update(client_progress, completed=True)
        print(table)
        server.sendInt()
        server.cmd("killall -9 iperf")


    @app.command(rich_help_panel="Testing utilities")
    def iperf(
        server: Annotated[Node, typer.Argument(help="Server to run iperf on", parser=mn_node)], 
        clients: Annotated[List[Node], typer.Argument(help="Clients to run iperf from", parser=mn_node)],
        port: Annotated[int, typer.Option("--port", "-p", help="Port to run iperf on")]=5001,
        format: Annotated[str, typer.Option("--format", "-f", help="A letter specifying the format for printing bandwidth numbers")]="m",
        length: Annotated[int, typer.Option("--length", "-l", help="Length of buffer to read or write (default 8 KB)")]=8192,
        udp: Annotated[bool, typer.Option("--udp", "-u", help="Use UDP instead of TCP")]=False,
        window: Annotated[int, typer.Option("--window", "-w", help="TCP window size")]=None,
        mss: Annotated[int, typer.Option("--mss", "-m", help="TCP maximum segment size")]=None,
        nodelay: Annotated[bool, typer.Option("--nodelay", "-N", help="Set TCP no delay, disabling Nagle's Algorithm")]=False,
        time: Annotated[int, typer.Option("--time", "-t", help="The time in seconds to transmit for")]=10,
        bandwidth: Annotated[int, typer.Option("--bandwidth", "-b", help="Set UDP target bandwidth to n bits/sec, implies UDP", )]=None,
        dualtest: Annotated[bool, typer.Option("--dualtest", "-d", help="Do a bidirectional test simultaneously")]=False,
        num: Annotated[int, typer.Option("--num", "-n", help="Number of buffers to transmit. Overrides the time")]=None,
        tradeoff: Annotated[bool, typer.Option("--tradeoff", "-r", help="Do a bidirectional test sequentially (server connects to client after the client test)")]=False,
        tos: Annotated[TOS, typer.Option("--tos", "-S", help="Set the IP type of service (tos) field in the IP header")]=None,
        tos_custom: Annotated[int, typer.Option("--tos-custom", help="Set the IP type of service (tos) field in the IP header to the specified value, for when you need something not specified in RFC 1349")]=None,
        ttl: Annotated[int, typer.Option("--ttl", help="Set the IP TTL field")]=None,
        file: Annotated[Path, typer.Option("--file", "-F", help="Use a file as a representative stream for measuring bandwidth")]=None,
        precision: Annotated[int, typer.Option("--precision", help="Number of decimal places to print (only really useful for fast links)")]=2,
        ):
        """Run iperf between hosts."""
        tos = tos_custom or (int(tos) if tos else None)
        run_iperf(server, clients, port, format, length, udp, window, mss, nodelay, time, bandwidth, dualtest, num, tradeoff, tos, ttl, file, precision)

    @app.command(rich_help_panel="Testing utilities")
    def iperfudp(
        server: Annotated[Node, typer.Argument(help="Server to run iperf on",  parser=mn_node)], 
        clients: Annotated[List[Node], typer.Argument(help="Clients to run iperf from", parser=mn_node)],
        port: Annotated[int, typer.Option("--port", "-p", help="Port to run iperf on")]=5001,
        format: Annotated[str, typer.Option("--format", "-f", help="A letter specifying the format for printing bandwidth numbers")]="m",
        length: Annotated[int, typer.Option("--length", "-l", help="Length of buffer to read or write (default 8 KB)")]=8192,
        time: Annotated[int, typer.Option("--time", "-t", help="The time in seconds to transmit for")]=10,
        bandwidth: Annotated[int, typer.Option("--bandwidth", "-b", help="Set UDP target bandwidth to n bits/sec", )]=None,
        dualtest: Annotated[bool, typer.Option("--dualtest", "-d", help="Do a bidirectional test simultaneously")]=False,
        num: Annotated[int, typer.Option("--num", "-n", help="Number of buffers to transmit. Overrides the time")]=None,
        tradeoff: Annotated[bool, typer.Option("--tradeoff", "-r", help="Do a bidirectional test sequentially (server connects to client after the client test)")]=False,
        tos: Annotated[TOS, typer.Option("--tos", "-S", help="Set the IP type of service (tos) field in the IP header", case_sensitive=False)]=None,
        tos_custom: Annotated[int, typer.Option("--tos-custom", help="Set the IP type of service (tos) field in the IP header to the specified value, for when you need something not specified in RFC 1349")]=None,
        ttl: Annotated[int, typer.Option("--ttl", help="Set the IP TTL field")]=None,
        file: Annotated[Path, typer.Option("--file", "-F", help="Use a file as a representative stream for measuring bandwidth")]=None,
        precision: Annotated[int, typer.Option("--precision", help="Number of decimal places to print (only really useful for fast links)")]=2,
        ):
        """Run iperf between hosts."""
        tos = tos_custom or (int(tos) if tos else None)
        run_iperf(server, clients, port, format, length, True, None, None, None, time, bandwidth, dualtest, num, tradeoff, tos, ttl, file, precision)

    @app.command(rich_help_panel="Node connections")
    def xterm(nodes: Annotated[List[Node], typer.Argument(help="Nodes to spawn xterm for", parser=mn_node)], term: Annotated[str, typer.Option("--term", "-t", help="Terminal type (xterm, xterm-color, gnome-terminal, ...)")]="xterm"):
        """Spawn xterm for given node(s)"""
        for node in nodes:
            mn.terms += makeTerms([node], term = term)

    @app.command(rich_help_panel="Node connections")
    def x(node: Annotated[Node, typer.Argument(help="Node to create X11 tunnel for", parser=mn_node)], cmd: Annotated[List[str], typer.Argument(help="Command to run on the host", shell_complete=False)]):
        """Create an X11 tunnel for a node"""
        mn.terms += runX11(node, cmd)
    @app.command(rich_help_panel="Node connections")
    def gterm(nodes: Annotated[List[Node], typer.Argument(help="Nodes to spawn gnome-terminal for", parser=mn_node)], term: Annotated[str, typer.Option("--term", "-t", help="Terminal type (xterm, xterm-color, gterm, ...)")]="gterm"):
        """Spawn gnome-terminal for given node(s)"""
        xterm(nodes, term)

    @app.command(rich_help_panel="utils")
    def wait():
        """Wait for all switches to connect to the controller"""
        mn.waitConnected()
    
    @app.command(rich_help_panel="utils")
    def dpctl(cmd: Annotated[List[str], typer.Argument(help="dptcl command to run", shell_complete=False)]):
        """Run dpctl on all switches"""
        tree = Tree("Results")
        for switch in mn.switches:
            tree.add(f"{switch.name}", style="cyan")
            switch.dpctl(*cmd)

    @app.command(hidden=True)
    def exit(ctx: typer.Context):
        """Exit the CLI"""
        raise typer.Exit()
    
    @app.command(hidden=True)
    def quit(ctx: typer.Context):
        """Exit the CLI"""
        raise typer.Exit()

    @app.command()
    def noecho(ctx: typer.Context, cmd: Annotated[List[str], typer.Argument(help="Commands to run", shell_complete=False)]):
        """Run a command with echoing turned off"""
        if is_atty():
            quietRun( 'stty -echo' )
        try:
            ctx.invoke(ctx.parent.command, *cmd)
        finally:
            if is_atty():
                quietRun( 'stty echo' )

    def overlap(a, b):
        return max(i for i in range(len(b)) if b[i-1] == a[-1] and a.endswith(b[:i]))

    commands = typer.main.get_group(app)
    class TyperCompleter(Completer):
        def get_completions(self, document: Document, complete_event: CompleteEvent):
            args = split_arg_string(document.text)
            completions: List[CompletionItem] = commands.shell_complete(commands.make_context("mn2", args), document.text_before_cursor)
            for item in completions:
                yield Completion(item.value, start_position=-overlap(document.text_before_cursor, item.value), display_meta=item.help)
    class MnCompleter(Completer):
        def get_completions(self, document: Document, complete_event: CompleteEvent):
            last_word = document.get_word_before_cursor()
            if last_word.startswith("h") or last_word.startswith("s") or last_word.startswith("c"):
                for key in mn.keys():
                    if key.startswith(last_word):
                        yield Completion(key, 
                                         start_position=-overlap(document.text_before_cursor, key),
                                         display_meta=f"Mininet {mn[key].__class__.__name__} {mn[key].name}"
                                         )
            
    app_dir = Path(typer.get_app_dir("mn2"))
    history_file = app_dir / ".history"
    if not app_dir.exists():
        app_dir.mkdir(parents=True)
    if not history_file.exists():
        history_file.touch()
    session = PromptSession(history=FileHistory(history_file), 
                            auto_suggest=AutoSuggestFromHistory(),
                            completer=merge_completers([TyperCompleter(), MnCompleter()], deduplicate=True)
                            )
    

    command = typer.main.get_command(app)
    def process_command(text: str):
        if not len(text.strip()) or text.strip().startswith("#"):
            return
        argv = split_arg_string(text)
        if argv[0] not in commands.commands.keys():
            argv.insert(0, "default")
        return command(argv, standalone_mode=False)

    while True:
        try:
            text = session.prompt('mn2> ')
        except KeyboardInterrupt:
            continue
        except EOFError:
            break
        else:
            try:
                process_command(text)
            except typer.Exit as e:
                if e.code != 0:
                    raise EOFError
            except typer.Abort:
                raise EOFError
            except KeyboardInterrupt:
                pass
            except Exception as e:
                if hasattr(e, "format_message"):
                    rich_format_error(e)
                else:
                    tb = Traceback.from_exception(
                        type(e),
                        e,
                        e.__traceback__,
                        show_locals=app.pretty_exceptions_show_locals,
                        suppress=[
                            "pygments",
                            "prompt_toolkit",
                            "click",
                            "typer",
                        ]
                    )
                    stderr.print(tb)

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