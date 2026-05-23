"""GitLab API client, git-remote project detection, and project resolution."""

from __future__ import annotations

import re
import subprocess
from urllib.parse import quote, urlparse

import requests

from gitmr.ui import print_detected_project


class GitLabError(Exception):
    pass


def get_remote_url(remote: str = "origin") -> str:
    result = subprocess.run(
        ["git", "remote", "get-url", remote],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GitLabError(
            f"Could not read git remote '{remote}'. "
            "Run this from inside a git repository."
        )
    return result.stdout.strip()


def _gitlab_host(gitlab_url: str) -> str:
    parsed = urlparse(gitlab_url if "://" in gitlab_url else f"http://{gitlab_url}")
    return (parsed.hostname or "").lower()


def parse_project_path(remote_url: str) -> str:
    remote_url = remote_url.strip()
    if remote_url.startswith("git@"):
        match = re.match(r"git@[^:]+:(.+)$", remote_url)
        if not match:
            raise GitLabError(f"Unrecognized SSH remote URL: {remote_url}")
        path = match.group(1)
    else:
        path = urlparse(remote_url).path.strip("/")

    if path.endswith(".git"):
        path = path[:-4]
    if not path:
        raise GitLabError(f"Could not parse project path from remote: {remote_url}")
    return path


def _remote_host(remote_url: str) -> str:
    if remote_url.startswith("git@"):
        match = re.match(r"git@([^:]+):", remote_url)
        return (match.group(1) if match else "").lower()
    return _gitlab_host(remote_url)


def detect_project_path(gitlab_url: str, remote: str = "origin") -> str:
    remote_url = get_remote_url(remote)
    path = parse_project_path(remote_url)
    expected = _gitlab_host(gitlab_url)
    actual = _remote_host(remote_url)
    if expected and actual and expected != actual:
        raise GitLabError(
            f"Git remote host '{actual}' does not match GITLAB_URL host '{expected}'. "
            f"Remote: {remote_url}"
        )
    return path


def resolve_project(config, client):
    """Set config['project_id'] and config['project_path'] from .env or git remote."""
    env_id = config.get("project_id", "").strip()
    env_path = config.get("project_path", "").strip()

    if env_id:
        config["project_id"] = env_id
        config["project_path"] = env_path or f"id:{env_id}"
        print_detected_project(config["project_path"], env_id, source="config")
        return

    remote = config.get("git_remote", "origin")
    path = env_path or detect_project_path(config["gitlab_url"], remote=remote)
    project = client.get_project(path)
    config["project_id"] = str(project["id"])
    config["project_path"] = project["path_with_namespace"]
    print_detected_project(config["project_path"], config["project_id"], source="git remote")


class GitLabClient:
    def __init__(self, config):
        self.base_url = config["gitlab_url"].rstrip("/")
        self.session = requests.Session()
        self.session.headers["PRIVATE-TOKEN"] = config["gitlab_token"]

    def _get(self, path, **params):
        r = self.session.get(f"{self.base_url}/api/v4/{path}", params=params)
        if not r.ok:
            raise GitLabError(f"GET {path} failed: {r.status_code} {r.text}")
        return r.json()

    def _post(self, path, payload):
        r = self.session.post(f"{self.base_url}/api/v4/{path}", json=payload)
        if not r.ok:
            raise GitLabError(f"POST {path} failed: {r.status_code} {r.text}")
        return r.json()

    def get_project(self, path_with_namespace):
        encoded = quote(path_with_namespace, safe="")
        project = self._get(f"projects/{encoded}")
        return {
            "id": project["id"],
            "path_with_namespace": project["path_with_namespace"],
            "name": project.get("name", path_with_namespace),
        }

    def compare(self, project_id, source, target):
        return self._get(
            f"projects/{project_id}/repository/compare",
            **{"from": target, "to": source},
        )

    def get_open_mr(self, project_id, source_branch, target_branch):
        results = self._get(
            f"projects/{project_id}/merge_requests",
            state="opened",
            source_branch=source_branch,
            target_branch=target_branch,
        )
        if not results:
            return None
        mr = results[0]
        return {"iid": mr["iid"], "title": mr["title"], "web_url": mr["web_url"]}

    def get_merged_mrs(self, project_id, source_branch, target_branch=None, limit=20):
        _ = target_branch
        results = self._get(
            f"projects/{project_id}/merge_requests",
            state="merged",
            target_branch=source_branch,
            per_page=limit,
            order_by="updated_at",
            sort="desc",
        )
        merged = []
        for mr in results:
            author = mr.get("author") or {}
            merged.append(
                {
                    "iid": mr["iid"],
                    "title": mr["title"],
                    "author": author.get("name", "Unknown"),
                    "merged": mr.get("merged_at"),
                }
            )
        return merged

    def search_users(self, query, max_results=5):
        if not query.strip():
            return []
        results = self._get("users", search=query, per_page=max_results, active=True)
        return [
            {"id": u["id"], "name": u["name"], "username": u["username"]}
            for u in results
        ]

    def create_mr(
        self,
        project_id,
        source,
        target,
        title,
        description="",
        assignee_id=None,
        reviewer_ids=None,
    ):
        payload = {
            "source_branch": source,
            "target_branch": target,
            "title": title,
            "description": description,
        }
        if assignee_id is not None:
            payload["assignee_id"] = assignee_id
        if reviewer_ids:
            payload["reviewer_ids"] = reviewer_ids
        return self._post(f"projects/{project_id}/merge_requests", payload)
