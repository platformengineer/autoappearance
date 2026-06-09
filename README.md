# AutoAppearance

AutoAppearance is a Sublime Text 4 plugin for Linux desktops that follow the
xdg-desktop-portal appearance setting. It runs `busctl --user monitor` in the
background, detects portal `SettingChanged` signals, reads
`org.freedesktop.appearance color-scheme`, and updates Sublime's `theme` and
`color_scheme` preferences from Sublime's own light/dark settings.

The portal color-scheme values are:

- `0`: no preference
- `1`: prefer dark
- `2`: prefer light

## Install

Place this folder in your Sublime Text `Packages` directory, for example:

```sh
~/.config/sublime-text/Packages/AutoAppearance
```

Then restart Sublime Text or run
`sublime_plugin.reload_plugin("auto_appearance")` from the Sublime console.

For package-based testing, build and install a `.sublime-package`:

```sh
make build
make install
```

The installer copies `dist/AutoAppearance.sublime-package` into Sublime's
`Installed Packages` directory. If your Sublime data directory lives somewhere
custom, pass it explicitly:

```sh
make install SUBLIME_INSTALLED_PACKAGES_DIR="$HOME/.config/sublime-text/Installed Packages"
```

## Configure

AutoAppearance reads these settings from `Preferences.sublime-settings`:

```jsonc
{
  "light_theme": "Default.sublime-theme",
  "dark_theme": "Default Dark.sublime-theme",
  "light_color_scheme": "Celeste.sublime-color-scheme",
  "dark_color_scheme": "Mariana.sublime-color-scheme",
}
```

When the system switches appearance, AutoAppearance copies the matching light/dark
values into Sublime's active `theme` and `color_scheme` settings.

Open `Preferences: Package Settings > AutoAppearance > Settings`, or edit
`AutoAppearance.sublime-settings` directly for plugin behavior such as `busctl` lookup
and how to handle the portal's `no preference` value.

If Sublime cannot find `busctl` when launched from your desktop environment,
set:

```jsonc
{
  "busctl_binary": "/usr/bin/busctl",
}
```

## Commands

The command palette includes:

- `AutoAppearance: Sync Appearance Now`
- `AutoAppearance: Restart busctl Monitor`

Package Control displays the install instructions from `messages/install.txt`.

## Contributing

Contributions are welcome. Please read `CONTRIBUTING.md`,
`CODE_OF_CONDUCT.md`, and `SECURITY.md` before opening issues or pull requests.

## License

AutoAppearance is released under the MIT License. See `LICENSE`.
