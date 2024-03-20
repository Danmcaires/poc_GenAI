import logging

CLIENT_ERROR_MSG = "No Wind River/Kubernetes API capable of answering your question was found!\nPleasy try again with another prompt."

LOG = logging.getLogger("chatbot")

MODEL_NAMES = {
    'meta.llama2-13b-chat-v1': 'Llama 2 Chat 13B',
    'meta.llama2-70b-chat-v1': 'Llama 2 Chat 70B',
    'mistral.mistral-7b-instruct-v0:2': 'Mistral 7B Instruct',
    'mistral.mixtral-8x7b-instruct-v0:1': 'Mixtral 8X7B Instruct'
}