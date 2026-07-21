The best bug report I ever received was four words long — "printer prints
yesterday's file" — and it was completely accurate. The spooler cached the
last rendered job and re-emitted it whenever the new job failed to parse.
Users never saw the failure — they saw yesterday.

It took me a week to believe them. I blamed drivers, the network, even the
user — the classic escalation of a developer who hasn't reproduced the bug
yet. Then it happened to me, on my own machine, with my own file — and the
four words were suddenly a complete specification.

I keep that report pinned above my desk — a reminder that users describe
what happened, not what's plausible. The fix was two lines. The apology was
longer. And the lesson has outlasted three jobs: when a report sounds
impossible, the impossibility is the clue — something in your model of the
system is wrong, and the user — bless them — just handed you the
coordinates.
