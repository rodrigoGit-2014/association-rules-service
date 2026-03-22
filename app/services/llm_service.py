"""LLM service for generating natural language explanations of association rules"""

import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.association_rule_repository import AssociationRuleRepository
from app.schemas.association import RuleExplanation

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """Eres un analista de retail experto. Para cada regla de asociación, genera una explicación breve (1-2 frases) en español que un gerente de tienda pueda entender sin conocimientos técnicos.

Formato de salida: una línea por regla, con el formato "REGLA_ID|explicación"

Reglas:
{rules_text}

Ejemplo de explicación:
"Los clientes que compran Cerveza tienen 3.2x más probabilidad de también comprar Papas Fritas. Esta combinación aparece en el 8% de los pedidos."

Genera las explicaciones ahora, una por línea con formato REGLA_ID|explicación:"""


class LLMService:
    """Generates natural language explanations for association rules"""

    def __init__(self, db: Session):
        self.db = db
        self.rule_repo = AssociationRuleRepository(db)

    def explain_rules(
        self,
        run_id: UUID,
        rule_ids: Optional[List[int]] = None,
        top_n: int = 10
    ) -> List[RuleExplanation]:
        """Generate LLM explanations for rules, using cache when available"""

        # Get rules to explain
        if rule_ids:
            rules = self.rule_repo.get_rules_by_ids(rule_ids)
        else:
            rules = self.rule_repo.get_top_rules(run_id, limit=top_n)

        if not rules:
            return []

        # Separate cached vs uncached
        cached = []
        uncached = []

        for rule in rules:
            if rule.llm_explanation:
                cached.append(RuleExplanation(
                    rule_id=rule.id,
                    antecedent=rule.antecedent_label,
                    consequent=rule.consequent_label,
                    lift=float(rule.lift),
                    explanation=rule.llm_explanation
                ))
            else:
                uncached.append(rule)

        # Generate explanations for uncached rules
        if uncached:
            new_explanations = self._generate_explanations(uncached)
            cached.extend(new_explanations)

            # Persist to DB for caching
            explanations_map = {e.rule_id: e.explanation for e in new_explanations}
            self.rule_repo.update_explanations(explanations_map)

        return cached

    def _generate_explanations(self, rules) -> List[RuleExplanation]:
        """Call LLM API to generate explanations"""
        results = []

        # Process in batches
        batch_size = settings.LLM_MAX_BATCH_SIZE
        for i in range(0, len(rules), batch_size):
            batch = rules[i:i + batch_size]
            batch_results = self._call_llm(batch)
            results.extend(batch_results)

        return results

    def _call_llm(self, rules) -> List[RuleExplanation]:
        """Make the actual LLM API call"""

        # Build rules text for prompt
        rules_text = ""
        for rule in rules:
            rules_text += (
                f"ID:{rule.id} | {rule.antecedent_label} → {rule.consequent_label} | "
                f"Soporte: {float(rule.support)*100:.1f}%, "
                f"Confianza: {float(rule.confidence)*100:.1f}%, "
                f"Lift: {float(rule.lift):.1f}\n"
            )

        prompt = PROMPT_TEMPLATE.format(rules_text=rules_text)

        try:
            response_text = self._invoke_provider(prompt)
            return self._parse_response(response_text, rules)
        except Exception as e:
            logger.error(f"LLM API call failed: {e}", exc_info=True)
            # Fallback: generate template-based explanations
            return self._generate_fallback(rules)

    def _invoke_provider(self, prompt: str) -> str:
        """Invoke the configured LLM provider"""

        if settings.LLM_PROVIDER == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=settings.LLM_API_KEY)
            message = client.messages.create(
                model=settings.LLM_MODEL,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text

        elif settings.LLM_PROVIDER == "openai":
            import openai
            client = openai.OpenAI(api_key=settings.LLM_API_KEY)
            response = client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000
            )
            return response.choices[0].message.content

        else:
            raise ValueError(f"Unsupported LLM provider: {settings.LLM_PROVIDER}")

    def _parse_response(self, response_text: str, rules) -> List[RuleExplanation]:
        """Parse LLM response into RuleExplanation objects"""
        rules_by_id = {rule.id: rule for rule in rules}
        results = []

        for line in response_text.strip().split("\n"):
            line = line.strip()
            if not line or "|" not in line:
                continue

            parts = line.split("|", 1)
            try:
                rule_id = int(parts[0].strip())
                explanation = parts[1].strip().strip('"')

                if rule_id in rules_by_id:
                    rule = rules_by_id[rule_id]
                    results.append(RuleExplanation(
                        rule_id=rule_id,
                        antecedent=rule.antecedent_label,
                        consequent=rule.consequent_label,
                        lift=float(rule.lift),
                        explanation=explanation
                    ))
            except (ValueError, IndexError):
                continue

        # Fill in any missing rules with fallback
        found_ids = {r.rule_id for r in results}
        for rule in rules:
            if rule.id not in found_ids:
                results.append(self._make_fallback(rule))

        return results

    def _generate_fallback(self, rules) -> List[RuleExplanation]:
        """Generate template-based explanations when LLM fails"""
        return [self._make_fallback(rule) for rule in rules]

    def _make_fallback(self, rule) -> RuleExplanation:
        """Create a single template-based explanation"""
        lift = float(rule.lift)
        confidence = float(rule.confidence) * 100
        support = float(rule.support) * 100

        explanation = (
            f"Los clientes que compran {rule.antecedent_label} tienen "
            f"{lift:.1f}x más probabilidad de también comprar {rule.consequent_label} "
            f"(confianza del {confidence:.0f}%, presente en {support:.1f}% de los pedidos)."
        )

        return RuleExplanation(
            rule_id=rule.id,
            antecedent=rule.antecedent_label,
            consequent=rule.consequent_label,
            lift=lift,
            explanation=explanation
        )
