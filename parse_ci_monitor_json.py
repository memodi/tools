#!/usr/bin/env python3

import json
import argparse
import re
import sys
import os
import subprocess
from datetime import datetime
from typing import List

from issue_finder import IssuesFinder


def argparser():
    parser = argparse.ArgumentParser(
        prog="This tool helps to group failed tests based on owners, feature tests and testcase ids across multiple nightly or upgrade runs "
    )

    parser.add_argument(
        "-r",
        "--runs",
        nargs="+",
        help="space seperated list of test run ids.",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="location to write output file",
        default=f"./{datetime.today().strftime('%Y%m%d')}.json",
    )
    parser.add_argument(
        "-i",
        "--issues",
        action="store_true",
        help="Searching for known issues.",
    )
    parser.add_argument(
        "-v",
        "--version",
        help="Specify OCP version",
        required=True,
    )
    return parser.parse_args()


def get_link_to_log(content: str):
    content = re.search("(http.*)", content)
    if content:
        return content.groups()[0]


def get_test_failure_profile(content: str, profile: str):
    content = get_link_to_log(content)
    if content:
        linkto_logs = "[Link to logs|" + content + "]|" + profile
    else:
        linkto_logs = f"not found|{profile}"
    return linkto_logs


def get_automation_script(cfields: List):
    for cf in cfields:
        if cf["key"] == "automation_script":
            script = cf["value"]["content"]
            m = re.search("file: (features.*feature)\\n", script)
            automation_script = m.groups()[0]
            break
    return automation_script


def get_owner(ascript: str, testid: str):
    BUSHSLICER_HOME = os.getenv("BUSHSLICER_HOME")
    dir = f"{BUSHSLICER_HOME}/{ascript}"
    owner = None
    try:
        owner = subprocess.check_output(
            f"egrep -B 1 {testid} {dir} | grep author", shell=True
        )
        owner = owner.decode().rstrip()
        owner = re.search("author\s*(.*)@redhat.com", owner)
        owner = owner.groups()[0]
    except subprocess.CalledProcessError:
        owner = "Not found"
    return owner


def get_testrun_json(run_id: str):
    """Download the test case json data from polarshift."""

    # Call $BUSHSLICER_HOME/tools/polarshift.rb get-run RUN_ID to download the json describing the test run
    BUSHSLICER_HOME = os.getenv("BUSHSLICER_HOME")
    # use -o to avoid extra non json garbage printed to stdout
    cmd = [
        f"{BUSHSLICER_HOME}/tools/polarshift.rb",
        "get-run",
        f"{run_id}",
        "-o",
        f"{run_id}.json",
    ]
    subprocess.check_output(cmd)
    run_json = get_json_from_file(f"{run_id}.json")
    return run_json


def get_json_from_file(file_path: str):
    """Read in json from file_path."""

    with open(file_path, "r") as f:
        content = json.load(f)
    return content


def write_output(data: dict, ofile: str):
    with open(ofile, "w") as outfile:
        json.dump(data, outfile, indent=4, sort_keys=True)


def main():
    args = argparser()
    report_struct = {"version": args.version}
    for run in args.runs:
        output = get_testrun_json(run)
        profile = output["title"]
        profile = re.search(".* - (.*)$", profile)
        profile = profile.groups()[0]
        for record in output["records"]["TestRecord"]:
            if record["result"] == "Failed":
                linkto_logs = get_test_failure_profile(
                    record["comment"]["content"], profile
                )
                automation_script = get_automation_script(
                    record["test_case"]["customFields"]["Custom"]
                )
                id = record["test_case"]["id"]
                owner = get_owner(automation_script, id)
                if report_struct.get(owner, 0):
                    if report_struct[owner].get(automation_script, 0):
                        if report_struct[owner][automation_script].get(id, 0):
                            report_struct[owner][automation_script][id].append(
                                linkto_logs
                            )
                        else:
                            report_struct[owner][automation_script].update(
                                {id: [linkto_logs]}
                            )
                    else:
                        report_struct[owner].update(
                            {automation_script: {id: [linkto_logs]}}
                        )
                else:
                    report_struct[owner] = {automation_script: {id: [linkto_logs]}}
                # Find known issues
                if args.issues:
                    issue_finder = IssuesFinder()
                    issues = issue_finder.find_issues(
                        get_link_to_log(record["comment"]["content"])
                    )
                    if issues:
                        print(f"Found issues for {id}: {issues}")
                        report_struct[owner][automation_script][id].append(
                            dict([("known_issues", issues)])
                        )

    write_output(report_struct, args.output)


if __name__ == "__main__":
    sys.exit(main())
