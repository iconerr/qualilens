<!--
Copyright 2026 Ashita Aggarwal and Suraj Commuri
SPDX-License-Identifier: Apache-2.0
-->

# 3. Choosing a Method

QualiLens offers five methods. Your choice is not reversible once a run exists, so make it deliberately. The method determines what the AI model is asked to do at each stage, where the pipeline stops for your review, what the report contains, and roughly what the analysis costs. This chapter compares the five. The five chapters that follow document each one option by option. Four of the methods analyze your own data — transcripts, documents, field notes. The fifth, literature synthesis, analyzes papers you upload, and is the one to reach for when the material under analysis is the literature itself.

## The short version

| If your position is | Choose |
|---|---|
| You want to build an explanation of a process from the data, and you are willing to let the organizing concept emerge | [Grounded theory](04-grounded-theory.md) |
| You want patterns of shared meaning across the corpus, reported as themes with evidence | [Thematic analysis](05-thematic-analysis.md) |
| You want to count how often defined categories occur, overall and across groups | [Content analysis](06-content-analysis.md) |
| You already hold a framework and want the data charted against it, case by case | [Framework and deductive coding](07-framework-analysis.md) |
| You have a corpus of papers and want a reviewed, evidence-linked synthesis across them | [Literature synthesis](08-literature-synthesis.md) |

## What each method produces

| | Grounded theory | Thematic analysis | Content analysis | Framework | Literature synthesis |
|---|---|---|---|---|---|
| Stages | 8 | 8 | 4 | 5 | 5 |
| Checkpoints | 3 | 2 | 1 | 1 | 2 |
| Familiarization pass before coding (first 60,000 characters of each source) | Yes | Yes | No | No | No — extraction is the first reading |
| Codes derived from data | Yes | Yes | Optional | No | Yes |
| Confidence scores on assignments | No | No | Yes, where the model gives one | Yes, where the model gives one | No |
| Numeric output | No | No | Frequency table | Source-by-code matrix | Concept-by-paper matrix |
| Report includes source summaries | Yes | Yes | No | No | Extraction table |
| Relative cost | Highest | Highest | Lowest | Low | Low |

The two inductive methods cost more for two reasons. They add a familiarization pass over every source before any coding happens, and they make a second grouping pass to build categories or themes out of the codes. The two deductive methods skip both, and literature synthesis reads each paper once — its extraction pass is also its first reading. Content analysis is the cheapest of the five, because it derives its codebook from a sample rather than reading everything twice.

## The pipelines side by side

**Grounded theory** runs familiarization, open coding, *review of open codes*, axial coding, *review of categories*, selective coding, *review of the core category*, and the theory narrative with report.

**Thematic analysis** runs familiarization, initial coding, *review of initial codes*, theme construction, theme review against the extracts, defining and naming, *review of themes*, and the report.

**Content analysis** runs codebook construction, *review of the codebook*, application of the codebook to every source, and quantification with report.

**Framework** runs framework loading, charting of every source against the framework, *review of the charting*, charting of any promoted emergent codes across every source, and the matrix with report.

**Literature synthesis** runs structured extraction from every paper, *review of the extraction table*, cross-paper synthesis, *review of the concepts*, and the concept matrix with report.

The italicized stages are the ones where the pipeline stops and waits for you.

## How to choose when two look plausible

**Grounded theory against thematic analysis.** Both methods code inductively and both group the codes, so the mechanical difference between them is smaller than the conceptual one. Grounded theory pushes toward a single core category and a storyline that explains a process. Its output makes a claim about how something works. Thematic analysis stops at themes. Its output makes a claim about what patterns of meaning are present. Choose grounded theory if you intend to write a theory. Choose thematic analysis if you intend to report patterns. Thematic analysis is the more modest claim and the easier one to defend, so choose it if the honest answer is that you do not yet know which you are writing.

**Content analysis against framework.** Both methods apply a fixed codebook to every source, and both attach a confidence score to each assignment. Content analysis counts, and its report is a frequency table you can cross-tabulate by group. Framework charts, and its report is a matrix whose cells summarize what each source said under each code. Choose content analysis when your question is how often. Choose framework when your question is what each case said. Framework can also admit codes your framework failed to anticipate, which content analysis cannot.

**Literature synthesis against everything else.** The other four methods assume the sources are your data. Literature synthesis assumes they are published papers, and it changes what the stages do accordingly: the coding pass becomes a structured extraction (aims, method, sample, findings, limitations), the grouping pass becomes a cross-paper synthesis, and the matrix crosses concepts with papers rather than codes with cases. It is also the one method with a structural guarantee about citations: every concept must be grounded in quotes located in the uploaded corpus, and the narrative is guarded against citation-shaped text that names no uploaded paper (see the method's chapter for exactly what is enforced and what is guarded). Running interview transcripts through it will produce a strained extraction table; running papers through thematic analysis will produce themes without the extraction table, the paper labels, or the citation guard. Match the method to the material.

**Deductive thematic analysis against framework.** Both methods read data through a stated prior structure. Deductive thematic analysis takes a theoretical lens as a paragraph of prose and lets the AI coder derive codes through it, so the codes are still discovered. Framework takes an explicit list of codes and definitions and applies exactly those. Choose the framework method when your prior structure is already a codebook. Choose deductive thematic analysis when your prior structure is a theory rather than a list.

## Provider and model

Every method uses the same providers. You choose the provider and model once per project, and QualiLens uses that choice for every call in the run.

| Provider | Models offered | Default |
|---|---|---|
| Anthropic (Claude) | `claude-sonnet-5`, `claude-opus-5`, `claude-haiku-4-5-20251001` | `claude-sonnet-5` |
| OpenAI (GPT) | `gpt-5.1`, `gpt-5`, `gpt-4.1`, `gpt-4o` | `gpt-5.1` |
| Google (Gemini) | `gemini-2.5-pro`, `gemini-2.5-flash` | `gemini-2.5-pro` |
| Mistral | `mistral-large-latest`, `mistral-medium-latest`, `mistral-small-latest` | `mistral-large-latest` |

Three considerations bear on your choice. None of them is about which AI model is best in the abstract.

Every analysis call asks for structured JSON. QualiLens refuses to parse a response that was cut off at the token limit, because repairing a truncated response would fabricate analysis content. A model that reliably closes its JSON therefore fails less often. QualiLens makes one repair call when a complete response is malformed rather than truncated, and that call is instructed to preserve content exactly, so a stray formatting error costs one small extra call rather than a failed stage.

Several current AI models spend output tokens on internal reasoning before they produce visible text, and those tokens are billed. QualiLens allows generous headroom for this, so that the visible answer is not starved, and unused headroom costs nothing. The tokens actually spent on reasoning do appear on your bill, and they are not modeled in the pre-run estimate.

Cost scales with data volume and with the pass factor of the method. The cheaper models within a provider's line therefore make the difference between an affordable pilot and an expensive one. One defensible pattern is to pilot on one or two sources with a smaller model to see the shape of the output, then run the full corpus with the larger one.

## Cost control before you commit

Four habits reduce your spend without weakening the analysis.

Run one short source through the whole pipeline first. You will see every checkpoint, and you will discover whether your research question is producing the codes you expected. Finding that out costs cents rather than dollars.

Prefer the cheaper deductive methods when your question is genuinely deductive. Applying a codebook you already hold costs roughly two-thirds of what building one from scratch costs on the same data.

Trim the corpus rather than the method. Cost scales linearly with characters, so removing the interviewer's boilerplate preamble from twenty transcripts saves you real money and improves the coding at the same time.

Read the checkpoints carefully the first time. A codebook you approve without scrutiny is applied to every source at full price, and the second run to fix it costs as much as the first.
