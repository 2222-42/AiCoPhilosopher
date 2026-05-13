import pytest


@pytest.fixture
def temp_workspace(tmp_path):
    return tmp_path


@pytest.fixture
def sample_project_state():
    return {
        "project_id": "test-proj-001",
        "title": "Test Project",
        "original_question": "What is consciousness?",
        "status": "created",
        "refined_goals": [],
        "workstreams": {},
        "living_document": "",
        "dialectical_history": [],
        "hypotheses": [],
        "conceptual_genealogy": {},
        "uncertainty_registry": [],
        "artifacts": [],
    }
