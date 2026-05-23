"""Interactive menu entry point."""

import sys

from gitmr.config import load_config
from gitmr.gitlab import GitLabClient, GitLabError, resolve_project
from gitmr.ui import print_cancelled, print_error, prompt_menu_choice, show_menu
from gitmr.workflows import run_feature, run_promote
from gitmr.wizard import WizardAbort

PROMOTE_HOPS = {
    "2": ("develop", "staging"),
    "3": ("staging", "master"),
}


def _run(config, client, fn, *args):
    resolve_project(config, client)
    fn(config, client, *args)


def main():
    config = load_config()
    client = GitLabClient(config)

    while True:
        show_menu()
        choice = prompt_menu_choice()

        if choice == "q":
            print("\n  Bye.\n")
            sys.exit(0)
        if choice == "1":
            try:
                _run(config, client, run_feature)
            except (GitLabError, ValueError) as e:
                print_error(str(e))
            except (KeyboardInterrupt, WizardAbort):
                print_cancelled()
        elif choice in PROMOTE_HOPS:
            source, target = PROMOTE_HOPS[choice]
            try:
                _run(config, client, run_promote, source, target)
            except (GitLabError, ValueError) as e:
                print_error(str(e))
            except (KeyboardInterrupt, WizardAbort):
                print_cancelled()
        else:
            print_error("Invalid choice.")
