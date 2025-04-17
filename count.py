# INSTRUCTIONS
# 1. Clone OpenDP somewhere
# 2. Update path to OpenDP clone
OPENDP_PATH = "../openDP"
# 3. Install requirements
#      pip install GitPython treelib
# 4. Run this script
#      python3 stats.py

import os
from git import Repo
import re
from treelib import Tree
import sys
import datetime

# comment to print to stdout
orig_stdout = sys.stdout
f = open('output.txt', 'w')
sys.stdout = f


os.chdir(OPENDP_PATH)
repo = Repo(".")

print("OpenDP Proof Statistics")
print("Branch:", repo.active_branch.name)
print("Current Date:", datetime.datetime.now().strftime("%Y-%m-%d"))

# Ignores .gitignored files
file_paths = repo.git.ls_files().splitlines()


def extract_needs_proof(lines, path):
    proven = False
    matches = []
    for line in lines:
        if "#[proven" in line:
            proven = True

        if (
            line.startswith("pub(crate) fn ")
            or line.startswith("pub fn ")
            or line.startswith("fn ")
            or line.startswith("def ")
        ):
            prefix, name = re.match(r".*(fn|def)\s(\w+).*", line).groups()
            if not proven:
                if os.path.exists(os.path.join(path, f"{name}.tex")):
                    proven = True
            matches.append(
                {
                    "name": name,
                    "type": prefix,
                    "proven": proven,
                }
            )
            proven = False

        if line.startswith("impl<") or line.startswith("impl "):
            ignore = [" Debug ", " Clone ", " Default "]
            if any(ignore_i in line for ignore_i in ignore):
                continue
            matches.append(
                {
                    "name": line[:-1],
                    "type": "impl",
                    "proven": proven,
                }
            )
            proven = False
    return matches


matches = {}
ignore = [
    "docs/", # not responsible
    "extras/_utilities", # not responsible
    "extras/examples", # not responsible
    "extras/polars", # outside trust boundary
    "opendp_derive/", # infrastructure
    "opendp_tooling/", # infrastructure
    "rust/src/data", # deprecated
    "rust/src/transformations/dataframe", # deprecated
    "tools/", # infrastructure
    "pseudocode/", # duplicates
    "test/", # not responsible
    "test.py", # not responsible
    "test.rs", # not responsible
    "ffi/", # not responsible
    "ffi.rs", # not responsible
    "build", # infrastructure
]
for file_path in file_paths:
    if not file_path.endswith(".py") and not file_path.endswith(".rs"):
        continue

    # ignore generated code
    if "python" in file_path and "extras" not in file_path:
        continue

    if any(ignored in file_path for ignored in ignore):
        continue
    with open(file_path, "r") as file:
        lines = file.readlines()
        file_matches = extract_needs_proof(lines, os.path.dirname(file_path))
        if file_matches:
            matches[file_path] = file_matches


def count_under(path):
    sub_matches = [m for p, m in matches.items() if path in p]
    print()
    print("Under", f"{path}/**")
    print("* Needed:", sum(len(m) for m in sub_matches))
    print("* Written:", sum(sum(1 for m_i in m if m_i["proven"]) for m in sub_matches))

count_under("")
count_under("rust/src/traits/samplers")
count_under("rust/src/measurements")
count_under("rust/src/combinators")
count_under("rust/src/transformations")


print()
tree = Tree()
tree.create_node(OPENDP_PATH, "")

for file_path, file_matches in matches.items():
    pathway = ""
    for segment in file_path.split("/"):
        new_pathway = pathway + "/" + segment
        if new_pathway not in tree:
            tree.create_node(segment, new_pathway, parent=pathway)
        pathway = new_pathway

    for match in file_matches:
        ident = hash(file_path + match["name"])
        if ident in tree:
            # rare case where impl spans several lines
            #   and first lines are same (like Shr)
            continue
        sym = "✅ " if match["proven"] else ""
        if match["type"] == "fn":
            tree.create_node(f"{sym}fn {match["name"]}", ident, parent=pathway)
        if match["type"] == "def":
            tree.create_node(f"{sym}def {match["name"]}", ident, parent=pathway)
        elif match["type"] == "impl":
            tree.create_node(f"{sym}{match["name"]}", ident, parent=pathway)
tree.show()