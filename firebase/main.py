import os

from flask import Flask

from firebase import load_firebase_collections

app = Flask(__name__)


@app.route("/")
def run():

    print("running firebase load job")
    load_firebase_collections()

    return ("", 204)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
