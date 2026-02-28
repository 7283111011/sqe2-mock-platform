"""
SQE2 Mock Practice Platform Prototype

This Python module provides a simple web application that simulates a
practice environment for candidates preparing for the Solicitors
Qualifying Examination 2 (SQE2).  It uses the Flask web framework to
deliver several assessment exercises reflecting the written elements
described in the official specification.  Each exercise accepts
candidate input and produces feedback based on a set of criteria
derived from the Solicitors Regulation Authority (SRA) assessment
criteria.  Because this is a demonstration, the assessment logic
uses heuristic scoring rather than a machine‑learning model.  The
module also contains an example of how to integrate text‑to‑speech and
speech recognition for the interview assessment.

Important: this prototype is intended for educational purposes and
illustrates how one might structure a training platform.  It should
not be used as an official marking tool nor relied upon for
definitive feedback.  For production use, developers would need to
integrate robust natural language processing services and ensure
appropriate security and privacy measures.
"""

from flask import Flask, render_template, request
from typing import Dict, Any, Tuple

# Optional imports for speech recognition and text to speech.
# These libraries are not required for the core functionality and
# should be installed only if audio functionality is desired.
try:
    import speech_recognition as sr  # type: ignore
    from gtts import gTTS  # type: ignore
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False


app = Flask(__name__)


######################################################################
# Templates
#
# To keep this example self contained, HTML templates are defined as
# strings.  In a larger project these would be placed in separate
# template files.  The templates use very basic Bootstrap styling for
# readability.
######################################################################

BASE_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ title }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  </head>
  <body>
    <div class="container mt-4">
      <h1>{{ title }}</h1>
      {% block content %}{% endblock %}
    </div>
  </body>
</html>
"""


HOME_TEMPLATE = """
{% extends base %}
{% block content %}
<p>This mock platform provides practice exercises for the written
components of SQE2: case and matter analysis, legal research, legal
writing and legal drafting.  Each exercise mirrors the structure
described by the Solicitors Regulation Authority.  Candidates can
select an exercise below and receive feedback based on the published
assessment criteria.</p>

<ul class="list-group">
  <li class="list-group-item"><a href="{{ url_for('exercise', name='case') }}">Case and matter analysis</a></li>
  <li class="list-group-item"><a href="{{ url_for('exercise', name='research') }}">Legal research</a></li>
  <li class="list-group-item"><a href="{{ url_for('exercise', name='writing') }}">Legal writing</a></li>
  <li class="list-group-item"><a href="{{ url_for('exercise', name='drafting') }}">Legal drafting</a></li>
  <li class="list-group-item"><a href="{{ url_for('interview') }}">Interview and attendance note (audio demo)</a></li>
</ul>
{% endblock %}
"""


EXERCISE_TEMPLATE = """
{% extends base %}
{% block content %}
<p>{{ description }}</p>

<form method="post">
  <div class="mb-3">
    <label for="response" class="form-label">Your response</label>
    <textarea class="form-control" id="response" name="response" rows="10" required></textarea>
  </div>
  <button type="submit" class="btn btn-primary">Submit for feedback</button>
</form>

{% if feedback %}
<hr>
<h3>Feedback</h3>
<p>The following scores are provided against the published criteria.  A score
of 5 corresponds to superior performance, 3 corresponds to a clear
pass and 0 indicates a poor attempt.</p>
<ul>
  {% for criterion, score in feedback.items() %}
    <li><strong>{{ criterion }}</strong>: {{ score }}</li>
  {% endfor %}
</ul>
{% endif %}
{% endblock %}
"""


INTERVIEW_TEMPLATE = """
{% extends base %}
{% block content %}
<p>This demonstration shows how a candidate might perform an interview
exercise with audio input.  In the actual SQE2 assessment the
candidate would have ten minutes to read an instruction email and
documents, followed by a twenty‑five minute conversation with a
client.  Here we simulate this interaction with simple audio
recording.</p>

{% if not audio_available %}
  <p><em>Speech recognition and text‑to‑speech libraries are not installed.
  Please install the <code>speech_recognition</code> and <code>gtts</code>
  packages to enable audio functionality.</em></p>
{% else %}
  {% if not transcript %}
    <p>When ready, press the start button below to record your
    response.  The application will stop recording after one minute.
    It will then display the transcription and you can review it
    against the assessment criteria.</p>
    <form method="post" enctype="multipart/form-data">
      <button type="submit" class="btn btn-primary">Start Recording</button>
    </form>
  {% else %}
    <h3>Transcript</h3>
    <pre>{{ transcript }}</pre>
    <p>The transcript above shows what you said.  Use the assessment
    criteria from the specification to evaluate your performance.</p>
  {% endif %}
{% endif %}
{% endblock %}
"""


######################################################################
# Evaluation functions
#
# Each exercise uses a simple heuristic to assign scores for the
# published criteria.  In production a machine‑learning model such as
# a large language model could analyse the response and generate
# marks.  For demonstration purposes the functions below look for
# indicative keywords and count sentence structure.  Scores are
# returned on a five‑point scale.
######################################################################


def evaluate_case_analysis(response: str) -> Dict[str, int]:
    """Score a case and matter analysis response.

    Criteria:
      - Identify relevant facts
      - Provide client‑focused advice
      - Use clear, precise and concise language
      - Apply the law correctly
      - Apply the law comprehensively, including ethics
    """
    response_lower = response.lower()
    scores: Dict[str, int] = {}

    # Identify relevant facts: count distinct factual terms
    fact_keywords = ["fact", "evidence", "issue", "event", "document"]
    facts_found = sum(1 for k in fact_keywords if k in response_lower)
    scores["Identify relevant facts"] = min(facts_found, 5)

    # Client‑focused advice: look for words like client, advise, objective
    client_keywords = ["client", "advise", "objective", "goal", "outcome"]
    client_found = sum(1 for k in client_keywords if k in response_lower)
    scores["Provide client‑focused advice"] = min(client_found, 5)

    # Clear, precise language: estimate by average sentence length
    sentences = [s.strip() for s in response.split('.') if s.strip()]
    if sentences:
        avg_len = sum(len(s.split()) for s in sentences) / len(sentences)
        # shorter sentences tend to be clearer.  Score inversely
        if avg_len < 15:
            lang_score = 5
        elif avg_len < 25:
            lang_score = 4
        elif avg_len < 35:
            lang_score = 3
        elif avg_len < 50:
            lang_score = 2
        else:
            lang_score = 1
    else:
        lang_score = 0
    scores["Use clear, precise and concise language"] = lang_score

    # Apply the law correctly: look for legal terminology such as statute, case law
    law_keywords = ["law", "statute", "section", "act", "case"]
    law_found = sum(1 for k in law_keywords if k in response_lower)
    scores["Apply the law correctly"] = min(law_found, 5)

    # Comprehensive application and ethics: look for references to ethics or professional conduct
    ethics_keywords = ["ethic", "professional", "duty", "integrity", "compliance"]
    ethics_found = sum(1 for k in ethics_keywords if k in response_lower)
    scores["Apply the law comprehensively including ethics"] = min(ethics_found, 5)

    return scores


def evaluate_research(response: str) -> Dict[str, int]:
    """Score a legal research response.

    Criteria:
      - Identify and use relevant sources
      - Provide client‑focused advice addressing the problem
      - Use clear, precise, concise language
      - Apply the law correctly
      - Apply the law comprehensively including ethics
    """
    response_lower = response.lower()
    scores: Dict[str, int] = {}

    # Relevant sources: detect citation markers or mentions of cases/statutes
    source_keywords = ["[", "case", "section", "article", "regulation"]
    sources_found = sum(1 for k in source_keywords if k in response)
    scores["Identify and use relevant sources"] = min(sources_found, 5)

    # Client‑focused advice: as above
    client_keywords = ["client", "advise", "objective", "goal", "outcome"]
    client_found = sum(1 for k in client_keywords if k in response_lower)
    scores["Provide client‑focused advice"] = min(client_found, 5)

    # Language clarity
    sentences = [s.strip() for s in response.split('.') if s.strip()]
    if sentences:
        avg_len = sum(len(s.split()) for s in sentences) / len(sentences)
        if avg_len < 15:
            lang_score = 5
        elif avg_len < 25:
            lang_score = 4
        elif avg_len < 35:
            lang_score = 3
        elif avg_len < 50:
            lang_score = 2
        else:
            lang_score = 1
    else:
        lang_score = 0
    scores["Use clear, precise and concise language"] = lang_score

    # Law application
    law_keywords = ["law", "statute", "section", "act", "case"]
    law_found = sum(1 for k in law_keywords if k in response_lower)
    scores["Apply the law correctly"] = min(law_found, 5)

    # Comprehensive application and ethics
    ethics_keywords = ["ethic", "professional", "duty", "integrity", "compliance"]
    ethics_found = sum(1 for k in ethics_keywords if k in response_lower)
    scores["Apply the law comprehensively including ethics"] = min(ethics_found, 5)

    return scores


def evaluate_writing(response: str) -> Dict[str, int]:
    """Score a legal writing response.

    Criteria:
      - Include relevant facts
      - Use a logical structure
      - Advice/content is client and recipient focused
      - Clear, precise, concise and appropriate language
      - Apply the law correctly and comprehensively
    """
    response_lower = response.lower()
    scores: Dict[str, int] = {}

    # Relevant facts
    fact_keywords = ["fact", "issue", "point", "detail", "evidence"]
    facts_found = sum(1 for k in fact_keywords if k in response_lower)
    scores["Include relevant facts"] = min(facts_found, 5)

    # Logical structure: we estimate by number of paragraphs with headings
    paragraphs = [p for p in response.split('\n') if p.strip()]
    if len(paragraphs) >= 3:
        struct_score = 5
    elif len(paragraphs) == 2:
        struct_score = 3
    else:
        struct_score = 2
    scores["Use a logical structure"] = struct_score

    # Client and recipient focus
    client_keywords = ["client", "you", "your", "recipient", "party"]
    client_found = sum(1 for k in client_keywords if k in response_lower)
    scores["Advice is client and recipient focused"] = min(client_found, 5)

    # Language clarity: similar to other functions
    sentences = [s.strip() for s in response.split('.') if s.strip()]
    if sentences:
        avg_len = sum(len(s.split()) for s in sentences) / len(sentences)
        if avg_len < 15:
            lang_score = 5
        elif avg_len < 25:
            lang_score = 4
        elif avg_len < 35:
            lang_score = 3
        elif avg_len < 50:
            lang_score = 2
        else:
            lang_score = 1
    else:
        lang_score = 0
    scores["Use clear, precise, concise and appropriate language"] = lang_score

    # Law application
    law_keywords = ["law", "statute", "section", "act", "case"]
    law_found = sum(1 for k in law_keywords if k in response_lower)
    ethics_keywords = ["ethic", "professional", "duty", "integrity", "compliance"]
    ethics_found = sum(1 for k in ethics_keywords if k in response_lower)
    scores["Apply the law correctly and comprehensively"] = min(law_found + ethics_found, 5)

    return scores


def evaluate_drafting(response: str) -> Dict[str, int]:
    """Score a legal drafting response.

    Criteria:
      - Use clear, precise, concise and acceptable language
      - Structure the document appropriately and logically
      - Draft a document which is legally correct
      - Draft a document which is legally comprehensive including ethics
    """
    response_lower = response.lower()
    scores: Dict[str, int] = {}

    # Language clarity
    sentences = [s.strip() for s in response.split('.') if s.strip()]
    if sentences:
        avg_len = sum(len(s.split()) for s in sentences) / len(sentences)
        if avg_len < 15:
            lang_score = 5
        elif avg_len < 25:
            lang_score = 4
        elif avg_len < 35:
            lang_score = 3
        elif avg_len < 50:
            lang_score = 2
        else:
            lang_score = 1
    else:
        lang_score = 0
    scores["Clear, precise and concise language"] = lang_score

    # Document structure: measure number of sections (e.g. paragraphs separated by blank lines)
    paragraphs = [p for p in response.split('\n') if p.strip()]
    if len(paragraphs) >= 3:
        struct_score = 5
    elif len(paragraphs) == 2:
        struct_score = 3
    else:
        struct_score = 2
    scores["Appropriate and logical structure"] = struct_score

    # Legal correctness: presence of standard drafting terminology ("shall", "must", "party")
    drafting_keywords = ["shall", "must", "party", "agreement", "clause", "section"]
    legal_found = sum(1 for k in drafting_keywords if k in response_lower)
    scores["Legally correct document"] = min(legal_found, 5)

    # Legal comprehensiveness and ethics: presence of warranty, indemnity, liability, ethics
    ethics_keywords = ["warranty", "indemnity", "liability", "ethic", "professional", "duty"]
    ethics_found = sum(1 for k in ethics_keywords if k in response_lower)
    scores["Legally comprehensive including ethics"] = min(ethics_found, 5)

    return scores


######################################################################
# Route handlers
######################################################################


@app.route('/')
def home() -> str:
    return render_template("home.html", title="SQE2 Mock Practice Platform")

@app.route('/exercise/<name>', methods=['GET', 'POST'])
def exercise(name: str) -> str:
    # Map exercise names to descriptions and evaluators
    exercises: Dict[str, Tuple[str, Any]] = {
        'case': (
            "Case and matter analysis: provide a written report to a partner with a legal analysis and client‑focused advice.",
            evaluate_case_analysis
        ),
        'research': (
            "Legal research: investigate a problem for a client and write a note explaining your reasoning and the key sources you rely on.",
            evaluate_research
        ),
        'writing': (
            "Legal writing: produce a letter or an email that applies the law to the client’s concerns and is appropriate for the recipient.",
            evaluate_writing
        ),
        'drafting': (
            "Legal drafting: draft a legal document or part of a document, either from scratch or by amending an existing precedent.",
            evaluate_drafting
        ),
    }
    if name not in exercises:
        return "Unknown exercise", 404
    description, evaluator = exercises[name]
    feedback = None
    if request.method == 'POST':
        response_text = request.form.get('response', '')
        feedback = evaluator(response_text)
    return render_template(
    "exercise.html",
    title=name.capitalize() + " Exercise",
    description=description,
    feedback=feedback
)

@app.route('/interview', methods=['GET', 'POST'])
def interview() -> str:
    transcript = None
    if request.method == 'POST' and AUDIO_AVAILABLE:
        # Record audio for demonstration: this uses the default microphone
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            audio_data = recognizer.listen(source, phrase_time_limit=60)
        try:
            transcript = recognizer.recognize_google(audio_data)
        except Exception:
            transcript = "(Could not transcribe audio)"
    return render_template(
        "interview.html",
        title="Interview and Attendance Note Demo",
        audio_available=AUDIO_AVAILABLE,
        transcript=transcript
    )

######################################################################
# Application entry point
######################################################################

if __name__ == '__main__':
    # For development purposes only.  In production, use a proper WSGI server.
    app.run(debug=True, host='0.0.0.0', port=5000)