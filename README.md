# Popl Google Cloud Functions

This project contains Google Cloud functions that are managed and deployed by the [Serverless Framework](https://www.serverless.com/framework/docs/) and triggered by Fivetran.

- Docs for setting up the [serverless.yml](serverless.yml) with Google Cloud as the provider can be found [here](https://www.serverless.com/framework/docs/providers/google/guide/credentials)

- Docs for setting up Fivetran trigger can be found [here](https://fivetran.com/docs/functions/google-cloud-functions/setup-guide)

## Environement Variables

This project looks for a `.env` file containing environment variables and uses the `serverless-dotenv-plugin` plugin to load the values from this file when deploying the project. All the variables in this file will be made available as environment variables to all the cloud functions deployed.

# Setup and Deploying

Before running the deploy command, you will need to install two required plugins by running the following commands:

```bash
# Install google cloud functions plugin
sls plugin install -n serverless-google-cloudfunctions

# Install dotenv loader plugin
npm i -D serverless-dotenv-plugin
```

Finally, when ready to deploy run:

```bash
serverless deploy
```
