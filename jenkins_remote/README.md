# Jenkins Remote

## Requirements
1. This script uses API TOKEN to trigger jenkins jobs. Below are the steps to create Jenkins API Token:
    * Replace your username in URL: https://mastern-jenkins-csb-openshift-qe.apps.ocp-c1.prod.psi.redhat.com/user/{your_username}/configure
    * Create API TOKEN.
    * Save API Token in environment vairable `JENKINS_API_TOKEN` in your shell's rc file (for e.g.: `~/.bashrc` for bash shell)

## Install Cluster
`install` command is used to trigger flexy-install jobs over a CLI. Currently it only supports profiles that are versioned-installer. The release version defaults to current OCP Qualifying OCP release.

```
$ ./jenkins_remote.py install --help
usage: jenkins_remote.py install [-h] -n NAME -p PROFILE [-v OCP_VERSION] [--ipi | --upi] [-c PROVIDER]

optional arguments:
  -h, --help            show this help message and exit
  -n NAME, --name NAME  specify cluster name (default: None)
  -p PROFILE, --profile PROFILE
                        specify profile to install with, NOTE: currently profiles specified as versioned-installer-{profile} are only supported (default: None)
  -v OCP_VERSION, --ocp-version OCP_VERSION
                        specify ocp version (default: 4.11)
  --ipi
  --upi
  -c PROVIDER, --provider PROVIDER
                        specify cloud provider (default: aws)
```

### Destroy Cluster
`destroy` command is used to trigger flexy-destroy jobs over a CLI. It takes flexy-install job ID as argument.

```
$ ./jenkins_remote.py destroy --help
usage: jenkins_remote.py destroy [-h] --build-number BUILD_NUMBER

optional arguments:
  -h, --help            show this help message and exit
  --build-number BUILD_NUMBER, -n BUILD_NUMBER
                        flexy build number to destroy (default: None)
```

### CI Monitor 

`ci_monitor` command is used to trigger ci_monitor/job/ci_failure_summary jenkins job.

```
$ ./jenkins_remote.py ci_monitor --help
usage: jenkins_remote.py ci_monitor [-h] --run-id RUN_ID [--file-jira]

optional arguments:
  -h, --help            show this help message and exit
  --run-id RUN_ID, -id RUN_ID
                        polarion run id (default: None)
  --file-jira, -fj      set to file JIRA tickets for CI monitor failures (default: False)
```

