import argparse, difflib, hashlib, json, os, sys, time, zlib

REPO = ".minigit"
def p(*a): return os.path.join(REPO, *a)

# ---------- storage ----------
def store(data):
    h = hashlib.sha1(data).hexdigest()
    d = p("objects", h[:2]); os.makedirs(d, exist_ok=True)
    path = os.path.join(d, h[2:])
    if not os.path.exists(path):
        with open(path, "wb") as f: f.write(zlib.compress(data))
    return h

def load(h):
    with open(p("objects", h[:2], h[2:]), "rb") as f:
        return zlib.decompress(f.read())

# ---------- helpers ----------
def current_branch(): return open(p("HEAD")).read().strip().split("refs/heads/")[1]
def bpath(name): return p("refs", "heads", name)
def head_commit(): return open(bpath(current_branch())).read().strip() or None
def read_index(): return json.load(open(p("index")))
def write_index(i): json.dump(i, open(p("index"), "w"))
def get_commit(h): return json.loads(load(h))

def list_files(path):
    if os.path.isfile(path): return [os.path.normpath(path)]
    out = []
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in (REPO, ".git", "__pycache__")]
        out += [os.path.normpath(os.path.join(root, f)) for f in files]
    return out

# ---------- commands ----------
def init():
    if os.path.exists(REPO): return print("already initialized")
    os.makedirs(p("objects")); os.makedirs(p("refs", "heads"))
    open(p("HEAD"), "w").write("ref: refs/heads/main")
    open(bpath("main"), "w").write("")
    write_index({})
    print("initialized empty repository")

def add(paths):
    idx = read_index()
    for path in paths:
        for f in list_files(path):
            idx[f] = store(open(f, "rb").read())
    write_index(idx)

def commit(msg):
    idx, parent = read_index(), head_commit()
    if parent and get_commit(parent)["files"] == idx:
        return print("nothing to commit")
    c = {"message": msg, "timestamp": time.ctime(), "parent": parent, "files": idx}
    h = store(json.dumps(c).encode())
    open(bpath(current_branch()), "w").write(h)
    print("committed", h[:7])

def log():
    h = head_commit()
    while h:
        c = get_commit(h)
        print(f"commit {h}\nDate:   {c['timestamp']}\n    {c['message']}\n")
        h = c["parent"]

def status():
    idx, h = read_index(), head_commit()
    last = get_commit(h)["files"] if h else {}
    print("On branch", current_branch())
    for f in sorted(set(idx) | set(last)):
        if idx.get(f) != last.get(f): print("staged:   ", f)
    for f in list_files("."):
        if f not in idx: print("untracked:", f)
        elif hashlib.sha1(open(f, "rb").read()).hexdigest() != idx[f]:
            print("modified: ", f)

def diff():
    for f, h in read_index().items():
        if not os.path.exists(f): continue
        old = load(h).decode(errors="ignore").splitlines()
        new = open(f, errors="ignore").read().splitlines()
        for line in difflib.unified_diff(old, new, "a/" + f, "b/" + f, lineterm=""):
            print(line)

def restore(h):
    files = get_commit(h)["files"] if h else {}
    for f in read_index():
        if f not in files and os.path.exists(f): os.remove(f)
    for f, bh in files.items():
        os.makedirs(os.path.dirname(f) or ".", exist_ok=True)
        open(f, "wb").write(load(bh))
    write_index(files)

def checkout(target):
    if os.path.exists(bpath(target)):          # switch branch
        h = open(bpath(target)).read().strip() or None
        restore(h)
        open(p("HEAD"), "w").write(f"ref: refs/heads/{target}")
        print("switched to branch", target)
    else:                                       # go to a commit hash
        restore(target)
        open(bpath(current_branch()), "w").write(target)
        print("moved", current_branch(), "to", target[:7])

def branch(name):
    open(bpath(name), "w").write(head_commit() or "")

def ancestors(h):
    s = set()
    while h:
        s.add(h); h = get_commit(h)["parent"]
    return s

def merge(name):
    cur, other = head_commit(), open(bpath(name)).read().strip()
    if not cur or cur in ancestors(other):      # fast-forward
        open(bpath(current_branch()), "w").write(other)
        restore(other); print("fast-forward merge done")
    else:
        print("branches diverged: only fast-forward merge is supported")

# ---------- CLI ----------
def main():
    ap = argparse.ArgumentParser(prog="minigit")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for n in ("init", "log", "status", "diff"): sub.add_parser(n)
    sub.add_parser("add").add_argument("paths", nargs="+")
    sub.add_parser("commit").add_argument("-m", "--message", required=True)
    for n in ("checkout", "branch", "merge"): sub.add_parser(n).add_argument("name")
    a = ap.parse_args()
    if a.cmd != "init" and not os.path.exists(REPO):
        sys.exit("not a minigit repository (run init first)")
    {"init": init, "log": log, "status": status, "diff": diff,
     "add": lambda: add(a.paths), "commit": lambda: commit(a.message),
     "checkout": lambda: checkout(a.name), "branch": lambda: branch(a.name),
     "merge": lambda: merge(a.name)}[a.cmd]()

if __name__ == "__main__":
    main()