# Contributing

Thanks for helping improve AutoAppearance.

## Getting Started

1. Fork or clone the repository.
2. Make your change in a focused branch.
3. Run the local checks below.
4. Open a pull request with a clear summary and test notes.

## Local Checks

Run these before opening a pull request:

```sh
python3 -c "import ast, pathlib; ast.parse(pathlib.Path('auto_appearance.py').read_text())"
python3 -m json.tool Default.sublime-commands
python3 -m json.tool Main.sublime-menu
python3 -m json.tool messages.json
make build
```

To test the package in Sublime Text:

```sh
make install
```

Restart Sublime Text if the package does not reload immediately.

## Development Notes

- Keep the plugin compatible with Sublime Text's plugin host.
- Avoid adding runtime dependencies.
- Keep Linux desktop integration behavior behind `busctl` and
  xdg-desktop-portal APIs.
- Update `messages/install.txt` and `README.md` when setup or behavior changes.

## Pull Requests

Please include:

- What changed and why.
- How you tested it.
- Any desktop environment, portal, or Sublime Text version details that matter.

Small, focused pull requests are easiest to review.
