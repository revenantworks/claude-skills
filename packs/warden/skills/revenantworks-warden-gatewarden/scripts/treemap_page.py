#!/usr/bin/env python3
"""gatewarden treemap: one self-contained HTML page from a scan_tree.py JSON. Local file only.

Run, never read into context. Stdlib only.

    treemap_page.py SCAN.json --out map.html [--title "Drive map"]

The page loads nothing from the network (no CDN, no fonts, no images): the squarified
treemap is an inline script over the embedded data. It lists private paths, so it is a
local file; it is published only on the owner's word. Links are drawn as hatched tiles of
zero size, so a junction is visible without being counted twice.
Exit codes: 0 ok, 2 input error.
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#fafaf8;--fg:#1d1d1b;--sub:#5f5e5a;--line:rgba(0,0,0,.18);--dir:#8fb3d9;--repo:#9ccf9a;--file:#d9c08f;--link:#c9c9c9}
@media (prefers-color-scheme:dark){:root{--bg:#161615;--fg:#ecebe6;--sub:#a3a29c;--line:rgba(255,255,255,.2);--dir:#3e6189;--repo:#3f7a3d;--file:#86703f;--link:#4a4a4a}}
body{margin:0;padding:16px;background:var(--bg);color:var(--fg);font:14px/1.4 system-ui,sans-serif}
h1{font-size:18px;margin:0 0 4px}p{margin:0 0 8px;color:var(--sub)}
#crumbs{margin:8px 0;font-family:ui-monospace,monospace;font-size:12px;word-break:break-all}
#crumbs a{color:inherit;cursor:pointer;text-decoration:underline}
#map{position:relative;width:100%;height:70vh;min-height:320px;border:1px solid var(--line)}
.t{position:absolute;box-sizing:border-box;border:1px solid var(--bg);overflow:hidden;font-size:11px;padding:2px 3px;cursor:pointer}
.t.dir{background:var(--dir)}.t.repo{background:var(--repo)}.t.file{background:var(--file)}
.t.link{background:repeating-linear-gradient(45deg,var(--link) 0 4px,transparent 4px 8px);cursor:default}
.legend span{display:inline-block;width:10px;height:10px;margin:0 4px 0 12px;vertical-align:middle}
table{border-collapse:collapse;margin-top:12px;font-size:12px;width:100%}td,th{border-bottom:1px solid var(--line);padding:3px 6px;text-align:left}
td.n{text-align:right;font-variant-numeric:tabular-nums}
</style></head><body>
<h1>__TITLE__</h1>
<p>Private local file: it lists folder paths. Publish only on the owner's word. Root __ROOT__, __TOTAL__, scanned __WHEN__ (__SOURCE__).</p>
<div class="legend">folder<span style="background:var(--dir)"></span>repo<span style="background:var(--repo)"></span>link (not counted)<span style="background:var(--link)"></span></div>
<div id="crumbs"></div><div id="map" role="img" aria-label="Treemap of folder sizes"></div><p id="links"></p>
<table><thead><tr><th>Largest folders</th><th>Kind</th><th>Size</th></tr></thead><tbody id="top"></tbody></table>
<script>
const DATA = __DATA__;
const fmt=b=>{const u=["B","KB","MB","GB","TB"];let i=0;while(b>=1024&&i<4){b/=1024;i++}return (i?b.toFixed(1):b)+" "+u[i]};
function worst(row,w){const s=row.reduce((a,r)=>a+r.a,0),mx=Math.max(...row.map(r=>r.a)),mn=Math.min(...row.map(r=>r.a));return Math.max(w*w*mx/(s*s),(s*s)/(w*w*mn))}
function squarify(items,x,y,w,h,out){
  items=items.filter(i=>i.a>0);
  while(items.length){const short=Math.min(w,h);let row=[items[0]],i=1;
    while(i<items.length&&worst(row.concat(items[i]),short)<=worst(row,short)){row.push(items[i]);i++}
    const s=row.reduce((a,r)=>a+r.a,0);
    if(w>=h){const cw=s/h;let cy=y;for(const r of row){const rh=r.a/cw;out.push({n:r.n,x,y:cy,w:cw,h:rh});cy+=rh}x+=cw;w-=cw}
    else{const rh=s/w;let cx=x;for(const r of row){const cw2=r.a/rh;out.push({n:r.n,x:cx,y,w:cw2,h:rh});cx+=cw2}y+=rh;h-=rh}
    items=items.slice(i)}
  return out}
const stack=[DATA.tree];
function draw(){const node=stack[stack.length-1],el=document.getElementById("map");el.textContent="";
  const W=el.clientWidth,H=el.clientHeight,kids=(node.children||[]).slice();
  const known=kids.reduce((a,c)=>a+(c.bytes||0),0),rest=(node.bytes||0)-known;
  if(rest>0)kids.push({name:"(files here)",kind:"file",bytes:rest});
  const total=kids.reduce((a,c)=>a+(c.bytes||0),0)||1;
  const items=kids.map(c=>({n:c,a:(c.bytes||0)/total*W*H})).sort((a,b)=>b.a-a.a);
  for(const r of squarify(items,0,0,W,H,[])){const d=document.createElement("div");d.className="t "+(r.n.kind||"dir");
    Object.assign(d.style,{left:r.x+"px",top:r.y+"px",width:r.w+"px",height:r.h+"px"});
    d.title=(r.n.path||r.n.name)+"  "+fmt(r.n.bytes||0);if(r.w>40&&r.h>14)d.textContent=r.n.name+" "+fmt(r.n.bytes||0);
    if(r.n.children){d.onclick=()=>{stack.push(r.n);draw()}}el.appendChild(d)}
  const links=kids.filter(c=>c.kind==="link");
  document.getElementById("links").textContent=links.length?("Links here, not followed or counted: "+links.map(l=>l.name+" ("+l.link+")").join(", ")):"";
  const c=document.getElementById("crumbs");c.textContent="";
  stack.forEach((n,i)=>{const a=document.createElement("a");a.textContent=n.name;a.onclick=()=>{stack.length=i+1;draw()};c.appendChild(a);if(i<stack.length-1)c.appendChild(document.createTextNode(" / "))})}
const tb=document.getElementById("top");
for(const t of (DATA.top_dirs||[]).slice(0,25)){const tr=document.createElement("tr");
  for(const [v,cls] of [[t.path,""],[t.kind,""],[fmt(t.bytes),"n"]]){const td=document.createElement("td");td.textContent=v;if(cls)td.className=cls;tr.appendChild(td)}tb.appendChild(tr)}
window.addEventListener("resize",draw);draw();
</script></body></html>
"""


def human(n: int) -> str:
    x = float(n)
    for u in ("B", "KB", "MB", "GB", "TB"):
        if x < 1024 or u == "TB":
            return f"{x:.1f} {u}"
        x /= 1024
    return f"{x:.1f} TB"


def render(scan: dict, title: str) -> str:
    data = json.dumps({"tree": scan.get("tree", {}), "top_dirs": scan.get("top_dirs", [])}, ensure_ascii=False)
    data = data.replace("</", "<\\/").replace("<!--", "<\\!--")
    t = scan.get("totals", {})
    return (PAGE.replace("__TITLE__", html.escape(title))
            .replace("__ROOT__", html.escape(str(scan.get("root", "?"))))
            .replace("__TOTAL__", html.escape(f"{human(t.get('bytes', 0))} in {t.get('files', 0)} files"))
            .replace("__WHEN__", html.escape(str(scan.get("generated", "?"))))
            .replace("__SOURCE__", html.escape(str(scan.get("source", "?"))))
            .replace("__DATA__", data))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("scan")
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="Drive map")
    a = ap.parse_args(argv)
    try:
        scan = json.loads(Path(a.scan).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"error: cannot read scan: {type(e).__name__}", file=sys.stderr)
        return 2
    if scan.get("tool") != "warden.scan_tree":
        print("error: not a gatewarden scan_tree JSON", file=sys.stderr)
        return 2
    Path(a.out).write_text(render(scan, a.title), encoding="utf-8", newline="\n")
    print(f"wrote {Path(a.out).name}: local file, not published")
    return 0


if __name__ == "__main__":
    sys.exit(main())
