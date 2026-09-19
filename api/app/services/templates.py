from __future__ import annotations

from dataclasses import dataclass

PAPER_TYPES = (
    "Empirical Study",
    "Literature Review",
    "Theoretical Paper",
    "Case Study",
)
PAPER_SECTIONS = (
    "Abstract",
    "Introduction",
    "Literature Review",
    "Methods",
    "Results",
    "Discussion",
    "Conclusion",
    "References",
)
DEFAULT_PAPER_SECTIONS = [
    "Abstract",
    "Introduction",
    "Methods",
    "Results",
    "Discussion",
    "Conclusion",
]
CITATION_STYLES = ("APA", "MLA", "Chicago")
OUTPUT_FORMATS = ("markdown", "word")


@dataclass(frozen=True)
class SectionTemplate:
    retrieval_query: str
    instructions: str
    preferred_source_role: str  # literature | primary | both | none


def role_for(paper_type: str, section: str) -> str:
    if section == "References":
        return "none"
    if paper_type == "Literature Review":
        return "literature"
    if section in ("Methods", "Results"):
        return "primary"
    if section in ("Discussion", "Conclusion"):
        return "both"
    return "literature"


_TEMPLATES: dict[str, dict[str, tuple[str, str]]] = {
    "Empirical Study": {
        "Abstract": (
            "Empirical study abstract: research question, sample, main numeric findings.",
            "Write a structured abstract for an empirical study. Cite only retrieved source ids.",
        ),
        "Introduction": (
            "Empirical study introduction: gap in prior work and why this study was run.",
            "Introduce an empirical study. Do not report new results here. Cite only retrieved source ids.",
        ),
        "Literature Review": (
            "Published literature for an empirical study: prior findings, measures, debates.",
            "Synthesize published work. Cite only retrieved literature source ids.",
        ),
        "Methods": (
            "This study methods: participants, materials, procedure, analysis plan.",
            "Write Methods from primary passages. Do not invent n or instruments. Cite only retrieved source ids.",
        ),
        "Results": (
            "This study results: outcomes, tables, effects, descriptive statistics.",
            "Write Results from primary passages. Cite only retrieved source ids.",
        ),
        "Discussion": (
            "Empirical discussion: this study findings versus published literature.",
            "Discuss this study’s results against published work. Cite only retrieved source ids.",
        ),
        "Conclusion": (
            "Empirical conclusion: takeaways, limits, next studies.",
            "Conclude the empirical study. Cite only retrieved source ids.",
        ),
        "References": ("", "List only works cited via retrieved source ids."),
    },
    "Literature Review": {
        "Abstract": (
            "Literature review abstract: scope of the published corpus and synthesis claim.",
            "Write an abstract for a literature review. Cite only retrieved literature source ids.",
        ),
        "Introduction": (
            "Literature review introduction: why this published body of work needs a synthesis.",
            "Introduce a literature review. Cite only retrieved literature source ids.",
        ),
        "Literature Review": (
            "Core published papers, themes, and disagreements for this review.",
            "Organize published findings by theme. Cite only retrieved literature source ids.",
        ),
        "Methods": (
            "Review methods: inclusion criteria, search terms, how sources were selected.",
            "Describe how this review selected published sources. Cite only retrieved literature source ids.",
        ),
        "Results": (
            "Review findings: patterns and gaps across the included publications.",
            "Report patterns in the included publications. Cite only retrieved literature source ids.",
        ),
        "Discussion": (
            "Literature review discussion: implications of the published pattern.",
            "Discuss what the published corpus implies. Cite only retrieved literature source ids.",
        ),
        "Conclusion": (
            "Literature review conclusion: synthesis and open questions in prior work.",
            "Conclude the review. Cite only retrieved literature source ids.",
        ),
        "References": ("", "List only works cited via retrieved source ids."),
    },
    "Theoretical Paper": {
        "Abstract": (
            "Theoretical paper abstract: claim, constructs, and argument outline.",
            "Write an abstract for a theoretical paper. Cite only retrieved source ids.",
        ),
        "Introduction": (
            "Theoretical introduction: constructs, puzzle, and proposed account.",
            "Introduce the theoretical claim. Cite only retrieved source ids.",
        ),
        "Literature Review": (
            "Theories and published accounts this argument builds on or rejects.",
            "Map prior theoretical accounts. Cite only retrieved literature source ids.",
        ),
        "Methods": (
            "How the theoretical argument is structured: assumptions, cases, derivations.",
            "Explain how the argument is built. Cite only retrieved source ids.",
        ),
        "Results": (
            "Implications or worked cases that follow from the theoretical claim.",
            "Show what follows from the claim. Cite only retrieved source ids.",
        ),
        "Discussion": (
            "Theoretical discussion: limits of the account versus published alternatives.",
            "Discuss the account against alternatives. Cite only retrieved source ids.",
        ),
        "Conclusion": (
            "Theoretical conclusion: claim restated and what would test it.",
            "Restate the claim. Cite only retrieved source ids.",
        ),
        "References": ("", "List only works cited via retrieved source ids."),
    },
    "Case Study": {
        "Abstract": (
            "Case study abstract: the case, setting, and what it illustrates.",
            "Write an abstract for a case study. Cite only retrieved source ids.",
        ),
        "Introduction": (
            "Case study introduction: why this case, in this setting.",
            "Introduce the case. Cite only retrieved source ids.",
        ),
        "Literature Review": (
            "Published cases and theory this case study sits in.",
            "Place the case in published work. Cite only retrieved literature source ids.",
        ),
        "Methods": (
            "Case study methods: case selection, sources, how evidence was gathered.",
            "Describe case selection from primary passages when present. Cite only retrieved source ids.",
        ),
        "Results": (
            "Case narrative and evidence from this study’s materials.",
            "Tell what the case shows using retrieved primary passages. Cite only retrieved source ids.",
        ),
        "Discussion": (
            "Case discussion: this case versus published theory and other cases.",
            "Interpret the case against literature. Cite only retrieved source ids.",
        ),
        "Conclusion": (
            "Case study conclusion: transferable lesson and limits of the case.",
            "State what transfers beyond this case. Cite only retrieved source ids.",
        ),
        "References": ("", "List only works cited via retrieved source ids."),
    },
}


def is_known_paper_type(value: str) -> bool:
    return value in _TEMPLATES


def get_section_template(paper_type: str, section: str) -> SectionTemplate:
    if section not in PAPER_SECTIONS:
        raise ValueError(f"Unknown paper section: {section}")
    if paper_type not in _TEMPLATES:
        raise ValueError(f"Unknown paper type: {paper_type}")
    query, instructions = _TEMPLATES[paper_type][section]
    return SectionTemplate(query, instructions, role_for(paper_type, section))


def build_retrieval_query(paper_type: str, section: str, research_prompt: str) -> str:
    template = get_section_template(paper_type, section)
    topic = research_prompt.strip()
    if not template.retrieval_query:
        return topic
    return f"{template.retrieval_query}\n{topic}" if topic else template.retrieval_query
