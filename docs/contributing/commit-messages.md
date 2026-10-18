# Commit messages

Keep them short and to the point — a single capitalized subject line describing what the commit does, no
trailing period:

- A noun phrase naming the change (`Datastar setup`, `Person list search`) or a past-tense/`Added …`
  phrase (`Added toast helpers`, `Fixed empty search result`).
- Join two related changes with `&` (`Login & data directory`).
- The issue number in parentheses at the end when the commit implements one: `Person list search (#10)`.
- No body or prefix unless a change genuinely needs explaining; then add a blank line and a couple of
  sentences.

## Pull request titles

A pull request for an issue starts with the issue number and a colon: `#10: Personenliste durchsuchen`.
The number comes first so a list of open PRs reads as a list of tickets. A pull request without an issue -
a docs change, a tooling fix - has no prefix.
