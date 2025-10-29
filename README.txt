# Keystone Arches for HER

> ℹ️ This is a forked branch of Arches for HERs that is used for Keystone.
> It should not be used by organisations outside of Historic England as there is no external consideration given to it's maintenance.
>
> Instead, please use the official Arches for HER project at https://github.com/archesproject/arches-her.

## Setup for developers

This project is configured to Arches container tools (ACT), so only provides instructions for setting up the development environment that way.  Instructions assume your workspace is in WSL or macOS.

1. Clone this repo to your vscode workspace into a directory call `arches_her`: `git clone https://github.com/HistoricEngland/arhces-her arches_her`
1. Checkout the Keystone branch: `cd arches_her && git checkout keystone/main && cd ..`
1. Create virtual env in the workspace: `python -m venv env && source ./env/bin/activate`.
1. Install ACT: `pip install arches-containers`
1. Import the ACT configuration from the repo: `act import -p arches_her`
1. Start the environment: `act up`

Use the Arches Containers documentation for setting up debug config.

The initial `act up` will force the database to be setup will install the Arches for HERs package so may take some time to complete.

It does not include setting up the functions in keystone-data repo. This will need to be done manually.

