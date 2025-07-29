disorders = [
    {
        "name": "Depression",
        "Symptom": ['hopeless', 'sad', 'nothing makes me happy', 'empty', 'numb', "can't focus", "can't concentrate"],
        "incrementation": 0,
        "stated": False
    },
    {
        "name": "Alzheimer",
        "Symptom": ["can't remember", "forget easily", "misplacing items", "misplace", "lost"],
        "incrementation": 0,
        "stated": False
    },
    {
        "name": "Autism",
        "Symptom": ['repetitive behaviors', 'talk to myself', 'hard to communicate', 'hard to make friends',
                    "can't make friends", 'hate changes', 'nervous'],
        "incrementation": 0,
        "stated": False
    },
    {
        "name": "Anxiety",
        "Symptom": [
            "nervous", "panicking", "racing heart", "can't breathe", "overthinking",
            "tight chest", "shaky", "sweating", "restless", "worried all the time",
            "can't relax", "feeling on edge", "fear for no reason"
        ],
        "incrementation": 0,
        "stated": False
    },
    {
        "name": "Bipolar",
        "Symptom": [
            "mood swings", "super energetic", "euphoric", "talking really fast",
            "spending sprees", "feel invincible", "can't sleep but not tired",
            "suddenly really depressed", "risky behavior", "feel on top of the world",
            "then crash", "my emotions are all over"
        ],
        "incrementation": 0,
        "stated": False
    },
    {
        "name": "OCD",
        "Symptom": [
            "intrusive thoughts", "can't stop thinking", "check things over and over",
            "obsessed with germs", "washing hands constantly", "counting things",
            "repeating behaviors", "everything must be perfect", "fear of contamination"
        ],
        "incrementation": 0,
        "stated": False
    },
    {
        "name": "Social Anxiety",
        "Symptom": [
            "afraid of talking to people", "embarrassed easily", "avoid eye contact",
            "fear of public speaking", "scared people are judging me",
            "nervous in social situations", "can't eat in front of others",
            "I avoid parties", "shy", "socially anxious"
        ],
        "incrementation": 0,
        "stated": False
    }
]

probabilities_calculation_list = []

def check_all_disorders(description):
    description = description.lower()

    for disorder in disorders:
        for symptom in disorder["Symptom"]:
            if symptom.strip().lower() in description and disorder["stated"] == False:
                print("It appears you may have " + disorder["name"])
                disorder["incrementation"] += 1
                disorder["stated"] = True