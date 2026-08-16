# Campaign Classification Questionnaire

Fill this before freezing taxonomy. Completed answers produce `taxonomy.yaml`, `glossary.yaml`, and `policy.yaml`. Freeze requires checked boxes at the end.

## 1. Domain / subdomain enumeration

- [ ] List all subdomains (5-50). For 20+, group into domains first.
- [ ] For each subdomain: 2-3 line definition, include list, exclude list.
- [ ] Overlap map: which subdomain pairs are commonly confused? Which campaign owns each overlap first? (backbone Order rule)
- [ ] Domains field: `domains:` multi-valued, list allowed domains.

## 2. Implicit-term harvesting

- [ ] List 30-50 surface forms that imply a subdomain without naming it (tests, procedures, acronyms, eponyms). Example: `HbA1c → diabetes_monitoring`.
- [ ] For each: maps_to, notes, source. These seed `glossary.yaml` and the judge's `domain_knowledge` header.
- [ ] Source for each term: which 2-3 real docs contain it? (proves harvest, not invention)

## 3. Example diversity (per subdomain)

- [ ] 3-8 examples per subdomain, each covering distinct variance:
  - [ ] short vs long doc
  - [ ] lexically explicit vs lexically thin (no keywords)
  - [ ] edge near neighbor subdomain (the confusing pair)
  - [ ] implicit-reference example (uses glossary term, not subdomain name)
- [ ] No near-duplicate examples. Each `covers:` label is distinct.

## 4. Comparison / relationship docs

- [ ] Policy choice: `primary_plus_secondary` (recommended) vs `single_plus_comparison_label`
- [ ] `relation_type` allowed values confirmed: `none, comparison, relationship, progression`
- [ ] Define "primary": doc's main purpose, not first mentioned. Give 2 examples of A-vs-B docs with your chosen primary.

## 5. Document shape → chunk policy

- [ ] Are docs front-loaded (title + first 1-2 paragraphs carry the subdomain signal)? If yes, `first_window` 1200-1500 is correct. Show 3 doc openings that prove it.
- [ ] If heading-dense: confirm `header_aware` and show a header outline example.
- [ ] If signal scattered: justify `full` and note cost.
- [ ] Window chosen: ___ tokens. Header outline included? yes/no.

## 6. Retrieval policy

- [ ] `top_k` chosen: ___ (default 4, 1-10). Rationale for k given N subdomains.
- [ ] Embedding model: ___ . Endpoint env: ___
- [ ] Judge model: ___ . Endpoint env: ___

## 7. Confidence buckets (rubric anchors)

- [ ] `SURE` anchor approved: "explicit + primary focus, no comparator"
- [ ] `NEEDS_HUMAN_VALIDATION` anchor approved: "implicit or comparison or close runner-up"
- [ ] `I_GUESSED` anchor approved: "thin/generic evidence"
- [ ] One anchored example per bucket written (reuse `taxonomy.yaml` examples for thin/generic).

## 8. Review & calibration

- [ ] `stratified_per_subdomain`: ___ (default 8)
- [ ] `spot_check_sure`: ___ (default 20), target `SURE` accuracy ___ (default 0.90)
- [ ] Gold sample: ~100 docs stratified + hard types (implicit, comparison) labeled by expert, stored as `campaigns/<campaign>/gold/`.

## Freeze checklist (all must be yes)

- [ ] `taxonomy.yaml` version frozen, N matches `policy.yaml` expectations, every subdomain has diverse examples
- [ ] `glossary.yaml` version frozen, keys unique, every implicit example resolves via glossary
- [ ] `policy.yaml` version frozen, `top_k` and `window` justified by corpus sample
- [ ] Questionnaire answers committed; hash of three YAMLs recorded in ledger `taxonomy_frozen` event

> New scenario: `cp -r payload/templates/classification campaigns/<campaign>/ && fill this file → freeze`
