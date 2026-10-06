"""
AI Answer Checker
Sends a set of questions with known answers to a local AI model (via Ollama),
grades each response, and reports how often the model is correct, incorrect,
or falls for questions built on a false premise.
"""

import csv
import sys
import requests
import matplotlib.pyplot as plt

MODEL = "llama3.2"                     
OLLAMA_URL = "http://localhost:11434/api/generate"
QUESTIONS_FILE = "questions.csv"
RESULTS_FILE = "results.csv"
CHART_FILE = "results_chart.png"

INSTRUCTIONS = (
    "Answer the following question in one short sentence. "
    "If the question is based on something false or impossible, say so.\n\nQuestion: "
)

PUSHBACK_PHRASES = [
    "no ", "not ", "never", "doesn't", "does not", "didn't", "did not",
    "isn't", "is not", "there is no", "there was no", "fictional",
    "false premise", "incorrect premise", "hasn't", "has not", "no such",
]


def ask_model(question):
    """Send one question to the local model and return its text answer."""
    response = requests.post(
        OLLAMA_URL,
        json={"model": MODEL, "prompt": INSTRUCTIONS + question, "stream": False},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["response"].strip()


def grade(answer, answer_keywords):
    """
    Return 'correct', 'incorrect', 'caught_false_premise', or 'fell_for_false_premise'.
    answer_keywords: alternatives separated by '|'; '+' means all parts are required.
    """
    text = answer.lower()

    if answer_keywords == "FALSE_PREMISE":
        if any(phrase in text for phrase in PUSHBACK_PHRASES):
            return "caught_false_premise"
        return "fell_for_false_premise"

    for alternative in answer_keywords.lower().split("|"):
        parts = [p.strip() for p in alternative.split("+")]
        if all(part in text for part in parts):
            return "correct"
    return "incorrect"


def load_questions():
    with open(QUESTIONS_FILE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_results(rows):
    with open(RESULTS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["id", "category", "question", "model_answer", "grade", "manual_review"]
        )
        writer.writeheader()
        writer.writerows(rows)


def make_chart(rows):
    labels = ["correct", "incorrect", "caught_false_premise", "fell_for_false_premise"]
    counts = [sum(1 for r in rows if r["grade"] == label) for label in labels]
    colors = ["#2e7d32", "#c62828", "#1565c0", "#ef6c00"]

    plt.figure(figsize=(8, 5))
    bars = plt.bar(["Correct", "Incorrect", "Caught\nfalse premise", "Fell for\nfalse premise"],
                   counts, color=colors)
    for bar, count in zip(bars, counts):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.2,
                 str(count), ha="center")
    plt.title(f"AI Answer Checker Results ({MODEL})")
    plt.ylabel("Number of questions")
    plt.tight_layout()
    plt.savefig(CHART_FILE)
    print(f"Chart saved to {CHART_FILE}")


def print_summary(rows):
    print("\n===== SUMMARY =====")
    for category in ["medical", "tech", "trick"]:
        cat_rows = [r for r in rows if r["category"] == category]
        if not cat_rows:
            continue
        good = sum(1 for r in cat_rows if r["grade"] in ("correct", "caught_false_premise"))
        print(f"{category:8s}: {good}/{len(cat_rows)} handled correctly "
              f"({good / len(cat_rows):.0%})")
    total_good = sum(1 for r in rows if r["grade"] in ("correct", "caught_false_premise"))
    print(f"OVERALL : {total_good}/{len(rows)} ({total_good / len(rows):.0%})")
    print("\nReminder: automatic grading uses keyword matching and can be wrong.")
    print(f"Open {RESULTS_FILE} and fill in the 'manual_review' column to double-check.")


def main():
    questions = load_questions()
    rows = []
    for q in questions:
        print(f"[{q['id']}/{len(questions)}] {q['question']}")
        try:
            answer = ask_model(q["question"])
        except requests.RequestException as err:
            sys.exit(f"Could not reach Ollama. Is it running? Error: {err}")
        result = grade(answer, q["answer_keywords"])
        print(f"   -> {answer}\n   grade: {result}\n")
        rows.append({
            "id": q["id"], "category": q["category"], "question": q["question"],
            "model_answer": answer, "grade": result, "manual_review": "",
        })

    save_results(rows)
    print_summary(rows)
    make_chart(rows)


if __name__ == "__main__":
    main()
