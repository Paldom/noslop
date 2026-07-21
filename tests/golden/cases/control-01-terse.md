The deploy broke at 14:20 on Friday. Root cause: a stale feature flag in the
payments service. The flag gated a code path we deleted in May, but the flag
itself survived. When the config service restarted, it re-emitted defaults,
and the dead path came back to life with no handler behind it.

Fix took eleven minutes once we found it. Finding it took three hours.

Two lessons. First, flags need owners and expiry dates, same as certs. We
have 340 flags in production and can name owners for maybe half. Second, our
config service should refuse to emit flags that no deployed binary reads.
That check is a day of work. The outage cost us six engineer-days and a
bruised SLA.

Priya volunteered to build the flag audit. It ships next sprint. Until then,
the deploy checklist gains one line: grep the diff for deleted flag reads,
and kill the flag in the same PR. Boring process fixes beat clever tooling
when the failure mode is forgetting.
