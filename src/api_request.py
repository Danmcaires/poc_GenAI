import sys

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from constants import CLIENT_ERROR_MSG
import requests
import os

class k8s_request():

    # def __init__(self):
    def __init__(self, user_query, key):
        # Necessary certificates
        self.ca_cert_path = os.path.abspath("/app/certs/ca.crt")
        self.client_cert_path = os.path.abspath("/app/certs/apiserver-kubelet-client.crt")
        self.client_key_path = os.path.abspath("/app/certs/apiserver-kubelet-client.key")

        # Namespaces to be ignored
        self.excluded_namespaces = ["armada", "cert-manager", "flux-helm", "kube-system"]

        # API key
        self.api_key = key

        # Necessary API address
        self.api_server_url = "https://192.168.206.1:6443"

        # User query
        self.query = user_query


    def get_endpoint(self):
        completion = self.get_api_completion()
        if completion[0] == "/":
            api_endpoint = f'{self.api_server_url}{completion}'
        elif completion == "-1":
            return completion
        else:
            api_endpoint = f'{self.api_server_url}/{completion}'

        return api_endpoint

    def get_api_completion(self):
        # Initiate OpenAI
        llm = ChatOpenAI(openai_api_key = self.api_key)

        # Expected llm response format
        format_response = "api: <api_completion>"

        # Create prompt
        prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are an API generator, based on the user input you will suggest the best API endpoint to retrieve the information from a kubernetes cluster.\n\nYou will only provide the API information that comes after the IP:PORT.\n\nMake sure the provided endpoint is a valid one.\n\nAlso make sure to only provide the API endpoint following the format: {format_response}. Guarantee that the format is followed."),
        ("user", "{input}")
        ])

        output_parser = StrOutputParser()
        chain = prompt | llm | output_parser

        # Get completion
        completion = chain.invoke({"input": self.query})
        if len(completion.split(":")) > 1:
            clean_completion = completion.split(":")[1].strip()
        else:
            clean_completion = "-1"

        return clean_completion

    def filter_response(self, response):
        pods = response.json().get('items', [])
        filtered_pods = [
            pod for pod in pods if pod['metadata']['namespace'] not in self.excluded_namespaces]

        return filtered_pods

    def get_API_response(self):
        # Define Kubernetes API endpoint
        api_endpoint = self.get_endpoint()
        if api_endpoint == "-1":
            return CLIENT_ERROR_MSG

        # Load Kubernetes certificates
        cert = (self.client_cert_path, self.client_key_path)
        verify = self.ca_cert_path

        # API request
        try:
            print(f'API address: {api_endpoint}', file=sys.stderr)
            response = requests.get(api_endpoint, cert=cert, verify=verify)
        except:
            return "An error ocurred while trying to retrieve the information, please rewrite the question and try again."

        if response.status_code == 200:
            # Filter response for undesired namespaces
            filtered_response = self.filter_response(response)
            buit_text_response = f"API {api_endpoint} response = {filtered_response}"
            return buit_text_response
        else:
            return f"Error trying to make API request:\n {response.status_code}, {response.text}"

    def summarize_response(self, response):
        llm = ChatOpenAI(openai_api_key = self.api_key)
        prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are a IA that transforms JSON objects into a plain text.\n\nYou will create a text summarizing all the information contained on the JSON that you will recieve as input from the user.\n\nMake sure that all the information in summarized into a human friendly text. Make sure to not create any information that is not contained in the JSON.\n\nYou may rename certain fields to be better readeble by a human."),
        ("user", "{input}")
        ])

        output_parser = StrOutputParser()
        chain = prompt | llm | output_parser

        # Get completion
        completion = chain.invoke({"input": response})

        return completion


class stx_request():

    def __init__(self, user_query, key):
        # Load env variables
        self.oam_ip = os.environ['OAM_IP']
        self.user = os.environ['STX_USER']
        self.password = os.environ['STX_PASSWORD']

        # Necessary token
        self.token = self.get_token()

        # API key
        self.api_key = key

        # Necessary API address
        self.api_server_url = f"http://{self.oam_ip}:"

        # User query
        self.query = user_query

        # Embedded list of StarlingX APIs
        self.apis = self.load_embedded_apis()


    def load_embedded_apis(self):
        with open ("Stx_apis.json", "r") as f:
            api_list = f.read()

        return api_list


    def get_endpoint(self):
        completion = self.get_api_completion()
        api = self.api_server_url + completion
        print(api)

        return api


    def get_api_completion(self):
        # Initiate OpenAI
        llm = ChatOpenAI(openai_api_key = self.api_key,
                         temperature=0.4)

        # Expected llm response format
        format_response = "api: <api_url>"

        # Create prompt
        prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are an API generator, based on the user question you will suggest the best API endpoint to retrieve the information from a StarlingX cluster.\n\nYou will look in the context for the available APIs in a StarlingX cluster.\n\nMake sure the provided endpoint is present on the provided context and check the action of the APIs to provide the ideal url for the user question.\n\nAlso make sure to only provide the API endpoint following the format: {format_response}. Guarantee that the format is followed."),
        ("user", "Context:{context} \n\n\n Question:{question}")
        ])

        output_parser = StrOutputParser()
        chain = prompt | llm | output_parser

        #Get completion
        completion = chain.invoke({"context":self.apis, "question": self.query})

        #completion = response.choices[0].message.content
        clean_completion = completion.split(":")[1].strip()

        return clean_completion


    def get_API_response(self):
        url = self.get_endpoint()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Auth-Token": self.token
        }


        try:
            print(f'API address: {url}', file=sys.stderr)
            response = requests.get(url, headers=headers)
        except:
            return "An error ocurred while trying to retrieve the information, please rewrite the question and try again."

        if response.status_code == 200:
            str_response = f"StarlingX API response = {response.text}"
            return str_response
        else:
            return f"Error trying to make API request:\n {response.status_code}, {response.text}"



    def get_token(self):
        url = f"http://{self.oam_ip}:5000/v3/auth/tokens"
        headers = {
            "Content-Type": "application/json"
        }
        data = {
            "auth": {
                "identity": {
                    "methods": ["password"],
                    "password": {
                        "user": {
                            "name": self.user,
                            "domain": {"id": "default"},
                            "password": self.password
                        }
                    }
                },
                "scope": {
                    "project": {
                        "name": "admin",
                        "domain": {"id": "default"}
                    }
                }
            }
        }

        try:
            response = requests.post(url, headers=headers, json=data)
        except:
            return "An error ocurred while trying to retrieve the authentication for the StarlingX APIs."

        if response.status_code == 201:
            # Get token from response
            x_auth_token = response.headers["x-subject-token"]

            return x_auth_token
        else:
            return f"Error trying to retrieve authentication token:\n {response.status_code}, {response.text}"




class openstack_request():
    pass
