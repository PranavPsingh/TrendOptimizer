from django.shortcuts import render
from django.http import JsonResponse
from .trend_optimizer import run_optimizer
import tempfile, os


def optimize_post(request):
    if request.method == "POST":
        text = request.POST.get("text")

        # Save uploaded files (if any)
        uploaded_files = request.FILES.getlist("files")
        temp_paths = []

        try:
            for f in uploaded_files:
                with tempfile.NamedTemporaryFile(delete=False, suffix=f.name) as tmp:
                    for chunk in f.chunks():
                        tmp.write(chunk)
                    temp_paths.append(tmp.name)

            # Decide whether to analyze text or media
            if temp_paths:
                # Use the first uploaded file (your run_optimizer expects one file or dir)
                suggestions = run_optimizer(file_path=temp_paths[0], text=text)
            else:
                if not text:
                    return JsonResponse({"error": "Missing text or files"}, status=400)
                suggestions = run_optimizer(text=text)

            # Render template with results
            return render(
                request,
                "marketing/optimizer_form.html",
                {
                    "suggestions": suggestions,
                    "entered_text": text,
                },
            )

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

        finally:
            # Cleanup temp files
            for p in temp_paths:
                try:
                    os.remove(p)
                except OSError:
                    pass

    # GET → show empty form
    return render(request, "marketing/optimizer_form.html")
