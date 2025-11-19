"""
Example: Panel interview system with round-robin voting.
"""

import json
from autonomy import PanelSystem
from tessera.config import FrameworkConfig
from tessera.llm import create_llm
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def main():
    """Demonstrate Panel interview system."""
    console.print("\n[bold blue]Autonomy Framework - Panel Interview Example[/bold blue]\n")

    # Initialize panel system
    config = FrameworkConfig.from_env()
    panel = PanelSystem(config=config)

    # Create panel with diverse perspectives
    console.print("[yellow]Creating evaluation panel with 5 diverse perspectives...[/yellow]\n")
    panelists = panel.create_default_panel(num_panelists=5)

    console.print("[bold]Panel Composition:[/bold]")
    for p in panelists:
        console.print(f"  • {p.name} ({p.role})")

    # Task to evaluate
    task_description = """
    Develop a real-time collaborative document editing system similar to Google Docs,
    handling concurrent edits, conflict resolution, and maintaining document consistency
    across multiple users.
    """

    console.print(f"\n{Panel(task_description.strip(), title='Task', border_style='green')}")

    # Set up candidates (different LLM configurations simulating different agents)
    console.print("\n[yellow]Setting up candidate agents...[/yellow]\n")

    candidates = {
        "PreciseArchitect": create_llm(temperature=0.2),
        "BalancedDev": create_llm(temperature=0.5),
        "InnovativeBuilder": create_llm(temperature=0.8),
    }

    console.print("[bold]Candidates:[/bold]")
    for name in candidates.keys():
        console.print(f"  • {name}")

    # Conduct panel interview
    console.print("\n[yellow]Conducting panel interview (this may take a few minutes)...[/yellow]\n")

    result = panel.conduct_panel_interview(
        task_description=task_description,
        candidates=list(candidates.keys()),
        candidate_llms=candidates,
    )

    # Display results
    console.print("\n[bold green]Panel Interview Complete![/bold green]\n")

    # Vote summary
    vote_summary = panel.get_vote_summary(result)

    console.print(Panel(
        f"Session ID: {result.session_id}\n"
        f"Decision: [green]{result.decision}[/green]\n"
        f"Confidence: {result.confidence}\n"
        f"Tie-breaker Used: {'Yes' if result.tie_breaker_used else 'No'}",
        title="Panel Decision",
        border_style="yellow"
    ))

    # Vote counts table
    vote_table = Table(title="Vote Counts")
    vote_table.add_column("Candidate", style="cyan")
    vote_table.add_column("HIRE", justify="center", style="green")
    vote_table.add_column("PASS", justify="center", style="red")
    vote_table.add_column("Avg Score", justify="right", style="magenta")

    for candidate in result.candidates:
        hire_votes = vote_summary["vote_counts"][candidate]["HIRE"]
        pass_votes = vote_summary["vote_counts"][candidate]["PASS"]

        # Calculate average score for this candidate
        candidate_ballots = [b for b in result.ballots if b.candidate == candidate]
        avg_score = sum(b.overall_score for b in candidate_ballots) / len(candidate_ballots) if candidate_ballots else 0

        vote_table.add_row(
            candidate,
            str(hire_votes),
            str(pass_votes),
            f"{avg_score:.2f}"
        )

    console.print(f"\n{vote_table}")

    # Final ranking
    ranking_table = Table(title="Final Ranking")
    ranking_table.add_column("Rank", justify="center", style="cyan")
    ranking_table.add_column("Candidate", style="magenta")
    ranking_table.add_column("Score", justify="right", style="green")

    for i, (candidate, score) in enumerate(result.final_ranking, 1):
        ranking_table.add_row(
            str(i),
            candidate,
            f"{score:.2f}"
        )

    console.print(f"\n{ranking_table}")

    # Show sample ballots
    console.print("\n[bold]Sample Ballots (first 3):[/bold]\n")

    for ballot in result.ballots[:3]:
        console.print(Panel(
            f"Candidate: {ballot.candidate}\n"
            f"Panelist: {ballot.panelist}\n"
            f"Vote: [{'green' if ballot.vote.value == 'hire' else 'red'}]{ballot.vote.value.upper()}[/]\n"
            f"Overall Score: {ballot.overall_score}/100\n\n"
            f"Metrics:\n"
            f"  Accuracy: {ballot.scores.accuracy}/5\n"
            f"  Relevance: {ballot.scores.relevance}/5\n"
            f"  Completeness: {ballot.scores.completeness}/5\n"
            f"  Explainability: {ballot.scores.explainability}/5\n"
            f"  Efficiency: {ballot.scores.efficiency}/5\n"
            f"  Safety: {ballot.scores.safety}/5\n\n"
            f"Rationale: {ballot.rationale}",
            border_style="blue"
        ))

    # Show tie-breaker info if used
    if result.tie_breaker_used:
        console.print("\n[bold yellow]Tie-Breaker Was Used[/bold yellow]")
        if "tie_breaker" in result.transcript:
            tb = result.transcript["tie_breaker"]
            console.print(Panel(
                f"Question: {tb.get('tiebreaker_question', 'N/A')}\n\n"
                f"Selected: {tb.get('selected_candidate', 'N/A')}\n"
                f"Justification: {tb.get('justification', 'N/A')}",
                title="Tie-Breaker Details",
                border_style="red"
            ))

    console.print("\n[bold green]Panel interview example completed![/bold green]\n")


if __name__ == "__main__":
    main()
