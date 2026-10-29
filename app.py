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

CSS = """
*{box-sizing:border-box}
body{margin:0;font-family:'Segoe UI',system-ui,Arial,sans-serif;background:#f1f5f9;color:#0f172a}
nav{background:linear-gradient(90deg,#4f46e5,#7c3aed);color:#fff;padding:14px 32px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 2px 10px rgba(0,0,0,.15)}
nav a{color:#fff;text-decoration:none;font-weight:700;font-size:22px;letter-spacing:.3px}
nav span{opacity:.85;font-size:14px}
.wrap{max-width:1100px;margin:28px auto;padding:0 20px}
.card{background:#fff;border-radius:14px;padding:22px;box-shadow:0 1px 3px rgba(0,0,0,.08),0 6px 20px rgba(15,23,42,.05);margin-bottom:22px}
.card h3{margin:0 0 14px;font-size:16px;color:#334155}
h1{margin:0 0 6px;font-size:28px}
.muted{color:#64748b;font-size:14px}
input,textarea{width:100%;padding:10px 12px;border:1px solid #cbd5e1;border-radius:8px;font:inherit;margin-bottom:10px;background:#f8fafc}
input:focus,textarea:focus{outline:none;border-color:#6366f1;box-shadow:0 0 0 3px rgba(99,102,241,.2);background:#fff}
textarea{font-family:Consolas,monospace;resize:vertical}
button{background:#4f46e5;color:#fff;border:0;padding:10px 16px;border-radius:8px;font:inherit;font-weight:600;cursor:pointer}
button:hover{background:#4338ca}
button.sec{background:#e0e7ff;color:#3730a3}
button.sec:hover{background:#c7d2fe}
button.sm{padding:5px 10px;font-size:13px}
.row{display:flex;gap:10px}
.row input{margin-bottom:0}
.grid{display:grid;grid-template-columns:2fr 1fr;gap:22px}
@media(max-width:800px){.grid{grid-template-columns:1fr}}
.badge{display:inline-block;padding:3px 10px;border-radius:999px;font-size:12px;font-weight:700}
.b-ver{background:#dcfce7;color:#166534}
.b-br{background:#e0e7ff;color:#3730a3}
.b-none{background:#f1f5f9;color:#64748b}
.b-merge{background:#fef3c7;color:#92400e}
.toast{padding:12px 16px;border-radius:10px;margin-bottom:20px;font-weight:600}
.ok{background:#dcfce7;color:#166534}
.warn{background:#fef3c7;color:#92400e}
.err{background:#fee2e2;color:#991b1b}
.repo{display:flex;justify-content:space-between;align-items:center;padding:14px 16px;border:1px solid #e2e8f0;border-radius:10px;margin-bottom:10px;text-decoration:none;color:inherit}
.repo:hover{border-color:#6366f1;background:#f5f3ff}
.repo b{font-size:16px}
.chips a{display:inline-block;padding:5px 12px;margin:0 6px 6px 0;border-radius:999px;background:#f1f5f9;color:#334155;text-decoration:none;font-size:13px;border:1px solid #e2e8f0}
.chips a:hover{background:#e0e7ff}
.br{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #f1f5f9}
.br form{display:inline;margin:0}
.tl{border-left:3px solid #c7d2fe;margin-left:8px;padding-left:20px}
.item{position:relative;margin-bottom:16px}
.item:before{content:'';position:absolute;left:-29px;top:5px;width:11px;height:11px;border-radius:50%;background:#6366f1;border:2px solid #fff}
code{background:#f1f5f9;padding:2px 6px;border-radius:5px;font-size:12px}
a.back{color:#4f46e5;text-decoration:none;font-weight:600;font-size:14px}
"""

HEAD = ("<!doctype html><html><head><meta charset='utf-8'><title>MiniGit</title>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'><style>" + CSS +
        "</style></head><body><nav><a href='/'>MiniGit</a><span>A mini version control system</span></nav>"
        "<div class='wrap'>")
FOOT = "</div></body></html>"

TOAST = """{% if msg %}<div class="toast {{ 'warn' if 'conflict' in msg else ('err' if 'Error' in msg else 'ok') }}">{{ msg }}</div>{% endif %}"""

HOME = HEAD + TOAST + """
<div class="card">
  <h1>Your repositories</h1>
  <p class="muted">Create a repository, save versions of your files, branch and merge.</p>
  <form method="post" class="row">
    <input name="name" placeholder="New repository name, e.g. project1" required>
    <button>Create repository</button>
  </form>
</div>
<div class="card">
  <h3>All repositories</h3>
  {% for r, n in repos %}
  <a class="repo" href="/repo/{{ r }}">
    <div><b>{{ r }}</b></div>
    <span class="badge {{ 'b-ver' if n else 'b-none' }}">{% if n %}version v{{ n }}{% else %}no commits yet{% endif %}</span>
  </a>
  {% else %}
  <p class="muted">No repositories yet. Create your first one above.</p>
  {% endfor %}
</div>
""" + FOOT

REPO = HEAD + """
<a class="back" href="/">&larr; All repositories</a>
<div style="margin:10px 0 20px">
  <h1>{{ name }}</h1>
  <span class="badge b-br">branch: {{ d.branch }}</span>
  {% if d.hist %}<span class="badge b-ver">current version: v{{ d.hist|length }}</span>
  {% else %}<span class="badge b-none">no versions yet</span>{% endif %}
</div>
""" + TOAST + """
<div class="grid">
  <div>
    <div class="card">
      <h3>Files</h3>
      <div class="chips">
        {% for f in d.files %}<a href="?file={{ f }}">{{ f }}</a>{% endfor %}
        <a href="/repo/{{ name }}" style="background:#4f46e5;color:#fff">+ New file</a>
      </div>
    </div>
    <div class="card">
      <h3>Create or edit a file (saving makes a new version)</h3>
      <form method="post" action="/repo/{{ name }}/save">
        <input name="filename" value="{{ d.file }}" placeholder="File name, e.g. notes.txt" required>
        <textarea name="content" rows="9" placeholder="Type your text here">{{ d.content }}</textarea>
        <div class="row">
          <input name="message" placeholder="Commit message, e.g. first version">
          <button style="white-space:nowrap">Save new version</button>
        </div>
      </form>
    </div>
    <div class="card">
      <h3>Version history ({{ d.branch }})</h3>
      <div class="tl">
        {% for h, c in d.hist %}
        <div class="item">
          <span class="badge b-ver">v{{ d.hist|length - loop.index0 }}</span>
          {% if c.get('merged') %}<span class="badge b-merge">merge</span>{% endif %}
          <b>{{ c.message }}</b><br>
          <span class="muted"><code>{{ h[:7] }}</code> &nbsp; {{ c.timestamp }}</span>
        </div>
        {% else %}
        <p class="muted">No versions yet. Save a file to create v1.</p>
        {% endfor %}
      </div>
    </div>
  </div>
  <div>
    <div class="card">
      <h3>Branches</h3>
      {% for b in d.branches %}
      <div class="br">
        <div><b>{{ b }}</b> {% if b == d.branch %}<span class="badge b-br">current</span>{% endif %}</div>
        {% if b != d.branch %}
        <div>
          <form method="post" action="/repo/{{ name }}/checkout"><input type="hidden" name="name" value="{{ b }}"><button class="sm sec">Switch</button></form>
          <form method="post" action="/repo/{{ name }}/merge"><input type="hidden" name="name" value="{{ b }}"><button class="sm">Merge here</button></form>
        </div>
        {% endif %}
      </div>
      {% endfor %}
      <form method="post" action="/repo/{{ name }}/branch" style="margin-top:16px">
        <input name="name" placeholder="New branch name" required>
        <button style="width:100%">Create branch</button>
      </form>
      <p class="muted" style="margin-top:12px">Create a branch from the current version, switch to it, make changes, then use Merge here to bring them into the branch you are on.</p>
    </div>
  </div>
</div>
""" + FOOT

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
            out = out or "Branch created"
        elif action == "checkout":
            _, out = run_in(name, lambda: mg.checkout(f["name"].strip()))
        elif action == "merge":
            _, out = run_in(name, lambda: mg.merge(f["name"].strip()))
    except Exception as e:
        out = "Error: " + str(e)
    return redirect(url_for("repo", name=name, msg=out.strip()))

if __name__ == "__main__":
    app.run(debug=False, threaded=False)
