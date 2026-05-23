"""MR workflows: feature → develop and promotion hops."""

import subprocess

from gitmr.gitlab import GitLabError
from gitmr.ui import (
    build_promote_description,
    confirm_continue_if_open_mr,
    console,
    print_aborted,
    print_error,
    print_fetching,
    print_header,
    print_merged_mrs,
    print_mr_created,
    print_summary,
)
from gitmr.wizard import WizardAbort, run_review_confirm


def build_context(source, target, compare):
    """Normalize GitLab compare JSON into a stable dict for UI and AI."""
    raw_commits = compare.get("commits", [])
    raw_diffs = compare.get("diffs", [])
    timed_out = compare.get("compare_timeout", False)

    commits = [
        {
            "sha": c["short_id"],
            "author": c["author_name"],
            "message": c["title"],
        }
        for c in raw_commits
    ]

    files = []
    for d in raw_diffs:
        if d.get("new_file"):
            status = "added"
        elif d.get("deleted_file"):
            status = "deleted"
        elif d.get("renamed_file"):
            status = "renamed"
        else:
            status = "modified"

        diff_text = d.get("diff", "")
        lines = diff_text.splitlines()
        if len(lines) > 400:
            diff_text = "\n".join(lines[:400]) + "\n...(truncated)"
        files.append({"status": status, "path": d["new_path"], "diff": diff_text})

    return {
        "source": source,
        "target": target,
        "commits": commits,
        "files": files,
        "timed_out": timed_out,
    }


def _guard_no_open_mr(client, project_id, source, target):
    existing = client.get_open_mr(project_id, source, target)
    return confirm_continue_if_open_mr(existing)


def _current_branch():
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GitLabError("Could not determine current branch.")
    return result.stdout.strip()


def run_feature(config, client):
    """Current branch → default target (usually develop)."""
    print_header()
    branch = _current_branch()
    target = config.get("default_target", "develop")
    project_id = config["project_id"]

    if branch == target:
        print_error(f"Already on {target}. Nothing to merge.")
        return

    if not _guard_no_open_mr(client, project_id, branch, target):
        print_aborted()
        return

    print_fetching(branch, target)
    ctx = build_context(branch, target, client.compare(project_id, branch, target))
    print_summary(ctx)

    try:
        title, description, assignee_id, reviewer_ids = run_review_confirm(
            ctx,
            config,
            client,
            default_title=f"Draft: {branch}",
        )
    except WizardAbort:
        print_aborted()
        return

    mr = client.create_mr(
        project_id=project_id,
        source=branch,
        target=target,
        title=title,
        description=description,
        assignee_id=assignee_id,
        reviewer_ids=reviewer_ids,
    )
    print_mr_created(mr["web_url"])


def run_promote(config, client, source, target):
    """Promotion MR: develop → staging or staging → master."""
    print_header()
    project_id = config["project_id"]

    if not _guard_no_open_mr(client, project_id, source, target):
        print_aborted()
        return

    console.print(f"\n[dim]Loading recent MRs merged into[/dim] [bold]{source}[/bold] ...")
    merged = client.get_merged_mrs(project_id, source, target)
    if not merged:
        print_error(f"No merged MRs found in {source}. Nothing to promote.")
        return

    print_merged_mrs(merged, source)
    print_fetching(source, target)
    ctx = build_context(source, target, client.compare(project_id, source, target))

    if not ctx["commits"]:
        print_error(f"No commits ahead. {source} is already up to date with {target}.")
        return

    print_summary(ctx)

    try:
        title, description, assignee_id, reviewer_ids = run_review_confirm(
            ctx,
            config,
            client,
            default_title=f"chore(release): promote {source} to {target}",
            default_description=build_promote_description(source, target, merged),
        )
    except WizardAbort:
        print_aborted()
        return

    mr = client.create_mr(
        project_id=project_id,
        source=source,
        target=target,
        title=title,
        description=description,
        assignee_id=assignee_id,
        reviewer_ids=reviewer_ids,
    )
    print_mr_created(mr["web_url"])
