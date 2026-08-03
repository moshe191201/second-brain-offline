---
title: "Summary — Claude Fable 5 and Claude Mythos 5"
type: source-summary
tags: [anthropic, claude, frontier-models, ai-safety, classifiers]
sources:
  - "[[Claude Fable 5 and Claude Mythos 5]]"
published: 2026-06-16
---

# Summary — Claude Fable 5 and Claude Mythos 5

**Anthropic launched Claude Fable 5 — a "Mythos-class" model (a tier above Opus) made safe for general use via fallback classifiers — alongside Claude Mythos 5, the same underlying model with safeguards lifted for trusted cyberdefenders.**

Anthropic announced two models. **Claude Fable 5** is described as state-of-the-art on nearly all tested benchmarks — software engineering, knowledge work, vision, scientific research — with its lead growing on longer, more complex tasks. Because such capability is dangerous if misused (notably in cybersecurity), Fable 5 ships with conservatively-tuned safeguards: certain queries instead receive a response from the next-most-capable model, Claude Opus 4.8, triggering in under 5% of sessions. **Claude Mythos 5** is the same underlying model with safeguards lifted in some areas, deployed first through Project Glasswing (with the US government) to cyberdefenders; it is described as having the strongest cybersecurity capabilities of any model in the world. The two names differ only by their safeguards (Fable, from Latin *fabula*, akin to Greek *mythos*). Both are priced at $10 per million input tokens and $50 per million output tokens — less than half the price of Claude Mythos Preview — and the API model id is `claude-fable-5`. The post details capability evidence (Stripe migration, Pokémon FireRed via vision alone, *Slay the Spire* with file memory, ~10× drug-design acceleration, novel genomics research), the safety-classifier system, and a new 30-day data-retention policy for Mythos-class traffic. *(As clipped, a banner notes access to both models was being suspended and was being worked on.)*

## Key claims
- Mythos-class is a capability tier above Opus; Fable 5 and Mythos 5 are the same model distinguished only by safeguards → [[mythos-class-models]]
- Fable 5 uses classifier safeguards that fall back to Opus 4.8 on cyber/bio-chem/distillation queries (>95% of sessions unaffected) → [[fable-5-safety-classifiers]]
- Fable 5 / Mythos 5 are state-of-the-art across SWE, knowledge work, vision, memory, and science → [[mythos-class-capabilities]]
- Mythos 5 deploys via Project Glasswing + trusted access programs; Mythos-class traffic carries a 30-day retention policy → [[mythos-trusted-access]]
- Pricing: $10/M input, $50/M output; API id `claude-fable-5`

## Derived concept notes
[[mythos-class-models]] · [[fable-5-safety-classifiers]] · [[mythos-class-capabilities]] · [[mythos-trusted-access]]
