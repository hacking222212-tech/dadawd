from flask import Flask, render_template, redirect, url_for, abort
import json, os

app = Flask(__name__)
BASE = os.path.dirname(os.path.abspath(__file__))

def load(f): return json.load(open(os.path.join(BASE, f))) if os.path.exists(os.path.join(BASE, f)) else ([] if f in ("codes.json","tickets.json") else {})
def save(f, d): json.dump(d, open(os.path.join(BASE, f), "w"), indent=2, ensure_ascii=False)

TYP_COLORS = {"kauf":"#5865F2","support":"#eb459e","bewerbung":"#57f287","report":"#ed4245","partner":"#fee75c"}
TYP_LABELS = {"kauf":"Bestellung","support":"Support","bewerbung":"Bewerbung","report":"Meldung","partner":"Partner"}

@app.route("/")
def index():
    tickets = load("tickets.json")
    for t in tickets:
        t["color"] = TYP_COLORS.get(t["typ"], "#888")
        t["label"] = TYP_LABELS.get(t["typ"], t["typ"])
    return render_template("index.html", tickets=tickets)

@app.route("/ticket/<tid>")
def ticket_detail(tid):
    tickets = load("tickets.json")
    t = next((x for x in tickets if x["id"] == tid), None)
    if not t: abort(404)
    t["color"] = TYP_COLORS.get(t["typ"], "#888")
    t["label"] = TYP_LABELS.get(t["typ"], t["typ"])
    return render_template("ticket_detail.html", ticket=t)

@app.route("/delete_ticket/<tid>")
def delete_ticket(tid):
    tickets = [t for t in load("tickets.json") if t["id"] != tid]
    save("tickets.json", tickets)
    return redirect(url_for("index"))

@app.route("/delete_code/<int:idx>")
def delete_code(idx):
    codes = load("codes.json")
    if 0 <= idx < len(codes): codes.pop(idx)
    save("codes.json", codes)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
