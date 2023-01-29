# NodeBB import fixes

The goal of this repository is to repair a NodeBB forum that was imported from PhpBB.

We tried using the "Post Import Tools" from the import plugin, but they didn't seem
to work as expected.

## Forum Import

The forum import process itself should be done via the [nodebb-plugin-import](https://github.com/akhoury/nodebb-plugin-import) plugin.

For example, you should use the [nodebb-plugin-import-phpbb](https://github.com/psychobunny/nodebb-plugin-import-phpbb) plugin.

## Dependencies

You have to install the [Write API](https://github.com/NodeBB/nodebb-plugin-write-api) plugin.

This script aims at versions the `nodebb-plugin-import` runs, so the `APIv3` is not yet available.

Here are the python dependencies:

* `pyyaml`

## Configuration

All the configuration is done via the `config.yaml` file.

You can create a basic one by copying `config.sample.yaml`, that contains all required documentation.

## Usage

Just run `repair_nodebb.py`!
