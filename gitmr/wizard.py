"""Review screen, in-terminal editing, assignee/reviewer pick, AI draft."""

from __future__ import annotations

from prompt_toolkit import prompt

from gitmr.content import ContentGenerationError, generate_content
from gitmr.gitlab import GitLabError
from gitmr.ui import console, pick_user, print_error, print_mr_review, prompt_line


class WizardAbort(Exception):
    """User quit from the review screen."""


def _default_assignee_id(config):
    raw = config.get("default_assignee_id")
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _pick_user(client, role_label):
    query = prompt_line(f"Search {role_label}", default="")
    if not query:
        return None
    try:
        users = client.search_users(query)
    except GitLabError as e:
        print_error(str(e))
        return None
    if not users:
        print_error(f"No users found for '{query}'.")
        return None
    user = pick_user(users, role_label=role_label)
    if not user:
        return None
    return {"id": user["id"], "name": user["name"], "username": user["username"]}


def prepare_draft(ctx, config, *, default_title: str, default_description: str = ""):
    title = default_title
    description = default_description
    api_key = config.get("openai_api_key", "")
    if not api_key or not config.get("auto_ai", True):
        return title, description

    try:
        with console.status("[dim]Generating MR content…[/dim]", spinner="dots"):
            content = generate_content(ctx, api_key=api_key)
        title = content["title"]
        description = content["description"]
    except ContentGenerationError as e:
        print_error(str(e))

    return title, description


def edit_draft_interactive(title: str, description: str):
    console.print(
        "\n[dim]Edit draft[/dim]  "
        "[dim](Alt+Enter or Esc then Enter to save description)[/dim]\n"
    )
    new_title = prompt("› Title: ", default=title).strip() or title
    new_description = prompt(
        "› Description:\n",
        multiline=True,
        default=description or "",
    ).strip()
    return new_title, new_description or description


def _format_assignee(state):
    if state.get("assignee_name"):
        return state["assignee_name"]
    aid = state.get("assignee_id")
    return f"user #{aid}" if aid else "—"


def _format_reviewers(state):
    names = state.get("reviewer_names") or []
    if names:
        return ", ".join(names)
    ids = state.get("reviewer_ids") or []
    return ", ".join(f"#{i}" for i in ids) if ids else "—"


def run_review_confirm(ctx, config, client, *, default_title: str, default_description: str = ""):
    title, description = prepare_draft(
        ctx, config, default_title=default_title, default_description=default_description
    )

    state = {
        "title": title,
        "description": description,
        "assignee_id": _default_assignee_id(config),
        "assignee_name": None,
        "reviewer_ids": [],
        "reviewer_names": [],
    }

    while True:
        print_mr_review(
            ctx,
            state["title"],
            state["description"],
            assignee=_format_assignee(state),
            reviewers=_format_reviewers(state),
        )
        console.print(
            "[dim]  Enter[/dim] create   "
            "[dim]e[/dim] edit   "
            "[dim]g[/dim] regenerate AI   "
            "[dim]a[/dim] assignee   "
            "[dim]r[/dim] reviewer   "
            "[dim]q[/dim] quit"
        )
        action = console.input("\n[bold green]›[/bold green]  ").strip().lower()

        if action in ("", "c", "create", "y", "yes"):
            if not state["title"].strip():
                print_error("Title cannot be empty.")
                continue
            return (
                state["title"].strip(),
                state["description"],
                state["assignee_id"],
                state["reviewer_ids"] or None,
            )

        if action in ("q", "quit", "n", "no"):
            raise WizardAbort()

        if action in ("e", "edit"):
            state["title"], state["description"] = edit_draft_interactive(
                state["title"], state["description"]
            )
            continue

        if action in ("g", "regenerate", "ai"):
            api_key = config.get("openai_api_key", "")
            if not api_key:
                print_error("OPENAI_API_KEY not set — cannot regenerate.")
                continue
            try:
                with console.status("[dim]Regenerating…[/dim]", spinner="dots"):
                    content = generate_content(ctx, api_key=api_key)
                state["title"] = content["title"]
                state["description"] = content["description"]
            except ContentGenerationError as e:
                print_error(str(e))
            continue

        if action in ("a", "assignee"):
            picked = _pick_user(client, "assignee")
            if picked:
                state["assignee_id"] = picked["id"]
                state["assignee_name"] = picked["name"]
            continue

        if action in ("r", "reviewer"):
            picked = _pick_user(client, "reviewer")
            if picked and picked["id"] not in state["reviewer_ids"]:
                state["reviewer_ids"].append(picked["id"])
                state["reviewer_names"].append(picked["name"])
            continue

        print_error(f"Unknown action '{action}'.")
