#!/usr/bin/env python3

import argparse
import requests
import sys
import os
import json
from datetime import datetime
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

JENKINS_URL = (
    "https://mastern-jenkins-csb-openshift-qe.apps.ocp-c1.prod.psi.redhat.com/job"
)

OCP_COMMON_JOBS = "ocp-common/job"
CI_MONITOR_JOBS = "ci_monitor/job"


def destroy_cluster(args):
    print(f"destroying cluster {args.build_number}")
    job_url = "Flexy-destroy"
    params = f"BUILD_NUMBER={args.build_number}"
    destroy_job_url = (
        f"{JENKINS_URL}/{OCP_COMMON_JOBS}/{job_url}/buildWithParameters?{params}"
    )
    r = requests.post(
        destroy_job_url,
        auth=(os.getenv("USER"), os.getenv("JENKINS_API_TOKEN")),
        verify=False,
    )
    if r.status_code == 201:
        nbuild = _get_jenkins_build_number(r.headers["location"])
        print("triggered job: {nbuild}  to destroy cluster successfully")


def ci_monitor(args):
    runid = args.run_id
    toFileJira = args.file_jira
    print(f"running ci monitor for run id {runid} with file_jira = {toFileJira} ")
    job_url = "ci_failure_summary"
    params = f"TEST_RUN_ID={runid}&FILE_JIRA_ISSUES={toFileJira}"
    ci_monitor_url = (
        f"{JENKINS_URL}/{CI_MONITOR_JOBS}/{job_url}/buildWithParameters?{params}"
    )
    r = requests.post(
        ci_monitor_url,
        auth=(os.getenv("USER"), os.getenv("JENKINS_API_TOKEN")),
        verify=False,
    )
    if r.status_code == 201:
        nbuild = _get_jenkins_build_number(r.headers["location"])
        print(f"triggered job: {nbuild} to report CI failures successfully")


def install_cluster(args):
    job_url = "Flexy-install"
    version = args.ocp_version
    install_type = "ipi" if args.ipi else "upi"
    provider = args.provider
    path_to_profile = ""
    name = ""

    if not args.name:
        name = os.getenv("USER") + "-" + datetime.today().strftime("%m%d%H%M")
    else:
        name = args.name

    if args.profile:
        path_to_profile = f"functionality-testing/aos-{version.replace('.', '_')}/{install_type}-on-{provider}/versioned-installer-{args.profile}"
    else:
        path_to_profile = f"functionality-testing/aos-{version.replace('.', '_')}/{install_type}-on-{provider}/versioned-installer"

    launcher_vars = ""
    if args.launcher_vars:
        launcher_vars = get_jenkins_launcher_vars(args.launcher_vars)

    git_localtion = f"https://gitlab.cee.redhat.com/aosqe/flexy-templates/-/raw/master/{path_to_profile}"

    r = requests.get(git_localtion, verify=False)
    if r.status_code != 200:
        raise Exception(f"profile {path_to_profile} not found")
    jenkins_path_to_profile = f"private-templates/{path_to_profile}"

    print(f"successfully found profile {path_to_profile}")

    flexy_job_url = f"{JENKINS_URL}/{OCP_COMMON_JOBS}/{job_url}/buildWithParameters"

    r = requests.post(
        flexy_job_url,
        auth=(os.getenv("USER"), os.getenv("JENKINS_API_TOKEN")),
        verify=False,
        params={
            "INSTANCE_NAME_PREFIX": name,
            "VARIABLES_LOCATION": jenkins_path_to_profile,
            "LAUNCHER_VARS": launcher_vars,
        },
    )
    if r.status_code == 201:
        nbuild = _get_jenkins_build_number(r.headers["location"])
        print(f"triggered job to install cluster successfully with build id: {nbuild}")


def get_jenkins_launcher_vars(vars):
    file = ""
    if vars.startswith("~"):
        vars = os.path.expanduser(vars)
    isfile = False
    if os.path.isfile(vars):
        file = os.path.abspath(vars)
        isfile = True
    varsd = None
    if isfile:
        fh = open(file)
        varsd = json.load(fh)
        fh.close()
    else:
        varsd = json.loads(vars)
    built_vars = ""
    for k, v in varsd.items():
        built_vars += f"{k}: {v}\n"
    return built_vars


def _get_jenkins_build_number(location):
    nbuild_resp = requests.get(f"{location}/api/json", verify=False)
    if nbuild_resp.status_code == 200:
        response = nbuild_resp.json()
        return response["executable"]["number"]


def args_parser():
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True
    install_parser = subparsers.add_parser("install")
    install_parser.add_argument(
        "-n", "--name", help="specify cluster name", required=False
    )
    install_parser.add_argument(
        "-p",
        "--profile",
        help="specify profile to install with, NOTE: currently profiles specified as versioned-installer-{profile} are only supported",
    )
    install_parser.add_argument(
        "-v", "--ocp-version", default="4.17", help="specify ocp version"
    )

    install_parser.add_argument(
        "-l",
        "--launcher-vars",
        type=str,
        required=False,
        help="Flexy launcher vars, can be supplied as JSON file or str",
    )

    group = install_parser.add_mutually_exclusive_group()
    group.add_argument("--ipi", action="store_false", default=True)
    group.add_argument("--upi", action="store_true", default=False)
    install_parser.add_argument(
        "-c", "--provider", default="aws", help="specify cloud provider"
    )

    install_parser.set_defaults(func=install_cluster)

    destroy_parser = subparsers.add_parser("destroy")
    destroy_parser.add_argument(
        "--build-number",
        "-n",
        type=int,
        required=True,
        help="flexy build number to destroy",
    )
    destroy_parser.set_defaults(func=destroy_cluster)

    ci_parser = subparsers.add_parser("ci_monitor")
    ci_parser.add_argument("--run-id", "-id", required=True, help="polarion run id")
    ci_parser.add_argument(
        "--file-jira",
        "-fj",
        action="store_true",
        help="set to file JIRA tickets for CI monitor failures",
    )
    ci_parser.set_defaults(func=ci_monitor)

    args = parser.parse_args()
    if args.command == "install" and args.upi:
        args.ipi = False
    return args


def main():
    args = args_parser()
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
