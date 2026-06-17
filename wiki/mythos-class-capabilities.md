---
title: "Mythos-Class Capabilities"
type: concept
tags: [benchmarks, agents, vision, long-context, life-sciences]
sources:
  - "[[Claude Fable 5 and Claude Mythos 5]]"
---

# Mythos-Class Capabilities

**Fable 5 / Mythos 5 are claimed state-of-the-art on nearly all tested benchmarks, with the lead widening on longer, more complex autonomous tasks across software engineering, knowledge work, vision, memory, and the life sciences.**

Evidence cited in the announcement (a [[mythos-class-models|Mythos-class]] model):

- **Software engineering.** Stripe reported Fable 5 compressed months of work into days — a codebase-wide migration of a 50-million-line Ruby codebase in a day (vs. a team-month+ by hand). It scores highest among frontier models on Cognition's *FrontierCode* even at medium effort, and is more token-efficient than past Claude models.
- **Knowledge work.** Highest score on Hebbia's senior-level Finance Benchmark (document reasoning, chart/table interpretation); IMC said it aced trading-analysis evaluations nearly across the board.
- **Vision.** New state-of-the-art for vision: extracts precise numbers from scientific figures, rebuilds a web app's source from screenshots, and beat Pokémon FireRed with a **minimal vision-only harness** where earlier models needed complex helper harnesses.
- **Memory / long-context.** Stays focused across millions of tokens and improves outputs from its own notes; with file-based memory in *Slay the Spire* it improved 3× more than Opus 4.8 and reached the final act 3× more often.
- **Life sciences (via Mythos 5).** Accelerated protein/drug-design work ~10× and, with tools but no human assistance, matched or beat skilled operators (9 of 14 protein targets yielded strong candidates); first model to consistently produce novel molecular-biology hypotheses (preferred ~80% in blinded comparisons, one corroborated independently); ran novel autonomous genomics research, training a model 100× smaller that outperformed a recent *Science* publication.

On alignment, the automated assessment found Mythos 5's misaligned behavior low and similar to Opus 4.8 (and thus similar for Fable 5, the same model). These capabilities are exactly why the [[fable-5-safety-classifiers]] and restricted [[mythos-trusted-access]] exist.

## Related
[[mythos-class-models]] · [[fable-5-safety-classifiers]] · [[mythos-trusted-access]]
