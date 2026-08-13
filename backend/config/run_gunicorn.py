import os

from config.memory import gunicorn_argv


def main() -> None:
    argv = gunicorn_argv()
    os.execvp(argv[0], argv)


if __name__ == "__main__":
    main()
