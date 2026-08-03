---
title: "Mythos-Class Models"
type: concept
tags: [anthropic, claude, frontier-models]
sources:
  - "[[Claude Fable 5 and Claude Mythos 5]]"
---

# Mythos-Class Models

**"Mythos-class" is a tier of Claude models that sits above the Opus class in capability; Claude Fable 5 and Claude Mythos 5 are the same underlying model, distinguished only by their safeguards.**

Per the announcement, the Mythos class was introduced with **Claude Mythos Preview** (released April through Project Glasswing) and continued with **Claude Fable 5** and **Claude Mythos 5**. Fable 5 and Mythos 5 share one underlying model; the difference is governance, not weights: **Fable 5** carries [[fable-5-safety-classifiers]] and is released for general use, while **Mythos 5** has those safeguards lifted in some areas and is restricted to trusted cyberdefenders (see [[mythos-trusted-access]]). The naming reflects this — *Fable* is from the Latin *fabula* ("that which is told"), akin to the Greek *mythos*; the safeguards are what justify the different names. Because they are the same model, Anthropic states Fable 5's alignment is similar to Mythos 5's, and for the >95% of Fable sessions with no safeguard fallback, Fable 5's performance is effectively the same as Mythos 5's. Both are priced identically ($10/M input, $50/M output) and surpass any model Anthropic had previously made generally available (see [[mythos-class-capabilities]]).

## Related
[[fable-5-safety-classifiers]] · [[mythos-class-capabilities]] · [[mythos-trusted-access]]
