
from firebase_admin import messaging


async def verify_fcm_token(token: str):
    message = messaging.Message(
        token=token,
    )
    try:
        # dry_run=True validates the message/token without sending
        messaging.send(message, dry_run=True)
        return True
    except messaging.UnregisteredError:
        # Token is no longer valid (app uninstalled, etc.)
        print("Token is unregistered")
        return False
    except messaging.SenderIdMismatchError:
        # Token belongs to a different Firebase project
        print("Token project mismatch")
        return False
    except Exception as e:
        print(f"Validation failed: {e}")
        return False
