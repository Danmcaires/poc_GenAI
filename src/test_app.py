import os

import boto3
from langchain_community.llms import Bedrock
from pytest import mark, param

import app
from api_request import k8s_request, wr_request
from constants import MODEL

K8S_QUERIES = {
    "How many pods I have in the default namespace?": "/api/v1/namespaces/default/pods",
    "What are my namespaces?": "/api/v1/namespaces",
    "Describe me pod copilot-adasas-asas3 on namespace copilot": "/api/v1/namespaces/copilot/pods/copilot-adasas-asas3",
    "What version os k8s am I running?": "/version",
}

WR_QUERIES = {
    "Are there any active alarms?": "18002/v1/alarms",
    "Give me information about active alarm asdas-12312312-ascas-ca": "18002/v1/alarms/asdas-12312312-ascas-ca",
    "List my subclouds": "8119/v1.0/subclouds",
    "What version is my system controller running?": "6385/v1/isystems",
    "Is the central cloud using any patches?": "15491/v1/query",
    "Are there any active alarms in subcloud-1?": "8119/v1.0/alarms",
}


def create_mock_session(model_id=MODEL, temperature=0):
    client = boto3.client(service_name='bedrock-runtime')
    llm = Bedrock(client=client, model_id=model_id, model_kwargs={"temperature": temperature})
    return {
        # "generator": generator,
        "llm": llm,
        # "id": session_id,
        # "k8s_bot": k8s_bot,
        # "wr_bot": wr_bot,
    }


@mark.parametrize(
    ("expected_answer", "queries"),
    [
        param("Kubernetes", K8S_QUERIES),
        param("Wind River", WR_QUERIES),
    ],
)
def test_define_api_pool(expected_answer, queries):
    session = create_mock_session()
    for query in queries:
        print(f"Testing app.py::define_api_pool with: {query}")
        for i in range(10):
            pool = app.define_api_pool(query, session)
            assert (
                pool == expected_answer
            ), f"API Pool definition failed for '{query}' query in attempt {i}. Expected: {expected_answer}, got: {pool}"


@mark.parametrize(
    ("api_request", "queries"),
    [
        param("k8s", K8S_QUERIES),
        param("wr", WR_QUERIES),
    ],
)
def test_api_completion(api_request, queries):
    session = create_mock_session()

    # Create api_request object
    if api_request == "k8s":
        api_request = k8s_request(session["llm"])
    else:
        api_request = wr_request(session["llm"])
        api_request.type = "System Controller"

    for query, expected_endpoint in queries.items():
        for i in range(10):
            api_request.query = query
            api_completion = api_request.get_api_completion()
            assert (
                api_completion == expected_endpoint
            ), f"API completion failed for '{query}' query in attempt {i}. Expected: {expected_endpoint}, got: {api_completion}"
