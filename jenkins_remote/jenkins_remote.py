#!/usr/bin/env python3

import argparse
import requests
import sys
import os

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
        verify="/etc/certs/ipa.crt",
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
        verify="/etc/certs/ipa.crt",
    )
    if r.status_code == 201:
        nbuild = _get_jenkins_build_number(r.headers["location"])
        print(f"triggered job: {nbuild} to report CI failures successfully")


def install_cluster(args):
    job_url = "Flexy-install"
    version = args.ocp_version
    install_type = "ipi" if args.ipi else "upi"
    provider = args.provider
    path_to_profile = f"functionality-testing/aos-{version.replace('.', '_')}/{install_type}-on-{provider}/versioned-installer-{args.profile}"
    git_localtion = f"https://gitlab.cee.redhat.com/aosqe/flexy-templates/-/raw/master/{path_to_profile}"

    r = requests.get(git_localtion, verify="/etc/certs/ipa.crt")
    if r.status_code != 200:
        raise Exception(f"profile {path_to_profile} not found")
    jenkins_path_to_profile = f"private-templates/{path_to_profile}"

    print(f"successfully found profile {path_to_profile}")

    flexy_job_url = f"{JENKINS_URL}/{OCP_COMMON_JOBS}/{job_url}/buildWithParameters"

    r = requests.post(
        flexy_job_url,
        auth=(os.getenv("USER"), os.getenv("JENKINS_API_TOKEN")),
        verify="/etc/certs/ipa.crt",
        params={
            "INSTANCE_NAME_PREFIX": args.name,
            "VARIABLES_LOCATION": jenkins_path_to_profile,
        },
    )
    if r.status_code == 201:
        nbuild = _get_jenkins_build_number(r.headers["location"])
        print(f"triggered job to install cluster successfully with build id: {nbuild}")


def _get_jenkins_build_number(location):
    nbuild_resp = requests.get(f"{location}/api/json", verify="/etc/certs/ipa.crt")
    if nbuild_resp.status_code == 200:
        response = nbuild_resp.json()
        return response["executable"]["number"]


def args_parser():
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True
    install_parser = subparsers.add_parser("install")
    install_parser.add_argument(
        "-n", "--name", help="specify cluster name", required=True
    )
    install_parser.add_argument(
        "-p",
        "--profile",
        help="specify profile to install with, NOTE: currently profiles specified as versioned-installer-{profile} are only supported",
        required=True,
    )
    install_parser.add_argument(
        "-v", "--ocp-version", default="4.10", help="specify ocp version"
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
        "--build-number", "-n", required=True, help="flexy build number to destroy"
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
