# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

A student-generated reviews, study strategies, and course-completion assistant for Western Governors University courses because it helps students discover practical insights, recommended resources, difficulty assessments and success strategies that are often scattered across various discussions, blogs, forums, and alumni experiences rather than official university materials.

## Document Sources

<!-- List every source you collected documents from.
     Be specific: include URLs, subreddit names, forum thread titles, or file names.
     Aim for variety — sources that together cover different subtopics or perspectives. -->

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | Reddit | txt | docs\a comprehensive guide to wgu.txt |
| 2 | YouTube | txt | docs\How to finish as fast as possible at WGU YT-XWg.txt |
| 3 | YouTube | txt | docs\How to Succeed at WGU YT-TKU.txt |
| 4 | Stunlock | txt | docs\My Thoughts on WGU and Online Schools -stunlock.txt |
| 5 | Reddit | txt | docs\need all the advice and resources.txt |
| 6 | Reddit | txt | docs\Review of all WGU classes I took and tips.txt |
| 7 | Infosecinstitute | txt | docs\Starting WGU MBA IT Management - infosecinstitute.txt |
| 8 | Reddit | txt | docs\structure of a typical course - reddit.txt|
| 9 | YouTube | txt | docs\Survival Tips to complete Your WGU Degree Any field -YT-MWL.txt |
| 10 | YouTube | txt | docs\Tips to Study 2-3x Faster For WGU Classes - YT-Xlw.txt |
| 11 | Reddit | txt | docs\What is your best study method-reddit.txt |

---

## Chunking Strategy

<!-- Describe your chunking approach with enough specificity that someone else could reproduce it.
     Include:
     - Chunk size (characters or tokens) and why that size fits your documents
     - Overlap size and why (or why not) you used overlap
     - Any preprocessing you did before chunking (e.g., stripping HTML, removing headers)
     - What your final chunk count was across all documents -->

**Chunk size:**
350-450 characters
To capture the core meaning with losing data to truncation.

**Overlap:**
50-75 characters
This ensures sentence continuity across boundaries without diluting the vector space.

**Why these choices fit your documents:**
All-MiniLM-L6-vs is optimized for short sentence-level or paragraph level embeddings. The documents are long and coversational with poor stucture and ideas often span multiple sentences.
**Final chunk count:**
432
---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Model used:**
sentence-transformers (all-MiniLM-L6-v2) which runs locally and does not require an API key and has no rate limits.
**Production tradeoff reflection:**
If deployed in production, I would evaluate larger embedding
models that provide higher retrieval accuracy on educational
content.

I would compare retrieval quality against latency and cost.
I would also consider multilingual support if the system
served international students and benchmark several models
against my evaluation dataset before making a final decision.
---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:**
Wire Generation by connecting to Groq's llama-3.3-70b-versatile LLM, which is free-tier and OpenAI-compatible — initialize it with from groq import Groq and my GROQ_API_KEY from .env. Write a prompt template that passes the retrieved chunks as context and explicitly instructs the model to answer only from that context. Example: "Answer the question using only the information in the provided documents. If the documents don't contain enough information to answer, say 'I don't have enough information on that.'"
Add source attribution to the response format. The LLM's response should name which document(s) the answer came from — either by instructing the model to cite sources in its response, or by appending retrieved source names programmatically after generation.
Test grounded generation end-to-end on 2–3 queries. The test: could this response have come from anywhere other than your retrieved chunks? If yes, it's a grounding failure — even if the answer happens to be correct.

**How source attribution is surfaced in the response:**
There are two layers of source attribution. 
Layer 1 - Model-generated citations in the answer text. This layer can't hallucinate because it comes from ChromaDB metadata, not the LLM.
Layer 2 - Programmatic attributions via the sources panel. The programmatic list tells you which documents it was shown. Comparing the two is how you catch a grounding failure: if the model cites a source that isn't in the programmatic list, it invented it.

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | What study techniques do students most frequently recommend for WGU courses? | Students recommend using course resources, taking practice assessments, reviewing Quizlets, and focusing on competency mastery rather than memorization | Students at WGU recommend various study techniques, including using quizzes and unit tests to their advantage, aiming for an 80% or higher score, and taking notes while learning through video chapters and practice tests. | relevant | partially accurate | 
| 2 | What are specific study tips for OA and PA assessments? | OAs are commonly approached through practice tests, flashcards, and course materials. PAs are typically completed by following the rubric closely and addressing each requirement directly. | For OA assessments, one strategy is to take the pre-assessment only when you think you might be ready for the OA, as you can only see the questions for the first time once. Additionally, taking the practice assessment early can give you an idea of what you need to restudy. For PA assessments, there is often a template or guide available, and it's recommended to look at the rubric and start the PA immediately, referring back to course material as needed. You can also take the PA, take notes or watch videos, and then take it again to reinforce your understanding. | relevant | accurate |
| 3 | What are three strategies to complete your WGU courses faster?  | Students recommend accelerating by: 1. Studying before the term begins, completing assessments as soon as ready. 3. Leveraging outside resources such as Quizlet and YouTube | To complete WGU courses faster, three strategies can be employed. Firstly, apply real-world knowledge to the course, as WGU allows this, and spend less time on courses where you already excel in your everyday work. Secondly, create a self-motivated study plan and execute it, utilizing the material provided by WGU upfront. Lastly, take advantage of the flexibility of WGU's course structure, which allows you to complete courses at your own pace and schedule the final assessment when you are ready. | relevant | accurate |
| 4 | How do WGU courses compare to traditional college courses? | Students describe WGU as self-paced, competency-based, and less dependent on scheduled lectures than traditional universities. |WGU courses are completely different from traditional college courses, mainly because of their flexibility and competency-based approach. Unlike traditional schools, WGU has no required quizzes, mid-terms, homework, etc. Classes at WGU either have a single exam or one or more tasks to complete. Additionally, students tend to spend much more time per class at traditional schools than at WGU. WGU courses also tend to be more business or vocationally focused, with less emphasis on theory, and may have some gaps in foundational topics. | relevant | partially accurate |
| 5 | What resources do students recommend outside of official WGU materials? | Students recommend using outside resources like Reddit, YouTube, and Quizlet. | Students recommend using resources outside of official WGU materials, such as Udemy, which is included in tuition. They also suggest searching for class-specific advice and study materials on Reddit, using the r/WGU or r/WGUIT community, where people share their experiences, study tips, and recommendations. Additionally, taking notes while learning through video chapters and practice tests is recommended for better retention. | relevant | accurate |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:**

What do you think about WGU?
I don't feel that any questions failed as I tried to trick the AI, but some of the answers did not specificlly point to a particular source - rather combined the answers from multiple sources.  

**What the system returned:**

WGU is considered a decent institution that provides enough fundamentals for software development without being too easy. It has a broad domain and delves deep into some topics, making it valuable for both employees and employers. However, it may not be suitable for everyone, especially those who need their hand held every step of the way. Additionally, there is a small stigma associated with WGU, possibly due to its absence from college ranking systems like US News, but this stigma is believed to fade over time as more alumni enter the workforce.

**Root cause (tied to a specific pipeline stage):**

This issue was caused during generate.py.

**What you would change to fix it:**

I would further insist that for each point listed to note the source at the end of the sentence - unless all sentences/points are from the same source. Also, cite the source document within the text instead of listing all the sources at the end, so it is clearly evident which document each answer was retrieved from.
---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:**
The implementation assisted with prompting the code companion with specific details.
**One way your implementation diverged from the spec, and why:**
I adjusted the chunking because the distance numbers were too high, but it was a problem with ChromaDB defaulting to L2 distance instead of cosine.

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1**

- *What I gave the AI:*
I gave the chunking strategy to target paragraph-aware chunking, target size 700 - 900 characters, and overlap of 100 - 150 characters.
- *What it produced:*
TARGET_MIN  = 700    # minimum chars per chunk
TARGET_MAX  = 900    # maximum chars per chunk before forcing a split
OVERLAP_MIN = 100    # minimum overlap chars carried forward
OVERLAP_MAX = 150    # maximum overlap chars carried forward
- *What I changed or overrode:*
TARGET_MIN  = 350    # minimum chars per chunk
TARGET_MAX  = 450    # maximum chars per chunk before forcing a split
OVERLAP_MIN = 50     # minimum overlap chars carried forward
OVERLAP_MAX = 75     # maximum overlap chars carried forward

**Instance 2**

- *What I gave the AI:*
Write a Python script that loads all my .txt student knowledge documents from: C:\projects\ai201-project1-unofficial-guide-starter\docs. The documents are from various sources, including Reddit, YouTube Transcripts, Stunlock, InfoSecInstitute, and Degree Forum.
- *What it produced:*
The AI produced chunk_documents.py
- *What I changed or overrode:*
I had to change the directory locations for the documents and chunks.json files because the AI was working in a separate environment.