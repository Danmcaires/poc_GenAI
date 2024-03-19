# Simple To-Do
1. Fix Authentication and Adapt from OpenAI Auth to AWS Bedrock Auth (not working)

## AWS Credentials
Store your credentials in a file on `~/.aws/crendetials.txt`

Example of `credentials.txt`. Please note that the credentials profile name,
here **windriver-poc-user** must be the same, as the temporary auth method chose.
```
[windriver-poc-user]
AWS_ACCESS_KEY_ID=X
AWS_SECRET_ACCESS_KEY=X
AWS_DEFAULT_REGION=us-east-1
```

## Useful documenation links
https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html
https://python.langchain.com/docs/integrations/platforms/aws
https://python.langchain.com/docs/integrations/llms/bedrock
https://api.python.langchain.com/en/latest/llms/langchain_community.llms.bedrock.Bedrock.html
https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html
