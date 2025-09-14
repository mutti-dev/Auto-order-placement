from flask import Flask, request, jsonify
import asyncio
import json  # needed for JSONDecodeError handling

app = Flask(__name__)

@app.route("/start-orders", methods=["POST"])
def start_orders():
    try:
        # Apps Script sends a sheet ID, but the service‑account only has access to the
        # spreadsheet defined in order_processor.py.  Ignore the incoming ID unless you
        # have explicitly shared that sheet with the service‑account.
        payload = request.get_json(silent=True) or {}
        # sheet_id = payload.get("sheet")   # <-- keep commented if you do not share extra sheets
        sheet_id = None                     # force use of the default SPREADSHEET_ID
        import order_processor
        asyncio.run(order_processor.main(sheet_id))
        return jsonify({"status": "success", "message": "Orders processed"}), 200
    except json.JSONDecodeError:
        return jsonify({
            "status": "error",
            "message": "Invalid or missing Google service account credentials."
        }), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

