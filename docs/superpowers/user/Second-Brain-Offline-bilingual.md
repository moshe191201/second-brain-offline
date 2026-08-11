# Bunker — באנקר — Deck (Bilingual: English + עברית)

> **Source:** `docs/superpowers/user/# Second Brain Offline Project/Bunker.html` (34 slides) — bundled
> deck (deck-stage)
> **Conversion:** `pandoc -f html -t gfm --wrap=none` per `<section>` → `/tmp/slides_md/slide_*.md` + manual cleanup
> (div soup stripped, headings preserved)
> **Hebrew:** תרגום עברי מקצועי. מונחים: vault נשאר vault · air-gapped = רשת סגורה · ingest = הכנסה ל-wiki.
> **How to read:** כל שקף מופיע פעמיים — קודם האנגלית הנקייה (פנדוק), ואז העברית. ה-speaker notes המקוריים הוטמעו
> בתרגום.


---

<style>
[dir="rtl"] { text-align: right; }
[dir="rtl"] table { direction: rtl; }
</style>

## Slide 01 — Title

### English (pandoc)

Bunker

An AI-operable knowledge vault that runs inside the air gap

Project review — Pilot in progress

### עברית

<div dir="rtl" lang="he">

כספת ידע מבוססת AI הפועלת כולה ברשת הסגורה — ללא חיבור לאינטרנט וללא יציאה החוצה.

סקירת פרויקט — פיילוט פעיל.

</div>


---

## Slide 02 — Agenda — How to read

### English (pandoc)

Two acts, one of which is optional

**ACT I — 15 MIN** — The problem, the prior art, how this compares, the three moats, and where the pilot stands.
Self-contained. If we stop here, you have the whole argument.

**ACT II — DEEP DIVE** — Vault lifecycle, infrastructure, retrieval engines, and the client ingest pipeline. For the
engineers in the room. Every slide here is skippable on its own.

Deep-dive slides are marked in the top-right corner.

### עברית

<div dir="rtl" lang="he">

שני חלקים, אחד מהם אופציונלי.

**חלק א' — 15 דקות**

הבעיה, הפתרונות הקיימים, במה אנו שונים, שלושת היתרונות המובהקים וסטטוס הפיילוט. חלק עצמאי וסגור — אם נעצור כאן, התמונה
המלאה הוצגה.

**חלק ב' — צלילה טכנית**

מחזור חיי ה-vault, תשתיות, מנועי שליפה ומסלול הכניסה ל wiki אצל הלקוח. מיועד לקהל הטכני. ניתן לדלג על כל שקף בנפרד.

שקפי deep-dive מסומנים בפינה הימנית העליונה.

</div>


---

## Slide 03 — The problem

### English (pandoc)

Three gaps block AI in our domains

**01 Hallucination — it doesn't know our domains.** The model knows generic knowledge and almost nothing about our
specific domains — so when asked, it hallucinates hard and with confidence.

**02 Translation — it doesn't speak our language.** Even with skills and agents, it cannot turn how we write and talk
into scripts, queries, and agentic actions. Our jargon, shorthand, and processes don't map.

**03 The knowledge exists — but disconnected.** Thousands of pages of internal documentation already hold the answers,
written over years. There is no way to ground the model in them today.

Every team that hits this builds its own half-solution.

### עברית

<div dir="rtl" lang="he">

שלושה פערים חוסמים שילוב AI במרכז

**01 הזיה — המודל אינו מכיר את התחומים שלנו.** המודל שולט בידע כללי וכמעט אינו מכיר את התחומים הספציפיים שלנו — לכן
כששואלים אותו הוא ממציא בביטחון רב.

**02 תרגום — הוא אינו דובר את השפה שלנו.** גם עם skills וסוכנים, הוא אינו יודע לתרגם את האופן שבו אנו כותבים ומדברים
לסקריפטים, שאילתות ופעולות סוכן. הז'רגון, הקיצורים והתהליכים שלנו אינם מתורגמים.

**03 הידע קיים — אך מנותק.** אלפי עמודים של תיעוד פנימי כבר מכילים את התשובות, שנכתבו לאורך שנים. כיום אין דרך לעגן בהם
את המודל.

כל צוות הנתקל בבעיה זו נאלץ לפתח פתרון חלקי באופן עצמאי.

</div>


---

## Slide 04 — Why now

### English (pandoc)

What the two gaps cost us — the expert fills both

He is the search engine *and* the translator — and he rarely knows the answer by heart. Each question costs him a manual
read of the documentation, plus a manual translation into the exact script or query the asker needs.

**60% OF A HEAVY DAY — HIS DAY**
Answering questions others could answer themselves if the vault grounded the model | Doing the analysis only he can do

Every answer he gives is one he has already given — and one that never gets written down.

### עברית

<div dir="rtl" lang="he">

מה הפערים עולים לנו

המומחה הוא גם מנוע החיפוש וגם המתרגם — וכמעט אף פעם אינו יודע את התשובה בעל פה. כל שאלה מחייבת אותו לקריאה ידנית בתיעוד, ולאחר
מכן לתרגום ידני לסקריפט או לשאילתא המדויקת שהשואל צריך.

**60% מיום עמוס — מוקדשים לכך**

מענה על שאלות שאנשים היו עונים עליהן בעצמם אילו ה-vault היה מעגן את המודל | לעומת העבודה האנליטית שרק הוא מסוגל לבצע

תשובות רבות שהוא נותן הן תשובות שכבר נתן בעבר — ואף אחת מהן אינה מתועדת.

</div>


---

## Slide 05a — Where the questions go

### English (pandoc)

Where the gaps hit — and how the vault closes them

**TODAY — Hallucination:** question → the model guesses from generic knowledge → hallucination. **Translation:**
request → the expert (rarely knows outright) → reads the docs manually, then hand-writes the script/query. One person is
both the index and the translator, and neither scales.

**WITH THE VAULT:** question → the vault (grounded in our docs, answers with sources; language already mapped to
scripts/queries/skills) → Only what the vault cannot answer reaches the expert — and his answer becomes a note. The
index and the dictionary stay behind, and both keep getting better.

### עברית

<div dir="rtl" lang="he">

היכן הפערים פוגשים אותנו — וכיצד ה-vault סוגר אותם

**היום — הזיה:** שאלה → המודל מנחש מידע כללי → הזיה.

**תרגום:** בקשה → נוחתת אצל המומחה (שגם הוא נדרש לעיין בתיעוד ולקרוא ידנית) → הוא קורא ומתרגם ידנית לסקריפט/שאילתא. אדם
אחד הוא גם האינדקס וגם המתרגם, ושניהם אינם ניתנים להרחבה.

**עם ה-vault:** שאלה → ה-vault משיב כשהוא מעוגן בתיעוד שלנו, בצירוף מקורות; השפה כבר ממופה לסקריפטים/שאילתות/skills → רק
מה שה-vault אינו יודע מגיע למומחה — ותשובתו הופכת ל-note חדש. האינדקס והמילון נשארים, ומשתפרים באופן רציף.

</div>


---

## Slide 05 — Prior art — llm-wiki in one slide

### English (pandoc)

Karpathy's idea: stop asking a model to read your documents every time. Have it read them once and write a wiki — then
answer from the wiki.

**SOURCES** — Immutable clippings. The evidence layer, never edited.

**WIKI** — One idea per note, densely cross-linked, written by the model.

**SCHEMA** — A fixed shape the model must follow, so the wiki stays navigable.

It is a good idea, and it is the starting point for this project. It is also a personal-scale idea, written for a
connected laptop and a frontier model.

### עברית

<div dir="rtl" lang="he">

הרעיון של קרפאת'י: במקום לבקש מהמודל לקרוא את המסמכים בכל פעם מחדש — תנו לו לקרוא אותם פעם אחת, לכתוב wiki, ומאז לענות
מתוך ה-wiki.

**מקורות** — קטעי מקור בלתי ניתנים לשינוי. שכבת הראיות, אינה נערכת. קונפלואנס, תיקיות רשת, מיילים.

**וויקי** — רעיון אחד לכל note, מקושר בצפיפות, נכתב על ידי המודל.

**סכמה** — מבנה קבוע שהמודל נדרש לעמוד בו, כדי שה-wiki יישאר מסודר.

רעיון מצוין, והוא נקודת המוצא שלנו.

אלא שהוא תוכנן למחשב נייד מחובר לרשת, עם מודל מתקדם, ולשימוש אישי — היקף מצומצם, מסמכים באנגלית רהוטה, גרסה אחת לכל מסמך
ורמת אמינות אחידה.

</div>


---

## Slide 05b — Four assumptions we cannot make

### English (pandoc)

Four assumptions it makes that we cannot make

**A frontier model is available** → Ours is a small in-gap model that is barely capable of open-ended judgement. **The
machine is online** → Every dependency has to be built outside and carried in, once. **The corpus is small and
English** → Ours is thousands of Hebrew pages with domain terminology the model doesn't know — we ground it by injecting
GT definitions into context. **One person owns it** → Ours is a team asset that has to be handed over, upgraded, and
audited.

### עברית

<div dir="rtl" lang="he">

ארבע הנחות שאינן תקפות אצלנו

**קיים מודל מתקדם זמין** → אצלנו פועל מודל קטן ברשת הסגורה, המוגבל ביכולת שיפוט פתוח.

**המחשב מחובר לרשת** → אצלנו כל תלות (dependency) נבנית בחוץ ומוכנסת פנימה פעם אחת.

**הקורפוס קטן ובאנגלית** → אצלנו אלפי עמודים בעברית עם טרמינולוגיה ייעודית שהמודל אינו מכיר — אנו מעגנים אותו באמצעות
הזרקת הגדרות GT להקשר.

**אדם אחד אחראי** → אצלנו מדובר בנכס צוותי — נדרשים תהליכי חפיפה, שדרוג וביקורת.

</div>


---

## Slide 06 — Comparison

### English (pandoc)

Same idea, different problem

|              | LLM-WIKI                   | SECOND BRAIN OFFLINE                            |
|--------------|----------------------------|-------------------------------------------------|
| Environment  | Connected laptop           | Air-gapped network, no GPU                      |
| Model        | Frontier, always available | Small in-gap model, tightly constrained         |
| Retrieval    | The model reads the wiki   | Hybrid search + knowledge graph + Obsidian      |
| Process      | Model judgement, freeform  | Scripted lifecycle, rubrics, fail-closed checks |
| Scale        | Personal reading list      | A team's full documentation estate              |
| Distribution | An idea you reimplement    | A package you install and upgrade               |

### עברית

<div dir="rtl" lang="he">

אותו רעיון, בעיה שונה לחלוטין

| | LLM-WIKI | SECOND BRAIN OFFLINE |
|-------|--------------------------|------------------------------------------------|
| סביבה | מחשב נייד מחובר | רשת סגורה, ללא GPU |
| מודל | המתקדם ביותר, זמין תמיד | מודל קטן ברשת הסגורה, מוגבל ומבוקר |
| שליפה | המודל קורא את ה-wiki | חיפוש היברידי + גרף ידע + Obsidian |
| תהליך | שיקול דעת חופשי של המודל | מחזור חיים מובנה, רובריקות, בדיקות fail-closed |
| היקף | רשימת קריאה אישית | מלוא התיעוד של צוות שלם |
| הפצה | רעיון למימוש עצמי | חבילה מוכנה להתקנה ולשדרוג |

</div>


---

## Slide 07 — Three moats

### English (pandoc)

What is defensible — Three moats

**I — It actually runs in the gap** — Every dependency staged, every API adapted, one boundary crossing per release.

**II — Two retrieval engines, not one** — Hybrid search for lookup, a knowledge graph for traversal, Obsidian for
humans.

**III — Guardrails that let a weak model work**— A defined lifecycle, deterministic scripts, and skills that leave the
model less to decide.

### עברית

<div dir="rtl" lang="he">

יתרונות תחרותיים — שלושה חסמים משמעותיים

**א' — פועל בפועל ברשת הסגורה** — כל תלות ארוזה, כל API מותאם, מעבר גבול אחד לכל גרסה.

**ב' — שני מנועי שליפה, לא אחד** — חיפוש היברידי לאיתור, גרף ידע לניתוח קשרים, ו-Obsidian לעיון אנושי.

**ג' — מנגנוני בקרה המאפשרים למודל חלש לספק תוצאות** — מחזור חיים מוגדר, סקריפטים דטרמיניסטיים ו-skills המצמצמים את מרחב
ההחלטה של המודל.

</div>


---

## Slide 08 — Moat I — Running in the gap

### English (pandoc)

Running in the gap is the work, not a deployment step

A tool that assumes a package registry, a model download, or a compiler with network access simply does not start on the
inside.

**Zero dependencies** — The CLI is pure standard library. Nothing to resolve, nothing to sync.

**Prebuilt engines** — Native modules compiled outside against the target's exact ABI, then carried in whole.

**No GPU required** — Search runs against the internal inference endpoint instead of local model files.

**One crossing per release** — After the transfer, updating inside the gap is an ordinary install over the LAN.

### עברית

<div dir="rtl" lang="he">

הפעלה ברשת סגורה אינה שלב פריסה — היא ליבת הפרויקט

כלי המניח קיום registry, הורדת מודל או קומפיילר עם גישה לרשת — פשוט אינו פועל ברשת הסגורה.

**אפס תלויות** — ה-CLI מבוסס על ספריית הסטנדרט בלבד (pure stdlib). אין מה לפתור, אין מה לסנכרן.

**מנועים מוכנים מראש** — מודולים native מקומפלים מחוץ לרשת מול ה-ABI המדויק של היעד ונכנסים כיחידה אחת.

**ללא צורך ב-GPU** — החיפוש פועל מול נקודת הקצה (endpoint) הפנימית להסקה, לא מול קבצי מודל מקומיים.

**מעבר אחד לכל גרסה** — לאחר ההעברה, עדכון ברשת הסגורה הוא התקנה רגילה ברשת הפנימית.

</div>


---

## Slide 09 — Moat II — Two engines

### English (pandoc)

Different questions need different engines — A single vector index answers one shape of question well and everything
else poorly.

**Find me the note about X.** → QMD — Hybrid keyword + vector search **How does X relate to Y?** → GRAPHIFY — Entity +
relationship graph **Let me just look around.** → OBSIDIAN — Human browsing and editing

ONE SET OF FILES — wiki/ · index/ · raw/ — Plain linked Markdown on disk. Nothing locked inside a database we would have
to migrate out of.

### עברית

<div dir="rtl" lang="he">

שאלות שונות דורשות מנועים שונים — אינדקס וקטורי יחיד נותן מענה מיטבי לסוג שאלות אחד ואינו מספק לשאר.

**איתור ממוקד — "מצא את ה-note על X"** → QMD — חיפוש היברידי, מילות מפתח + וקטורים. **ניתוח קשרים — "כיצד X קשור
ל-Y?"** → GRAPHIFY — גרף ישויות וקשרים. **עיון חופשי** → OBSIDIAN — דפדוף ועריכה אנושית.

סט קבצים אחד — wiki/ · index/ · raw/ — קבצי Markdown מקושרים על הדיסק. דבר אינו נעול בתוך מסד נתונים שיהיה צורך לחלץ
ממנו.

</div>


---

## Slide 10 — Moat III — Weak model, strong guardrails

### English (pandoc)

Make the model decide less, and a weak model becomes enough

The heavy thinking happens outside the gap, with a frontier model, once — and ships in as structure.

**LIFECYCLE** — A named stage for every action, so the model never has to invent a plan.

**SCRIPTS** — Scaffolding, registries, logs and validation are deterministic. The model only writes prose.

**SKILLS** — Four operating skills — setup, ingest, query, lint — each wrapping the CLI it needs.

**RUBRICS** — Closed-choice decisions against fixed anchors. Never free-form judgement.

### עברית

<div dir="rtl" lang="he">

צמצום מרחב ההחלטה של המודל — כך מודל חלש הופך למספיק

עבודת החשיבה המורכבת מתבצעת מחוץ לרשת הסגורה, עם מודל מתקדם, פעם אחת — ונכנסת פנימה כמבנה מוכן.

**LIFECYCLE** — שלב מוגדר לכל פעולה, כך שהמודל אינו נדרש להמציא תכנית.

**SCRIPTS** — הקמת תשתית, רישום, תיעוד ואימות — דטרמיניסטיים. המודל כותב פרוזה בלבד.

**SKILLS** — ארבעה skills תפעוליים — setup, הכנסה ל-wiki, query, lint — כל אחד עוטף את ה-CLI הנדרש לו.

**RUBRICS** — החלטות בחירה סגורה מול עוגנים קבועים. לעולם לא שיפוט חופשי ופתוח.

</div>


---

## Slide 11 — Lifecycle — A vault does three things

### English (pandoc)

A vault does three things

**01 Setup** — Lay down the framework, register the engines, verify the bootstrap actually works.

**02 Ingest** — Turn a source document into atomic notes, cross-linked and registered.

**03 Query** — Answer a question from the vault, grounded and cited — or say it isn't covered.

The third one is the product. The first two exist to make it trustworthy.

### עברית

<div dir="rtl" lang="he">

vault מבצע שלוש פעולות בלבד

**01 סטאפ** — הנחת ה-framework, רישום המנועים ואימות שה-bootstrap פועל כנדרש.

**02 הכנסה ל-wiki** — הפיכת מסמך מקור ל-notes אטומיים, מקושרים ורשומים.

**03 שאילתא** — מענה על שאלה מתוך ה-vault עם ציטוט ומקור — או ציון מפורש כי אין כיסוי.

השלישי הוא המוצר. השניים הראשונים קיימים כדי שניתן יהיה לסמוך עליו. (+ בדיקת lint רביעית כ-guardrail — `vault check`)

</div>


---

## Slide 12 — Infrastructure — Boring on purpose

### English (pandoc)

Boring on purpose — The whole install and upgrade surface is two commands anyone in the organization already knows.

`$ pip install --upgrade second-brain-vault-framework` `$ vault upgrade ./my-vault`

**Infra owns its paths** — Skills, scripts and schema live in framework-owned files, replaced wholesale on upgrade.

**You own your content** — Sources, notes and indexes are never read or written by an upgrade. No merge conflicts, ever.

### עברית

<div dir="rtl" lang="he">

פשטות מכוונת — כל תהליך ההתקנה והשדרוג הוא שתי פקודות המוכרות לכלל הארגון.

`$ pip install --upgrade second-brain-vault-framework` `$ vault upgrade ./my-vault`

**התשתית אחראית על הקבצים שלה** — skills, סקריפטים ו-schema נמצאים בקבצים בבעלות ה-framework ומוחלפים במלואם בעת שדרוג.

**אתם אחראים על התוכן שלכם** — מקורות, notes ואינדקסים — שדרוג לעולם אינו נוגע בהם. ללא התנגשויות מיזוג (merge
conflicts).

</div>


---

## Slide 13 — Ingest pipeline — Six steps

### English (pandoc)

Six planning steps — `templates/ingest-pipeline/` (`README.md` is the source of truth). Each folder is a step with its own `QUESTIONS.md`, entry condition and artifact — a weak model and a busy expert split the work.

**01 Assess** — `A1–A5` → `domains.md` + out-of-scope + authority map (needs nothing)
**02 Filtering** — `C,D` → scope cards + deterministic filter seed rules + protect list (needs `domains.md`, `A3`)
**03 Translation** — `I` (`I0–I5`) → translation policy + layered glossary org/domain (needs `domains.md`)
**04 Classification** — `B,E` → `sources.md` + trust-tier map `T1–T5` + doc-type vocabulary (needs `domains.md`)
**05 Domain model** — `A6,A7,F,G,H` → dependency graph + completeness loop + layer order + overlaps + work-unit sequence (needs `domains.md`, `sources.md`, a filtered+translated corpus)
**06 Success criteria** — `J,K` → gold sample + reference translations + acceptance tests + definition of done (needs `domains.md`, `E1`, `H3`)

Steps sign off independently; filtering can run while classification is still open. The actual ingest (document → notes) runs inside the work-unit sequence defined in 05/H, not as a separate planning step.

### עברית

<div dir="rtl" lang="he">

שישה שלבי תכנון — `templates/ingest-pipeline/` (`README.md` הוא המקור). כל תיקייה היא שלב עם `QUESTIONS.md` משלה, תנאי כניסה ותוצר — כך שמודל חלש ומומחה עסוק חולקים עומס.

**01 Assess — מיפוי תחומים** — `A1–A5` → `domains.md` + רשימת out-of-scope + מפת סמכויות
**02 Filtering — סינון** — `C,D` → כרטיסי scope + חוקי סינון דטרמיניסטיים + protect list
**03 Translation — שפה ומינוח** — `I` + glossary מדורג (I0–I5) → מדיניות תרגום + glossary
**04 Classification — סיווג** — `B,E` → `sources.md` + מפת trust tiers + אוצר סוגי מסמכים
**05 Domain model — מודל תחום** — `A6,A7,F,G,H` → גרף תלויות + בדיקת שלמות + סדר שכבות + חפיפות + רצף work units
**06 Success criteria — קריטריוני הצלחה** — `J,K` → gold sample + תרגומי ייחוס + שאלות קבלה + הגדרת done

כל שלב נחתם בנפרד; ה-ingest עצמו רץ ברצף ה-work units של 05/H.

</div>


---

## Slide 14 — Beyond one team

### English (pandoc)

Other teams are solving the same ingest problem, each on their own, in the margins of another job

The corpus differs. The questions — what to keep, in what order, judged by whom — do not.

This project is the one that gets to research it full time and hand back a pipeline plan with steps and rubrics anyone
can fill in.

### עברית

<div dir="rtl" lang="he">

צוותים נוספים מתמודדים עם אותה בעיית הכנסה ל-wiki — כל אחד בנפרד, בשולי משימה אחרת

הקורפוס שונה. השאלות — מה לשמור, באיזה סדר, מי שופט — זהות.

פרויקט זה הוא היחיד המוקדש לחקר הנושא במשרה מלאה, במטרה להחזיר תכנית לבניית מסלול הכניסה ל wiki עם שלבים ורובריקות שכל צוות יוכל ליישם.

בנוסף, קיימת חפיפה משמעותית מאוד בידע של הדומיין, ולכן נכון יהיה ליצור wiki פר מערכה במרכז, ועליו כל צוות יוסיף את הידע הספציפי שלו, ואולי גם פר תפקידן.
</div>


---

## Slide 15 — Status — Where the project stands

### English (pandoc)

Where the project stands

**SHIPPING** — The framework installs, scaffolds, ingests, queries and lints — with a reference vault that CI keeps
honest. Both retrieval engines run inside the gap with no GPU.

**IN FLIGHT** — First client corpus: pipeline defined end to end, calibration complete, filtering underway. Next: finish
filtering, run the first domain campaign through to a passing quality gate. Handover to Genie is already in motion —
materials shared, technical drill-down done.

The ask: time to carry one domain all the way through, and turn that into the pattern everyone else copies.

### עברית

<div dir="rtl" lang="he">

סטטוס הפרויקט

**פעיל ויציב** — ה-framework מתקין, מבצע scaffold, הכנסה ל-wiki, query ו-lint — עם vault רפרנס ש-CI מוודא את תקינותו.
שני מנועי השליפה פועלים ברשת הסגורה ללא GPU.

**בהתקדמות** — קורפוס לקוח ראשון: מסלול הכניסה ל wiki מוגדר מקצה לקצה, כיול הושלם, שלב הסינון בעיצומו. השלב הבא: השלמת הסינון, הרצת
קמפיין הדומיין הראשון עד לעמידה בקריטריוני איכות.

תהליך החפיפה ל-Genie בעיצומו — חומרים הועברו והועברה סקירה טכנית
מעמיקה.

הבקשות:
1. הקצאת זמן להשלמת דומיין אחד מקצה לקצה, והפיכתו לתבנית ארגונית לשכפול.
2. הקצאת אנשים, בדגש על חייל מצוות ג'יני. משה משתחרר בקרוב ולכן לפני השחרור יש להעביר מקל לחייב בצוות ג'יני שיוביל את הפרויקט.
</div>


---

## Slide 16 — Act II — Technical deep dive

### English (pandoc)

Act II — Technical deep dive

How the vault is structured, how it gets into the gap, and what the engines actually do.

### עברית

<div dir="rtl" lang="he">

חלק ב' — צלילה טכנית

כיצד ה-vault בנוי, כיצד מעבירים אותו לרשת הסגורה, ומה המנועים מבצעים בפועל.

</div>


---

## Slide 17 — Structure — Three layers

### English (pandoc)

Three layers, one rule each

**index/** — Map of content, source registry, log, key takeaways — how you navigate

**wiki/** — One concept per note, frontmatter required, wikilinked to its sources

**raw/** — Immutable evidence. Never edited, renamed or deleted. — synthesis flows upward, citations point back down

**tests/** — Gold answers, deliberately outside the stack and never indexed — otherwise the eval leaks into retrieval
and every score is a lie.

### עברית

<div dir="rtl" lang="he">

שלוש שכבות, כלל אחד לכל שכבה

**index/** — מפת תוכן, רישום מקורות, לוג, תובנות — שכבת הניווט

**wiki/** — רעיון אחד לכל note, עם frontmatter חובה, מקושר למקורות ב-wikilink

**raw/** — ראיות בלתי ניתנות לשינוי. לעולם אינן נערכות, אינן משנות שם ואינן נמחקות. הסינתזה זורמת כלפי מעלה, הציטוטים
מצביעים כלפי מטה

**tests/** — תשובות זהב, מחוץ ל-stack במכוון ולעולם אינן מאונדקסות — אחרת ה-eval זולג ל-retrieval וכל ציון הופך לבלתי
אמין.

</div>


---

## Slide 18 — Setup — Ends with proof

### English (pandoc)

Setup ends with proof, not with files

`$ vault scaffold "MT Knowledge"` # lay down the framework `$ vault check` # must exit 0 `$ qmd doctor` # backend green

**Structural check** — Links resolve, stubs are filled, no framework drift, the eval collection is not registered.

**Behavioural check** — A short test suite: does it answer what it knows, and refuse what it doesn't?

### עברית

<div dir="rtl" lang="he">

סטאפ מסתיים בהוכחת תקינות, לא בהנחת קבצים

`$ vault scaffold "MT Knowledge"` # הנחת ה-framework `$ vault check` # חייב להסתיים ב-0
`$ qmd doctor` # backend תקין

**בדיקה מבנית** — קישורים תקינים, אין stubs פתוחים, אין drift של ה-framework, אוסף ה-eval אינו רשום.

**בדיקה התנהגותית** — סוויטת בדיקות קצרה: האם המערכת עונה על מה שהיא יודעת, ומסרבת להשיב על מה שאינה מכסה?

</div>


---

## Slide 19 — Ingest — One document becomes notes

### English (pandoc)

One document becomes notes

**01 Search first** — Find related notes before writing anything — update beats duplicate.

**02 Script the scaffolding** — Summary stub, registry row and log entry are generated, not written.

**03 Fill the blanks** — The model writes note bodies into a fixed template. That is all it writes.

**04 Link into navigation** — Map of content and key takeaways stay current by construction.

**05 Check, then re-index** — Validation must pass before search and graph are updated.

### עברית

<div dir="rtl" lang="he">

מסמך אחד הופך ל-notes

**01 חיפוש מקדים** — איתור notes קשורים לפני כתיבה — עדכון עדיף על כפילות.

**02 יצירת תשתית אוטומטית** — תקציר, שורה ב-registry ורשומת לוג נוצרים על ידי סקריפט, לא נכתבים ידנית.

**03 מילוי התבנית** — המודל כותב את גוף ה-note בלבד, לתוך תבנית קבועה.

**04 קישור לניווט** — מפת התוכן והתובנות מתעדכנות באופן מובנה (by construction).

**05 בדיקה ולאחריה אינדוקס מחדש** — אימות חייב לעבור לפני עדכון מנועי החיפוש והגרף.

</div>


---

## Slide 20 — Query — Grounded or refusal

### English (pandoc)

Grounded answers, or an honest refusal — If the vault does not cover it, say so. Never fill the gap from training data
and present it as if it came from the vault.

**Retrieve, then claim** — Search for lookup, graph for multi-hop, fetch the full document before asserting anything,
cite the note or its source.

**Write back** — If answering produced genuinely new cross-source synthesis, it becomes a note. The vault compounds with
use.

### עברית

<div dir="rtl" lang="he">

תשובה מעוגנת או סירוב מפורש — אם אין כיסוי ב-vault, יש לציין זאת. לעולם לא להשלים פערים מתוך ידע האימון ולהציגם כאילו
מקורם ב-vault.

**שליפה ולאחריה טענה** — חיפוש לאיתור, גרף ל-multi-hop, שליפת המסמך המלא לפני כל קביעה, ציטוט ה-note או מקורו.

**כתיבה חזרה** — אם המענה יצר סינתזה חדשה ומהותית בין מקורות, היא הופכת ל-note. ה-vault משתבח עם השימוש.

</div>


---

## Slide 21 — In practice — What it looks like

### English (pandoc)

What it looks like on screen

The wiki as a network — notes clustered by concept, not by folder. Fail-closed validation, and the findings it refuses
to let through. A step per folder, with the guiding questions the expert fills in.

### עברית

<div dir="rtl" lang="he">

כפי שזה נראה על המסך

ה-wiki כתצוגת רשת — notes מקובצים לפי רעיון, לא לפי תיקייה. אימות fail-closed, והממצאים שהוא אינו מאפשר להעביר. תיקייה
לכל שלב, עם שאלות מנחות שהמומחה ממלא.

</div>


---

## Slide 22 — Guardrails — Fail-closed

### English (pandoc)

Validation is fail-closed, so a half-finished vault never looks finished

**Broken wikilinks · Orphaned notes · Unfilled stubs · Framework drift**

Any one of these exits non-zero. The model cannot declare work done that the checker rejects — which is exactly the
assurance you need before delegating to a small model.

### עברית

<div dir="rtl" lang="he">

אימות fail-closed — vault שאינו שלם לעולם אינו נראה גמור

**קישורים שבורים · notes יתומים · stubs לא ממולאים · drift של ה-framework**

כל אחד מאלה מחזיר exit non-zero. המודל אינו יכול להכריז על סיום עבודה שה-checker דוחה — וזוהי בדיוק רשת הביטחון הנדרשת
לפני האצלת עבודה למודל קטן.

</div>


---

## Slide 23 — Framework vs vault

### English (pandoc)

Framework and vault are different things

**THE FRAMEWORK** — A package the org maintains — Schema, skills, scripts and templates. Versioned, tested, replaced
wholesale on upgrade.

**A VAULT** — A folder a team owns — Their sources, their notes, their indexes — plus one preserved zone for local
conventions.

Every team's vault gets the improvements without anyone merging anything.

### עברית

<div dir="rtl" lang="he">

Framework ו-vault הם שני דברים שונים

**ה-FRAMEWORK** — חבילה שהארגון מתחזק — סכמה, skills, סקריפטים ותבניות. עם גרסאות, בדיקות, מוחלף במלואו בעת שדרוג.

**VAULT** — תיקייה בבעלות הצוות — המקורות שלו, ה-notes, האינדקסים — לצד אזור שמור לקונבנציות מקומיות.

כל vault צוותי מקבל את השיפורים ללא צורך במיזוג כלשהו.

</div>


---

## Slide 24 — One boundary crossing per release

### English (pandoc)

One boundary crossing per release

**OUTSIDE — CONNECTED** — Version and tag the release. Build the wheel. Pack every artifact that isn't already on the
internal index. Compile the native engine modules against the target's exact platform and runtime. A fresh install
inside the gap cannot succeed. That is structural, not a configuration problem.

**INSIDE — AIR-GAPPED** — Publish once to the internal index. From then on, every machine on the inside upgrades with a
normal install over the LAN — no copying files, no knowledge of the internals.

Verification is scripted: the install script checks the binary and the native module load before you find out the hard
way.

### עברית

<div dir="rtl" lang="he">

מעבר גבול אחד לכל גרסה

**מחוץ לרשת — מחובר** — קביעת גרסה ותג. בניית wheel. אריזת כל ארטיפקט שטרם נמצא באינדקס הפנימי. קומפילציה של מודולים
native מול הפלטפורמה וה-runtime המדויקים של היעד. התקנה טרייה ברשת הסגורה אינה יכולה להצליח ללא זאת — זהו אילוץ מבני, לא
בעיית קונפיגורציה.

**בתוך הרשת — מנותק** — פרסום חד-פעמי לאינדקס הפנימי. מכאן ואילך כל מכונה ברשת הסגורה משודרגת בהתקנה רגילה ברשת
הפנימית — ללא העתקת קבצים, ללא היכרות עם פרטי המימוש.

האימות אוטומטי: סקריפט ההתקנה מוודא שהבינארי והמודול ה-native נטענים לפני שמתגלה כשל בשטח.

</div>


---

## Slide 25 — Engines — No GPU

### English (pandoc)

Adapting search to a gap with no GPU — The search engine normally loads local model files for embeddings. We run a fork
that talks to the internal inference endpoint instead.

**No model tarball** — Hundreds of megabytes of weights no longer have to cross the boundary or sit on every machine.

**No GPU needed** — Embeddings and generation both go to infrastructure the gap already runs.

**ABI verified on install** — The install script proves the compiled modules load on this machine, catching mismatches
immediately.

**Graph ships as wheels** — The knowledge graph engine vendors the same way — build once outside, carry the result in.

### עברית

<div dir="rtl" lang="he">

התאמת חיפוש לרשת סגורה ללא GPU — מנוע החיפוש טוען בדרך כלל קבצי מודל מקומיים ל-embeddings. אנו מפעילים fork המדבר עם
נקודת הקצה הפנימית להסקה.

**ללא tarball של מודל** — מאות מגה-בייט של weights אינם נדרשים לחצות את הגבול או לשבת על כל מכונה.

**ללא צורך ב-GPU** — גם embeddings וגם generation מופנים לתשתית שכבר פועלת ברשת הסגורה.

**ABI מאומת בהתקנה** — סקריפט ההתקנה מוכיח שהמודולים המקומפלים נטענים על מכונה זו, ותופס אי-התאמות באופן מיידי.

**הגרף מופץ כ-wheels** — מנוע גרף הידע נארז באותו אופן — בנייה חד-פעמית מחוץ לרשת, והכנסת התוצר פנימה.

</div>


---

## Slide 26 — The ingest pipeline (divider)

### English (pandoc)

Act II — continued — The ingest pipeline

Turning thousands of pages of someone else's documentation into a vault worth trusting.

### עברית

<div dir="rtl" lang="he">

חלק ב' — המשך — מסלול הכניסה ל wiki

הפיכת אלפי עמודים של תיעוד קיים ל-vault שניתן לסמוך עליו.

</div>


---

## Slide 27 — What we are actually working with

### English (pandoc)

What we are actually working with

**Thousands of pages** — A full documentation space plus file-share documents, of wildly uneven quality and age.

**Domain terminology gap** — The model doesn't know our domain terms, so we ground it by injecting GT definitions into
context — heavy reasoning only happens when grounded.

**A weak in-gap model** — Good for narrow closed choices against a rubric. Never trusted with open-ended synthesis.

**One embedded expert** — Available hours a day — so review gates are affordable, and they are the safety net.

### עברית

<div dir="rtl" lang="he">

תנאי העבודה בפועל

**אלפי עמודים** — ספייס קונפלואנס מלא + מסמכים מ-file-share, באיכות וגיל בלתי אחידים בעליל.

**פער טרמינולוגי** — המודל אינו מכיר את המונחים הייעודיים שלנו, לכן אנו מעגנים אותו באמצעות יצירת מילון מונחים מראש —
חשיבה מורכבת מתבצעת רק כשהמודל מעוגן.

**מודל חלש ברשת הסגורה** — יעיל לבחירות סגורות וממוקדות מול רובריקה. לעולם אינו אמון על סינתזה פתוחה.

**מומחה אחד מעורב בפרויקט** — זמין שעות ביום — לכן תורי הביקורת ישימים, והם רשת הביטחון.

</div>


---

## Slide 28 — Filtering runs in three lanes

### English (pandoc)

Filtering runs in three lanes — Every check is named, versioned and recorded separately — so we can ask afterwards which
rule rejected what, and why.

**GATE — Rules reject** — Empty pages, boilerplate, navigation stubs, near-duplicates and version copies. Deterministic,
with a reason code.

**EVIDENCE — Signals inform** — Annotations that shape the verdict and help the reviewer, but never decide on their own.

**JUDGE — Model decides** — In, out, or can't-tell. Confident verdicts stand; everything else goes to the expert queue.

Rejected documents keep their records forever — every decision is auditable and reversible.

### עברית

<div dir="rtl" lang="he">

סינון בשלושה נתיבים — כל בדיקה עם שם, גרסה ורישום נפרד — כך שניתן לשאול בדיעבד איזה כלל פסל מה ומדוע.

**כללים פוסלים** — עמודים ריקים, boilerplate, stubs ניווט, כמעט-כפילויות ועותקי גרסאות. דטרמיניסטי, עם reason
code.

**סימנים מעשירים** — אנוטציות המעצבות את ההכרעה ומסייעות ל-reviewer, אך לעולם אינן מכריעות לבדן.

**המודל מכריע** — בפנים, בחוץ, או לא ניתן להכריע. הכרעות בביטחון גבוה עומדות; היתר מופנה לתור המומחה.

מסמכים שנפסלו שומרים רישום לצמיתות — כל החלטה ניתנת לביקורת ולשחזור.

</div>


---

## Slide 29 — Domain campaigns, planned by questionnaire

### English (pandoc)

Domain campaigns, planned by questionnaire — Work is scoped into domain campaigns, run in dependency order.

**CAMPAIGN 1 — Foundations** — Highest trust. Runs first and writes the concept notes. **CAMPAIGN 2 — Domain A**
**CAMPAIGN 3 — Domain B**

**CAMPAIGN 4 — Domain C** — Extends existing notes rather than starting new ones. At a shared concept the later campaign
agrees, extends, or escalates to the expert.

The questionnaire produces this graph — domains, sources, trust, and what done means.

### עברית

<div dir="rtl" lang="he">

קמפיינים לפי תחום, מתוכננים באמצעות שאלון — העבודה מחולקת לקמפיינים לפי תחום, ומבוצעת לפי סדר תלויות.

**קמפיין 1 — יסודות** — רמת ה-trust הגבוהה ביותר. רץ ראשון וכותב את ה-concept notes.

**קמפיינים 2 — תחום A** - תלוי ביסודות הבסיסיים בלבד

**קמפיין 3 — תחום B** - חייב להשתמש בידע היסודי, יכול להשתמש בידע מקמפיין 2

**קמפיין 4 — תחום C** - - חייב להשתמש בידע היסודי, יכול להשתמש בידע מקמפיינים 2 ו 3


</div>


---

## Slide 30 — Every decision about every document, kept forever

### English (pandoc)

Every decision about every document, kept forever — ONE DOCUMENT, AS THE LEDGER SEES IT

Entered → hash → Gate passed → rule → Judged in scope → model → Grounded (GT) → model + expert → Classified → model →
Ingested → model + script → Verified → expert

**APPEND-ONLY** — Events are never overwritten. Current state is a projection of the log.

**RE-RUNNABLE** — Stages never mutate their inputs and writes are atomic — recovery is just running it again.

**CHEAP HISTORY** — Bulk artifacts sit in a content-addressed store; only the small text layer is versioned.

### עברית

<div dir="rtl" lang="he">

כל החלטה על כל מסמך, נשמרת לצמיתות — מסמך אחד כפי שה-ledger רואה אותו

נכנס → hash → עבר gate → כלל → נשפט in-scope → מודל → עוגן (GT) → מודל+מומחה → סווג → מודל → הוכנס → מודל+סקריפט →
אומת → מומחה

**כתיבה בלבד, ללא עריכה** — אירועים לעולם אינם נדרסים. המצב הנוכחי הוא projection של הלוג.

**ניתן להרצה מחדש** — שלבים לעולם אינם משנים את הקלט שלהם וכתיבות הן אטומיות — שחזור הוא פשוט הרצה חוזרת.

**היסטוריה חסכונית** — ארטיפקטים כבדים יושבים ב-store לפי תוכן; רק שכבת הטקסט המצומצמת מגורסנת.

</div>


---

## Slide 31 — What the pilot worked will mean

### English (pandoc)

What the pilot worked will mean

**One domain, end to end** — Filtered, GT-grounded, classified, ingested, and queryable by the client while later
domains are still queued.

**Answers with sources** — Gold questions pass, and negative controls get an honest not covered rather than a
fabrication.

**Nothing unexplainable** — For any document, the ledger says where it is and why — including everything we rejected.

**Repeatable by others** — A second team can take the questionnaire and the step definitions and start without us.

### עברית

<div dir="rtl" lang="he">

מה המשמעות של פיילוט מוצלח

**תחום אחד מקצה לקצה** — מסונן, מעוגן (GT), מסווג, מוכנס וניתן לשאילתא אצל הלקוח, בעוד תחומים נוספים עדיין ממתינים בתור.

**תשובות עם מקורות** — שאלות זהב עוברות, ובקרות שליליות מקבלות חיווי "אין כיסוי" ולא תשובה מומצאת.

**הכל מוסבר** — לכל מסמך ה-ledger מציין היכן הוא ומדוע — כולל כל מה שנפסל.

**ניתן לשחזור** — צוות נוסף יכול לקחת את השאלון והגדרות השלבים ולהתחיל באופן עצמאי.

</div>


---

## Slide 32 — In closing

### English (pandoc)

A knowledge system that runs where the knowledge already is. Structure and rubrics doing the work a frontier model would
otherwise do. An ingest pipeline the rest of the organization can copy.

The ask stays simple: the time to carry the first domain all the way through, and write down how we did it.

### עברית

<div dir="rtl" lang="he">

מערכת ידע הפועלת היכן שהידע כבר נמצא. מבנה ורובריקות מבצעים את העבודה שמודל מתקדם היה מבצע.

מסלול הכניסה ל wiki ששאר הארגון יכול לאמץ.

הבקשות:
1. הקצאת זמן להשלמת תחום אחד מקצה לקצה והפיכתו לתבנית ארגונית.
2. הקצאת חייל מצוות ג'יני להחלפת משה (משתחרר בקרוב) ולהובלת הפרויקט בהמשך.

</div>


---

