


def start_mn2( mn ):
    from prompt_toolkit import PromptSession
    from prompt_toolkit import print_formatted_text as print, HTML
    import typer
    from typer.rich_utils import rich_format_error
    from typing import List, Optional
    from typing_extensions import Annotated

    class MnObject:
        def __init__(self, value: str):
            self.value = mn[value]
        def __str__(self):
            return str(self.value)
    def mn_object_parser(value: str):
        try:
            return MnObject(value)
        except Exception as e:
            raise typer.BadParameter(f"Host {value} not found in topology")
    app = typer.Typer(name="mn2>", rich_markup_mode="rich", pretty_exceptions_enable=True)
    @app.command(hidden=True)
    def default(host: Annotated[MnObject, typer.Argument(help="Host to run the command on", parser=mn_object_parser)]):
        print("default command")
        print(host)

    @app.command(hidden=True)
    def help(ctx: typer.Context, command: Annotated[Optional[str], typer.Argument()] = None):
        """Get help on the CLI or a single command."""
        print("\n Type 'command --help' or 'help <command>' for help on a specific command.")
        if not command:
            ctx.parent.get_help()
            return
        ctx.parent.command.get_command(ctx, command).get_help(ctx)
        

    @app.command(rich_help_panel="Testing utilities")
    def pingall():
        """Ping between all hosts."""
        mn.pingAll()
    
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



    session = PromptSession()
    
    while True:
        try:
            text = session.prompt('mn2> ')
        except KeyboardInterrupt:
            continue
        except EOFError:
            break
        else:
            try:
                argv = text.split(' ')
                commands = typer.main.get_group(app)
                if argv[0] not in commands.commands.keys():
                    argv.insert(0, "default")
                command = typer.main.get_command(app)
                result = command(argv, standalone_mode=False)
            except typer.Exit as e:
                if e.code != 0:
                    raise EOFError

            except KeyboardInterrupt:
                pass
            except Exception as e:
                if hasattr(e, "format_message"):
                    rich_format_error(e)
                else:
                    print(e)

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