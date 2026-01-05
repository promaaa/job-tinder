from typing import Any, Dict, List


def normalize(text: str | None) -> str:
    return (text or "").lower()


def job_matches(job: Dict[str, Any], query: str | None, company: str | None, tags: List[str], remote: str, emp_type: str | None) -> bool:
    if query:
        haystack = " ".join(
            [
                job.get("title", ""),
                job.get("company", ""),
                job.get("description", ""),
                " ".join(job.get("tags", []) or []),
            ]
        ).lower()
        if query.lower() not in haystack:
            return False
    if company and company.lower() not in normalize(job.get("company")):
        return False
    if tags:
        job_tags = [normalize(t) for t in (job.get("tags") or [])]
        if not all(normalize(tag) in job_tags for tag in tags):
            return False
    if remote != "any":
        wants_remote = remote == "true"
        if bool(job.get("is_remote")) != wants_remote:
            return False
    if emp_type and job.get("employment_type") != emp_type:
        return False
    return True
