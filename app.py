"""
app.py
------
Gradio web interface for the WGU Unofficial Guide RAG system.

Run:
  python app.py
Then open http://localhost:7860 in your browser.
"""

import gradio as gr
from generate import RAGPipeline

# Initialise once at startup so the embedding model and ChromaDB collection
# are loaded into memory before the first query arrives.
pipeline = RAGPipeline()


def handle_query(question: str):
    question = question.strip()
    if not question:
        return "", "", ""

    result = pipeline.ask(question)

    sources_text = "\n".join(f"• {s}" for s in result.sources)

    chunks_text = ""
    for chunk in result.chunks:
        label = (
            f"[{chunk.rank}] {chunk.title or chunk.source_file}"
            f" — chunk {chunk.chunk_index}, dist={chunk.distance:.4f}"
        )
        preview = chunk.text[:300].replace("\n", " ")
        if len(chunk.text) > 300:
            preview += "…"
        chunks_text += f"{label}\n{preview}\n\n"

    return result.answer, sources_text, chunks_text.strip()


with gr.Blocks(title="WGU Unofficial Guide") as demo:
    gr.Markdown(
        """
        # 🎓 WGU Unofficial Student Guide
        Ask questions about WGU courses, study strategies, and student experiences.
        Answers are grounded in real student reviews, Reddit posts, and YouTube transcripts.
        """
    )

    with gr.Row():
        with gr.Column(scale=3):
            inp = gr.Textbox(
                label="Your question",
                placeholder="e.g. What study techniques do students recommend for WGU?",
                lines=2,
            )
            btn = gr.Button("Ask", variant="primary")

    with gr.Row():
        answer = gr.Textbox(label="Answer", lines=10, interactive=False)

    with gr.Row():
        with gr.Column():
            sources = gr.Textbox(label="Sources", lines=4, interactive=False)
        with gr.Column():
            chunks = gr.Textbox(label="Retrieved chunks", lines=4, interactive=False)

    btn.click(handle_query, inputs=inp, outputs=[answer, sources, chunks])
    inp.submit(handle_query, inputs=inp, outputs=[answer, sources, chunks])

    gr.Examples(
        examples=[
            "What study techniques do students most frequently recommend for WGU courses?",
            "What are three strategies to complete your WGU courses faster?",
            "How do WGU courses compare to traditional college courses?",
            "What resources do students recommend outside of official WGU materials?",
            "What are specific tips for OA and PA assessments?",
        ],
        inputs=inp,
    )

demo.launch()
