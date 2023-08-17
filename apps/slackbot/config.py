"""
App configuration settings.

Usage:

    First define variables in runtime environment or in your `.env` file.
    Then, ...

    import Config as cfg
    secret = cfg.SLACK_SIGNING_SECRET
    another_variable = cfg.ANOTHER_ENVIRONMENT_VARIABLE
"""

import sys
import os
from os import environ
from dotenv import load_dotenv

load_dotenv()

SLACK_SIGNING_SECRET = environ.get('SLACK_SIGNING_SECRET')
SLACK_OAUTH_TOKEN = environ.get('SLACK_OAUTH_TOKEN')
SLACK_VERIFICATION_TOKEN = environ.get('SLACK_VERIFICATION_TOKEN')
SLACK_PORT = environ.get('SLACK_PORT', 3000)
OPENAI_KEY=environ.get('OPENAI_KEY')
PINECONE_API_KEY = environ.get('PINECONE_API_KEY')
PINECONE_NAMESPACE = environ.get('PINECONE_NAMESPACE', 'ReadTheDocs')
PINECONE_ENV = environ.get('PINECONE_ENV')
PINECONE_INDEX = environ.get('PINECONE_INDEX')


# `this` is a pointer to the module object instance itself.
this = sys.modules[__name__]


# Ensure all mandatory environment variables are set, otherwise exit
if None in [this.SLACK_VERIFICATION_TOKEN, this.SLACK_SIGNING_SECRET, this.SLACK_OAUTH_TOKEN, this.SLACK_PORT]:
    print('Config: Slack environment variables not set, unable to run')
    raise SystemExit(1)
else:
    print('Config: Slack environment variables are set')

if this.OPENAI_KEY is None:
    print('Config: OpenAI environment variables not set, unable to run')
    raise SystemExit(1)
else:
    print('Config: OpenAI environment variables are set')

# TODO verify we need OPENAI_API_KEY; can we just use OPENAI_KEY instead?
os.environ['OPENAI_API_KEY'] = this.OPENAI_KEY

if this.PINECONE_API_KEY is None:
    print('Config: Pinecone environment variables not set')
else:
    if None in [this.PINECONE_NAMESPACE, this.PINECONE_ENV, this.PINECONE_INDEX]:
        print('Config: Pinecone environment variables not set, unable to run')
        raise SystemExit(1)
    else:
        print('Config: Pinecone environment variables are set')
