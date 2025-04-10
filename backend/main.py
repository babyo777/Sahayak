from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, auth
from mongoConfig import users_collection
from bson import ObjectId

app = Flask(__name__)
CORS(app)
cred = credentials.Certificate("firebase-admin-sdk.json")
firebase_admin.initialize_app(cred)

from functools import wraps


def verify_firebase_token(func):
    @wraps(func)  # ✅ preserves function name and metadata
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return (
                jsonify(
                    {
                        "error": "Unauthorized",
                        "details": "Missing or invalid Authorization header",
                    }
                ),
                401,
            )

        id_token = auth_header.split(" ")[1]

        try:
            decoded_token = auth.verify_id_token(id_token)
            request.user = decoded_token
            return func(*args, **kwargs)
        except Exception as e:
            return jsonify({"error": "Unauthorized", "details": str(e)}), 401

    return wrapper


@app.route("/store_user", methods=["POST"])
@verify_firebase_token
def store_user():
    try:
        # Get data from request body
        data = request.get_json()
        user_email = request.user["email"]
        user_uid = request.user["uid"]

        print(user_email, user_uid, data)
        # Store all data
        user_data = {
            "uid": user_uid,
            "email": user_email,
            **data,  # Spread all incoming data fields
        }

        # Save to database
        users_collection.update_one({"uid": user_uid}, {"$set": user_data}, upsert=True)

        return jsonify({"message": f"User data stored successfully."}), 200

    except KeyError as e:
        return jsonify({"error": "Missing required user data", "details": str(e)}), 400
    except ValueError as e:
        return jsonify({"error": "Invalid request data", "details": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@app.route("/get_user", methods=["POST"])
@verify_firebase_token
def get_user():
    try:
        user_uid = request.user["uid"]
        user_data = users_collection.find_one({"uid": user_uid})

        if not user_data:
            return jsonify({"error": "User not found"}), 404

        # Convert ObjectId to string
        user_data["_id"] = str(user_data["_id"])

        return jsonify(user_data), 200

    except KeyError as e:
        return jsonify({"error": "Missing required user data", "details": str(e)}), 400
    except ValueError as e:
        return jsonify({"error": "Invalid request data", "details": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
