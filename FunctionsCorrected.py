from typing import Tuple, Dict, Any, List, Optional
from Data import (
    disorders,
    disorders_and_DSM5Symptoms,
    probabilities_calculation_list,
    response_identifier_list,
    symptom_index_number,
)
from dotenv import load_dotenv
import os
import re
import io
import time
import random
from contextlib import redirect_stdout

# --------------------------
# ENV + CLIENT
# --------------------------
load_dotenv()
from openai import OpenAI

API_KEY = os.getenv("OPENAI_API_KEY")
CHAT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-latest")      # main chat/explanations
SCORING_MODEL = os.getenv("OPENAI_SCORING_MODEL", "gpt-4o-mini")  # cheaper/faster scorer
MAX_RETRIES = 5

EXIT_WORDS = {"exit", "quit", "bye", "stop"}
RESTART_WORDS = {"restart", "/restart", "reset", "start over"}

if not API_KEY:
    raise ValueError("OPENAI_API_KEY not set in environment or .env file")

client = OpenAI(api_key=API_KEY)

# -------------------------------------------------
# Canonicalization helpers (avoid name mismatches)
# -------------------------------------------------
def _canon(s: str) -> str:
    return (s or "").strip().lower()

# Build a canonical name list from the Data.disorders
CANON_NAMES: List[str] = [_canon(d.get("name", "")) for d in disorders]

# Disorder-specific hints to help GPT map colloquial phrases to DSM categories
DISORDER_HINTS_RAW = {
    "Social Anxiety": "Relevant examples include: fear of public speaking, performance anxiety, fear of embarrassment, scrutiny by others, avoiding presentations or parties.",
    "Depression": "Relevant examples include: persistent sadness, hopelessness, loss of interest, changes in sleep or appetite, fatigue, guilt, poor concentration, suicidal thoughts.",
    "Anxiety": "Relevant examples include: excessive worry, restlessness, muscle tension, difficulty concentrating, sleep disturbance, panic attacks, racing heart.",
    "OCD": "Relevant examples include: intrusive thoughts, compulsive checking/cleaning/counting, repetitive rituals to reduce anxiety.",
    "Bipolar": "Relevant examples include: periods of elevated or irritable mood, decreased need for sleep, grandiosity, racing thoughts, risky behavior, alternating with low mood.",
    "Autism": "Relevant examples include: social-communication difficulties, restricted/repetitive behaviors, sensory sensitivities, insistence on routines.",
    "Alzheimer": "Relevant examples include: progressive memory loss, disorientation, trouble with familiar tasks, language problems, impaired judgment.",
}
DISORDER_HINTS = {_canon(k): v for k, v in DISORDER_HINTS_RAW.items()}

# Very small keyword map to prevent 'bogus' for obvious colloquial cues
DISORDER_KEYWORDS_RAW = {
    "Depression": [r"\bdepress(ion|ed)?\b", r"\bsad(ness)?\b", r"\bhopeless(ness)?\b", r"\banhedonia\b"],
    "Anxiety":    [r"\banxious(ness)?\b", r"\bworry(ing)?\b", r"\bpanic\b", r"\bracing heart\b", r"\brestless\b"],
    "Social Anxiety": [r"\bpublic speaking\b", r"\bstage fright\b", r"\bsocial(ly)? anxious\b"],
    "Bipolar":    [r"\bmanic\b", r"\bgrandios(e|ity)\b", r"\bdecreased need for sleep\b"],
    "OCD":        [r"\bobsess(ion|ive)\b", r"\bcompuls(ion|ive)\b", r"\bchecking\b", r"\bcleaning\b", r"\bcounting\b"],
    "Autism":     [r"\broutine(s)?\b", r"\bsensory\b", r"\bsocial[- ]?communication\b"],
    "Alzheimer":  [r"\bmemory (loss|problem|issues?)\b", r"\bdisorient(ed|ation)\b"],
}
DISORDER_KEYWORDS = {
    _canon(k): [re.compile(p, re.I) for p in pats] for k, pats in DISORDER_KEYWORDS_RAW.items()
}

def _keywords_match(desc: str, disorder_name: str) -> bool:
    pats = DISORDER_KEYWORDS.get(_canon(disorder_name), [])
    return any(p.search(desc) for p in pats)

# --------------------------
# GLOBAL STATE + resets
# --------------------------
_bogus_notice_printed = False  # one-time bogus notice per description

def clear_incrementation_and_state():
    # keep original side-effects + reset our globals
    probabilities_calculation_list.clear()
    disorders_and_DSM5Symptoms.clear()
    symptom_index_number.clear()

def reset_for_new_description():
    """Reset all per-description global state."""
    clear_incrementation_and_state()
    response_identifier_list.clear()
    global _bogus_notice_printed
    _bogus_notice_printed = False

def print_blank_statement(num_times):
    for _ in range(num_times):
        print()

def print_list_in_commas(list_one):
    return ", ".join(str(item) for item in list_one) + ", "

def increment_DSM_symptoms(disorder_name, second_most_likely_disorder, returning_other_disorder):
    if not returning_other_disorder:
        disorder_number = 1
        for disorder in disorders:
            if disorder_name == disorder["name"]:
                for symptom in disorder["DSM-5 Symptoms"]:
                    print(f"Symptom {disorder_number}: {symptom}")
                    disorder_number += 1
        return disorder_number  # count of symptoms
    else:
        disorder_number = 1
        next_most_likely_disorder_symptoms = ""
        for disorder in disorders:
            if second_most_likely_disorder == disorder["name"]:
                for symptom in disorder["DSM-5 Symptoms"]:
                    next_most_likely_disorder_symptoms = f"Symptom {disorder_number}: {symptom}"
                    disorder_number += 1
        return next_most_likely_disorder_symptoms

# --------------------------
# Input guard
# --------------------------
STOPWORDS = set("""
a an and are as at be but by for from has have i i'm i've in is it of on or so that the their them they this to we you your
""".split())

def _looks_mental_health_related(text: str) -> bool:
    """
    Allow most free-text descriptions through to GPT, except very short greetings or obvious noise.
    """
    t = (text or "").lower().strip()
    if len(t) < 3:
        return False
    if t in {"hello", "hi", "hey", "what is my name"}:
        return False
    if not re.search(r"[a-z]", t):
        return False
    return True

# --------------------------
# GPT scoring + explanation
# --------------------------
def _explain_rating(disorder: str, rating: int, description: str) -> str:
    prompt = (
        f"{rating} is the rating (1–100) you gave for likelihood of having {disorder}. "
        "Now explain why this rating was given based on the user's description and the DSM symptoms."
    )
    try:
        return client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "user", "content": prompt}],
        ).choices[0].message.content.strip()
    except Exception:
        return "Explanation unavailable due to a temporary error."

def Detect_with_GPT(description: str, disorder: str, explain: bool = False) -> Tuple[str, Optional[str]]:
    """
    Robust scoring:
    - Pre-filter obvious non-mental-health text.
    - Ask GPT for an integer 1..100 or 'bogus' (strict).
    - If GPT returns 'bogus' but the description clearly contains colloquial cues for this disorder,
      coerce a conservative score (60) to avoid dead-ends.
    - Cap retries with jittered backoff; print the bogus notice once per description.
    - If explain=True, fetch an explanation after a valid score is obtained.
    """
    global _bogus_notice_printed

    if not _looks_mental_health_related(description):
        return "BOGUS", None

    dsm = List_DSM_Symptoms(disorder)
    hint = DISORDER_HINTS.get(_canon(disorder), "")

    promptOne = (
        "You are an AI tasked with using the initial user input to help diagnose disorders. "
        f"For the disorder {disorder}, the DSM symptoms are: {dsm} "
        f"and the user description is: {description}. "
        "Analyze them and give a rating of the likelihood (1–100) that the user has this disorder, "
        "based strictly on the DSM symptoms provided.\n"
        f"{('Guidance: ' + hint) if hint else ''}\n"
        "IMPORTANT OUTPUT RULES:\n"
        "- Respond with ONLY the integer number (no words), OR 'bogus' if the description does NOT mention any of "
        "  this disorder’s DSM symptoms or closely related complaints.\n"
        "- Do NOT return a number for irrelevant input (e.g., greetings, 'what is my name').\n"
        "- Do NOT include any extra text besides the integer or the single word 'bogus'."
    )

    rating: Optional[int] = None
    desc_lc = (description or "").lower()

    for attempt in range(MAX_RETRIES):
        try:
            resp_text = client.chat.completions.create(
                model=SCORING_MODEL,
                messages=[{"role": "user", "content": promptOne}],
            ).choices[0].message.content.strip()
        except Exception:
            # transient failure: back off and retry
            time.sleep(0.4 * (attempt + 1) + random.random() * 0.2)
            continue

        if resp_text.lower() == "bogus":
            if _keywords_match(desc_lc, disorder):
                rating = 60
                break
            if not _bogus_notice_printed:
                print("Your response doesn’t seem to be genuine or relevant. "
                      "Please provide an honest and thoughtful description so I can assist you better.")
                _bogus_notice_printed = True
            return "BOGUS", None

        # parse integer (first number if any)
        try:
            rating = int(resp_text)
        except ValueError:
            m = re.search(r"\d+", resp_text)
            if m:
                rating = int(m.group(0))

        if rating is not None and 1 <= rating <= 100:
            break
        else:
            rating = None
            time.sleep(0.2 + 0.2 * attempt)

    if rating is None:
        if not _bogus_notice_printed:
            print("Your response doesn’t seem to be genuine or relevant. "
                  "Please provide an honest and thoughtful description so I can assist you better.")
            _bogus_notice_printed = True
        return "BOGUS", None

    # Optionally fetch explanation (only for the top disorder in practice)
    explanation = _explain_rating(disorder, rating, description) if explain else None
    return str(rating), explanation

def chat_with_gpt(prompt, DSM_list, General_Info, highest_probability_disorder, second_most_likely_disorder,
                  DSM_list_second_most_likely_disorder, responseOne, responseTwo, description):
    SYSTEM_PROMPT = (
        "You are Cerebot, a direct, pragmatic AI assistant developed by a clinical research team. "
        "You give medically relevant, evidence-based responses. "
        "You do not hallucinate. If unsure, admit it. No emojis."
    )
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                  {"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

# --------------------------
# CLI pieces (kept, but hardened)
# --------------------------
def run_main_chatbot(DSM_list, General_Info, highest_probability_disorder, next_most_likely_disorder,
                     next_most_likely_disorder_symptoms, responseOne, responseTwo, description):
    while True:
        user_input = input("You: ")
        if any(keyword in user_input.lower() for keyword in ["exit", "quit", "bye", "stop"]):
            break
        response = chat_with_gpt(user_input, DSM_list, General_Info, highest_probability_disorder,
                                 next_most_likely_disorder, next_most_likely_disorder_symptoms, responseOne,
                                 responseTwo, description)
        print("Chatbot: ", response)
        print()
    print("Thank you for using Cerebot!")
    while True:
        again = input("Would you like to run this chatbot again? (yes/no)")
        if again.strip().lower() == "yes":
            return True
        elif again.strip().lower() == "no":
            return False
        else:
            print("please enter either yes or no.")
def check_all_disorders(description: str) -> Tuple[int, int, str]:
    global probabilities_calculation_list, response_identifier_list  # <-- fix 1

    desc = (description or "").lower().strip()
    # fresh scan
    probabilities_calculation_list.clear()

    triples: List[Tuple[str, int]] = []

    for d in disorders:
        name = d.get("name")
        r1, _ = Detect_with_GPT(desc, name, explain=False)
        if r1 == "BOGUS":
            continue
        try:
            score = int(r1)
        except (ValueError, TypeError):
            continue
        if score >= 1:
            probabilities_calculation_list.append(name)
            probabilities_calculation_list.append(score)
            triples.append((name, score))

    # Conservative keyword nudges if nothing scored (use .extend, not +=)  <-- fix 2
    if not probabilities_calculation_list:
        if re.search(r"\bpublic speaking|stage fright|social anxiety\b", desc):
            probabilities_calculation_list.extend(["Social Anxiety", 60])
            triples.append(("Social Anxiety", 60))
        if re.search(r"\banxi(ety|ous)\b", desc):
            probabilities_calculation_list.extend(["Anxiety", 60])
            triples.append(("Anxiety", 60))
        if re.search(r"\bsad(ness)?\b|\bhopeless\b|\banhedonia\b", desc):
            probabilities_calculation_list.extend(["Depression", 60])
            triples.append(("Depression", 60))

    if not probabilities_calculation_list:
        print('No disorders found in the input. Please try and use certain precise keywords, such as "fear of public speaking" or "socially anxious" to get a better response')
        return 0, 0, ""

    # Determine top
    triples.sort(key=lambda x: x[1], reverse=True)
    top_name, top_score = triples[0]

    # Only get explanation for the top
    _, top_expl = Detect_with_GPT(desc, top_name, explain=True)

    response_identifier_list.clear()
    response_identifier_list.append(top_score)
    response_identifier_list.append(top_expl or "")

    return len(probabilities_calculation_list), top_score, (top_expl or "")


def calculate_probability_percentage() -> Tuple[Optional[str], Optional[str]]:
    # Sum of int scores
    ints = [x for x in probabilities_calculation_list if isinstance(x, int)]
    total_probabilities = sum(ints)
    if total_probabilities == 0:
        print("Unable to compute percentages right now.")
        return None, None

    # Print percentages (exact CLI format)
    for index, item in enumerate(probabilities_calculation_list):
        if isinstance(item, int):
            probability_percent = round((item / total_probabilities) * 100)
            print(f"Your chances of having {probabilities_calculation_list[index - 1]} is {probability_percent}%.")

    # top + next-most-likely
    max_val = max(ints)
    i = probabilities_calculation_list.index(max_val)
    most_likely_disorder = probabilities_calculation_list[i - 1]

    unique_sorted = sorted(set(ints), reverse=True)
    if len(unique_sorted) >= 2:
        next_val = unique_sorted[1]
        idx = probabilities_calculation_list.index(next_val)
        return most_likely_disorder, probabilities_calculation_list[idx - 1]
    return most_likely_disorder, None

def check_with_DSM():
    if all(not isinstance(x, int) for x in probabilities_calculation_list):
        print("Unable to diagnose. Try again with more detail.")
        clear_incrementation_and_state()
        return False, True, 0, ""
    max_val = max(x for x in probabilities_calculation_list if isinstance(x, int))
    i = probabilities_calculation_list.index(max_val)
    most_likely_disorder = probabilities_calculation_list[i - 1]
    print(f"It appears that according to our calculations, you have the highest chance of having {most_likely_disorder}")
    print_blank_statement(3)
    print("We will now list official symptoms using the DSM-5. If you have any of these symptoms, please indicate that using the words yes or no and either indicate the number of the symptom that you have")
    print_blank_statement(3)

    # List symptoms and get count
    placeholder = None
    disorder_length = increment_DSM_symptoms(most_likely_disorder, placeholder, False)

    # Guard: empty DSM list configured
    if not disorder_length or disorder_length <= 1:  # 1 means loop printed once and then incremented
        print("No official DSM-5 symptoms are configured for this disorder. Try another description.")
        return False, True, 0, most_likely_disorder

    answer = ""
    second_answer = ""  # initialize to avoid NameError
    while True:
        answer = input("Do you have any of these symptoms? (yes/no): ")
        if answer.strip().lower() == "yes":
            while True:
                try:
                    second_answer = input("What symptom number do you have? If you are done typing symptoms, say done ")
                    if second_answer.strip().lower() == "done":
                        break
                    if int(second_answer) >= disorder_length or int(second_answer) < 1:
                        print("Sorry, but your number is too high/low. Please enter the disorder number properly.")
                    else:
                        symptom_index_number.append(int(second_answer))
                except ValueError:
                    if second_answer.strip().lower() == "done":
                        break
                    else:
                        print("Please enter a number or 'done'. Try again.")
        if second_answer and second_answer.strip().lower() == "done":
            break
        elif answer.strip().lower() == "no":
            del probabilities_calculation_list[i]
            del probabilities_calculation_list[i - 1]
            return False, False, 0, most_likely_disorder
        else:
            print("Please enter yes or no.")
    print("I'm sorry you're experiencing these symptoms. Please talk to to this AI where you can discuss your symptoms.")
    return True, False, 1, most_likely_disorder

def close_program():
    while True:
        again = input("Would you like to enter symptoms again? (yes/no): ").strip().lower()
        if again == 'no':
            print("Thank you for using Cerebot. Take care!")
            return again
        elif again == 'yes':
            clear_incrementation_and_state()
            return again
        else:
            print("Please enter either yes or no!")

def List_DSM_Symptoms(highest_probability_disorder):
    """
    Returns the exact string your code expects.
    If no symptom numbers have been selected yet (initial scoring pass),
    include ALL DSM-5 symptoms for the disorder so GPT has real context.
    """
    DSM_message = "These are the DSM-5 Symptoms that the user has:"
    target = None
    name_c = _canon(highest_probability_disorder)
    for d in disorders:
        if _canon(d["name"]) == name_c:
            target = d
            break
    if not target:
        return DSM_message  # disorder not found; keep original shape

    # If user hasn't selected any indices yet, include ALL symptoms for scoring
    if not symptom_index_number:
        for symptom in target.get("DSM-5 Symptoms", []):
            DSM_message += symptom + ", "
        return DSM_message

    # Otherwise include only chosen symptoms (original behavior)
    for idx in symptom_index_number:
        if 1 <= idx <= len(target.get("DSM-5 Symptoms", [])):
            DSM_message += target["DSM-5 Symptoms"][idx - 1] + ", "
    return DSM_message

def Get_General_info(highest_probability_disorder):
    tgt = _canon(highest_probability_disorder)
    for disorder in disorders:
        if _canon(disorder["name"]) == tgt:
            return disorder.get("General Info", "")
    return ""

# ======================================================
# GRADIO HELPERS — replicate CLI text EXACTLY (no input)
# ======================================================
def _capture_output(fn, *args, **kwargs):
    buf = io.StringIO()
    with redirect_stdout(buf):
        result = fn(*args, **kwargs)
    return result, buf.getvalue()

def _list_symptoms_text(disorder_name: str) -> Tuple[str, int]:
    lines = []
    count = 0
    name_c = _canon(disorder_name)
    for d in disorders:
        if _canon(d["name"]) == name_c:
            for i, symptom in enumerate(d.get("DSM-5 Symptoms", []), start=1):
                lines.append(f"Symptom {i}: {symptom}")
                count = i
            break
    return "\n".join(lines), count

def _has_scores() -> bool:
    return any(isinstance(x, int) for x in probabilities_calculation_list)

def _remove_current_top_disorder() -> bool:
    ints = [x for x in probabilities_calculation_list if isinstance(x, int)]
    if not ints:
        return False
    max_val = max(ints)
    idx = probabilities_calculation_list.index(max_val)
    # Remove score then its preceding name
    del probabilities_calculation_list[idx]
    del probabilities_calculation_list[idx - 1]
    return _has_scores()

def _current_top_disorder() -> str:
    max_val = max(x for x in probabilities_calculation_list if isinstance(x, int))
    i = probabilities_calculation_list.index(max_val)
    return probabilities_calculation_list[i - 1]

def _dsm_intro_block(disorder_name: str) -> Tuple[str, int]:
    header = (
        f"It appears that according to our calculations, you have the highest chance of having {disorder_name}\n"
        "\n\n"
        "We will now list official symptoms using the DSM-5. If you have any of these symptoms, please indicate that using the words yes or no and either indicate the number of the symptom that you have\n"
        "\n\n"
    )
    sym_text, length = _list_symptoms_text(disorder_name)
    return header + sym_text, length

# --------------------------
# GRADIO: EXACT CLI REPLICA (no blocking input())
# --------------------------
def gradio_init_state() -> Dict[str, Any]:
    reset_for_new_description()
    return {
        "stage": "awaiting_description",
        "number_matches": 0,
        "DSM_Symptoms_identified": False,
        "Symptoms_ran_out": False,
        "again": False,
        "highest_probability_disorder": None,
        "next_most_likely_disorder": None,
        "responseOne": None,
        "responseTwo": None,
        "description": None,
        "DSM_list": None,
        "next_most_likely_disorder_symptoms": None,
        "General_Info": None,
        "current_disorder_length": 0,
    }
def gradio_step(user_text: str, state: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """One step of the chatbot in Gradio, mimicking the CLI exactly (no input())."""
    msg = (user_text or "").strip()
    msg_lc = msg.lower()

    # Reset per-turn bogus flag
    global _bogus_notice_printed
    _bogus_notice_printed = False

    # ---------- UNIVERSAL COMMANDS (work in any stage) ----------
    if msg_lc in EXIT_WORDS:
        # Emulate ending the CLI chat loop + post-exit message
        clear_incrementation_and_state()
        return "Thank you for using Cerebot!", gradio_init_state()

    if msg_lc in RESTART_WORDS:
        clear_incrementation_and_state()
        return gradio_welcome_text(), gradio_init_state()
    # ------------------------------------------------------------

    # ===========================
    # Stage 1: Awaiting description
    # ===========================
    if state["stage"] == "awaiting_description":
        clear_incrementation_and_state()
        response_identifier_list.clear()
        symptom_index_number.clear()
        state["description"] = msg_lc
        (number_matches, responseOne, responseTwo), printed1 = _capture_output(check_all_disorders, state["description"])
        state["number_matches"] = number_matches
        state["responseOne"] = responseOne
        state["responseTwo"] = responseTwo

        if number_matches == 0:
            return (printed1.strip() or
                    'No disorders found in the input. Please try and use certain precise keywords, such as "fear of public speaking" or "socially anxious" to get a better response',
                    state)

        (highest, second), printed2 = _capture_output(calculate_probability_percentage)
        state["highest_probability_disorder"] = highest
        state["next_most_likely_disorder"] = second

        top = _current_top_disorder()
        dsm_block, length = _dsm_intro_block(top)
        state["current_disorder_length"] = length
        state["highest_probability_disorder"] = top

        state["stage"] = "awaiting_dsm_yesno"
        full_text = (printed2 + dsm_block + "\n" + "Do you have any of these symptoms? (yes/no): ")
        return full_text, state
    # ===========================
    # Stage 2: Yes/No to DSM list
    # ===========================
    if state["stage"] == "awaiting_dsm_yesno":
        ans = msg.lower()
        if ans == "yes":
            state["stage"] = "awaiting_dsm_numbers"
            return "What symptom number do you have? If you are done typing symptoms, say done ", state
        elif ans == "no":
            has_more = _remove_current_top_disorder()
            if not has_more:
                reset_for_new_description()
                state["stage"] = "awaiting_description"
                return "Unable to diagnose. Try again with more detail.", state
            top = _current_top_disorder()
            dsm_block, length = _dsm_intro_block(top)
            state["current_disorder_length"] = length
            state["highest_probability_disorder"] = top
            return dsm_block + "\n" + "Do you have any of these symptoms? (yes/no): ", state
        else:
            return "Please enter yes or no.", state

    # ===========================
    # Stage 3: Entering DSM numbers (one-by-one, exactly like CLI)
    # ===========================
    if state["stage"] == "awaiting_dsm_numbers":
        if msg.lower() == "done":
            apology = "I'm sorry you're experiencing these symptoms. Please talk to to this AI where you can discuss your symptoms."
            state["DSM_list"] = List_DSM_Symptoms(state["highest_probability_disorder"])
            state["General_Info"] = Get_General_info(state["highest_probability_disorder"])
            state["stage"] = "chat_followup"
            return apology, state

        try:
            n = int(msg)
            if n > state.get("current_disorder_length", 0) or n < 1:
                return "Sorry, but your number is too high/low. Please enter the disorder number properly.", state
            symptom_index_number.append(n)
            return "What symptom number do you have? If you are done typing symptoms, say done ", state
        except ValueError:
            return "Please enter a number or 'done'. Try again.", state

    # ===========================
    # Stage 4: Chat follow-up (free-form, same prompt as CLI backend)
    # ===========================
    if state["stage"] == "chat_followup":
        reply = chat_with_gpt(
            prompt=msg,
            DSM_list=state.get("DSM_list", ""),
            General_Info=state.get("General_Info", ""),
            highest_probability_disorder=state.get("highest_probability_disorder", ""),
            second_most_likely_disorder=state.get("next_most_likely_disorder"),
            DSM_list_second_most_likely_disorder=None,
            responseOne=state.get("responseOne"),
            responseTwo=state.get("responseTwo"),
            description=state.get("description", ""),
        )
        return reply, state

    # Fallback
    state["stage"] = "awaiting_description"
    return "I didn’t understand. Please start again by describing your symptoms.", state

def gradio_welcome_text() -> str:
    return "Welcome to Cerebot.\nTo get started, please give me a detailed description of the symptoms you currently face:"

def gradio_reset() -> Tuple[Dict[str, Any], str]:
    reset_for_new_description()
    return gradio_init_state(), ""

# --------------------------
# CLI entrypoint (kept)
# --------------------------
def main():
    number_matches = 0
    DSM_Symptoms_identified = False
    Symptoms_ran_out = False
    again = False

    while again is False:
        reset_for_new_description()
        while DSM_Symptoms_identified is False:
            while number_matches == 0:
                description = input("To get started, please give me a detailed description of the symptoms you currently face: ").strip().lower()
                number_matches, responseOne, responseTwo = check_all_disorders(description)
            highest_probability_disorder, next_most_likely_disorder = calculate_probability_percentage()
            DSM_Symptoms_identified, Symptoms_ran_out, number_matches, highest_probability_disorder = check_with_DSM()
            while DSM_Symptoms_identified is False and Symptoms_ran_out is False:
                DSM_Symptoms_identified, Symptoms_ran_out, number_matches, highest_probability_disorder = check_with_DSM()

        DSM_list = List_DSM_Symptoms(highest_probability_disorder)
        next_most_likely_disorder_symptoms = increment_DSM_symptoms(highest_probability_disorder, next_most_likely_disorder, True)
        General_Info = Get_General_info(highest_probability_disorder)
        again = run_main_chatbot(DSM_list, General_Info, highest_probability_disorder, next_most_likely_disorder,
                                 next_most_likely_disorder_symptoms, responseOne, responseTwo, description)
        if again:
            print("Redirecting you back to beginning . . .")
            again = False
            DSM_Symptoms_identified = False
            number_matches = 0
            continue
        else:
            print("Thank you for using cerebot!")
            break

if __name__ == "__main__":
    main()
