import logging

CLIENT_ERROR_MSG = "No Wind River/Kubernetes API capable of answering your question was found!\nPleasy try again with another prompt."  # noqa: E501

LOG = logging.getLogger("chatbot")

MODEL = 'meta.llama2-70b-chat-v1'

LLAMA_PROMPT_END = "Do not acknowledge my request with 'sure' or in any other way besides going straight to the answer. Do not respond with anything more than the answer. Guarantee that the format is followed."  # noqa: E501
