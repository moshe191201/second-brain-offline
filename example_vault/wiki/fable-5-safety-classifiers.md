---
title: "Fable 5 Safety Classifiers"
type: concept
tags: [ai-safety, classifiers, jailbreaks, anthropic]
sources:
  - "[[Claude Fable 5 and Claude Mythos 5]]"
---

# Fable 5 Safety Classifiers

**Fable 5's safeguards are separate classifier AI systems that detect potential misuse and, instead of refusing, route the flagged request to Claude Opus 4.8 — making safe general release of a [[mythos-class-models|Mythos-class]] model possible.**

The classifiers are an extension of Anthropic's prior constitutional-classifier work, with broader coverage. They detect misuse (including jailbreak attempts) and prevent the main model (Fable 5) from responding; the user is informed and the response is **handled by Claude Opus 4.8** instead. Anthropic frames this fallback as a far better experience than an outright refusal, since Opus 4.8 is itself highly capable. The classifiers cover three areas: **cybersecurity** (Mythos-class models excel at finding/exploiting vulnerabilities and agentic hacking, so coverage spans exploitation and broader offensive-cyber tasks), **biology and chemistry** (dual-use uplift risk — e.g. predicting AAV viral-shell assembly relevant to gene therapy but also to dangerous viruses), and **distillation** (attempts to extract Fable 5's capabilities to train competing, unsafeguarded models). The safeguards are deliberately tuned conservatively: they trigger on average in **under 5% of sessions**, and **more than 95% of Fable sessions involve no fallback at all** — though benign requests are sometimes caught (false positives Anthropic aims to reduce). Robustness: an external bug bounty found no universal jailbreaks in over 1,000 hours, and Fable 5 complied with zero harmful single-turn cyberattack requests even against 30 public jailbreak techniques (the UK AISI made some progress toward one). A new **30-day data-retention policy** for Mythos-class traffic supports detection of novel/cross-request attacks and false-positive reduction (see [[mythos-trusted-access]]).

## Related
[[mythos-class-models]] · [[mythos-class-capabilities]] · [[mythos-trusted-access]]
