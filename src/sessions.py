from collections import OrderedDict
import time

class SessionManager(OrderedDict):
    def __init__(self, session_buffer_limit=20):
        self.session_buffer_limit = session_buffer_limit
        self.last_session_clear = time.time()
    
    def clear_older_sessions(self):
        while (
            len(self) > 0 and
            len(self) > self.session_buffer_limit and
            time.time() - self.last_session_clear > 600
        ):
            self.popitem(last=False)
            self.last_session_clear = time.time()