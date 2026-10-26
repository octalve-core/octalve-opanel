"""GitHub App static deployment preparation; NO repository fetch or publish.

The artifact must be produced by a trusted isolated build/inspection pipeline,
from an approved installation and immutable commit. This record grants no
filesystem, GitHub, runtime, or domain DNS permission.
"""
from dataclasses import dataclass
import re

from .static_upload import UploadInspection


REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]{1,60}/[A-Za-z0-9_.-]{1,100}$")
GIT_SHA = re.compile(r"^[a-f0-9]{40}$")


class GitHubDeployRejected(ValueError):
    pass


@dataclass(frozen=True)
class GitHubStaticDeployPlan:
    service_id: int
    installation_id: int
    repository: str
    commit_sha: str
    artifact_sha256: str
    file_count: int
    root_index: str = "index.html"
    deploy_enabled: bool = False


def prepare_github_static(*, service_id, installation_id, repository, commit_sha,
                          installed_repositories, inspected_artifact,
                          trusted_installation=False, runtimes=()):
    if (type(service_id) is not int or service_id < 1
            or type(installation_id) is not int or installation_id < 1
            or not isinstance(repository, str) or not REPOSITORY.fullmatch(repository)
            or repository.startswith(".") or "/." in repository
            or not isinstance(commit_sha, str) or not GIT_SHA.fullmatch(commit_sha)
            or not isinstance(installed_repositories, (tuple,list,frozenset))
            or repository not in installed_repositories
            or trusted_installation is not True
            or "static" not in runtimes
            or not isinstance(inspected_artifact, UploadInspection)
            or not inspected_artifact.has_root_index
            or inspected_artifact.publish_enabled
            or not inspected_artifact.files):
        raise GitHubDeployRejected("Approved GitHub installation and verified static artifact required.")
    return GitHubStaticDeployPlan(
        service_id=service_id, installation_id=installation_id,
        repository=repository, commit_sha=commit_sha,
        artifact_sha256=inspected_artifact.sha256_digest,
        file_count=len(inspected_artifact.files),
    )


def execute_github_deploy(*_args, **_kwargs):
    raise GitHubDeployRejected("Repository fetch and account-scoped publishing are disabled.")
