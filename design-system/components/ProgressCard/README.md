# ProgressCard

The waiting state. The real engine takes 6 to 40 seconds on a home PC, so waiting is a screen of its own, not a flicker.

- Lists the engine's real steps. Done steps are `forest` and bold; the current step has a pulsing `lantern` marker (still under `prefers-reduced-motion`).
- An elapsed timer in `timer`, hidden from screen readers so they are not interrupted every second.
- One honest line about how long it usually takes; after 20 seconds it changes to reassurance.
- In the recorded demo: replay the real timings at 4× speed, say "The real engine took 18.4 s", and offer "Skip the wait".
