import structlog
from langgraph.graph import StateGraph, END
from app.types import AppState
from sqlalchemy.orm import Session
import asyncio
from langchain_core.runnables import Runnable

logger = structlog.get_logger()

class AsyncRunnable(Runnable):
    def __init__(self, async_func, name: str):
        self.async_func = async_func
        self.name = name

    def invoke(self, input, config=None):
        return asyncio.run(self.async_func(input, config))

    async def ainvoke(self, input, config=None):
        return await self.async_func(input, config)

def uploader_success_condition(state: AppState) -> str:
    resumes = state.get("resumes", [])
    if not resumes:
        logger.warning("Uploader failed: No resumes uploaded. Ending workflow.")
        return "end"
    logger.info("Transitioning from Uploader to Resume Parser")
    return "resume_parser"

def parser_success_condition(state: AppState) -> str:
    parsed_resumes = state.get("parsed_resumes", [])
    if not parsed_resumes:
        logger.warning("Parser failed: No resumes parsed. Ending workflow.")
        return "end"
    logger.info("Transitioning from Resume Parser to Classifier")
    return "classifier"

def classifier_success_condition(state: AppState) -> str:
    classified_candidates = state.get("classified_candidates", [])
    if not classified_candidates:
        logger.warning("Classifier failed: No candidates classified. Ending workflow.")
        return "end"
    logger.info("Transitioning from Classifier to Matcher")
    return "matcher"

def matcher_success_condition(state: AppState) -> str:
    matched_candidates = state.get("matched_candidates", [])
    if not matched_candidates:
        logger.warning("Matcher failed: No candidates matched. Ending workflow.")
        return "end"
    logger.info("Transitioning from Matcher to Scorer")
    return "scorer"

def scorer_success_condition(state: AppState) -> str:
    scored_resumes = state.get("scored_resumes", [])
    if not scored_resumes:
        logger.warning("Scorer failed: No resumes scored. Ending workflow.")
        return "end"
    logger.info("Transitioning from Scorer to Scheduler")
    return "scheduler"

async def run_workflow_with_visualization(state: AppState, llm: any, db: Session, config: dict = None) -> AppState:
    logger.info("Starting workflow execution...")
    # Remove detailed state logging
    # logger.info(f"Initial state: {state}")

    from app.agents import (
        uploader,
        resume_parser,
        classifier,
        matcher,
        scorer,
        scheduler,
    )

    workflow = StateGraph(AppState)

    workflow.add_node("uploader", AsyncRunnable(uploader, "uploader"))
    workflow.add_node("resume_parser", AsyncRunnable(resume_parser, "resume_parser"))
    workflow.add_node("classifier", AsyncRunnable(classifier, "classifier"))
    workflow.add_node("matcher", AsyncRunnable(matcher, "matcher"))
    workflow.add_node("scorer", AsyncRunnable(scorer, "scorer"))
    workflow.add_node("scheduler", AsyncRunnable(scheduler, "scheduler"))

    workflow.add_conditional_edges("uploader", uploader_success_condition, {"resume_parser": "resume_parser", "end": END})
    workflow.add_conditional_edges("resume_parser", parser_success_condition, {"classifier": "classifier", "end": END})
    workflow.add_conditional_edges("classifier", classifier_success_condition, {"matcher": "matcher", "end": END})
    workflow.add_conditional_edges("matcher", matcher_success_condition, {"scorer": "scorer", "end": END})
    workflow.add_conditional_edges("scorer", scorer_success_condition, {"scheduler": "scheduler", "end": END})
    workflow.add_edge("scheduler", END)

    workflow.set_entry_point("uploader")

    compiled_workflow = workflow.compile()

    state["llm"] = llm
    state["db"] = db

    final_state = await compiled_workflow.ainvoke(state, config=config)
    
    logger.info("Workflow execution complete")
    return final_state