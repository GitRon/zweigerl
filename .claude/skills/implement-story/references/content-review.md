# Content review: using the story

The gates prove the code agrees with itself. The review lenses prove it reads correctly. Neither of them
ever loaded a page. This is the phase where the app runs and somebody looks at it.

## What this phase catches, and what it does not

Worth the wall-clock: a flow a person cannot finish, a control wired to nothing, a screen that renders
empty or 500s, a fact shown without its source when it has one, a relationship named wrong, a feature no
link ever leads to, a datastar request failing behind a page that looks fine.

Not worth it: spacing and colour judgement, timing races, and any state you had to hand-edit the database
into. Those are either somebody else's phase or nobody's.

## Getting the app up

```bash
bash .claude/skills/implement-story/scripts/content-server.sh fresh   .claude/runs/<slug>
bash .claude/skills/implement-story/scripts/content-server.sh restart .claude/runs/<slug>
bash .claude/skills/implement-story/scripts/content-server.sh stop    .claude/runs/<slug>
```

`fresh` deletes the smoke database and starts from an empty tree, with every fixture loaded again.
`restart` keeps it. **Use `restart` after every code change** - the server runs with `--noreload`, so
until you do, the browser is still testing the code you just replaced. This is the mistake that turns a
fixed bug into a second fix round.

The script prints the base URL, the smoke user, its password and the log path. It runs on a throwaway
SQLite file inside the run directory, so nothing here can touch the development data. The smoke user is a
superuser, so `/admin/` is there for reading the resulting state when a page does not show enough of it.

## The habits of this app, which decide how you drive it

1. **The interactive parts are datastar.** A control is a `data-on:click` with `@get`/`@post` on an
   ordinary element, usually a `<button>`, so it reaches the accessibility tree as a button: addressable
   by role and name. After a click the URL often does not change - the server patched a fragment into the
   page. Snapshot again to see what changed.
2. **A failing datastar request does not look like a failure.** The response is a stream of events; when
   it is a 500, nothing is patched and the page just sits there looking fine. **Check
   `browser_network_requests` after every interaction that talks to the server.** This is the single most
   missable failure in this codebase.
3. **Toasts remove themselves after five seconds.** If you need to read one, snapshot immediately after
   the click.
4. **Navigation moves the address bar without loading the page** (`render_page`), and the back button
   reloads it. A back button that changes the URL but not the content is a finding.
5. **`DEBUG` is on**, so a full-page 500 arrives as the yellow traceback page - the exception is right
   there in the snapshot, and the full traceback is in `content/server.log`. A 500 inside a datastar
   request shows up only in the network list and the log.
6. **datastar is vendored**, under `static/vendor/datastar/`. The script refuses to start without it,
   because without it every control on every page is dead and the whole review is false negatives.
7. **The Tailwind stylesheet is compiled, not committed.** Bringing a server up runs `yarn build:css`,
   because Tailwind only emits the utilities it finds in the templates - a sheet compiled before the story
   added a class leaves a page that has quietly lost that bit of layout. After a template change it is
   `restart` that gets you the new stylesheet, exactly as it is `restart` that gets you the new Python.
8. **The login arrives with #3.** From then on every page sits behind it; a redirect to the login page
   means your session is gone, not that the feature is broken. Log in with the smoke user the script
   prints. Once django-axes is in, failed logins lock the account out - never guess the password.

## Write the journey before you click

Put it in `content/journey.md` first, as numbered steps with an expected outcome each. A journey written
afterwards is just a description of whatever happened.

The baseline journey runs every time, whatever the story was. It catches the damage a story does somewhere
other than where it was aimed:

1. Log in, once the login exists.
2. The start page renders, and `browser_console_messages` shows no error - a broken datastar bundle or a
   script error shows up here first.
3. The Familie Huber is there: `/admin/stammbaum/person/` lists fifteen people and Lena Huber's page shows
   her parents, her partner and her two children. Until the tree has a screen of its own (#11) this is
   where a story that broke the models or the fixture shows it.
4. Every page the app links to from the start page loads.
5. Every page the diff touched, whether or not the story mentions it.
6. **`browser_resize` to 1024x768, then every page the diff touched again.** The laptop is the default
   width in this project and a narrow window has to stay usable, see
   [responsive layout](../../../../docs/patterns/responsive-layout.md). Nothing in the suite asserts on
   markup, so this is the only gate the convention has. What counts is the page scrolling sideways, a
   control pushed off-screen, or information a wide window shows and a narrow one drops; spacing judgement
   is not a finding. Resize back to 1280x800 afterwards.

Then the story journey: the steps a person takes to reach and use the new behaviour, straight out of
`spec.md`, with the expected outcome of each written down before you start. Include the failure paths the
story specifies - refusing to delete the starting person is behaviour too.

## Reaching the state the story needs

Use the app where using it is cheap. `fresh` loads the invented Familie Huber
(`apps/stammbaum/fixtures/familie_huber.json`, fifteen people around Lena Huber, the Ausgangsperson), so most
stories have a family to work on from the first click. `/admin/` shows all of it.

Where using the app is not cheap, seed the precondition through the shell:

```bash
SMOKE_DB_PATH=.claude/runs/<slug>/content/smoke.sqlite3 \
  DJANGO_SETTINGS_MODULE=apps.config.settings_smoke \
  uv run python manage.py shell -c "<python>"
```

**Seed preconditions, never the effect you are checking.** Creating the parents a person needs before
their sibling can be derived is a precondition. Creating the sibling relationship the story is supposed to
derive means you tested nothing and will report a pass. If a state cannot be reached by using the app and
cannot be seeded without faking the outcome, say so in the journey and leave the step unverified rather
than pretending.

**Everything you seed is invented.** No real name, date or place goes into the smoke database either - see
[data storage](../../../../docs/patterns/data-storage.md).

## Observing

- `browser_snapshot` is the default. It is the accessibility tree, it is cheap, and you can quote it.
- `browser_take_screenshot` only when the finding is visual, saved next to the journey in `content/`.
- `browser_network_requests` after every interaction that talks to the server - see habit 2.
- `browser_console_messages` at the end of each leg of the journey.
- `tail` the server log when anything returned 500.

One browser, one tab, driven from this session. Do not hand this phase to parallel agents: there is a
single browser behind the Playwright tools and two drivers would fight over it.

## The browser is shared with every other worktree on this machine

`@playwright/mcp` does not launch a browser per server. Unless it was started with `--isolated`, it asks a
machine-wide daemon for the *unnamed* browser, and every other unnamed server gets the same one. Two
content reviews running at once therefore share one Chrome: one of them finds the other's tabs in its
snapshot, and the other loses its page mid-navigation to

```
Error: async initializeServer: Target page, context or browser has been closed
```

That error is not your story and no amount of restarting the smoke server fixes it.

**Isolate the server** and the problem disappears: once, in the `playwright` entry of `~/.claude.json`,
add `"--isolated"` to its `args`. Concurrent servers then each get their own browser. The cost is that the
profile lives in memory, so nothing survives an MCP restart - which for this phase is no cost at all,
because every round starts from scratch anyway. With `--isolated` in place, skip the rest of this section.

Without it, ask before the first click rather than finding out mid-navigation:

1. Read the neighbouring worktrees' `state.json`, the same ones Phase 1 scanned. A neighbour whose `phase`
   is `content` is the one in the browser, whatever its `content.status` says - a run in a fix round has
   `findings` and is still clicking. None, no contention - go.
2. Message that neighbour, and only it, at the `session` name its `state.json` records. One `SendMessage`,
   carrying `notify_when_idle: true` so the same call both asks the question and subscribes to the notice
   for when it goes idle. Do not send a second one, and never message a name that no `state.json` claims -
   `ListAgents` also lists sessions working on entirely different projects.
3. Do not wait in a loop and do not follow up. If no answer arrives, or it does not arrive inside this
   phase's budget, record `content.status` as `blocked` with the reason and ship - a phase that could not
   run is a gap like any other, and naming it beats guessing at it.

`notify_when_idle` fires when that session finishes its turn, not when it leaves Phase 6. As an
approximation that is enough; as a guarantee it is not, so re-check with a cheap `browser_snapshot` before
committing to the journey.

Never `browser_close` your way out of a collision: on a shared daemon browser that is the other run's
browser too.

Budget: the baseline journey, the story journey, and **at most ten exploratory interactions beyond them.**
Past that, write down what you have and stop. A browser is an excellent place to lose an hour.

## Recording what you found

Each step in `journey.md` gets a `result:` line - `pass`, or `fail` and the finding it produced. Findings
go in `content/findings.md`:

```content-finding
claim: One sentence stating what a person sees that is wrong.
severity: blocker | high | medium | low
where: URL, and the control you clicked
steps: the shortest path from a fresh smoke database that reproduces it
expected: what the story says should happen
actual: what happened
evidence: the failing request, the console error, the traceback line, or the screenshot path
story-caused: yes | no
```

`story-caused: no` goes to the out-of-scope list, same as in the code review - name it, do not fix it.

## Not a finding

- Styling and spacing, unless the page is unusable.
- The plain Tailwind look before the visual identity (#4) lands.
- Anything below 1024px wide; the phone is not a target before #38.
- Behaviour `spec.md` explicitly put under "Nicht Teil davon".
- Anything reproducible only from a database state the app cannot produce.
- Slowness on a first request, which is Django importing itself, not the story.

## When it will not run

- **The server will not start.** The script says why: no virtualenv, no `settings_smoke`, no datastar
  bundle, no frontend dependencies. Fix the environment; if you cannot, the phase is blocked, and that
  goes in the report.
- **You cannot reach the story's screen at all.** That is not a blocked phase, that is the finding - an
  unreachable feature, severity high.
- **Playwright is not connected.** Record the phase as skipped with the reason. Never report a pass you
  did not see.
- **A neighbour is already driving the browser.** `Target page, context or browser has been closed`, or
  tabs you never opened. Isolate the MCP server, or ask and wait for the idle notice - see above - and
  record the phase as `blocked` if neither gets you a browser.

## Teardown

Stop the server and close your tab, pass or fail. A server left running holds the port and will serve
pre-fix code to the next run, which is a lie that costs a whole round to notice. `browser_close` only
when the Playwright server runs `--isolated`: on the shared daemon browser it closes the neighbour's
browser too.
