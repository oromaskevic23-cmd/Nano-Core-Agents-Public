"""First REAL read-only cloud adapter: public GitHub repo metadata only.

No credentials, OAuth, token, private repository access, writes or arbitrary URLs.
Network calls are disabled by default; one explicit invocation is required.
"""
from __future__ import annotations
import hashlib
import http.client
import json
import ssl


HOST = "api.github.com"
REPO = "oromaskevic23-cmd/Nano-Core-Agents-Public"
PATH = "/repos/"+REPO


class CloudDenied(ValueError):
    pass


def read_public_repo(*, live=False, timeout=8) -> dict:
    if live is not True:
        raise CloudDenied("EXPLICIT_READ_ONLY_OPT_IN_REQUIRED")
    if type(timeout) is not int or not 1 <= timeout <= 15:
        raise CloudDenied("INVALID_TIMEOUT")
    # Direct TLS connection to the one fixed public provider endpoint;
    # http.client does not follow redirects and no user URL is accepted.
    conn=http.client.HTTPSConnection(HOST,443,timeout=timeout,
                                      context=ssl.create_default_context())
    try:
        conn.request("GET",PATH,headers={
            "User-Agent":"IMPERIAL-NCA-READONLY-LAB/0.1",
            "Accept":"application/vnd.github+json",
            "X-GitHub-Api-Version":"2022-11-28"})
        response=conn.getresponse()
        if response.status!=200:
            raise CloudDenied("GITHUB_PUBLIC_READ_HTTP_"+str(response.status))
        data=response.read(256000+1)
        if len(data)>256000:
            raise CloudDenied("RESPONSE_TOO_LARGE")
        try:
            obj=json.loads(data)
        except (ValueError,UnicodeDecodeError):
            raise CloudDenied("INVALID_GITHUB_JSON") from None
        if (type(obj) is not dict or obj.get("full_name")!=REPO or
            obj.get("private") is not False or
            type(obj.get("default_branch")) is not str or
            not obj["default_branch"]):
            raise CloudDenied("REPOSITORY_IDENTITY_MISMATCH")
        stars=obj.get("stargazers_count")
        if type(stars) is not int or stars < 0:
            raise CloudDenied("INVALID_PUBLIC_REPO_FIELDS")
        return {
            "provider":"github_public",
            "resource":REPO,
            "default_branch":obj["default_branch"],
            "stars":stars,
            "source_sha256":hashlib.sha256(data).hexdigest(),
            "read_only":True,
            "authenticated":False,
            "credentials_present":False,
            "private_resource_read":False,
            "cloud_write_authorized":False,
            "mission_authority":"NONE_PUBLIC_METADATA_ONLY",
            "api_endpoint":"https://"+HOST+PATH
        }
    except (OSError,http.client.HTTPException) as exc:
        raise CloudDenied("PUBLIC_GITHUB_UNAVAILABLE") from exc
    finally:
        conn.close()
