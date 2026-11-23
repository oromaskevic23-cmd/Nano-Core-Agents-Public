"""Local lab operator controls; never an authenticated remote Owner interface."""
import argparse
import json
from pathlib import Path
import time

from .queue import LocalQueue


def main():
    parser=argparse.ArgumentParser(description="Inspect or stop the single-host NCA lab worker")
    parser.add_argument("--database",required=True)
    commands=parser.add_subparsers(dest="command",required=True)
    status=commands.add_parser("status")
    status.add_argument("--worker-id",default="nca-local-worker-1")
    status.add_argument("--stale-after",type=int,default=60)
    job=commands.add_parser("job")
    job.add_argument("--job-id",required=True)
    for name in ("stop","resume"):
        sub=commands.add_parser(name)
        sub.add_argument("--scope",choices=["global","agent"],required=True)
        sub.add_argument("--subject",required=True,help="Use '*' for global or an exact lab agent id")
        if name=="stop":
            sub.add_argument("--reason",required=True)
    args=parser.parse_args()
    path=Path(args.database)
    if not path.is_file() or path.is_symlink():
        parser.error("an existing, non-symlink lab database is required")
    queue=LocalQueue(path)
    now=int(time.time())
    if args.command=="status":
        result=queue.inspect_worker(args.worker_id,now,stale_after=args.stale_after)
        result["local_global_stop_active"]=queue.global_stop_active()
    elif args.command=="job":
        result=queue.inspect(args.job_id) or {"status":"NOT_FOUND","production_authorized":False}
    elif args.command=="stop":
        queue.stop(args.scope,args.subject,args.reason,now)
        result={"local_stop_recorded":True,"production_authorized":False}
    else:
        result=queue.clear_stop(args.scope,args.subject,now)
    print(json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()
