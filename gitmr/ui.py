from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

console = Console()


def print_header():
    console.print("\n[bold purple]git-mr[/bold purple] [dim]v0.1[/dim]\n")


def print_detected_project(path, project_id, *, source="git"):
    console.print(
        f"[dim]Project[/dim] ([dim]{source}[/dim]): "
        f"[bold cyan]{path}[/bold cyan] "
        f"[dim](id {project_id})[/dim]\n"
    )


def show_menu():
    body = (
        "[bold]1[/bold]  feature → develop\n"
        "[bold]2[/bold]  develop → staging\n"
        "[bold]3[/bold]  staging → master\n"
        "[dim]q[/dim]  quit"
    )
    console.print(Panel(body, title="[bold purple]git-mr[/bold purple]", border_style="purple"))


def prompt_menu_choice():
    return console.input("\n[bold green]›[/bold green] [bold]Choose[/bold]  ").strip().lower()


def print_cancelled():
    console.print("\n[dim]Cancelled.[/dim]\n")


def print_existing_open_mr(mr):
    body = (
        f"[cyan]!{mr['iid']}[/cyan]  [bold]{mr['title']}[/bold]\n"
        f"[dim]{mr['web_url']}[/dim]"
    )
    console.print(
        Panel(
            body,
            title="Open MR already exists for this branch",
            border_style="yellow",
        )
    )


def confirm_continue_if_open_mr(existing):
    if not existing:
        return True
    print_existing_open_mr(existing)
    return ask("Open a new one anyway?", default_yes=False)


def print_merged_mrs(merged, source):
    table = Table(
        show_header=True,
        header_style="bold dim",
        box=box.SIMPLE_HEAD,
        padding=(0, 1),
    )
    table.add_column("MR", style="cyan", width=6)
    table.add_column("Title", style="bold")
    table.add_column("Author", style="dim italic")

    for m in merged:
        table.add_row(f"!{m['iid']}", m["title"], m["author"])

    count = f"{len(merged)} total"
    console.print(
        Panel(
            table,
            title=f"Merged into [bold]{source}[/bold]  [dim]{count}[/dim]",
            border_style="dim",
        )
    )


def build_promote_description(source, target, merged):
    lines = [
        f"## Summary\n\nPromotion of `{source}` into `{target}`.\n",
        "## Included MRs\n",
    ]
    for m in merged:
        lines.append(f"- !{m['iid']} {m['title']} ({m['author']})")
    return "\n".join(lines)


def print_summary(ctx):
    branch_text = Text()
    branch_text.append(ctx["source"], style="bold blue")
    branch_text.append("  →  ", style="dim")
    branch_text.append(ctx["target"], style="bold green")
    console.print(Panel(branch_text, title="Branch", border_style="dim"))

    commit_table = Table(box=None, show_header=False, padding=(0, 1))
    commit_table.add_column(style="dim", width=8)
    commit_table.add_column(style="default", ratio=1)
    commit_table.add_column(style="dim italic")
    for c in ctx["commits"]:
        commit_table.add_row(c["sha"], c["message"], f"({c['author']})")
    count = f"{len(ctx['commits'])} total"
    console.print(
        Panel(commit_table, title=f"Commits  [dim]{count}[/dim]", border_style="dim")
    )

    file_table = Table(box=None, show_header=False, padding=(0, 1))
    file_table.add_column(width=10)
    file_table.add_column()
    status_style = {
        "added": ("added", "green"),
        "modified": ("modified", "yellow"),
        "deleted": ("deleted", "red"),
        "renamed": ("renamed", "blue"),
    }
    for f in ctx["files"]:
        label, color = status_style.get(f["status"], (f["status"], "white"))
        file_table.add_row(f"[{color}]{label}[/{color}]", f["path"])
    count = f"{len(ctx['files'])} total"
    console.print(
        Panel(file_table, title=f"Files changed  [dim]{count}[/dim]", border_style="dim")
    )

    if ctx["timed_out"]:
        console.print("[yellow]Warning:[/yellow] diff was too large, GitLab truncated it.\n")


def print_mr_review(ctx, title, description, *, assignee="—", reviewers="—"):
    n_commits = len(ctx.get("commits", []))
    n_files = len(ctx.get("files", []))
    panel_title = (
        f"{ctx['source']} → {ctx['target']}  "
        f"({n_commits} commit{'s' if n_commits != 1 else ''}, "
        f"{n_files} file{'s' if n_files != 1 else ''})"
    )

    body = Text()
    body.append("Title\n", style="dim")
    body.append(title + "\n\n", style="bold yellow")
    body.append("Description\n", style="dim")

    lines = (description or "").strip().splitlines()
    preview = "\n".join(lines[:12])
    if len(lines) > 12:
        preview += "\n…"
    body.append(preview or "(empty)", style="white")
    body.append("\n\n", style="")
    body.append("Assignee   ", style="dim")
    body.append(assignee + "\n", style="cyan")
    body.append("Reviewers  ", style="dim")
    body.append(reviewers, style="cyan")

    console.print(
        Panel(
            body,
            title=panel_title,
            border_style="purple",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )
    if ctx.get("timed_out"):
        console.print("[yellow]Note:[/yellow] GitLab truncated a large diff.\n")


def print_mr_created(url):
    console.print(
        Panel(
            f"[bold green]MR created[/bold green]\n[dim]{url}[/dim]",
            border_style="green",
        )
    )


def print_error(msg):
    console.print(f"[bold red]Error:[/bold red] {msg}")


def print_aborted():
    console.print("[dim]Aborted.[/dim]")


def ask(question, default_yes=True):
    hint = "[Y/n]" if default_yes else "[y/N]"
    answer = console.input(
        f"\n[bold green]›[/bold green] [bold]{question}[/bold] [dim]{hint}[/dim]  "
    )
    if default_yes:
        return answer.strip().lower() != "n"
    return answer.strip().lower() == "y"


def print_fetching(source, target):
    console.print(
        f"\n[dim]Fetching compare:[/dim] [bold blue]{source}[/bold blue]"
        f" [dim]→[/dim] [bold green]{target}[/bold green] ..."
    )


def prompt_line(label, default=""):
    hint = f" [dim]({default})[/dim]" if default else ""
    value = console.input(
        f"\n[bold green]›[/bold green] [bold]{label}[/bold]{hint}  "
    )
    return value.strip() or default


def pick_user(users, role_label="user"):
    if not users:
        console.print(f"[yellow]No users found.[/yellow]")
        return None

    table = Table(
        show_header=True,
        header_style="bold dim",
        box=box.SIMPLE_HEAD,
        padding=(0, 1),
    )
    table.add_column("#", justify="right", style="dim", width=4)
    table.add_column("Name", style="bold")
    table.add_column("Username", style="cyan")

    for idx, user in enumerate(users, start=1):
        table.add_row(str(idx), user["name"], f"@{user['username']}")

    console.print(
        Panel(
            table,
            title=f"[bold]Select {role_label}[/bold]",
            border_style="purple",
        )
    )

    raw = prompt_line(f"Enter number (1–{len(users)}, blank to skip)", default="")
    if not raw:
        return None

    try:
        choice = int(raw)
    except ValueError:
        print_error(f"Invalid choice '{raw}'.")
        return None

    if choice < 1 or choice > len(users):
        print_error(f"Choose a number between 1 and {len(users)}.")
        return None

    return users[choice - 1]
