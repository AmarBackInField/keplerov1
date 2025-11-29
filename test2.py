from flask import Flask, request

app = Flask(__name__)

@app.route("/sms", methods=["POST"])
def sms():
    print("From:", request.form.get("From"))
    print("Body:", request.form.get("Body"))
    return "ok"

app.run(port=5000)
