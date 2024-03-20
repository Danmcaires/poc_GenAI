from flask import Flask, Response, request
from flask_restful import Api, Resource

import app as chat

app = Flask(__name__)
api = Api(app)


class Chat(Resource):
    def post(self):
        question = request.json['message']
        session_id = request.json['session_id']
        session = chat.get_session(session_id)
        if session is None:
            return Response("Session not found", status=404)

        answer = chat.ask(question, session)
        response = Response(answer, content_type="text/plain; charset=utf-8")
        return response


class Session(Resource):
    def get(self):
        session_temp = request.headers['temperature']
        session_model = request.headers['model']
        session = chat.new_session(session_model, session_temp)

        response = Response(session['id'], content_type="text/plain; charset=utf-8")
        return response


api.add_resource(Chat, '/chat')
api.add_resource(Session, '/session')


if __name__ == "__main__":
    chat.set_openai_key()
    chat.initiate_sessions()
    app.run(host="0.0.0.0", port=2000)
