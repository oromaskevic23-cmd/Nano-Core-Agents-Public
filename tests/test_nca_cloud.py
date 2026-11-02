"""No-token GitHub public-only connector tests; no network in this suite."""
import json
import unittest
from unittest.mock import patch
from nca_cloud.github_public import CloudDenied, REPO, HOST, PATH, read_public_repo


class FakeResponse:
    def __init__(self, code=200, obj=None):
        self.status=code
        self.body=json.dumps(obj if obj is not None else {
            "full_name":REPO,"private":False,"default_branch":"main",
            "stargazers_count":0}).encode()
    def read(self,n): return self.body


class Connection:
    calls=[]
    response=FakeResponse()
    def __init__(self,host,port,*,timeout,context):
        self.calls.append(("connect",host,port,timeout))
    def request(self,method,path,*,headers):
        self.calls.append(("request",method,path,dict(headers)))
    def getresponse(self): return self.response
    def close(self): self.calls.append(("closed",))


class Tests(unittest.TestCase):
    def setUp(self):
        Connection.calls.clear()
        Connection.response=FakeResponse()
        patcher=patch("nca_cloud.github_public.http.client.HTTPSConnection",Connection)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_explicit_opt_in_is_required(self):
        with self.assertRaisesRegex(CloudDenied,"EXPLICIT_READ_ONLY"):
            read_public_repo()
        self.assertEqual(Connection.calls,[])

    def test_read_exact_public_repository(self):
        result=read_public_repo(live=True)
        self.assertEqual(result["resource"],REPO)
        self.assertTrue(result["read_only"])
        self.assertFalse(result["authenticated"])
        self.assertFalse(result["cloud_write_authorized"])
        self.assertEqual(Connection.calls[0][1:3],(HOST,443))
        self.assertEqual(Connection.calls[1][1:3],("GET",PATH))
        self.assertNotIn("Authorization",Connection.calls[1][3])

    def test_redirect_to_untrusted_host_never_followed(self):
        Connection.response=FakeResponse(302)
        with self.assertRaisesRegex(CloudDenied,"GITHUB_PUBLIC_READ_HTTP_302"):
            read_public_repo(live=True)
        self.assertEqual(sum(1 for x in Connection.calls if x[0]=="connect"),1)

    def test_private_repository_response_is_rejected(self):
        Connection.response=FakeResponse(obj={
            "full_name":REPO,"private":True,"default_branch":"main","stargazers_count":1})
        with self.assertRaisesRegex(CloudDenied,"REPOSITORY_IDENTITY_MISMATCH"):
            read_public_repo(live=True)

    def test_wrong_resource_is_rejected(self):
        Connection.response=FakeResponse(obj={
            "full_name":"attacker/evil","private":False,
            "default_branch":"main","stargazers_count":1})
        with self.assertRaisesRegex(CloudDenied,"REPOSITORY_IDENTITY_MISMATCH"):
            read_public_repo(live=True)

    def test_noninteger_stars_are_denied(self):
        Connection.response=FakeResponse(obj={
            "full_name":REPO,"private":False,"default_branch":"main","stargazers_count":True})
        with self.assertRaisesRegex(CloudDenied,"INVALID_PUBLIC_REPO_FIELDS"):
            read_public_repo(live=True)

    def test_no_arbitrary_timeout(self):
        with self.assertRaisesRegex(CloudDenied,"INVALID_TIMEOUT"):
            read_public_repo(live=True,timeout=999)

    def test_not_found_is_not_accepted(self):
        Connection.response=FakeResponse(404)
        with self.assertRaisesRegex(CloudDenied,"GITHUB_PUBLIC_READ_HTTP_404"):
            read_public_repo(live=True)


if __name__=="__main__":
    unittest.main()
