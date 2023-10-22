# mn2
## A better Mininet CLI

Have you ever wanted Mininet CLI to be just a bit more modern? Or maybe tried to look up what can you even run just to be greeted with entirely unhelpful help output?

Look no further, this project abuses the `px` command to replace the default `cmd`-based CLI with a new one using `prompt_toolkit` and `typer` for improved user and developer experience.

### Current improvements
- help for all commands and their options
- expanded iperf command (to cover most of iperf2 options)
- rich text output
- ability to pass arguments to scripts loaded with `source`
- better autocomplete, including option autocomplete and autocompletion from your topology
  - also, suggestions from your shell history
- better host replacement (e.g. `http://h1:8080` will correctly replace `h1` with its IP address)

### Planned features
- some basic control flow (loops, conditionals, etc.) for in-shell scripting
- file autocomplete for relevant options
- live input validation
- better output options (e.g. allowing for CSV output from iperf)
- pipelining commands maybe?

## Installation and usage

1. [Download `mn2`](https://github.com/oplik0/mn2/releases/latest/download/mn2) from the [latest release](https://github.com/oplik0/mn2/releases/latest) to your work folder in the Mininet VM (or just wherever you're planning on using mininet)
2. Open the mininet CLI
3. Run `source mn2`
4. Your prompt should change to `mn2>` and you should now be using the new shell :) Rerunning `source mn2` should no longer do anything (because it checks if it's already being used)
5. you can go back to mininet using `quit` and `exit` commands or just by sending EOF with `Ctrl+D`

## Screenshots

![running iperf in mn2](https://github.com/oplik0/mn2/assets/25460763/f5544d02-52aa-41ed-894a-0dcce77916e4)


## FAQ

#### Q: Why even make this?
**A:** I was annoyed at the mininet CLI when doing a lab excercise. That's enough for me.

#### Q: Why not just contribute to Mininet?
**A:** The Python portion of Mininet currently doesn't have any external dependencies - it's standard library all the way down. While it's probably great for CI and means users won't have weird dependency issues, it means that adding many of the features here would require either changing that status quo or significant work to reimplement them.

Both would be difficult and take a lot of time.

Besides - at the time of writing last Mininet release was 2 years old. I wanted to have something usable for my lab excercises, not lab excercises someone else will have in a few years.

#### Q: What the hell is this script doing?
**A:** the `mn2` script simply runs a base85 encoded (to fit in a single line) script generrated from the `mn2` module with `stickytape` - a slightly cursed bundler that embeds all external dependencies within the script itself, unpacking them on startup. I'm using a significantly modified version here which you can find under [oplik0/stickytape](https://github.com/oplik0/stickytape) - primary difference from upstream is usage of an encoded zip file instead of just embeding sources as strings.

Additionally, for the production build, 
