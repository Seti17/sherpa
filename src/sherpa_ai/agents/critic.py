from typing import List, Optional

from langchain_core.language_models import BaseChatModel
from loguru import logger

from sherpa_ai.prompts.prompt_template import PromptTemplate
from sherpa_ai.agents.base import BaseAgent
from sherpa_ai.events import EventType
from sherpa_ai.memory import Belief, SharedMemory
from sherpa_ai.verbose_loggers.verbose_loggers import DummyVerboseLogger

template = PromptTemplate("./sherpa_ai/prompts/prompts.json")
description_prompt =  template.format_prompt(
            wrapper="critic_prompts",
            name="DESCRIPTION_PROMPT",
            version="1.0",
        )

class Critic(BaseAgent):
    """
    The critic agent receives a plan from the planner and evaluate the plan based on
    some pre-defined metrics. At the same time, it gives the feedback to the planner.
    """

    name: str = "Critic"
    description: str = description_prompt
    ratio: float = 0.9
    num_feedback: int = 3

    def get_importance_evaluation(self, task: str, plan: str):
        # return score in int and evaluation in string for importance matrix
        variables = {
            "task": task,
            "plan": plan,
        }
        prompt = template.format_prompt(
            wrapper="critic_prompts",
            name="IMPORTANCE_PROMPT",
            version="1.0",
            variables=variables,
        )
        output = self.llm.predict(prompt)
        score = int(output.split("Score:")[1].split("Evaluation")[0])
        evaluation = output.split("Evaluation: ")[1]
        return score, evaluation

    def get_detail_evaluation(self, task: str, plan: str):
        # return score in int and evaluation in string for detail matrix
        variables = {
            "task": task,
            "plan": plan,
        }
        prompt = template.format_prompt(
            wrapper="critic_prompts",
            name="DETAIL_PROMPT",
            version="1.0",
            variables=variables,
        )
        output = self.llm.predict(prompt)
        score = int(output.split("Score:")[1].split("Evaluation")[0])
        evaluation = output.split("Evaluation: ")[1]
        return score, evaluation

    def get_insight(self):
        # return a list of string: top 5 important insight given the belief and memory
        # (observation)
        variables = {
            "observation": self.observe(self.belief)
        }
        prompt = template.format_prompt(
            wrapper="critic_prompts",
            name="INSIGHT_PROMPT",
            version="1.0",
            variables=variables,
        )
        result = self.llm.predict(prompt)
        insights = [i for i in result.split("\n") if len(i.strip()) > 0][:5]
        return insights

    def post_process(self, feedback: str):
        return [i for i in feedback.split("\n") if i]

    def get_feedback(self, task: str, plan: str) -> List[str]:
        # observation = self.observe(self.belief)
        i_score, i_evaluation = self.get_importance_evaluation(task, plan)
        d_score, d_evaluation = self.get_detail_evaluation(task, plan)
        # approve or not, check score/ ratio
        # insights = self.get_insight()

        logger.info(f"i_score: {i_score}, d_score: {d_score}")

        if i_score < 10 * self.ratio or d_score < 10 * self.ratio:
            variables = {
                "task": task,
                "i_evaluation": i_evaluation,
                "d_evaluation": d_evaluation,
                "num_feedback": self.num_feedback

            }
            prompt = template.format_prompt(
                wrapper="critic_prompts",
                name="FEEDBACK_PROMPT",
                version="1.0",
                variables=variables,
            )
            feedback = self.llm.predict(self.description + prompt)

            self.shared_memory.add(EventType.feedback, self.name, feedback)
            logger.info(f"feedback: {feedback}")

            return self.post_process(feedback)
        else:
            return ""

    def create_actions(self):
        pass

    def synthesize_output(self) -> str:
        pass
