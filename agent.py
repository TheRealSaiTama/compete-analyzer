import json
import os
import re
import sys
from pathlib import Path
from datetime import date
from groq import Groq


class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


CONFIG_PATH = Path.home() / ".competitive_agent_config"

ANALYSIS_PROMPT = """
You are an elite Competitive Intelligence Analyst with expertise in market positioning, 
competitive strategy, and business differentiation.

Your Analysis Framework:
1. MARKET CONTEXT - Understand the landscape and dynamics
2. COMPETITOR DEEP DIVE - Analyze each competitor objectively
3. STRATEGIC GAPS - Identify underserved needs and opportunities
4. POSITIONING MATRIX - Define clear differentiation angles
5. ACTIONABLE INSIGHTS - Provide specific, implementable recommendations

Analysis Standards:
- Be brutally objective, no promotional fluff
- Ground insights in market realities
- Quantify where possible (market size, pricing tiers, etc.)
- Identify both threats and opportunities
- Focus on actionable strategic recommendations

Return ONLY valid JSON matching this schema exactly:

{
    "market_overview": {
        "industry": "",
        "market_dynamics": "",
        "key_trends": [],
        "market_maturity": ""
    },
    "primary_company": {
        "name": "",
        "core_value_proposition": "",
        "target_segments": [],
        "current_positioning": ""
    },
    "competitors": [
        {
            "name": "",
            "category": "",
            "strengths": [],
            "weaknesses": [],
            "pricing_model": "",
            "target_audience": "",
            "positioning": "",
            "threat_level": ""
        }
    ],
    "competitive_matrix": {
        "differentiation_factors": [],
        "competitive_advantages": [],
        "vulnerabilities": []
    },
    "gaps_and_opportunities": [
        {
            "gap": "",
            "opportunity": "",
            "priority": "",
            "implementation_difficulty": ""
        }
    ],
    "strategic_recommendations": [
        {
            "recommendation": "",
            "rationale": "",
            "expected_impact": ""
        }
    ],
    "positioning_statement": ""
}
"""


def print_banner():
    banner = f"""
{Colors.CYAN}{Colors.BOLD}
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ⚔️  COMPETITIVE ANALYSIS AGENT                              ║
║                                                               ║
║   Powered by Groq AI • Strategic Intelligence Engine          ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
{Colors.RESET}"""
    print(banner)


def print_step(message, step_type="info"):
    icons = {
        "info": f"{Colors.BLUE}→{Colors.RESET}",
        "success": f"{Colors.GREEN}✓{Colors.RESET}",
        "warning": f"{Colors.YELLOW}⚠{Colors.RESET}",
        "error": f"{Colors.RED}✗{Colors.RESET}",
        "processing": f"{Colors.CYAN}◉{Colors.RESET}",
    }
    icon = icons.get(step_type, icons["info"])
    print(f"  {icon} {message}")


def print_section(title):
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'─' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.HEADER}  {title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'─' * 60}{Colors.RESET}\n")


def load_api_key():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
            return config.get("groq_api_key")
    return None


def save_api_key(api_key):
    with open(CONFIG_PATH, "w") as f:
        json.dump({"groq_api_key": api_key}, f)
    os.chmod(CONFIG_PATH, 0o600)


def get_api_key():
    existing_key = load_api_key()

    if existing_key:
        masked = existing_key[:8] + "..." + existing_key[-4:]
        print_step(
            f"Found saved API key: {Colors.DIM}{masked}{Colors.RESET}", "success"
        )

        use_existing = (
            input(f"\n  {Colors.YELLOW}Use this key? [Y/n]:{Colors.RESET} ")
            .strip()
            .lower()
        )
        if use_existing != "n":
            return existing_key

    print(f"\n  {Colors.CYAN}Enter your Groq API key{Colors.RESET}")
    print(f"  {Colors.DIM}(Get one free at https://console.groq.com){Colors.RESET}")

    api_key = input(f"\n  {Colors.YELLOW}API Key:{Colors.RESET} ").strip()

    if not api_key:
        print_step("No API key provided. Exiting.", "error")
        sys.exit(1)

    save_api_key(api_key)
    print_step("API key saved for future sessions", "success")

    return api_key


def read_analysis_input(filepath="input.txt"):
    if not Path(filepath).exists():
        print_step(f"Input file '{filepath}' not found", "error")
        sys.exit(1)

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    print_step(f"Loaded analysis context from {filepath}", "success")
    return content


def extract_json_from_response(response_text):
    json_match = re.search(r"```json\s*([\s\S]*?)\s*```", response_text)
    if json_match:
        return json_match.group(1).strip()

    json_match = re.search(r"```\s*([\s\S]*?)\s*```", response_text)
    if json_match:
        potential_json = json_match.group(1).strip()
        if potential_json.startswith("{"):
            return potential_json

    start_idx = response_text.find("{")
    end_idx = response_text.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        return response_text[start_idx : end_idx + 1]

    return None


def fix_common_json_errors(json_str):
    json_str = re.sub(
        r"\{([^{}]*?)\}(?=\s*[,\]])",
        lambda m: '["' + m.group(1).replace('"', "") + '"]'
        if "," in m.group(1) and ":" not in m.group(1)
        else m.group(0),
        json_str,
    )
    json_str = re.sub(r",\s*}", "}", json_str)
    json_str = re.sub(r",\s*]", "]", json_str)
    return json_str


def run_competitive_analysis(client, analysis_context, max_retries=2):
    print_section("RUNNING ANALYSIS")
    print_step("Analyzing market landscape...", "processing")
    print_step("Evaluating competitor positions...", "processing")
    print_step("Identifying strategic gaps...", "processing")
    print()

    models_to_try = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "meta-llama/llama-4-scout-17b-16e-instruct",
    ]

    for attempt, model in enumerate(models_to_try):
        print(f"  {Colors.DIM}Using model: {model}{Colors.RESET}")
        print(f"  {Colors.DIM}Generating insights...{Colors.RESET}\n")

        full_response = ""

        try:
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": ANALYSIS_PROMPT},
                    {
                        "role": "user",
                        "content": f"Perform a comprehensive competitive analysis based on this context:\n\n{analysis_context}",
                    },
                ],
                temperature=0.2,
                max_completion_tokens=8192,
                stream=True,
            )

            for chunk in completion:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    sys.stdout.write(f"{Colors.DIM}.{Colors.RESET}")
                    sys.stdout.flush()

            print(f"\n\n  {Colors.GREEN}Analysis complete!{Colors.RESET}\n")

            json_str = extract_json_from_response(full_response)
            if not json_str:
                raise ValueError("No JSON found in response")

            json_str = fix_common_json_errors(json_str)

            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                print_step(f"JSON parse error: {e}", "warning")
                with open("debug_response.txt", "w") as f:
                    f.write(full_response)
                if attempt < len(models_to_try) - 1:
                    print_step(f"Retrying with different model...", "info")
                    continue
                raise

        except Exception as e:
            if attempt < len(models_to_try) - 1:
                print_step(f"Attempt failed: {e}", "warning")
                print_step("Retrying with different model...", "info")
                continue
            print_step(f"All attempts failed: {e}", "error")
            print_step("Raw response saved to debug_response.txt", "warning")
            with open("debug_response.txt", "w") as f:
                f.write(full_response)
            sys.exit(1)

    sys.exit(1)


def save_json_output(analysis_data):
    output_path = "competitive_analysis.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(analysis_data, f, indent=2, ensure_ascii=False)
    print_step(f"Saved JSON report: {output_path}", "success")


def save_text_report(analysis_data):
    output_path = "competitive_analysis.txt"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("  COMPETITIVE ANALYSIS REPORT\n")
        f.write(f"  Generated: {date.today()}\n")
        f.write("=" * 70 + "\n\n")

        if "market_overview" in analysis_data:
            overview = analysis_data["market_overview"]
            f.write("MARKET OVERVIEW\n")
            f.write("-" * 40 + "\n")
            f.write(f"Industry: {overview.get('industry', 'N/A')}\n")
            f.write(f"Market Dynamics: {overview.get('market_dynamics', 'N/A')}\n")
            f.write(f"Market Maturity: {overview.get('market_maturity', 'N/A')}\n")
            if overview.get("key_trends"):
                f.write("\nKey Trends:\n")
                for trend in overview["key_trends"]:
                    f.write(f"  • {trend}\n")
            f.write("\n")

        if "primary_company" in analysis_data:
            company = analysis_data["primary_company"]
            f.write("PRIMARY COMPANY PROFILE\n")
            f.write("-" * 40 + "\n")
            f.write(f"Name: {company.get('name', 'N/A')}\n")
            f.write(
                f"Value Proposition: {company.get('core_value_proposition', 'N/A')}\n"
            )
            f.write(f"Positioning: {company.get('current_positioning', 'N/A')}\n")
            if company.get("target_segments"):
                f.write("Target Segments:\n")
                for segment in company["target_segments"]:
                    f.write(f"  • {segment}\n")
            f.write("\n")

        if "competitors" in analysis_data:
            f.write("COMPETITOR ANALYSIS\n")
            f.write("-" * 40 + "\n\n")
            for competitor in analysis_data["competitors"]:
                if not isinstance(competitor, dict):
                    continue
                f.write(f"► {competitor.get('name', 'Unknown')}\n")
                f.write(f"  Category: {competitor.get('category', 'N/A')}\n")
                f.write(f"  Threat Level: {competitor.get('threat_level', 'N/A')}\n")
                f.write(f"  Pricing: {competitor.get('pricing_model', 'N/A')}\n")
                f.write(f"  Target: {competitor.get('target_audience', 'N/A')}\n")

                strengths = competitor.get("strengths", [])
                if strengths and isinstance(strengths, list):
                    f.write("  Strengths:\n")
                    for strength in strengths:
                        f.write(f"    + {strength}\n")

                weaknesses = competitor.get("weaknesses", [])
                if weaknesses and isinstance(weaknesses, list):
                    f.write("  Weaknesses:\n")
                    for weakness in weaknesses:
                        f.write(f"    - {weakness}\n")

                f.write(f"  Positioning: {competitor.get('positioning', 'N/A')}\n")
                f.write("\n")

        if "competitive_matrix" in analysis_data:
            matrix = analysis_data["competitive_matrix"]
            f.write("COMPETITIVE MATRIX\n")
            f.write("-" * 40 + "\n")

            if matrix.get("differentiation_factors"):
                f.write("Differentiation Factors:\n")
                for factor in matrix["differentiation_factors"]:
                    f.write(f"  ◆ {factor}\n")

            if matrix.get("competitive_advantages"):
                f.write("\nCompetitive Advantages:\n")
                for advantage in matrix["competitive_advantages"]:
                    f.write(f"  ✓ {advantage}\n")

            if matrix.get("vulnerabilities"):
                f.write("\nVulnerabilities:\n")
                for vulnerability in matrix["vulnerabilities"]:
                    f.write(f"  ⚠ {vulnerability}\n")
            f.write("\n")

        if "gaps_and_opportunities" in analysis_data:
            f.write("GAPS & OPPORTUNITIES\n")
            f.write("-" * 40 + "\n")
            for item in analysis_data["gaps_and_opportunities"]:
                if isinstance(item, dict):
                    f.write(f"\n  Gap: {item.get('gap', 'N/A')}\n")
                    f.write(f"  Opportunity: {item.get('opportunity', 'N/A')}\n")
                    f.write(f"  Priority: {item.get('priority', 'N/A')}\n")
                    f.write(
                        f"  Difficulty: {item.get('implementation_difficulty', 'N/A')}\n"
                    )
                else:
                    f.write(f"  • {item}\n")
            f.write("\n")

        if "strategic_recommendations" in analysis_data:
            f.write("STRATEGIC RECOMMENDATIONS\n")
            f.write("-" * 40 + "\n")
            for idx, rec in enumerate(analysis_data["strategic_recommendations"], 1):
                if isinstance(rec, dict):
                    f.write(f"\n  {idx}. {rec.get('recommendation', 'N/A')}\n")
                    f.write(f"     Rationale: {rec.get('rationale', 'N/A')}\n")
                    f.write(f"     Impact: {rec.get('expected_impact', 'N/A')}\n")
                else:
                    f.write(f"  {idx}. {rec}\n")
            f.write("\n")

        if "positioning_statement" in analysis_data:
            f.write("POSITIONING STATEMENT\n")
            f.write("-" * 40 + "\n")
            f.write(f"{analysis_data['positioning_statement']}\n\n")

        f.write("=" * 70 + "\n")
        f.write("  End of Report\n")
        f.write("=" * 70 + "\n")

    print_step(f"Saved text report: {output_path}", "success")


def display_summary(analysis_data):
    print_section("ANALYSIS SUMMARY")

    if "market_overview" in analysis_data:
        overview = analysis_data["market_overview"]
        print(
            f"  {Colors.BOLD}Industry:{Colors.RESET} {overview.get('industry', 'N/A')}"
        )
        print(
            f"  {Colors.BOLD}Market Maturity:{Colors.RESET} {overview.get('market_maturity', 'N/A')}"
        )

    if "competitors" in analysis_data:
        valid_competitors = [
            c for c in analysis_data["competitors"] if isinstance(c, dict)
        ]
        print(
            f"\n  {Colors.BOLD}Competitors Analyzed:{Colors.RESET} {len(valid_competitors)}"
        )
        for comp in valid_competitors:
            threat = comp.get("threat_level", "unknown")
            if isinstance(threat, str):
                threat_color = (
                    Colors.RED
                    if "high" in threat.lower()
                    else Colors.YELLOW
                    if "medium" in threat.lower()
                    else Colors.GREEN
                )
            else:
                threat_color = Colors.YELLOW
                threat = "unknown"
            print(
                f"    • {comp.get('name', 'Unknown')} {threat_color}[{threat}]{Colors.RESET}"
            )

    if "gaps_and_opportunities" in analysis_data:
        print(
            f"\n  {Colors.BOLD}Opportunities Identified:{Colors.RESET} {len(analysis_data['gaps_and_opportunities'])}"
        )

    if "strategic_recommendations" in analysis_data:
        print(
            f"  {Colors.BOLD}Strategic Recommendations:{Colors.RESET} {len(analysis_data['strategic_recommendations'])}"
        )

    if "positioning_statement" in analysis_data:
        print(f"\n  {Colors.BOLD}{Colors.CYAN}Positioning:{Colors.RESET}")
        print(f'  {Colors.DIM}"{analysis_data["positioning_statement"]}"{Colors.RESET}')


def main():
    print_banner()

    print_section("INITIALIZATION")
    api_key = get_api_key()

    client = Groq(api_key=api_key)
    print_step("Groq client initialized", "success")

    analysis_context = read_analysis_input()

    analysis_data = run_competitive_analysis(client, analysis_context)

    print_section("GENERATING REPORTS")
    save_json_output(analysis_data)
    save_text_report(analysis_data)

    display_summary(analysis_data)

    print(f"\n{Colors.GREEN}{Colors.BOLD}  ✓ Analysis complete!{Colors.RESET}")
    print(
        f"  {Colors.DIM}Check competitive_analysis.json and competitive_analysis.txt{Colors.RESET}\n"
    )


if __name__ == "__main__":
    main()
