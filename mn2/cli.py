from datetime import datetime
from turtle import st
from prompt_toolkit import PromptSession
from prompt_toolkit.document import Document
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import CompleteEvent, Completer, Completion, merge_completers, PathCompleter
import typer
from typer.rich_utils import rich_format_error
from typer.completion import shell_complete
from typing import List, Optional, Any, cast
from typing_extensions import Annotated
from pathlib import Path
from click import MultiCommand
from click.parser import split_arg_string
from click.shell_completion import CompletionItem
import re
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.traceback import Traceback
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from subprocess import TimeoutExpired, call
from enum import Enum
from select import poll
import select
import sys
import csv
from os import environ
import time
import errno
from pathvalidate import sanitize_filepath
import builtins
import threading
from concurrent.futures import ThreadPoolExecutor
sleep = time.sleep

from mininet.node import Node
from mininet.util import quietRun, dumpNodeConnections
from mininet.term import makeTerms, runX11

import locale

from mn2.utils import isReadable, is_atty, wait_listening, bit_convert, optional_list, timeout

def start_mn2( mn ):
    
    stderr = Console(stderr=True)
    console = Console()

    if locale.getpreferredencoding() != "UTF-8":
        stderr.print("Warning: your locale is not set to UTF-8, this may cause issues with mn2. Trying to override it...")
        try:
            locale.setlocale(locale.LC_ALL, "UTF-8")
            stderr.print("Locale overriden successfully")
        except locale.Error:
            stderr.print("Warning: failed to override locale. You might need to change your system locale (e.g. usinag `sudo localectl set-locale LANG=en_US.UTF-8`)")
    
    def mn_node(value: str):
        try:
            return mn[value]
        except KeyError as e:
            raise typer.BadParameter(f"Host {value} not found in topology")
    
    def default_parser(value: str):
        try:
            return mn[value]
        except KeyError as e:
            if Path(value).exists():
                return Path(value)
            raise typer.BadParameter(f"Host {value} not found in topology")
    app = typer.Typer(name="mn2>", 
                      rich_markup_mode="rich", 
                      pretty_exceptions_enable=True, 
                      pretty_exceptions_show_locals=False,
                      add_completion=False, 
                      help="mn2 is an improved version of the Mininet CLI. It is based on Typer and Prompt Toolkit, and provides a more user-friendly and complete interface to Mininet.",
                      context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
                      )
    @app.command(hidden=True, help="", context_settings={"ignore_unknown_options": True})
    def default(ctx: typer.Context, host: Annotated[Node, typer.Argument(help="Host to run the command on", parser=default_parser)], cmd: Annotated[List[str], typer.Argument(help="Commands to run on the host", shell_complete=False, callback=optional_list)]):
        if isinstance(host, Node):
            if cmd is None or (len(cmd)==1 and cmd[0] == ""):
                raise typer.BadParameter("No command given")
            cmd_string = " ".join(cmd)
            node = host
            hostRegex = re.compile(f"(?:$|(?<=[\s\$/:]))(?P<host>{'|'.join(mn.keys())})(?=[\s:\.]|$)")
            final_cmd = hostRegex.sub(lambda match: mn[match.group("host")].IP() or match.group("host"), cmd_string)
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
                        console.print(data)
                    if not node.waiting:
                        break
                except KeyboardInterrupt:
                    node.sendInt()
                except select.error as e:
                    errno_, errmsg = e.args
                    if errno_ != errno.EINTR:
                        node.sendInt()
                        raise
        elif isinstance(host, Path):
            with host.open() as f:
                source(f, cmd)

    @app.command()
    def help(ctx: typer.Context, command: Annotated[Optional[str], typer.Argument()] = None):
        """Get help on the CLI or a single command."""
        console.print("\n Type 'command --help' or 'help <command>' for help on a specific command.")
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
        console.print(table)
    
    @app.command(rich_help_panel="Topology")
    def ports():
        """List ports and interfaces for each switch"""
        tree = Tree("Switches")
        for switch in sorted(mn.switches):
            sw_tree = tree.add(str(switch), style="cyan")
            for intf in switch.intfList():
                port = switch.ports[intf]
                sw_tree.add(f"{intf}:{port}", style="green")
        console.print(tree)
    
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
        console.print(tree)
    @app.command(rich_help_panel="Topology")
    def dump():
        """Dump node info"""
        for node in mn.values():
            console.print(repr(node))
    
    @app.command(rich_help_panel="Topology")
    def links():
        """List links"""
        for link in mn.links:
            console.print(link)
    
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
            console.print(result)
        except Exception as e:
            stderr.print_exception(e)

    @app.command(rich_help_panel="Scripting")
    def px(expr: Annotated[List[str], typer.Argument(help="Expression to evaluate", shell_complete=False)]):
        try:
            exec(" ".join(expr), globals(), mn)
        except Exception as e:
            stderr.print_exception(e)

    @app.command(rich_help_panel="Scripting")
    def source(script: Annotated[typer.FileText, typer.Argument(help="Script to run")], args: Annotated[List[str], typer.Argument(help="Arguments to pass to the script in name=value format. Will replace {name} in script with the given string", shell_complete=False, callback=optional_list)]):
        """Run a script file"""
        argdict = {}
        arglist = []
        if len(args):
            for index,arg in enumerate(args):
                if "=" in arg:
                    key, value = arg.split("=", 1)
                    argdict[key] = value
                    argdict[index] = value
                else:
                    argdict[index] = arg
                    arglist.append(arg)
        for line in script.readlines():
            try:
                # don't parse extremely long lines for performance reasons
                if len(line) < 100_000:
                    line = line.strip().format(*arglist, **argdict)
            except ValueError:
                pass
            try:
                process_command(line)
            except Exception as e:
                stderr.print_exception(e)
    @app.command(rich_help_panel="Scripting")
    def run(script: Annotated[typer.FileText, typer.Argument(help="Script to run")]):
        """Run a script file"""
        argdict = { f"$"  }
        
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
            iperf_time: int,
            bandwidth: str,
            dualtest: bool,
            num: int,
            tradeoff: bool,
            tos: int,
            ttl: int,
            file: Path,
            precision: int,
            parallel: bool,
            simultaneous: bool,
            fail_fast: bool,
            retries: int = 3,
            output: Path = None,
            congestion: str = None,
            additional_args: dict = {},
    ):
        if server.waiting:
            server.sendInt()
            server.monitor(timeoutms=100)
        if length == 8192:
            length = None
        server.cmd("killall -9 iperf")
        iperf_server_cmd = f"iperf -y C -s -p {port} {'--len ' + str(length) if length and (dualtest or tradeoff) else ''}{' -u' if udp or bandwidth else ''} {'-Z' + congestion if congestion else ''}"
        iperf_client_cmd = f"iperf -y C -c {server.IP()} -p {port} -t {iperf_time} --len {length} {'-u' if udp or bandwidth else ''} {'--window ' + str(window) if window else ''} {'--mss ' + str(mss) if mss else ''} {'--nodelay' if nodelay else ''} {'--bandwidth ' + str(bandwidth) if bandwidth else ''} {'--dualtest' if dualtest else ''} {'--num ' + str(num) if num else ''} {'--tradeoff' if tradeoff else ''} {'--tos' + hex(tos) if tos else ''} {'--ttl ' + str(ttl) if ttl else ''} {'-F ' + str(file) if file else ''} {'-P ' + str(parallel) if parallel else ''}  {'-Z' + congestion if congestion else ''}"
        
        table = Table(title="iperf results", expand=True)
        table.add_column("Client", justify="left", style="cyan")
        table.add_column("Client IP", justify="left", style="green")
        table.add_column("Server", justify="left", style="cyan")
        table.add_column("Server IP", justify="left", style="green")
        table.add_column("Interval", justify="left", style="blue")
        table.add_column("Rate (server)", justify="left", style="yellow")
        table.add_column("Rate (client)", justify="left", style="yellow")
        table.add_column("Transfered", justify="left", style="magenta")
        if udp or bandwidth:
            table.add_column("Jitter", justify="left", style="blue")
            table.add_column("Sent", justify="left", style="magenta")
            table.add_column("Received", justify="left", style="magenta")
            table.add_column("Loss", justify="left", style="red")
            table.add_column("Out of order", justify="left", style="red")
        listening = threading.Barrier(len(clients) + 1 if simultaneous else 2, timeout=20)
        finished = threading.Barrier(len(clients)+1 if simultaneous else 2, timeout=iperf_time+10 if simultaneous else iperf_time*len(clients)+10)
        server_values = None
        iperf_fieldnames = ["date", "client_ip", "client_port", "server_ip", "server_port", "process_number", "interval", "transmitted", "rate", "jitter", "lost", "sent", "loss", "out of order"]
        failed = False
        try:
            with timeout((iperf_time + 2) * (len(clients) if not simultaneous else 1)):
                with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), TimeElapsedColumn(), transient=True) as progress:
                    def server_thread():
                        server_progress = progress.add_task("Starting iperf server", total=True)
                        popen = server.popen(iperf_server_cmd, shell=True, text=True)
                        listening.wait()
                        progress.update(server_progress, completed=True, description=f"Started iperf server on {server.name}")
                        server_values = {}
                        data = ""
                        finished.wait()
                        results_progress = progress.add_task("Collecting results", total=len(clients))
                        start = time.time()
                        while len(server_values) < len(clients) and time.time() - start < (iperf_time * len(clients)) + 10:
                            progress.update(results_progress, description=f"Collecting results ({len(server_values)}/{len(clients)})")
                            data += popen.stdout.readline()
                            server_csv = [line for line in data.strip().split() if line.count(",")>=4]
                            server_reader = csv.DictReader(server_csv, fieldnames=iperf_fieldnames)
                            server_values = {**server_values, **{row["server_ip"] : row for row in server_reader if int(row.get("rate", "0")) > 0}}
                        progress.update(results_progress, description="Finished collecting results")
                        for value in server_values.values():
                            if value["client_ip"] == server.IP():
                                value["client_ip"], value["server_ip"] = value["server_ip"], value["client_ip"]
                                value["client_port"], value["server_port"] = value["server_port"], value["client_port"]
                        return server_values

                    def node_thread(client: Node, last = False):
                        client_progress = progress.add_task(f"Preparing to run iperf client on {client.name}", total=True)
                        if not udp and not wait_listening(client, server.IP(), port):
                            listening.abort()
                            raise Exception("iperf server failed to start")
                        if listening.n_waiting != 0:
                            listening.wait()
                        cmd = iperf_client_cmd
                        if client.name in additional_args:
                            cmd += " " + additional_args[client.name]
                        client.sendCmd(cmd)
                        progress.update(client_progress, description=f"Running iperf client on {client.name}", )
                        data = client.waitOutput()
                        progress.update(client_progress, completed=True, description=f"Finished iperf client on {client.name}")
                        if simultaneous or last:
                            finished.wait()
                        client_csv = [line for line in data.strip().split("\n") if line.count(",")>=4]
                        client_reader = csv.DictReader(client_csv, fieldnames=iperf_fieldnames)
                        client_values = [row for row in client_reader]
                        for value in client_values:
                            if value["client_ip"] == server.IP():
                                value["client_ip"], value["server_ip"] = value["server_ip"], value["client_ip"]
                                value["client_port"], value["server_port"] = value["server_port"], value["client_port"]
                        if len(client_values):
                            return client_values[-1]
                    with ThreadPoolExecutor(max_workers=len(clients) + 1 if simultaneous else 2) as executor:
                        server_future = executor.submit(server_thread)
                        while listening.n_waiting == 0:
                            sleep(0.1)
                        client_futures = [executor.submit(node_thread, client, index + 1 == len(clients)) for index, client in enumerate(clients)]
                        client_values = {value["client_ip"] : value for value in [future.result() for future in client_futures]}
                        server_values = server_future.result()
        except TimeoutError:
            if fail_fast or retries == 0:
                failed = True
                server_values = {ip: {"rate": 0, "jitter": 0, "loss": 0, "out of order": 0} for ip in [client.IP() for client in clients]}
            else:
                pass
        if not server_values:
            return run_iperf(server, clients, port, format, length, udp, window, mss, nodelay, iperf_time, bandwidth, dualtest, num, tradeoff, tos, ttl, file, precision, parallel, simultaneous, fail_fast, retries - 1, output, congestion, additional_args) if retries else None
        clientips = [client.IP() for client in clients]
        for ip in client_values.keys():
            if ip not in server_values:
                server_values[ip] = {                   
                    "rate": 0,
                    "jitter": 0,
                    "loss": 0,
                    "out of order": 0,
                }

            client = clients[clientips.index(ip)]
            client_value = client_values[ip]
            server_value = server_values[ip]

            if udp or bandwidth:
                table.add_row(
                    client.name, 
                    client.IP(),
                    server.name,
                    server.IP(), 
                    client_value["interval"] + "s",
                    bit_convert(int(server_value["rate"]), True, precision, format),
                    bit_convert(int(client_value["rate"]), True, precision, format),
                    bit_convert(int(client_value["transmitted"] or server_value["transmitted"])*8, False, precision, format),
                    f"{float(client_value['jitter'] or server_value['jitter']):.2f}ms" if client_value["jitter"] != None or server_value["jitter"] != None else None,
                    client_value["sent"]  or server_value["sent"],
                    str(int(client_value["sent"] or server_value["sent"])  - int(client_value["lost"] or server_value["lost"])),
                    f"{float(client_value['loss'] or server_value['loss']):.2f}%",
                    client_value["out of order"] or server_value["out of order"],
                    )
            else:
                table.add_row(
                    client.name, 
                    client.IP(),
                    server.name,
                    server.IP(), 
                    client_value["interval"] + "s",
                    bit_convert(int(server_value["rate"]), True, precision, format),
                    bit_convert(int(client_value["rate"]), True, precision, format),
                    bit_convert(int(client_value["transmitted"]) * 8, False, precision, format),
                    )
        if failed:
            console.print("[red]failed to read from server[/red]")
        console.print(table)
        if output is not None:
            with Progress(SpinnerColumn(finished_text="[green]✓[/green]"), TextColumn("[progress.description]{task.description}"), TimeElapsedColumn(), transient=False) as progress:
                write_task = progress.add_task(f"Writing results to {output}", total=True)
                headers = [Text.from_markup(column.header) for column in table.columns]
                columns = [[Text.from_markup(cell) for cell in column.cells] for column in table.columns]
                rows = list(zip(*columns))
                with output.open("w") as f:
                    writer = csv.writer(f, )
                    writer.writerow(headers)
                    writer.writerows(rows)
                progress.update(write_task, completed=True, description=f"Wrote results to [cyan]{output}[/cyan]")
                
        server.sendInt()

    unit_regex = re.compile(r"(?P<value>\d+)\s*(?P<unit>[kKmMgG]?i?)(?P<byte>[bB]?).*")
    units = {
        "GI": 2**30,
        "G": 10**9,
        "MI": 2**20,
        "M": 10**6,
        "KI": 2**10,
        "K": 10**3,
    }
    def bit_unit_parser(s: str) -> int:
        if s is None:
            return s
        match = unit_regex.match(s)
        return int(int(match.group("value")) * units.get(match.group("unit").upper(), 1) * (8 if match.group("byte") == "B" else 1))
    
    def file_completion(incomplete: str) -> List[Path]:
        path = Path(".")
        return list(path.glob(f"{incomplete}*"))

    @app.command(rich_help_panel="Testing utilities")
    def iperf(
        server: Annotated[Node, typer.Argument(help="Server to run iperf on", parser=mn_node)], 
        clients: Annotated[List[Node], typer.Argument(help="Clients to run iperf from", parser=mn_node)],
        port: Annotated[int, typer.Option("--port", "-p", help="Port to run iperf on")]=5001,
        format: Annotated[str, typer.Option("--format", "-f", help="A letter specifying the format for printing bandwidth numbers. Defaults to a for adaptive")]="a",
        length: Annotated[int, typer.Option("--length", "-l", help="Length of buffer to read or write (default 8 KB)", parser=bit_unit_parser)]="8192",
        udp: Annotated[bool, typer.Option("--udp", "-u", help="Use UDP instead of TCP")]=False,
        window: Annotated[int, typer.Option("--window", "-w", help="TCP window size", parser=bit_unit_parser)]=None,
        mss: Annotated[int, typer.Option("--mss", "-m", help="TCP maximum segment size", parser=bit_unit_parser)]=None,
        nodelay: Annotated[bool, typer.Option("--nodelay", "-N", help="Set TCP no delay, disabling Nagle's Algorithm")]=False,
        time: Annotated[int, typer.Option("--time", "-t", help="The time in seconds to transmit for")]=10,
        bandwidth: Annotated[int, typer.Option("--bandwidth", "-b", help="Set UDP target bandwidth to n bits/sec, implies UDP", parser=bit_unit_parser)]=None,
        dualtest: Annotated[bool, typer.Option("--dualtest", "-d", help="Do a bidirectional test simultaneously")]=False,
        num: Annotated[int, typer.Option("--num", "-n", help="Number of buffers to transmit. Overrides the time")]=None,
        tradeoff: Annotated[bool, typer.Option("--tradeoff", "-r", help="Do a bidirectional test sequentially (server connects to client after the client test)")]=False,
        tos: Annotated[TOS, typer.Option("--tos", "-S", help="Set the IP type of service (tos) field in the IP header")]=None,
        tos_custom: Annotated[int, typer.Option("--tos-custom", help="Set the IP type of service to any custom (even one not in RFC1349) value")]=None,
        ttl: Annotated[int, typer.Option("--ttl", help="Set the IP TTL field")]=None,
        file: Annotated[Path, typer.Option("--file", "-F", help="Use a file as a representative stream for measuring bandwidth", autocompletion=file_completion)]=None,
        precision: Annotated[int, typer.Option("--precision", help="Number of decimal places to print (only really useful for fast links)")]=2,
        parallel: Annotated[int, typer.Option("--parallel", "-P", help="Have each client make a set number of parallel connections")]=1,
        simultaneous: Annotated[bool, typer.Option("--simultaneous", "-s", help="Run iperf on all clients at once")]=False,
        fail_fast: Annotated[bool, typer.Option("--fail-fast", "-F", help="Stop iperf on failure without any retries")]=False,
        retries: Annotated[int, typer.Option("--retries", "-R", help="Number of times to retry iperf on failure")]=3,
        output: Annotated[Path, typer.Option("--output", "-o", help="Output file to write results to")]=None,
        congestion: Annotated[str, typer.Option("--congestion", "-Z", help="Set TCP congestion control algorithm")]=None,
        special_args: Annotated[str, typer.Option("--individual", "-i", help="Additional arguments to pass to specific iperf instances. Single comma separated string in the format host='args'", shell_complete=False)]=None,
        ):
        """Run iperf between hosts."""
        tos = tos_custom or (int(tos) if tos else None)
        additional_args = {}
        if special_args is not None:
            for arg in special_args.split(","):
                [host, args] = arg.split("=", 1)
                if host not in mn:
                    raise typer.BadParameter(f"Host {host} not found in topology")
                additional_args[host] = args.strip().strip("'").strip('"')
        try:
            run_iperf(server, clients, port, format, length, udp, window, mss, nodelay, time, bandwidth, dualtest, num, tradeoff, tos, ttl, file, precision, parallel, simultaneous, fail_fast, retries, output, congestion, additional_args)
        finally:
            try:
                server.cmd("killall -9 iperf")
            except:
                pass
    @app.command(rich_help_panel="Testing utilities")
    def iperfudp(
        server: Annotated[Node, typer.Argument(help="Server to run iperf on",  parser=mn_node)], 
        clients: Annotated[List[Node], typer.Argument(help="Clients to run iperf from", parser=mn_node)],
        port: Annotated[int, typer.Option("--port", "-p", help="Port to run iperf on")]=5001,
        format: Annotated[str, typer.Option("--format", "-f", help="A letter specifying the format for printing bandwidth numbers. Defaults to a for adaptive")]="a",
        length: Annotated[int, typer.Option("--length", "-l", help="Length of buffer to read or write (default 8 KB)", parser=bit_unit_parser)]="8192",
        time: Annotated[int, typer.Option("--time", "-t", help="The time in seconds to transmit for")]=10,
        bandwidth: Annotated[int, typer.Option("--bandwidth", "-b", help="Set UDP target bandwidth to n bits/sec", parser=bit_unit_parser)]=None,
        dualtest: Annotated[bool, typer.Option("--dualtest", "-d", help="Do a bidirectional test simultaneously")]=False,
        num: Annotated[int, typer.Option("--num", "-n", help="Number of buffers to transmit. Overrides the time")]=None,
        tradeoff: Annotated[bool, typer.Option("--tradeoff", "-r", help="Do a bidirectional test sequentially (server connects to client after the client test)")]=False,
        tos: Annotated[TOS, typer.Option("--tos", "-S", help="Set the IP type of service (tos) field in the IP header", case_sensitive=False)]=None,
        tos_custom: Annotated[int, typer.Option("--tos-custom", help="Set the IP type of service (tos) field in the IP header to the specified value, for when you need something not specified in RFC 1349")]=None,
        ttl: Annotated[int, typer.Option("--ttl", help="Set the IP TTL field")]=None,
        file: Annotated[Path, typer.Option("--file", "-F", help="Use a file as a representative stream for measuring bandwidth")]=None,
        precision: Annotated[int, typer.Option("--precision", help="Number of decimal places to print (only really useful for fast links)")]=2,
        parallel: Annotated[int, typer.Option("--parallel", "-P", help="Have each client make a set number of parallel connections")]=1,
        simultaneous: Annotated[bool, typer.Option("--simultaneous", "-s", help="Run iperf on all clients at once")]=False,
        fail_fast: Annotated[bool, typer.Option("--fail-fast", "-F", help="Stop iperf on failure without any retries")]=False,
        retries: Annotated[int, typer.Option("--retries", "-R", help="Number of times to retry iperf on failure")]=3,
        output: Annotated[Path, typer.Option("--output", "-o", help="Output file to write results to")]=None,
        ):
        """Run iperf between hosts using UDP (can also be achieved by using iperf -u)."""
        tos = tos_custom or (int(tos) if tos else None)
        try:
            run_iperf(server, clients, port, format, length, True, None, None, None, time, bandwidth, dualtest, num, tradeoff, tos, ttl, file, precision, parallel, simultaneous, fail_fast, retries, output)
        finally:
            try:
                server.cmd("killall -9 iperf")
            except:
                pass
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
        raise SystemExit()
    
    @app.command(hidden=True)
    def quit(ctx: typer.Context):
        """Exit the CLI"""
        raise SystemExit()

    @app.command()
    def noecho(ctx: typer.Context, cmd: Annotated[List[str], typer.Argument(help="Commands to run", shell_complete=False)]):
        """Run a command with echoing turned off"""
        if is_atty():
            quietRun('stty -echo')
        try:
            ctx.invoke(ctx.parent.command, *cmd)
        finally:
            if is_atty():
                quietRun('stty echo')

    def overlap(a, b):
        return max(i for i in range(len(b)+1) if b[i-1] == a[-1] and a.endswith(b[:i]))

    commands = typer.main.get_group(app)
    class TyperCompleter(Completer):
        def get_completions(self, document: Document, complete_event: CompleteEvent):
            args = split_arg_string(document.text)
            args_before_cursor = split_arg_string(document.text_before_cursor)
            if not len(args) or not len(args_before_cursor):
                return
            ctx = commands.make_context(args[0], args)
            multi = cast(MultiCommand, ctx.command)
            command_completions: List[CompletionItem] = commands.shell_complete(ctx, document.text)
            arg_completions: List[CompletionItem] = []
            if len(command_completions) == 0 and document.text_before_cursor[-1] != " ":
                command = multi.get_command(ctx, args[0])
                if command is not None and not command.hidden:
                    arg_completions.extend(command.shell_complete(ctx, args_before_cursor[-1]))
            for completion in command_completions:
                command = multi.get_command(ctx, completion.value)
                if command is not None and not command.hidden:
                    arg_completions.extend(command.shell_complete(ctx, document.text_before_cursor[len(completion.value):].strip()))
            for item in command_completions + arg_completions:
                if len(document.text_before_cursor) > 2 and document.text_before_cursor[-1] == "-" and document.text_before_cursor[-2] != "-" and item.value.startswith("--"):
                    continue
                yield Completion(item.value, start_position=-overlap(document.text_before_cursor.strip(), item.value), display_meta=item.help)
    class MnCompleter(Completer):
        def get_completions(self, document: Document, complete_event: CompleteEvent):
            last_word = document.get_word_before_cursor()
            if document.text_before_cursor.strip().split(" ")[-1].startswith("-"):
                return
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
                            completer=merge_completers([TyperCompleter(), MnCompleter(), PathCompleter(file_filter=lambda s: s.endswith(".mn") or s.endswith(".mn2") or s.endswith(".txt"))], deduplicate=True)
                            )
    
    pipe_regex = re.compile(r".*(?P<pipetype>>{1,2})\s*(?P<file>[^\s]*)$")

    command = typer.main.get_command(app)
    def process_command(text: str):
        if not len(text.strip()) or text.strip().startswith("#"):
            return
        argv = split_arg_string(text)
        if argv[0] == "source" or (len(argv) == 1 and argv[0] not in commands.commands.keys()):
            argv.append("")
        if argv[0] not in commands.commands.keys():
            argv.insert(0, "default")
        
        if text.count(">") >= 1:
            try:
                pipe_match = pipe_regex.match(text[text.rindex(">")-1:])
                target = Path(sanitize_filepath(pipe_match.group("file")))
            except (ValueError, AttributeError):
                return command(argv, standalone_mode=False)
            try:
                argv = split_arg_string(text[:text.rindex(pipe_match.group("pipetype"))])
                with console.capture() as capture:
                    return command(argv, standalone_mode=False)
            finally:
                mode = "w" if pipe_match.group("pipetype") == ">" else "a"
                with target.open(mode) as f:
                    f.write(capture.get() + "\n")
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
                return
            except typer.Abort:
                pass
            except SystemExit:
                return
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

