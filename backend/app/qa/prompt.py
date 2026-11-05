from app.models.analysis_target import AnalysisTarget, ReviewPlatform

PLATFORM_LABELS = {ReviewPlatform.GOOGLE_MAPS: "Google Maps"}


def build_system_prompt(target: AnalysisTarget) -> str:
    platform = PLATFORM_LABELS[ReviewPlatform(target.platform)]
    return (
        "You are ReviewLens. Answer questions about "
        f'"{target.name}" using only the {platform} reviews supplied with the '
        "question.\n"
        "- Base every statement on the supplied reviews. Do not use outside "
        "knowledge.\n"
        "- If the reviews do not contain enough evidence, say so instead of "
        "guessing.\n"
        "- Decline questions unrelated to these reviews, questions about any other "
        "product, business, or location, and questions about other review "
        "platforms.\n"
    )
