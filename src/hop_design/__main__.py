"""Invoke the CLI without registering commands in spawned render processes."""


def main() -> None:
    from hop_design.cli import app

    app()


if __name__ == "__main__":
    main()
