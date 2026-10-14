# Trigger evals — revenantworks-localops-duckrunner

Counts: 24 queries (12 should, 12 should-not, 2 pairs)

Provenance: derived from SKILL.md v0.1.0 (description as built 2026-10-01; rows 21-24 added for the analytics-export trigger, P1e2). Status: authored, not run. **Re-anchored to v1.0.0, 2026-10-01:** 1.0.0 launch version; suite content unchanged from the build the A6 evals ran against.

Read each query cold against the name and description only, and compare with the Expected
column. Twelve should fire, twelve should not; the should-not half is mostly near-misses against the
siblings and rivals the description names.

**Re-anchored to the K6b description cut, 2026-10-08 (commit b338715):** every row re-read against the cut text; row wording only, no row added, removed or flipped; a row whose routing words left the description says so in its reason. A reader re-read, not a cold judge: the `tools/blind_queries.py` cold re-judge is still owed.

| # | Query | Expected | Why |
|---|---|---|---|
| 1 | How many entries in state/queue.yml are marked done? Show me the query you used. | fire | YAML state file, count, show the SQL |
| 2 | Join orders.csv and customers.csv on customer_id and give me revenue per region, with the SQL. | fire | join over repo CSVs |
| 3 | Rebuild the parquet cache from the data files in this repo. | fire | `cache` |
| 4 | Is any .duckdb or .parquet file committed in this repo by mistake? | fire | `check`, tracked cache |
| 5 | Querying cache/state.duckdb fails with a conflicting lock error. What do I do? | fire | locked database file |
| 6 | Summarise the JSON logs under logs/ as counts per status per day. | fire | summarise data files |
| 7 | Which tasks in tasks.yaml are past their due date? Answer from the file, not from memory. | fire | YAML question |
| 8 | My DuckDB cache was built before yesterday's commit to the CSVs. Is it stale? | fire | stamp freshness |
| 9 | duckrunner check | fire | named keyword and mode |
| 10 | Filter events.jsonl for errors in the last week and group them by service. | fire | filter and group over a repo file |
| 11 | Set up Postgres in Docker for this web app. | no | a database server ("never a database server"); out of scope |
| 12 | Search the DuckDB docs for how window functions break ties. | no | docs search; duckdb-skills or duckdb.org |
| 13 | Research which embedded database to use for a desktop app. | no | research across sources; researchscribe |
| 14 | Query my MotherDuck share of the sales data. | no | MotherDuck; out of scope |
| 15 | Read the parquet files in my S3 bucket with DuckDB. | no | S3; out of scope |
| 16 | Write a prompt that makes a model summarise CSV files well. | no | prompt text; promptwright |
| 17 | Have the local LM Studio model write a prose summary of this README. | no | local LLM work; lmstudiorunner |
| 18 | Scan this repo's history for leaked API keys. | no | security sweep; the warden pack |
| 19 | Fix the YAML syntax error on line 12 of the CI workflow file. | no | editing YAML, not querying it |
| 20 | Turn this Excel workbook into a chart for my slides. | no | spreadsheet and chart work |
| 21 | Which of my videos had the most watch time in last month's channel analytics export? Show the SQL. | fire | analytics CSV export (P1e2, R8 fold) |
| 22 | From the traffic-source CSV I exported from my channel, what share of views came from search? | fire | analytics CSV export |
| 23 | Cut three short clips from last night's stream recording. | no | clip and VOD work; obsrunner |
| 24 | Write the title and description for my next stream from these numbers. | no | words for a platform; commscribe |

Edge notes. The sharpest pair is 1 against 19: both name a YAML file, and only a question asked
of the data fires. Second sharpest: 3 against 11 ("cache" and "database" both appear in server
set-up requests). Tuning rule: a miss on rows 1-10 means the triggers need to be pushier; a fire
on rows 11-20 means the boundary sentence needs tightening.
