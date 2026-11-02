"""One explicit unauthenticated read of an owned public GitHub repository."""
import argparse
import json
from .github_public import read_public_repo


def main():
    parser=argparse.ArgumentParser(description="NCA free read-only cloud probe")
    parser.add_argument("--live",action="store_true")
    args=parser.parse_args()
    if not args.live:
        parser.error("Explicit --live required: no cloud call by default")
    print(json.dumps(read_public_repo(live=True),indent=2,sort_keys=True))


if __name__=="__main__":
    main()
