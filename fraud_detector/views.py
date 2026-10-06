from django.shortcuts import render, redirect
from django.http import JsonResponse
from crypto_fraud_tracker.main import run
import threading


# Stores analysis status temporarily
analysis_status = {}


def run_analysis(wallet, session_key):
    try:
        analysis_status[session_key] = {
            "status": "running",
            "message": "Fetching blockchain transactions..."
        }

        result = run(wallet, 3)

        if result == 0:
            analysis_status[session_key] = {
                "status": "completed",
                "message": "Transactions extracted successfully."
            }
        else:
            analysis_status[session_key] = {
                "status": "failed",
                "message": "Failed to extract transactions."
            }

    except Exception as e:
        analysis_status[session_key] = {
            "status": "failed",
            "message": str(e)
        }




def home(request):
    wallet = ""
    message = ""

    if request.method == "POST":
        wallet = request.POST.get("wallet", "").strip()

        if wallet:
            request.session["wallet"] = wallet

            return redirect("loading")

        message = "Please enter a wallet address."

    return render(request, "index.html", {
        "wallet": wallet,
        "message": message,
    })


def loading(request):
    wallet = request.session.get("wallet")

    if not wallet:
        return redirect("home")

    session_key = request.session.session_key

    # Start analysis only once
    if session_key not in analysis_status:
        analysis_status[session_key] = {
            "status": "starting",
            "message": "Starting analysis..."
        }

        thread = threading.Thread(
            target=run_analysis,
            args=(wallet, session_key)
        )

        thread.start()

    return render(request, "loading.html")


def analysis_status_view(request):
    session_key = request.session.session_key

    status = analysis_status.get(
        session_key,
        {
            "status": "unknown",
            "message": "Analysis not found."
        }
    )

    return JsonResponse(status)


def results(request):
    session_key = request.session.session_key

    status = analysis_status.get(session_key)

    if not status or status["status"] != "completed":
        return redirect("loading")

    wallet = request.session.get("wallet")

    return render(request, "results.html", {
        "wallet": wallet,
        "message": status["message"],
    })