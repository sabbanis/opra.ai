# Messaging Module

Messaging models a Slack-like conversation as a GitHub pull request:

- A new top-level message creates one pull request.
- Collaborators are requested on the pull request.
- Replies are added as pull-request comments.
- Local preview artifacts are saved under `platform/integrations/github/message_threads/`.

The first implementation is local-first and uses the same mock/real GitHub adapter boundary as proposal PRs and issue previews. The localhost UI exposes this through the Messages tab for owner and admin personas.
