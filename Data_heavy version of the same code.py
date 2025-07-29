
#Data initialization via dictionary
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

#function to traverse data and match to input
def check_all_disorders(description):
    description = description.lower()

    for disorder in disorders:
        for symptom in disorder["Symptom"]:
            if symptom.strip().lower() in description and disorder["stated"] == False:
                print("It appears you may have " + disorder["name"])
                disorder["incrementation"] += 1
                disorder["stated"] = True


            elif symptom.lower() in description:
                disorder["incrementation"] += 1

        if disorder["incrementation"] >= 1:
            probabilities_calculation_list.append(disorder["name"])
            probabilities_calculation_list.append(disorder["incrementation"])


def clear_incrementation_and_state():
    total_probabilities = 0
    probabilities_calculation_list.clear()
    for disorder in disorders:
        for incrementation in disorder["incrementation"]:
            disorder["incrementation"] = 0

        for stated in disorder["stated"]:
            disorder["stated"] = False




while True:
    total_probabilities = 0
    description = input("To get started, please give me a detailed description of the symptoms you currently face: ").strip().lower()

    check_all_disorders(description)


    #adds up all the numbers in the probabilities calculation list to calculate percentages
    for item in probabilities_calculation_list:
        if type(item) == int:
            total_probabilities += item

    #calculates probability percentage and identifies chances of having certain disorders
    for index, item in enumerate(probabilities_calculation_list):
        if type(item) == int:
            probability_percent = (item / total_probabilities) * 100
            print("Your chances of having " + probabilities_calculation_list[index - 1] + " is "  + str(probability_percent) + "%.")


    while True:
        again = input("Would you like to enter symptoms again? (yes/no): ").strip().lower()
        if again == 'no':
            print("Thank you for using Cerebot. Take care!")
            break
        elif again == 'yes': #resets everything
            clear_incrementation_and_state()
            break
        else:
            print("Please enter either yes or no!")

    if again == 'no':
        break





