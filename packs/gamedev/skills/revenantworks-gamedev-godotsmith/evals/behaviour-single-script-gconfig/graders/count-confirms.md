---
type: llm
weight: 2
---
PASS when the reply says the config file's dirs were still loaded so the run covered the whole suite, gives a narrowed command that passes an empty config (`-gconfig=`) or a scratch config without dirs, AND says to confirm the narrowing by reading the run's Scripts count (1 for one file).
FAIL when it blames the machine or the test, offers only `-gtest` again, or gives no way to confirm the narrowing.
