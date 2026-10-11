<p align="center">
  <img src="assets/logo.png" alt="Claude Orchestra logo: a conductor among musical notes" width="240">
</p>

# Claude Orchestra

**Add some music to your Claude session, and turn your multi-agent workflows into an orchestra.**

Claude works quietly. With this mod you can *hear* it as Claude thinks, writes and runs tools: a soft tick, a room full of busy people, or a full orchestra.

## Install

At the prompt of a Claude Code session in your terminal:

```
/plugin install orchestra --marketplace hari90/claude_orchestra
```

Answer `y` to add the marketplace, then pick a scope (user scope plays in every session). That's it: send a prompt and listen.

Requires macOS (sound plays through the built-in `afplay`). On Linux and Windows the mod loads but stays silent.

## What you'll hear

- **A tick** while Claude is thinking, writing a reply or calling a tool.
- **Silence** when Claude is idle or waiting on you.

Every session ticks on its own, so parallel sessions layer on top of each other.

## Coming soon

Sound packs to choose from: a room of typists, an orchestra, a piano.

## More

- [How it works](docs/how-it-works.md): the hooks, the sounds and how to develop the mod.
- [AGENTS.md](AGENTS.md): notes for AI agents working in this repo.

## License

[Apache 2.0](LICENSE)
