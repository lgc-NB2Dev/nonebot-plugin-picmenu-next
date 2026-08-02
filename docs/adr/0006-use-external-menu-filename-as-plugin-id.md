# Use External Menu Filename as Plugin ID

External menu config uses the config file stem as the plugin ID. That ID decides whether the config overrides a loaded plugin menu or creates an external plugin menu, keeping identity in the filesystem name instead of duplicating it inside every file; duplicate plugin IDs from multiple files are ignored after the first loaded file.
