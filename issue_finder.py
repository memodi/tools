from fnmatch import fnmatch
from http.client import IncompleteRead
import os
import pathlib
from urllib.error import HTTPError
import urllib.request
import yaml

from issues.issues import Issues


class IssuesFinder:
    """Known OCP CI issues."""

    def __init__(self):
        self.issues_found = []
        self.issues = Issues()
        self.issue_yamls = self.read_issue_yaml()

    def read_issue_yaml(self):
        """Return a list of objects read in from issue yaml defs."""
        issue_yamls = []
        script_dir_path = pathlib.Path(__file__).parent.resolve()
        for (dirpath, dirnames, filenames) in os.walk(
            os.path.join(script_dir_path, "issues")
        ):
            for name in filenames:
                if fnmatch(name, "issue_*.yaml"):
                    yaml_path = os.path.join(dirpath, name)
                    content = yaml.load(open(yaml_path), Loader=yaml.SafeLoader)
                    issue_yamls.append(content)
        return issue_yamls

    def find_issues(self, logs):
        """Returns a list of known issues found in the test logs."""
        if logs is not None:
            log_text = self.get_file_from_url(logs)
            if log_text is not None:
                for issue_def in self.issue_yamls:
                    # This could take awhile.
                    # Let the user know something is happening
                    print(" .")
                    if self.issues.search(log_text, issue_def):
                        self.issues_found.append(issue_def["description"])
        return self.issues_found

    def get_file_from_url(self, url: str):
        "Return file content downloaded from url."
        # Try three times to help with intermittent connection issues.
        for i in range(3):
            content = None
            try:
                content = urllib.request.urlopen(url).read().decode("utf8")
            except IncompleteRead:
                print(f"Caught IncompleteRead in iteration {i}.")
                continue
            except HTTPError:
                print(f"Skipping download due to HTTPError: {url}")
                break
            else:
                break
        return content
