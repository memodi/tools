import re


class Issues:
    """Issues definitions."""

    def match_ordered_strings(self, log: str, targets: list):
        """Returns True if all the regex strings in targets are found in order."""
        found_all = set()
        last_match_line = 0
        for target in targets:
            line_count = 0
            found = False
            for line in log.splitlines():
                if line_count < last_match_line:
                    continue
                line_count += 1
                match = re.search(target, line)
                if match:
                    found = True
                    break
            found_all.add(found)
        return all(found_all)

    def get_method_refs(self, names):
        """Return a dict of callable method refs, keyed by name in names."""
        refs = dict()
        for name in names:
            if name == "description":
                continue
            refs[name] = getattr(self, name)
        return refs

    def search(self, log_text, issue_def):
        """
        Return True if log_text matches all the criteria in issue_def.

        issue_def: A dict with keys that match method names defined in this
            class.
        description: issue_def.keys() is expected to be a list of method
            names, that match up with methods defined in this class. Each
            method is called with log_text and the coresponding issue_def
            value as arguments. The issue_def value must contain all the
            structured data that is required by the called method.
        """

        found_all = set()
        method_refs = self.get_method_refs(issue_def.keys())
        for name, ref in method_refs.items():
            found_all.add(ref(log_text, issue_def[name]))
        return all(found_all)
