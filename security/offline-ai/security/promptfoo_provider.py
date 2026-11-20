from security.mock_agent import respond

def call_api(prompt, options=None, context=None):
    return {"output": respond(prompt)}
