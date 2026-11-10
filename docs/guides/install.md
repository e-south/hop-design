# Install HOP

Use [uv](https://docs.astral.sh/uv/getting-started/installation/) with Python
3.12–3.14. It gives HOP its own environment.

```bash
# Install HOP in its own environment.
uv tool install "hop-design==0.1.0a10"

# Check which version is installed.
hop-design --version
# hop-design 0.1.0a10
```

HOP is alpha software, so record the version used for your work. For a new
similarity map, [include the atlas extra](#fit-a-new-molecular-map) before starting
your discovery.

## Start designing

Follow [Discover designs around your stem](discover-designs.md) to find choices,
inspect a molecule and retrieve its oligos. Run `hop-design --help` to see the
available commands.

## Fit a new molecular map

Choose the `atlas` extra before starting a discovery whose map you want to fit.
The base installation can inspect saved coordinates and export preparations.
To add fitting support to the command installation, use:

```bash
# Include the numerical dependencies used to fit new atlas coordinates.
uv tool install --reinstall "hop-design[atlas]==0.1.0a10"
```

For a Python project, use `uv add "hop-design[atlas]==0.1.0a10"`. In a source
checkout, use `uv sync --locked --extra atlas` and pass `--extra atlas` to the
`uv run` command that fits coordinates. Keep the same HOP and Python installation
when continuing a saved search.

## Use Python

Add HOP to your own uv project, then open Python in that environment.

```bash
# Add the same package as a project dependency.
uv add "hop-design==0.1.0a10"
uv run python
```

```pycon
>>> # Confirm the package in this Python environment.
>>> from importlib.metadata import version
>>> version("hop-design")
'0.1.0a10'
```

## Work from source

Use a checkout to run the repository's `examples/` files or contribute changes.

```bash
# Create a checkout with its locked development environment.
git clone https://github.com/e-south/hop-design.git
cd hop-design
uv sync --locked

# Run this checkout rather than a separately installed command.
uv run hop-design --version
# hop-design 0.1.0a10
```

For the earlier GitHub-only package, use its
[v0.1.0a8 documentation](https://github.com/e-south/hop-design/tree/v0.1.0a8).
