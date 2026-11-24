# Evaluation Cases

Each case describes a trigger and the behaviour that counts as correct. Cases are reviewed when the skill or its references change.

| ID | Trigger | Expected behaviour |
|---|---|---|
| E-1 | User attaches a 28-day Queries export and asks what to fix first | Runs `analyze`, states the impression floor and the 1,000-row cap, returns 5 to 10 actions with evidence, labels upside as an estimate |
| E-2 | User attaches a combined `query,page` export and asks about cannibalization | Runs `cannibalization`, names one owner per query, gives one action per other page, refuses queries below the rule |
| E-3 | User asks whether a title change made 10 days ago worked | Refuses the verdict as `too early`, explains the 28-day rule and offers the before/after protocol |
| E-4 | User asks for search volume, difficulty and intent for the exported queries | States that these are not in the file, does not invent numbers, offers the `seo-google` handoff |
| E-5 | User pastes a screenshot of the Performance chart | Stops and asks for a CSV export, since rows cannot be read from an image |
| E-6 | User asks to pull fresh GSC data through the API | Hands off to `seo-google`, does not request credentials in chat |
| E-7 | User has only a Queries export and asks which pages cannibalize each other | Explains that the UI exports one dimension at a time, asks for a combined file from the API or BigQuery, offers `seo-google` |
| E-8 | User asks why a brand query is missing from the queue | Explains the `--brand` filter or the position band, checks which one applied, does not silently re-add the row |
