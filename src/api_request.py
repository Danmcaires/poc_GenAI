from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from constants import LOG
from sdk.sdk import OpenstackSdk
import re
import sys


class openstack_request():

    def __init__(self, key):

        # API key
        self.api_key = key

        # List of OpenStack functions
        self.apis = self.load_openstack_functions()

        # Load Openstack SDK
        self.openstack_sdk = OpenstackSdk()

        # Load enabled Openstack services in the cluster
        self.enabled_openstack_services = self.openstack_sdk.enabled_services


    def load_openstack_functions(self):
        with open ("os_functions.json", "r") as f:
            function_list = f.read()

        return function_list


    def get_path(self,):
        completion = self.get_path_completion(self.query)
        if completion[-1] == ")":
            path = "self.openstack_sdk." + completion
        else:
            path = "self.openstack_sdk." + completion + "()"

        return path


    def get_path_completion(self):
        # Initiate OpenAI
        llm = ChatOpenAI(openai_api_key = self.api_key,
                         model_name="gpt-4-turbo-preview",
                         temperature=0.4)

        # Expected llm response format
        format_response = "path: <function_path>"

        # Create prompt
        prompt = ChatPromptTemplate.from_messages([
        ("system", f"As a function path generator, your role is to suggest the most suitable function path for retrieving information from an OpenStack platform based on the user's question.\n\nYou'll need to analyze the context to identify available functions within the platform.\n\nIt's important to note that sometimes the user query will lead to a function that has an attribute associated with it. This attribute value will typically be implied within the user query rather than explicitly stated. In such cases, the suggested path should include the attribute value enclosed in quotes inside parentheses after the function path, like so: path('value'). Additionally, ensure that the function path in the answer is never 'path'. \n\nBefore providing a recommendation, ensure that the recommended function is indeed present in the provided context and analyze its action to determine the best path for addressing the user's query.\n\nWhen offering suggestions, only provide the API endpoint in the following format: {format_response}. Consistently maintain this format. Remember to review the entire context thoroughly before providing an answer."),
        ("user", "Context:{context} \n\n\n Question:{question}")
        ])

        output_parser = StrOutputParser()
        chain = prompt | llm | output_parser

        #Get completion
        completion = chain.invoke({"context":self.apis, "question": self.query})

        #completion = response.choices[0].message.content
        clean_completion = completion.split(":")[1].strip()

        return clean_completion


    def get_API_response(self, query):
        self.query = query
        path = self.get_path()
        LOG.info(f"running '{path}' function")

        try:
            service = re.findall(r'[A-Z][A-Z\d]+', path)[0]
            if service.lower() in self.enabled_openstack_services:
                try:
                    response = eval(path)
                except:
                    msg = f"Error trying to execute {path} function. No information was retrieved"
                    LOG.warn(msg)
                    return msg

                str_response = f"OpenStack {service} API response = {response}"
                LOG.info("API response successfully retrieved.")
                return str_response

            msg = f"Service {service} is not available in this cluster"
            LOG.warn(msg)
            return msg
        except Exception as e:
            error = f"An error ocurred while trying to retrieve the information, please rewrite the question and try again.\n Error: {e}"
            LOG.warning(error)
            return error
