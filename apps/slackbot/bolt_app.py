##############################################
#  Implementation of the slack app using Bolt     
#  Importing necessary modules
##############################################

import os
from os import environ
from dotenv import load_dotenv
from flask import Flask, request
from scrape.prompt_reconstructor import PromptReconstructor
from langchain.chat_models import ChatOpenAI
from vectorstores import ConversationStore, LocalChromaStore
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from tools import get_tools
from task_agent import TaskAgent


#####################################################################################################
# Load environment variables and instantiate Slack client:
#####################################################################################################
load_dotenv()

SLACK_SIGNING_SECRET = environ.get("SLACK_SIGNING_SECRET")
SLACK_OAUTH_TOKEN = environ.get("SLACK_OAUTH_TOKEN")
SLACK_VERIFICATION_TOKEN = environ.get("SLACK_VERIFICATION_TOKEN")
SLACK_PORT = environ.get("SLACK_PORT", 3000)

if None in [SLACK_VERIFICATION_TOKEN, SLACK_SIGNING_SECRET, SLACK_OAUTH_TOKEN, SLACK_PORT]:
  print("App init: Slack environment variables not set, app is unable to run")
  raise SystemExit(1)
else:
  print("App init: Slack environment variables are set")

# Instantiate the app
app = App(
    token=SLACK_OAUTH_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET,
)
bot = app.client.auth_test()
print("App init: bot auth_test results", bot)

OPENAI_KEY=environ.get("OPENAI_KEY")
if OPENAI_KEY is None:
  print("App init: OpenAI environment variables not set, app is unable to run")
  raise SystemExit(1)
else:
  print("App init: OpenAI environment variables are set")
  os.environ['OPENAI_API_KEY'] = OPENAI_KEY

PINECONE_API_KEY = environ.get("PINECONE_API_KEY")
if PINECONE_API_KEY is None:
  print("App init: Pinecone environment variables not set. Using local Chroma database instead.")
  print("App init: loading documents into Chroma:")
  local_memory = LocalChromaStore.from_folder('files', OPENAI_KEY).as_retriever()
else:
  print("App init: Pinecone environment variables are set")


###########################################################################
# Define Slack client functionality:
###########################################################################

@app.command("/hello-socket-mode")
def hello_command(ack, body):
    user_id = body["user_id"]
    ack(f"Hi, <@{user_id}>!")

def contains_verbose(query: str) -> bool:
    '''looks for -verbose in the question and returns True or False'''
    return "-verbose" in query.lower()

def contains_verbosex(query: str) -> bool:
    '''looks for -verbosex in the question and returns True or False'''
    return "-verbosex" in query.lower()

@app.event("app_mention")
def event_test(client, say, event):
    question = event['text']
    thread_ts = event.get("thread_ts", None) or event["ts"]
    replies = client.conversations_replies(channel=event['channel'], ts=thread_ts)
    previous_messages = replies['messages'][:-1]
    
    # used to reconstruct the question. if the question contains a link recreate
    # them so that they contain scraped and summerized content of the link
    reconstructor = PromptReconstructor(question=question, 
                                        slack_message=[replies['messages'][-1]])
    question = reconstructor.reconstruct_prompt()

    results, verbose_message = get_response(question, previous_messages)
    say(results, thread_ts=thread_ts)

    if contains_verbose(question):
        say(f"#verbose message: \n```{verbose_message}```", thread_ts=thread_ts)

@app.event("app_home_opened")
def update_home_tab(client, event, logger):
  try:
    # views.publish is the method that your app uses to push a view to the Home tab
    client.views_publish(
      # the user that opened your app's app home
      user_id=event["user"],
      # the view object that appears in the app home
      view={
        "type": "home",
        "callback_id": "home_view",

        # body of the view
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "*Welcome to your _App's Home_* :tada:"
            }
          },
          {
            "type": "divider"
          },
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "This button won't do much for now but you can set up a listener for it using the `actions()` method and passing its unique `action_id`. See an example in the `examples` folder within your Bolt app."
            }
          },
          {
            "type": "actions",
            "elements": [
              {
                "type": "button",
                "text": {
                  "type": "plain_text",
                  "text": "Click me!"
                }
              }
            ]
          }
        ]
      }
    )

  except Exception as e:
    logger.error(f"Error publishing home tab: {e}")


###########################################################################
# Setup Flask app:
###########################################################################

flask_app = Flask(__name__)
handler = SlackRequestHandler(app)

# Start the HTTP server 
if __name__ == "__main__":
    # documents = getDocuments('files')
    # vectorstore = getVectoreStore(documents)
    # qa = createLangchainQA(vectorstore)
    
    # chain = createIndex("files")
    print("App init: starting HTTP server on port {port}".format(port=SLACK_PORT))
    flask_app.run(host="0.0.0.0", port=SLACK_PORT)
    # SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

@flask_app.route("/hello", methods=["GET"])
def hello():
    return "OK"

# ---- add this for verbose output --- #

def log_formatter(logger):
    '''Formats the logger into readable string'''
    log_strings = []
    for log in logger:

        reply = log["reply"]
        if "thoughts" in reply:
            # reply = json.loads(reply)
            formatted_reply = f"""-- Step: {log["Step"]} -- \nThoughts: \n {reply["thoughts"]} """
            
            if "command" in reply: # add command if it exists
              formatted_reply += f"""\nCommand: \n {reply["command"]}"""
            
            log_strings.append(formatted_reply)

        else: # for final response
            formatted_reply = f"""-- Step: {log["Step"]} -- \nFinal Response: \n {reply}"""
            log_strings.append(formatted_reply)
    
    log_string =  "\n".join(log_strings)
    return log_string

def show_commands_only(logger):
    '''Modified version of log_formatter that only shows commands'''
    log_strings = []
    for log in logger:
        reply = log["reply"]
        if "command" in reply:
          # reply = json.loads(reply)
          formatted_reply = f"""-- Step: {log["Step"]} -- \nCommand: \n {reply["command"]}"""
          log_strings.append(formatted_reply)
        else: # for final response
          formatted_reply = f"""-- Step: {log["Step"]} -- \nFinal Response: \n {reply}"""
          log_strings.append(formatted_reply)
    log_string =  "\n".join(log_strings)
    return log_string

def get_response(question, previous_messages):
    llm = ChatOpenAI(
        openai_api_key=OPENAI_KEY, request_timeout=120
    )
    
    if PINECONE_API_KEY:
      # If pinecone API is specified, then use the Pinecone Database
      memory = ConversationStore.get_vector_retrieval(
        'ReadTheDocs', OPENAI_KEY, index_name=os.getenv("PINECONE_INDEX"), search_type='similarity_score_threshold', search_kwargs={'score_threshold': 0.0}
      )
    else:
      # use the local Chroma database
      memory = local_memory


    tools=get_tools(memory)
    ai_name='Sherpa'
    ai_id = bot['user_id']
    

    task_agent = TaskAgent.from_llm_and_tools(ai_name="Sherpa", 
                                              ai_role="assistant", 
                                              ai_id=bot['user_id'], 
                                              memory=memory, tools=tools, 
                                              previous_messages = previous_messages, 
                                              llm=llm)
    
    if contains_verbosex(query = question):
      print("Verbose mode is on, show all")
      question = question.replace(f'@{ai_id}', f'@{ai_name}')
      question = question.replace('-verbose', '')
      response = task_agent.run(question)
      logger = task_agent.logger # logger is updated after running task_agent.run(question)
      try:  # in case log_formatter fails
        verbose_message = log_formatter(logger)
      except:
        verbose_message = str(logger)
      return response, verbose_message
    
    elif contains_verbose(query = question):
      print("Verbose mode is on, commands only")
      question = question.replace(f'@{ai_id}', f'@{ai_name}')
      question = question.replace('-verbose', '')
      response = task_agent.run(question)
      logger = task_agent.logger # logger is updated after running task_agent.run(question)
      try:  # in case log_formatter fails
        verbose_message = show_commands_only(logger)
      except:
        verbose_message = str(logger)
      return response, verbose_message
    
    else:
      print("Verbose mode is off")
      question = question.replace(f'@{ai_id}', f'@{ai_name}')
      response = task_agent.run(question)
      return response, None
