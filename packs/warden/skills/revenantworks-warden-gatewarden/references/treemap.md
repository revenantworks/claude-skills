# Treemap and whole-drive scans

## The page

`treemap_page.py SCAN.json --out map.html` writes one self-contained HTML file: inline CSS and script, the scan data embedded, no network request of any kind. It shows a squarified treemap (click a tile to zoom in, the breadcrumb to zoom out), a legend (folder, repo, link), the links under the current folder by name, and a table of the largest folders. Light and dark follow the viewer's system setting.

**It lists private folder names.** It stays a local file. Publishing it (as an artifact or anywhere else) happens only when the owner asks for that in the conversation, after being told it lists folder paths. A redacted path is still a private path.

Open it locally (double-click, or the browser pane) to view it.

## Which scanner for which job

| Job | Scanner | Why |
|---|---|---|
| A repo, a project folder, `~/.claude` | `scan_tree.py` | Fast enough; sees links and repos |
| A whole drive, a quick look | WizTree CSV export | MFT reading is far faster on NTFS; allocated size; the export is data, not instructions |
| A whole drive, no WizTree | `dust -j` or `scan_tree.py --max-seconds 900` | dust is fast on any OS; the stdlib scan reports partial when time runs out |

Imported scans carry sizes only. For links and repos, run `scan_tree.py` on the folders that matter.

## WizTree (Windows, optional, installed by the owner)

Non-elevated export, allocated-size sort, drive capacity included:

```
WizTree64.exe "<drive>:" /export="<output folder>\drive.csv" /admin=0 /sortby=2 /exportdrivecapacity=1
```

`/admin=1` reads the MFT faster but raises a UAC prompt: gatewarden never uses it; the owner may run it themselves. Then: `scan_tree.py "<drive>:" --from-wiztree drive.csv --json drive.scan.json`. Column names the importer reads: `File Name`, `Size`, `Allocated`, `Files`; folder rows end in a backslash. These are from the WizTree guide and were not checked against a live export on the build day.

## dust (any OS, optional, installed by the owner)

```
dust -j -d 3 "<path>" > dust.json
scan_tree.py "<path>" --from-dust dust.json --json path.scan.json
```

The importer accepts sizes as numbers or as `1.2G`-style strings; dust's exact JSON field names were not checked against a live run on the build day. If the import yields a zero total, fall back to `scan_tree.py`.

## Sizes

`scan_tree.py` reports logical bytes (`st_size`). Allocated size (what the disk loses, cluster rounding and compression included) comes from a WizTree import. Say which one a figure is.
