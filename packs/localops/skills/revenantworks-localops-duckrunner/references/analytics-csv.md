# Analytics CSV exports — recipes

Read this file in `ask` when the sources are analytics exports from a video or streaming
platform (views, watch time, retention, traffic sources). The platform, its export screen and
its column names are read live from the file and the platform's own help page, never from
memory: they change, and they differ by platform and by the account's language.

## Contents

1. Before the first query
2. Clean-up in SQL
3. Recipes
4. Limits to say in the answer

## 1. Before the first query

- **Where the files live.** Exports go in a folder inside the repo. In a public repo that folder
  is gitignored: channel analytics are the user's data. `ask` reads an ignored file; `cache`
  refuses uncommitted sources unless the user says `--allow-dirty`, and the stamp records it.
- **One export, one source.** Each export is its own file; a folder of weekly exports is one glob
  (`exports/*.csv`) only when every file has the same header.
- **Read the header, nothing more.** Open the first line to learn the column names. Quote names
  with spaces or symbols (`"Watch time (hours)"`). Do not guess a column from another platform.
- **Find the totals row.** Many exports add a first or last row that sums the table (a blank
  title, or a word such as "Total"). Exclude it in the SQL, or every sum doubles.
- **Note the export cap.** Some export screens cap the rows per file (the top N items only).
  Read the platform's help page for the current cap; if the row count equals it, the export is
  cut, and the answer says so.

## 2. Clean-up in SQL

Type sniffing reads most exports. When it does not, fix the value in the query, never in the file:

| Symptom | Fix in the SELECT |
|---|---|
| Numbers read as text (`1,204`) | `TRY_CAST(replace(col, ',', '') AS BIGINT)` |
| Percent as text (`43.2%`) | `TRY_CAST(rtrim(col, '%') AS DOUBLE) / 100` |
| Duration as `h:mm:ss` | `TRY_CAST(col AS INTERVAL)`, or split on `:` and sum seconds |
| Dates as text | `TRY_STRPTIME(col, '<format read from the file>')` |
| A decimal comma (locale) | `replace(col, ',', '.')` before the cast |

`TRY_CAST` returns NULL instead of failing; report how many rows came back NULL.

## 3. Recipes

Names below are placeholders: put the real header names from the file in their place.

**Top items by watch time**

```sql
FROM content
SELECT "<title>", "<watch time>", "<views>"
WHERE "<title>" IS NOT NULL AND "<title>" <> '<totals label>'
ORDER BY "<watch time>" DESC
LIMIT 10
```

**Week over week** (a daily export with a date column)

```sql
FROM daily
SELECT date_trunc('week', "<date>") AS week, sum("<views>") AS views, sum("<watch time>") AS watch
GROUP BY week ORDER BY week
```

**Traffic-source share**

```sql
FROM sources
SELECT "<source>", "<views>", round(100.0 * "<views>" / sum("<views>") OVER (), 1) AS pct
WHERE "<source>" <> '<totals label>'
ORDER BY "<views>" DESC
```

**Retention drop points** (an audience-retention export: position and share still watching)

```sql
FROM retention
SELECT "<position>", "<share watching>",
       "<share watching>" - lag("<share watching>") OVER (ORDER BY "<position>") AS change
ORDER BY change ASC NULLS LAST
LIMIT 5
```

**Short-form versus long-form** (when the export carries a content-type or duration column)

```sql
FROM content
SELECT "<content type>", count(*) AS items, avg("<average view duration>") AS avg_view
GROUP BY ALL
```

## 4. Limits to say in the answer

- The export date range, read from the file name or the platform's screen, never assumed.
- A capped export (row count equals the cap) is a sample of the top items, not the whole channel.
- Platform figures are revised for days after the fact; an export is a snapshot.
- Titles, descriptions and schedules written from these numbers are commscribe's; clip and VOD
  work is obsrunner's. duckrunner answers the question and shows the SQL.
