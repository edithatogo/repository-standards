"""Read-only, bounded audit of local and inherited GitHub community material.

This checks the documented baseline, not every optional GitHub schema feature or
live repository setting. Settings and default-repository visibility are explicit
observations supplied by the caller. It never executes repository content.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import stat
import sys
from pathlib import Path
from urllib.parse import urlsplit

try:
    import yaml
except ImportError:  # Missing parser is unknown evidence, never a successful check.
    yaml = None


MAX_BYTES = 262_144
MAX_FILES = 20_000
CONTROLS = (
    "readme", "contributing", "code_of_conduct", "security", "support",
    "issue_templates", "issue_chooser", "pull_request_template", "agents",
    "workflows", "dependency_updates", "gitignore", "editorconfig",
    "env_example", "devcontainer", "discussion_templates", "template_repository",
)
NATIVE_COMMUNITY_CONTROLS = (
    "readme", "contributing", "code_of_conduct", "security",
    "issue_templates", "pull_request_template",
)
DEFAULT_POLICY = {
    "schema_version": 1, "required": list(CONTROLS), "recommended": [],
    "environment_configuration": None, "devcontainer": "optional",
    "template_repository": False,
    "issue_form_kinds": {
        "bug": ["bug", "bug_report"],
        "feature": ["feature", "feature_request"],
        "documentation": ["documentation", "docs"],
    },
}
GUIDANCE = {
    "readme": ("usage|installation|getting started|access", "development|verification|validation|testing", "security", "licen[cs]e|rights"),
    "contributing": ("getting started|setup|development", "validation|verification|testing|tests", "pull requests?|submitting|making changes"),
    "code_of_conduct": ("expected behavio[u]?r|standards|conduct", "reporting|report a concern", "enforcement|consequences"),
    "security": ("supported versions?|support policy", "reporting|report a vulnerability", "response|disclosure"),
    "support": ("getting help|where to ask|support channels?", "what to include|information to provide", "availability|expectations|response"),
    "agents": ("architecture|structure|operating model|boundaries", "validation|verification|testing|required evidence"),
    "pull_request_template": ("summary|change|purpose", "related|issues?|references", "validation|evidence|tests?|verification", "compatibility|rollout|risk", "documentation|docs"),
}
DOC_NAMES = {
    "readme": "README.md", "contributing": "CONTRIBUTING.md",
    "code_of_conduct": "CODE_OF_CONDUCT.md", "security": "SECURITY.md",
    "support": "SUPPORT.md", "agents": "AGENTS.md",
}


class EvidenceError(ValueError):
    """A safe fixed reason for unavailable or invalid evidence."""

    def __init__(self, status, reason):
        super().__init__(reason)
        self.status = status


def record(status, source, paths=(), details=()):
    return {"status": status, "source": source, "paths": list(paths), "details": list(details)}


def directory_descriptors(directory, *, create=False):
    """Open every absolute path component without following any symlink."""
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise EvidenceError("unknown", "Safe non-following file reads are unavailable")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptors = [os.open(Path(directory).anchor, flags)]
    try:
        for component in Path(directory).parts[1:]:
            if component == "..":
                raise ValueError("Parent traversal is not supported")
            try:
                following = os.open(component, flags, dir_fd=descriptors[-1])
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(component, mode=0o700, dir_fd=descriptors[-1])
                following = os.open(component, flags, dir_fd=descriptors[-1])
            descriptors.append(following)
        return descriptors
    except BaseException:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
        raise


def bounded_text(root, relative):
    """Read UTF-8 text through bounded, no-follow directory and file descriptors."""
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or not path.name:
        raise EvidenceError("unknown", "Symlink or unsafe path is not inspected")
    descriptors = []
    try:
        descriptors.extend(directory_descriptors(root))
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        for component in path.parts[:-1]:
            descriptors.append(os.open(component, directory_flags, dir_fd=descriptors[-1]))
        file_descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptors[-1])
        descriptors.append(file_descriptor)
        if not stat.S_ISREG(os.fstat(file_descriptor).st_mode):
            raise EvidenceError("unknown", "Non-regular files are not inspected")
        data = b""
        while len(data) <= MAX_BYTES:
            chunk = os.read(file_descriptor, min(65_536, MAX_BYTES + 1 - len(data)))
            if not chunk:
                break
            data += chunk
        if len(data) > MAX_BYTES:
            raise EvidenceError("unknown", "File exceeds bounded audit size")
        return data.decode("utf-8-sig")
    except (OSError, UnicodeError) as exc:
        raise EvidenceError("unknown", "File is unavailable or not UTF-8 text") from exc
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


class Tree:
    """Inventory and bounded reads that refuse symlinks and non-regular files."""

    def __init__(self, root):
        root = Path(root).absolute()
        if any(path.is_symlink() for path in [root, *root.parents]) or not root.is_dir():
            raise ValueError("Repository root must be a real directory")
        root = Path(os.path.normpath(root))
        self.root, self.paths, self.blocked = root, set(), set()
        for directory, dirs, files in os.walk(root, followlinks=False):
            for name in list(dirs):
                path = Path(directory) / name
                if path.is_symlink():
                    self.blocked.add(path.relative_to(root).as_posix())
                    dirs.remove(name)
                elif name in {".git", ".venv", "node_modules", "__pycache__"}:
                    dirs.remove(name)
            for name in files:
                path = Path(directory) / name
                relative = path.relative_to(root).as_posix()
                self.paths.add(relative)
                if path.is_symlink() or not path.is_file():
                    self.blocked.add(relative)
                if len(self.paths) > MAX_FILES:
                    raise ValueError("Repository exceeds bounded audit file count")

    def is_blocked(self, relative):
        return any(relative == item or relative.startswith(item + "/") for item in self.blocked)

    def read(self, relative):
        if self.is_blocked(relative):
            raise EvidenceError("unknown", "Symlink or unsafe path is not inspected")
        return bounded_text(self.root, relative)

    def select(self, names, folders=(".github", "", "docs")):
        wanted = {name.casefold() for name in names}
        for folder in folders:
            if folder and self.is_blocked(folder):
                raise EvidenceError("unknown", "Higher-precedence directory is a symlink")
            matches = sorted(path for path in self.paths if (Path(path).parent.as_posix() if Path(path).parent.as_posix() != "." else "") == folder and Path(path).name.casefold() in wanted)
            if len(matches) > 1:
                raise EvidenceError("unknown", "Ambiguous case-equivalent files")
            if matches:
                return matches[0]
        return None

    def under(self, directory, suffixes):
        if self.is_blocked(directory):
            raise EvidenceError("unknown", "Template directory is a symlink")
        return sorted(path for path in self.paths if Path(path).parent.as_posix() == directory and Path(path).suffix.casefold() in suffixes)


def yaml_value(text):
    if yaml is None:
        raise EvidenceError("unknown", "PyYAML is unavailable; YAML was not validated")

    class Loader(yaml.SafeLoader):
        pass

    Loader.yaml_implicit_resolvers = {
        key: [(tag, expression) for tag, expression in entries if tag != "tag:yaml.org,2002:bool"]
        for key, entries in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }
    Loader.add_implicit_resolver("tag:yaml.org,2002:bool", re.compile(r"^(?:true|false)$", re.I), list("tTfF"))

    def mapping(loader, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if not isinstance(key, (str, int, float, bool, type(None))) or key in result:
                raise ValueError("Duplicate or unsupported YAML key")
            result[key] = loader.construct_object(value_node, deep=deep)
        return result

    Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
    try:
        depth = 0
        for number, event in enumerate(yaml.parse(text)):
            if number > 10_000 or isinstance(event, yaml.events.AliasEvent):
                raise ValueError("YAML aliases or excessive events are unsupported")
            if isinstance(event, (yaml.events.MappingStartEvent, yaml.events.SequenceStartEvent)):
                depth += 1
            elif isinstance(event, (yaml.events.MappingEndEvent, yaml.events.SequenceEndEvent)):
                depth -= 1
            if depth > 40:
                raise ValueError("YAML nesting is excessive")
        return yaml.load(text, Loader=Loader)
    except (yaml.YAMLError, ValueError, TypeError, RecursionError) as exc:
        raise EvidenceError("fail", "Invalid YAML, duplicate keys, aliases or unsupported structure") from exc


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def guidance_errors(text, control, *, native=False):
    if native:
        text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
        body = "\n".join(line for line in text.splitlines() if line.strip()
                         and not re.match(r"^\s*(?:#{1,6}\s|`{3,}|~{3,}|[-*_]{3,}\s*$)", line))
        return [] if nonempty(body) and not re.match(r"^\s*(TODO|TBD|placeholder)\b", body, re.I) else ["Empty or placeholder community document"]
    sections = []
    for line in text.splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if match:
            sections.append([match.group(1).casefold(), ""])
        elif sections:
            sections[-1][1] += line + "\n"
    errors = []
    for pattern in GUIDANCE[control]:
        matches = [body for title, body in sections if re.search(pattern, title, re.I)]
        if not matches or not any(nonempty(body) and not re.match(r"^\s*(TODO|TBD|placeholder)\b", body, re.I) for body in matches):
            errors.append("Missing substantive guidance: " + pattern)
    return errors


def form_errors(value, *, discussion=False, markdown=False, native=False):
    if not isinstance(value, dict):
        return ["Template must be a mapping"]
    allowed = {"body", "title", "labels"} if discussion else {"name", "description", "about", "title", "labels", "assignees", "projects", "type", "body"}
    errors = []
    if set(value) - allowed:
        errors.append("Unsupported top-level template fields")
    if not discussion:
        if not nonempty(value.get("name")) or len(value["name"].strip()) <= 3:
            errors.append("Template name must contain more than three characters")
        if not nonempty(value.get("about" if markdown else "description")):
            errors.append("Template description is required")
    for key in ("title", "type"):
        if key in value and not isinstance(value[key], str):
            errors.append(key + " must be text")
    for key in ("labels", "assignees", "projects"):
        empty_legacy_metadata = native and markdown and key in {"labels", "assignees"} and value.get(key) == ""
        if key in value and not empty_legacy_metadata and not (nonempty(value[key]) or isinstance(value[key], list) and all(nonempty(item) for item in value[key])):
            errors.append(key + " must contain text values")
    if markdown:
        return errors
    body = value.get("body")
    if not isinstance(body, list) or not body or len(body) > 100:
        return errors + ["Form requires a bounded non-empty body array"]
    ids, inputs = set(), 0
    for field in body:
        if not isinstance(field, dict) or set(field) - {"type", "id", "attributes", "validations"}:
            errors.append("Invalid form field mapping")
            continue
        kind, attrs = field.get("type"), field.get("attributes")
        if not isinstance(kind, str) or kind not in {"markdown", "textarea", "input", "dropdown", "checkboxes"}:
            errors.append("Unsupported input type; baseline schema does not validate it")
            continue
        if not isinstance(attrs, dict):
            errors.append("Field attributes must be a mapping")
            continue
        allowed_attributes = {
            "markdown": {"value"},
            "input": {"label", "description", "placeholder", "value"},
            "textarea": {"label", "description", "placeholder", "value", "render"},
            "dropdown": {"label", "description", "multiple", "options", "default"},
            "checkboxes": {"label", "description", "options"},
        }
        if set(attrs) - allowed_attributes[kind]:
            errors.append("Unsupported attributes for this input type")
        if "id" in field:
            field_id = field["id"]
            if not nonempty(field_id) or not re.fullmatch(r"[A-Za-z0-9_-]+", field_id) or field_id in ids:
                errors.append("Field IDs must be valid and unique")
            else:
                ids.add(field_id)
        validation = field.get("validations", {})
        if not isinstance(validation, dict) or set(validation) - {"required"} or "required" in validation and type(validation["required"]) is not bool:
            errors.append("Required validation must be a boolean")
        if kind == "markdown":
            if not nonempty(attrs.get("value")):
                errors.append("Markdown field requires text")
            continue
        inputs += 1
        if not nonempty(attrs.get("label")):
            errors.append("Input field requires a label")
        if kind in {"dropdown", "checkboxes"}:
            options = attrs.get("options")
            if not isinstance(options, list) or not options:
                errors.append("Selection field requires options")
            elif kind == "dropdown" and not all(nonempty(item) for item in options):
                errors.append("Dropdown options must be text")
            elif kind == "dropdown":
                if len(options) != len(set(options)):
                    errors.append("Dropdown options must be distinct")
                if "default" in attrs and (type(attrs["default"]) is not int or not 0 <= attrs["default"] < len(options) or any(option.casefold() in {"none", "n/a"} for option in options)):
                    errors.append("Dropdown default must be a valid option index without None/n/a choices")
            elif kind == "checkboxes" and not all(isinstance(item, dict) and nonempty(item.get("label")) and ("required" not in item or type(item["required"]) is bool) and not set(item) - {"label", "required"} for item in options):
                errors.append("Checkbox options must have valid labels and requirements")
        for key in ("description", "placeholder", "render", "value"):
            if key in attrs and not isinstance(attrs[key], str):
                errors.append("Text field attributes must be strings")
        if "multiple" in attrs and type(attrs["multiple"]) is not bool:
            errors.append("Multiple selection must be a boolean")
    if not inputs:
        errors.append("Form requires at least one non-Markdown input")
    return errors


def template_errors(tree, path, *, discussion=False, native=False):
    text = tree.read(path)
    if Path(path).suffix.casefold() == ".md":
        lines = text.splitlines()
        if not lines or lines[0].strip() != "---":
            return ["Markdown issue template requires YAML frontmatter"]
        end = next((i for i, line in enumerate(lines[1:], 1) if line.strip() == "---"), None)
        if end is None or not nonempty("\n".join(lines[end + 1:])):
            return ["Markdown issue template requires closed frontmatter and prompts"]
        return form_errors(yaml_value("\n".join(lines[1:end])), markdown=True, native=native)
    return form_errors(yaml_value(text), discussion=discussion, native=native)


def chooser_errors(value):
    if not isinstance(value, dict) or not value or set(value) - {"blank_issues_enabled", "contact_links"}:
        return ["Chooser requires recognised configuration fields"]
    errors = []
    if "blank_issues_enabled" in value and type(value["blank_issues_enabled"]) is not bool:
        errors.append("blank_issues_enabled must be a boolean")
    links = value.get("contact_links", [])
    if not isinstance(links, list):
        return errors + ["Contact links must be an array"]
    for link in links:
        if not isinstance(link, dict) or set(link) != {"name", "url", "about"} or not all(nonempty(link.get(key)) for key in ("name", "url", "about")):
            errors.append("Contact link requires name, URL and description")
        else:
            try:
                parsed = urlsplit(link["url"])
                if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
                    errors.append("Contact links require an absolute HTTPS URL without credentials")
            except ValueError:
                errors.append("Contact link has an invalid URL")
    return errors


def validate_policy(policy):
    result = dict(DEFAULT_POLICY)
    if policy is not None:
        if not isinstance(policy, dict) or set(policy) != set(DEFAULT_POLICY):
            raise ValueError("Invalid community bootstrap policy fields")
        result.update(policy)
    if type(result["schema_version"]) is not int or result["schema_version"] != 1:
        raise ValueError("Unsupported community bootstrap policy version")
    for key in ("required", "recommended"):
        values = result[key]
        if not isinstance(values, list) or key == "required" and not values or not all(isinstance(item, str) and item in CONTROLS for item in values) or len(values) != len(set(values)):
            raise ValueError("Policy control list is invalid")
    if result["environment_configuration"] is not None and type(result["environment_configuration"]) is not bool:
        raise ValueError("Environment applicability must be boolean or null")
    if not isinstance(result["devcontainer"], str) or result["devcontainer"] not in {"required", "optional"} or type(result["template_repository"]) is not bool:
        raise ValueError("Invalid bootstrap applicability")
    kinds = result["issue_form_kinds"]
    narrow = result["required"] == list(NATIVE_COMMUNITY_CONTROLS) and not result["recommended"]
    if not isinstance(kinds, dict) or (not kinds and not narrow) or not all(nonempty(role) and re.fullmatch(r"[a-z][a-z_]*", role) and isinstance(stems, list) and stems and all(nonempty(stem) and re.fullmatch(r"[A-Za-z0-9_-]+", stem) for stem in stems) and len(stems) == len(set(stems)) for role, stems in kinds.items()):
        raise ValueError("Issue form role mapping is invalid")
    return result


def local_policy(tree, policy):
    path = ".github/community-bootstrap.json"
    if path not in tree.paths and not tree.is_blocked(path):
        return policy
    try:
        declaration = json.loads(tree.read(path))
    except (EvidenceError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid local applicability declaration") from exc
    allowed = {"schema_version", "environment_configuration", "devcontainer", "template_repository", "rationale"}
    if not isinstance(declaration, dict) or set(declaration) != allowed or type(declaration.get("schema_version")) is not int or declaration["schema_version"] != 1:
        raise ValueError("Local declaration may only set explicit applicability")
    reasons = declaration.get("rationale", {})
    if not isinstance(reasons, dict) or set(reasons) != {"environment_configuration", "devcontainer"}:
        raise ValueError("Invalid local applicability rationale")
    for key in ("environment_configuration", "devcontainer"):
        if not nonempty(reasons.get(key)) or len(reasons[key].strip()) < 20:
            raise ValueError("Local applicability requires a rationale")
    combined = validate_policy({**policy, **{key: value for key, value in declaration.items() if key != "rationale"}})
    for key in ("environment_configuration", "template_repository"):
        if policy[key] is True:
            combined[key] = True
    if policy["devcontainer"] == "required":
        combined["devcontainer"] = "required"
    return combined


def workflow_job_valid(job):
    """Check the executable/reusable job shape without simulating execution."""
    if not isinstance(job, dict) or not job:
        return False
    if "uses" in job:
        return nonempty(job["uses"]) and "steps" not in job and "runs-on" not in job
    runner = job.get("runs-on")
    if isinstance(runner, dict):
        labels = runner.get("labels")
        runner_valid = (
            bool(runner) and set(runner).issubset({"group", "labels"})
            and ("group" not in runner or nonempty(runner["group"]))
            and ("labels" not in runner or nonempty(labels)
                 or isinstance(labels, list) and bool(labels) and all(nonempty(item) for item in labels))
        )
    else:
        runner_valid = nonempty(runner) or isinstance(runner, list) and bool(runner) and all(nonempty(item) for item in runner)
    steps = job.get("steps")
    return runner_valid and isinstance(steps, list) and bool(steps) and all(
        isinstance(step, dict)
        and (("run" in step) != ("uses" in step))
        and nonempty(step["run"] if "run" in step else step["uses"])
        for step in steps
    )

def container_backend_valid(value):
    """Validate the types of the declared image/build/compose alternatives."""
    if not isinstance(value, dict):
        return False
    supplied = set(value).intersection({"image", "build", "dockerFile", "dockerComposeFile"})
    if not supplied:
        return False
    for key in supplied:
        item = value[key]
        if key in {"image", "dockerFile"} and not nonempty(item):
            return False
        if key == "build":
            if not isinstance(item, dict) or not item:
                return False
            if any(field in item and not nonempty(item[field]) for field in ("dockerfile", "context", "target")):
                return False
        if key == "dockerComposeFile" and not (
            nonempty(item) or isinstance(item, list) and bool(item) and all(nonempty(path) for path in item)
        ):
            return False
    return True


def audit_repository(repository_dir, *, defaults_dir=None, metadata=None, policy=None):
    """Return evidence without executing files or inferring live settings."""
    metadata = {} if metadata is None else metadata
    if not isinstance(metadata, dict):
        raise ValueError("Metadata must be an object")
    visibility = metadata.get("defaults_visibility", "unknown")
    if not isinstance(visibility, str) or visibility not in {"public", "private", "absent", "unknown"}:
        raise ValueError("Invalid default repository visibility")
    for key in ("has_discussions", "is_template"):
        if metadata.get(key) is not None and type(metadata[key]) is not bool:
            raise ValueError("Repository settings must be boolean or unknown")
    categories = metadata.get("discussion_categories")
    if categories is not None and (not isinstance(categories, list) or not all(nonempty(item) and re.fullmatch(r"[a-z0-9-]+", item) for item in categories) or len(categories) != len(set(categories))):
        raise ValueError("Discussion categories must be unique non-poll slugs")
    local = Tree(repository_dir)
    defaults = Tree(defaults_dir) if defaults_dir is not None and visibility == "public" else None
    policy = local_policy(local, validate_policy(policy))
    native = (policy["required"] == list(NATIVE_COMMUNITY_CONTROLS)
              and not policy["recommended"] and not policy["issue_form_kinds"])
    checks = {}

    def default_missing():
        known_absent = visibility in {"private", "absent"} or defaults is not None
        return record("fail" if known_absent else "unknown", "missing" if known_absent else "unavailable", details=["No eligible default found" if known_absent else "Account defaults were not available for inspection"])

    def effective(names, *, inherit=True, folders=(".github", "", "docs")):
        path = local.select(names, folders)
        if path:
            return local, path, "local"
        if inherit and defaults is not None:
            path = defaults.select(names, folders)
            if path:
                return defaults, path, "inherited"
        return None, None, None

    def run(control, operation):
        try:
            checks[control] = operation()
        except EvidenceError as exc:
            checks[control] = record(exc.status, "unavailable", details=[str(exc)])

    for control, filename in DOC_NAMES.items():
        def document(control=control, filename=filename):
            inherit = control not in {"readme", "agents"}
            tree, path, source = effective([filename], inherit=inherit, folders=("",) if control in {"readme", "agents"} else (".github", "", "docs"))
            if control == "agents" and tree is None:
                path = local.select(["copilot-instructions.md"], (".github",))
                if path is not None:
                    tree, source = local, "local"
            if tree is None:
                return default_missing() if inherit else record("fail", "missing", details=["Repository-local file is required"])
            errors = guidance_errors(tree.read(path), control, native=native)
            return record("fail" if errors else "pass", source, [path], errors)
        run(control, document)

    def issue_inventory(tree):
        forms = [path for path in tree.under(".github/ISSUE_TEMPLATE", {".md", ".yml"}) if Path(path).name.casefold() != "config.yml"]
        config = tree.select(["config.yml"], (".github/ISSUE_TEMPLATE",))
        unsupported = tree.under(".github/ISSUE_TEMPLATE", {".yaml"})
        return forms, config, unsupported

    try:
        forms, chooser, unsupported = issue_inventory(local)
        source, tree = "local", local
        if not forms and not chooser and not unsupported:
            if defaults is None:
                checks["issue_templates"] = checks["issue_chooser"] = default_missing()
                tree = None
            else:
                tree, source = defaults, "inherited"
                forms, chooser, unsupported = issue_inventory(tree)
        if tree is not None:
            errors, valid, unknown = [], [], []
            for path in forms:
                try:
                    found = template_errors(tree, path, native=native)
                    errors.extend(path + ": " + reason for reason in found)
                    if not found:
                        valid.append(path)
                except EvidenceError as exc:
                    (unknown if exc.status == "unknown" else errors).append(path + ": " + str(exc))
            chooser_error = chooser_errors(yaml_value(tree.read(chooser))) if chooser else ["Effective issue directory has no chooser configuration"]
            checks["issue_chooser"] = record("fail" if chooser_error else "pass", source, [chooser] if chooser else [], chooser_error)
            errors.extend("Issue forms require .yml; unsupported file: " + path for path in unsupported)
            if not valid and not unknown:
                errors.append("No valid effective issue template")
            stems = {re.sub(r"^\d+[-_]", "", Path(path).stem.casefold()) for path in valid}
            for role, accepted in policy["issue_form_kinds"].items():
                if not stems.intersection(stem.casefold() for stem in accepted):
                    errors.append("Missing effective issue form role: " + role)
            # Invalid local attempts are not silently certified via inherited forms.
            status = "pass" if native and valid else "unknown" if unknown else "fail" if errors else "pass"
            checks["issue_templates"] = record(status, source, forms + unsupported, errors + unknown)
    except EvidenceError as exc:
        checks["issue_templates"] = checks["issue_chooser"] = record(exc.status, "unavailable", details=[str(exc)])

    def pr_templates():
        for tree, source in [(local, "local"), (defaults, "inherited")]:
            if tree is None:
                continue
            path = tree.select(["pull_request_template.md", "pull_request_template.txt"])
            paths = [path] if path else []
            if not paths:
                for folder in (".github/PULL_REQUEST_TEMPLATE", "PULL_REQUEST_TEMPLATE", "docs/PULL_REQUEST_TEMPLATE"):
                    paths = tree.under(folder, {".md", ".txt"})
                    if paths:
                        break
            if paths:
                errors = [path + ": " + reason for path in paths for reason in guidance_errors(tree.read(path), "pull_request_template", native=native)]
                return record("fail" if errors else "pass", source, paths, errors)
        return default_missing()
    run("pull_request_template", pr_templates)

    def text_baseline(path, control):
        if path not in local.paths:
            if local.is_blocked(path):
                raise EvidenceError("unknown", "Required local path is a symlink")
            return record("fail", "missing", details=["Required local configuration is absent"])
        text = local.read(path)
        useful = [line for line in text.splitlines() if line.strip() and not line.lstrip().startswith(("#", ";"))]
        ok = bool(useful)
        if control == "editorconfig":
            ok = ok and bool(re.search(r"(?m)^\s*root\s*=\s*true\s*$", text)) and bool(re.search(r"(?m)^\s*\[.+\]\s*$", text)) and bool(re.search(r"(?m)^\s*(?:charset|indent_style|end_of_line|insert_final_newline|trim_trailing_whitespace)\s*=\s*\S+", text))
        elif control == "env_example":
            ok = ok and bool(re.search(r"(?m)^\s*(?:export\s+)?[A-Za-z_][A-Za-z0-9_]*\s*=", text))
        return record("pass" if ok else "fail", "local", [path], [] if ok else ["Configuration contains no usable baseline"])
    for control, path in [("gitignore", ".gitignore"), ("editorconfig", ".editorconfig")]:
        run(control, lambda control=control, path=path: text_baseline(path, control))

    def workflows():
        paths = local.under(".github/workflows", {".yml", ".yaml"})
        if not paths:
            return record("fail", "missing", details=["No local workflow is configured"])
        errors = []
        for path in paths:
            value = yaml_value(local.read(path))
            if not isinstance(value, dict) or not value.get("on") or not isinstance(value.get("jobs"), dict) or not value["jobs"]:
                errors.append(path + ": workflow requires triggers and jobs")
            elif not all(workflow_job_valid(job) for job in value["jobs"].values()):
                errors.append(path + ": jobs require a valid reusable call or runner and executable steps")
        return record("fail" if errors else "pass", "local", paths, errors + ["Workflow structure observed; execution and required checks are not certified"])
    run("workflows", workflows)

    def dependencies():
        paths = [path for path in ("renovate.json", "renovate.json5", ".github/renovate.json", ".github/renovate.json5", ".github/dependabot.yml", ".github/dependabot.yaml") if path in local.paths]
        if not paths:
            return record("fail", "missing", details=["No repository dependency-update configuration"])
        errors = []
        for path in paths:
            if path.endswith(".json5"):
                raise EvidenceError("unknown", "JSON5 Renovate configuration needs a qualified parser")
            try:
                value = yaml_value(local.read(path)) if "dependabot." in path else json.loads(local.read(path))
            except json.JSONDecodeError as exc:
                raise EvidenceError("fail", "Invalid dependency configuration JSON") from exc
            if "dependabot." in path:
                updates = value.get("updates") if isinstance(value, dict) else None
                if not isinstance(value, dict) or value.get("version") != 2 or not isinstance(updates, list) or not updates or not all(isinstance(item, dict) and nonempty(item.get("package-ecosystem")) and (nonempty(item.get("directory")) or isinstance(item.get("directories"), list) and item["directories"] and all(nonempty(directory) for directory in item["directories"])) and isinstance(item.get("schedule"), dict) and nonempty(item["schedule"].get("interval")) for item in updates):
                    errors.append(path + ": invalid dependency ecosystem/directory/schedule configuration")
            elif not isinstance(value, dict) or not value or value.get("enabled") is False:
                errors.append(path + ": dependency updates are empty or disabled")
            elif "extends" in value and (not isinstance(value["extends"], list) or not value["extends"] or not all(nonempty(item) for item in value["extends"])):
                errors.append(path + ": Renovate extends must be a non-empty string array")
            elif "enabledManagers" in value and (not isinstance(value["enabledManagers"], list) or not value["enabledManagers"] or not all(nonempty(item) for item in value["enabledManagers"])):
                errors.append(path + ": Renovate enabled managers must be a non-empty string array")
        return record("fail" if errors else "pass", "local", paths, errors + ["Configuration observed; provider activation and complete ecosystem coverage are unverified"])
    run("dependency_updates", dependencies)

    if policy["environment_configuration"] is False:
        checks["env_example"] = record("not_applicable", "metadata", details=["Owner declares no environment configuration"])
    elif policy["environment_configuration"] is None:
        checks["env_example"] = record("unknown", "metadata", details=["Environment applicability has not been declared"])
    else:
        run("env_example", lambda: text_baseline(".env.example", "env_example"))

    def devcontainer():
        paths = [path for path in local.paths if path == ".devcontainer.json" or path == ".devcontainer/devcontainer.json" or re.fullmatch(r"\.devcontainer/[^/]+/devcontainer\.json", path)]
        if not paths:
            return record("not_applicable" if policy["devcontainer"] == "optional" else "fail", "missing", details=["No custom development container requested" if policy["devcontainer"] == "optional" else "Required development container is absent"])
        errors = []
        for path in sorted(paths):
            try:
                value = json.loads(local.read(path))
            except json.JSONDecodeError:
                raise EvidenceError("unknown", "Devcontainer JSONC needs a qualified parser; not validated")
            if not container_backend_valid(value):
                errors.append(path + ": container definition requires valid image/build/compose configuration")
        return record("fail" if errors else "pass", "local", sorted(paths), errors + ["Configuration only; container build and commands were not executed"])
    run("devcontainer", devcontainer)

    def discussions():
        if metadata.get("has_discussions") is False:
            return record("not_applicable", "metadata", details=["Discussions observed disabled"])
        if metadata.get("has_discussions") is not True or categories is None:
            return record("unknown", "metadata", details=["Enabled setting and non-poll category slugs must be observed"])
        paths, errors, sources = [], [], set()
        if not categories:
            errors.append("No observed non-poll discussion categories")
        for category in categories:
            tree, path, source = effective([category + ".yml"], folders=(".github/DISCUSSION_TEMPLATE",))
            if tree is None:
                missing = default_missing()
                if missing["status"] == "unknown":
                    return missing
                errors.append("No form for observed category: " + category)
                continue
            paths.append(path)
            sources.add(source)
            errors.extend(path + ": " + reason for reason in template_errors(tree, path, discussion=True))
        for path in local.under(".github/DISCUSSION_TEMPLATE", {".yml", ".yaml"}):
            if Path(path).stem not in categories or Path(path).suffix != ".yml":
                errors.append("Local discussion form does not match an eligible observed category: " + path)
        return record("fail" if errors else "pass", "mixed" if len(sources) > 1 else next(iter(sources), "missing"), paths, errors)
    run("discussion_templates", discussions)
    checks["template_repository"] = record(
        "not_applicable" if not policy["template_repository"] else "unknown" if metadata.get("is_template") is None else "pass" if metadata["is_template"] else "fail",
        "metadata", details=["Template flag is caller-supplied observed metadata, not inferred from filenames"],
    )
    failures = [control for control in policy["required"] if checks[control]["status"] not in {"pass", "not_applicable"}]
    return {
        "schema_version": 1, "conformant": not failures, "failures": failures,
        "checks": checks,
        "metadata": {key: metadata[key] for key in ("repository", "revision", "defaults_repository", "defaults_revision", "defaults_visibility", "has_discussions", "discussion_categories", "is_template") if key in metadata},
        "limitations": ["Read-only source and caller-supplied settings audit; hosted execution, credential availability and reporting-channel activation are not verified", "Baseline YAML form subset; unsupported forms, JSON5 and JSONC are not silently certified"],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-dir", type=Path, required=True)
    parser.add_argument("--defaults-dir", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        def config(path):
            if path is None:
                return None
            path = path.absolute()
            if any(part.is_symlink() for part in [path, *path.parents]):
                raise ValueError("Configuration path must not traverse symlinks")
            path = Path(os.path.normpath(path))
            return json.loads(bounded_text(path.parent, path.name))
        result = audit_repository(args.repository_dir, defaults_dir=args.defaults_dir, metadata=config(args.metadata), policy=config(args.policy))
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output:
            output = args.output.absolute()
            if any(path.is_symlink() for path in [output, *output.parents]):
                raise ValueError("Output path must not traverse symlinks")
            output = Path(os.path.normpath(output))
            inputs = [Path(os.path.abspath(args.repository_dir))]
            if args.defaults_dir is not None:
                inputs.append(Path(os.path.abspath(args.defaults_dir)))
            if any(output.is_relative_to(snapshot) for snapshot in inputs):
                raise ValueError("Audit reports must be outside inspected repositories")
            if any(path is not None and output == Path(os.path.abspath(path)) for path in (args.metadata, args.policy)):
                raise ValueError("Audit reports must not replace policy or metadata inputs")
            if output.exists() and not output.is_file():
                raise ValueError("Output must be a regular report file")
            descriptors = directory_descriptors(output.parent, create=True)
            temporary = "." + output.name + ".tmp-" + secrets.token_hex(8)
            try:
                descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600, dir_fd=descriptors[-1])
                with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                    stream.write(rendered)
                os.replace(temporary, output.name, src_dir_fd=descriptors[-1], dst_dir_fd=descriptors[-1])
            finally:
                try:
                    os.unlink(temporary, dir_fd=descriptors[-1])
                except FileNotFoundError:
                    pass
                for descriptor in reversed(descriptors):
                    os.close(descriptor)
        else:
            sys.stdout.write(rendered)
        return 0 if result["conformant"] else 1
    except (ValueError, OSError):
        print("community_bootstrap_invalid_input: inspect policy, metadata and filesystem paths", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
