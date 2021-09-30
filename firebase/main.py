import logging
import logging.config
import os

from flask import Flask

from firebase import load_firebase_collections

logging.config.fileConfig(fname='logging.conf', disable_existing_loggers=False)

# Get the logger specified in the file
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route("/")
def run():

    logger.info("running firebase load job...")
    load_firebase_collections()

    return ("", 204)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
