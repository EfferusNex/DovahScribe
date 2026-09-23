from pathlib import Path

review_file = Path("data/review/Rafaela_review.json")
template_path = Path("web/cat_dashboard.html")
target_ui_path = Path("web/Rafaela_dashboard.html")

if review_file.exists() and template_path.exists():
    review_content = review_file.read_text(encoding="utf-8")
    template_content = template_path.read_text(encoding="utf-8")
    injected_html = template_content.replace(
        '<script id="preloaded-data" type="application/json"></script>',
        f'<script id="preloaded-data" type="application/json">\n{review_content}\n</script>'
    )
    target_ui_path.write_text(injected_html, encoding="utf-8")
    print("Updated web/Rafaela_dashboard.html successfully!")
