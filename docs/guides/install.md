# Install HOP

Use [uv](https://docs.astral.sh/uv/getting-started/installation/) with Python
3.12–3.14. It gives HOP its own environment.

```bash
# Install HOP in its own environment.
uv tool install "hop-design==0.1.0a9"

# Check which version is installed.
hop-design --version
# hop-design 0.1.0a9
```

HOP is alpha software, so record the version used for your work.

## Start designing

Follow [Discover designs around your stem](discover-designs.md) to find choices,
inspect a molecule and retrieve its oligos. Run `hop-design --help` to see the
available commands.

## Use Python

Add HOP to your own uv project, then open Python in that environment.

```bash
# Add the same package as a project dependency.
uv add "hop-design==0.1.0a9"
uv run python
```

```pycon
>>> # Confirm the package in this Python environment.
>>> from importlib.metadata import version
>>> version("hop-design")
'0.1.0a9'
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
# hop-design 0.1.0a9
```

For the earlier GitHub-only package, use its
[v0.1.0a8 documentation](https://github.com/e-south/hop-design/tree/v0.1.0a8).
