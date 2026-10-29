import os, io, contextlib
from flask import Flask, request, redirect, url_for, render_template_string
import minigit as mg

BASE = os.path.abspath("repos")
os.makedirs(BASE, exist_ok=True)
app = Flask(__name__)

def run_in(repo, fn):
    old = os.getcwd()
    os.chdir(os.path.join(BASE, repo))
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            result = fn()
    finally:
        os.chdir(old)
    return result, buf.getvalue()

def history():
    out, h = [], mg.head_commit()
    while h:
        c = mg.get_commit(h)
        out.append((h, c))
        h = c["parent"]
    return out

HOME = """
<h1>MiniGit</h1>
<p style="color:green">{{ msg }}</p>
<form method="post">
  <input name="name" placeholder="new repository name" required>
  <button>Create repository</button>
</form>
<h3>Repositories</h3>
<ul>
{% for r, n in repos %}
  <li><a href="/repo/{{ r }}">{{ r }}</a> - {% if n %}version v{{ n }}{% else %}no commits yet{% endif %}</li>
{% endfor %}
</ul>
"""

REPO = """
<a href="/">&larr; all repositories</a>
<h1>{{ name }}</h1>
<p><b>Branch:</b> {{ d.branch }} &nbsp; <b>Current version:</b>
   {% if d.hist %}v{{ d.hist|length }}{% else %}none yet{% endif %}</p>
<p style="color:green">{{ msg }}</p>

<h3>Files</h3>
<ul>{% for f in d.files %}<li><a href="?file={{ f }}">{{ f }}</a></li>{% endfor %}</ul>

<h3>Create / edit a file (saving makes a new version)</h3>
<form method="post" action="/repo/{{ name }}/save">
  <input name="filename" value="{{ d.file }}" placeholder="file name e.g. notes.txt" required><br>
  <textarea name="content" rows="8" cols="60">{{ d.content }}</textarea><br>
  <input name="message" placeholder="commit message">
  <button>Save new version</button>
</form>

<h3>Branches</h3>
<p>{% for b in d.branches %}{{ b }}{% if b == d.branch %} (current){% endif %}{% if not loop.last %}, {% endif %}{% endfor %}</p>
<form method="post" action="/repo/{{ name }}/branch">
  <input name="name" placeholder="new branch name" required><button>Create branch</button>
</form>
<form method="post" action="/repo/{{ name }}/checkout">
  <input name="name" placeholder="branch to switch to" required><button>Switch branch</button>
</form>
<form method="post" action="/repo/{{ name }}/merge">
  <input name="name" placeholder="branch to merge into current" required><button>Merge</button>
</form>

<h3>Version history (this branch)</h3>
<table border="1" cellpadding="5">
<tr><th>Version</th><th>Commit</th><th>Message</th><th>Time</th></tr>
{% for h, c in d.hist %}
<tr><td>v{{ d.hist|length - loop.index0 }}</td><td>{{ h[:7] }}</td><td>{{ c.message }}</td><td>{{ c.timestamp }}</td></tr>
{% endfor %}
</table>
"""

@app.route("/", methods=["GET", "POST"])
def home():
    msg = ""
    if request.method == "POST":
        name = request.form["name"].strip()
        if not name.replace("-", "").replace("_", "").isalnum():
            msg = "Use only letters, numbers, - or _"
        elif os.path.exists(os.path.join(BASE, name)):
            msg = "That repository already exists"
        else:
            os.makedirs(os.path.join(BASE, name))
            run_in(name, mg.init)
            return redirect(url_for("repo", name=name))
    repos = []
    for r in sorted(os.listdir(BASE)):
        n, _ = run_in(r, lambda: len(history()))
        repos.append((r, n))
    return render_template_string(HOME, repos=repos, msg=msg)

@app.route("/repo/<name>")
def repo(name):
    if not os.path.isdir(os.path.join(BASE, name)):
        return "Repository not found", 404
    file = request.args.get("file", "")

    def collect():
        files = sorted(mg.list_files("."))
        content = ""
        if file in files:
            content = open(file, encoding="utf-8", errors="ignore").read()
        return dict(branch=mg.current_branch(),
                    branches=sorted(os.listdir(os.path.join(".minigit", "refs", "heads"))),
                    files=files, hist=history(), file=file, content=content)

    d, _ = run_in(name, collect)
    return render_template_string(REPO, name=name, d=d, msg=request.args.get("msg", ""))

@app.route("/repo/<name>/<action>", methods=["POST"])
def act(name, action):
    f = request.form
    out = ""
    try:
        if action == "save":
            fn = os.path.basename(f["filename"].strip())
            text = f["content"].replace("\r\n", "\n")
            message = f["message"].strip() or "update " + fn

            def job():
                with open(fn, "w", encoding="utf-8", newline="") as fh:
                    fh.write(text)
                mg.add([fn])
                mg.commit(message)
            _, out = run_in(name, job)
        elif action == "branch":
            _, out = run_in(name, lambda: mg.branch(f["name"].strip()))
            out = out or "branch created"
        elif action == "checkout":
            _, out = run_in(name, lambda: mg.checkout(f["name"].strip()))
        elif action == "merge":
            _, out = run_in(name, lambda: mg.merge(f["name"].strip()))
    except Exception as e:
        out = "Error: " + str(e)
    return redirect(url_for("repo", name=name, msg=out.strip()))

if __name__ == "__main__":
    app.run(debug=False, threaded=False)
