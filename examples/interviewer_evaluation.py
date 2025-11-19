"""
Example: Interviewer agent evaluating multiple candidates.
"""

import json
from autonomy import InterviewerAgent
from tessera.config import FrameworkConfig
from tessera.llm import create_llm
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.json import JSON

console = Console()


def main():
    """Demonstrate Interviewer evaluation capabilities."""
    console.print("\n[bold blue]Autonomy Framework - Interviewer Example[/bold blue]\n")

    # Initialize interviewer
    config = FrameworkConfig.from_env()
    interviewer = InterviewerAgent(config=config)

    # Task to evaluate for
    task_description = """
    Design and implement a caching strategy for a high-traffic API service
    that needs to balance performance, data freshness, and memory usage.
    """

    console.print(Panel(task_description.strip(), title="Task", border_style="green"))

    # Design interview questions
    console.print("\n[yellow]Designing interview questions...[/yellow]\n")
    questions = interviewer.design_interview(task_description, num_questions=4)

    console.print("[bold]Interview Questions:[/bold]")
    for i, q in enumerate(questions, 1):
        console.print(f"\n{i}. [{q.get('type', 'general')}] {q['text']}")
        console.print(f"   Focus: {q.get('evaluation_focus', 'N/A')}")

    # Create candidate LLMs (simulating different agents)
    console.print("\n[yellow]Setting up candidate agents...[/yellow]\n")

    candidates = {
        "CacheExpert": create_llm(temperature=0.3),  # More deterministic
        "GeneralistDev": create_llm(temperature=0.7),  # Balanced
        "CreativeEngineer": create_llm(temperature=0.9),  # More creative
    }

    # Conduct interviews
    interview_results = []

    for candidate_name, candidate_llm in candidates.items():
        console.print(f"\n[cyan]Interviewing {candidate_name}...[/cyan]")

        result = interviewer.conduct_interview(
            candidate_name=candidate_name,
            candidate_llm=candidate_llm,
            questions=questions,
            task_description=task_description,
        )

        interview_results.append(result)

        # Show summary
        console.print(f"  Aggregated Score: {result.aggregated_score:.2f}/100")
        console.print(f"  Recommendation: {result.recommendation}")

    # Compare candidates
    console.print("\n[yellow]Comparing all candidates...[/yellow]\n")
    comparison = interviewer.compare_candidates(interview_results)

    # Create comparison table
    table = Table(title="Candidate Rankings")
    table.add_column("Rank", style="cyan", justify="center")
    table.add_column("Candidate", style="magenta")
    table.add_column("Score", justify="right", style="green")

    for ranking in comparison["rankings"]:
        table.add_row(
            str(ranking["rank"]),
            ranking["candidate"],
            f"{ranking['score']:.2f}",
        )

    console.print(table)

    # Show final selection
    console.print("\n[bold]Final Selection:[/bold]")
    console.print(Panel(
        f"Selected: [green]{comparison['selected_candidate']}[/green]\n\n"
        f"Justification:\n{comparison['justification']}\n\n"
        f"Confidence: {comparison['confidence']}\n"
        f"Runner-up: {comparison.get('runner_up', 'N/A')}",
        title="Interview Decision",
        border_style="yellow"
    ))

    # Show key differentiators
    if comparison.get("key_differentiators"):
        console.print("\n[bold]Key Differentiators:[/bold]")
        for diff in comparison["key_differentiators"]:
            console.print(f"  • {diff}")

    # Demonstrate detailed score breakdown for winner
    winner_result = next(r for r in interview_results if r.candidate == comparison["selected_candidate"])

    console.print(f"\n[yellow]Detailed scores for {comparison['selected_candidate']}:[/yellow]\n")

    score_table = Table(title=f"{comparison['selected_candidate']} - Score Breakdown")
    score_table.add_column("Question", style="cyan")
    score_table.add_column("Overall", justify="right", style="green")
    score_table.add_column("Rationale", style="white")

    for score in winner_result.scores:
        score_table.add_row(
            score.question_id,
            f"{score.overall_score:.1f}/100",
            score.rationale[:60] + "..." if len(score.rationale) > 60 else score.rationale,
        )

    console.print(score_table)

    # Show metrics breakdown for one question
    if winner_result.scores:
        first_score = winner_result.scores[0]
        console.print(f"\n[yellow]Metric breakdown for {first_score.question_id}:[/yellow]")

        metrics_data = {
            "Accuracy": f"{first_score.metrics.accuracy}/5",
            "Relevance": f"{first_score.metrics.relevance}/5",
            "Completeness": f"{first_score.metrics.completeness}/5",
            "Explainability": f"{first_score.metrics.explainability}/5",
            "Efficiency": f"{first_score.metrics.efficiency}/5",
            "Safety": f"{first_score.metrics.safety}/5",
        }

        for metric, value in metrics_data.items():
            console.print(f"  {metric}: {value}")

    console.print("\n[bold green]Interviewer example completed![/bold green]\n")


if __name__ == "__main__":
    main()
