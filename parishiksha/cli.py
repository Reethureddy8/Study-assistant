"""Command-line entry point: ``python -m parishiksha <command>``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import SETTINGS


def _retriever(kind: str):
    from .chunking import load_chunks
    from .retrieval import BM25Retriever, DenseRetriever

    chunks = load_chunks()
    return BM25Retriever(chunks) if kind == "bm25" else DenseRetriever(chunks)


def cmd_chunk(args: argparse.Namespace) -> None:
    from .chunking import build_chunks, save_chunks
    from .ingest import load_corpus

    sections = load_corpus(SETTINGS.raw_dir, SETTINGS.chapters)
    chunks = build_chunks(sections)
    save_chunks(chunks, SETTINGS.chunks_path)
    print(f"{len(sections)} pages -> {len(chunks)} chunks saved to {SETTINGS.chunks_path}")


def cmd_index(args: argparse.Namespace) -> None:
    retriever = _retriever("dense")
    size = retriever.build_index(rebuild=args.rebuild)
    print(f"Vector index ready: {size} chunks in {SETTINGS.chroma_dir}")


def cmd_ask(args: argparse.Namespace) -> None:
    from .generation import StudyAssistant

    assistant = StudyAssistant(_retriever(args.retriever), k=args.k)
    answer = assistant.ask(args.question)

    if args.show_context:
        print("Retrieved:")
        for r in answer.retrieved:
            print(f"  [{r.score:.3f}] {r.chunk_id}  {r.chunk.section[:60]}")
        print()
    print(answer.text)
    if answer.unknown_citations:
        print(f"\nWarning: cited ids not in context: {', '.join(answer.unknown_citations)}")


def cmd_evaluate(args: argparse.Namespace) -> None:
    from .evaluation import run_evaluation, write_csv
    from .generation import StudyAssistant

    assistant = StudyAssistant(_retriever(args.retriever), k=args.k)
    rows = run_evaluation(assistant)
    write_csv(rows, args.out)
    print(f"{len(rows)} answers written to {args.out}. Score them by hand, then run `score`.")


def cmd_score(args: argparse.Namespace) -> None:
    from .evaluation import format_summary, read_csv, summarize

    print(format_summary(summarize(read_csv(args.csv))))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="parishiksha", description="NCERT Class 9 Science RAG assistant")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("chunk", help="extract the PDFs in data/raw and write chunks").set_defaults(func=cmd_chunk)

    p = sub.add_parser("index", help="embed chunks into the Chroma vector store")
    p.add_argument("--rebuild", action="store_true", help="drop and re-embed everything")
    p.set_defaults(func=cmd_index)

    for name, func, help_text in [
        ("ask", cmd_ask, "answer one question"),
        ("evaluate", cmd_evaluate, "run the 12-question evaluation set"),
    ]:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--retriever", choices=["dense", "bm25"], default="dense")
        p.add_argument("-k", type=int, default=SETTINGS.top_k, help="chunks passed to the model")
        p.set_defaults(func=func)
    ask = sub.choices["ask"]
    ask.add_argument("question")
    ask.add_argument("--show-context", action="store_true", help="print retrieved chunks first")
    sub.choices["evaluate"].add_argument(
        "--out", type=Path, default=SETTINGS.evaluation_dir / "eval_latest_raw.csv"
    )

    p = sub.add_parser("score", help="summarise a hand-scored evaluation CSV")
    p.add_argument("csv", type=Path, nargs="?", default=SETTINGS.evaluation_dir / "eval_scored.csv")
    p.set_defaults(func=cmd_score)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except (RuntimeError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except ImportError as exc:
        print(f"error: {exc.name} is not installed. Run `pip install -r requirements.txt`.", file=sys.stderr)
        return 1
    return 0
