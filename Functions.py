from dotenv import load_dotenv
import os

load_dotenv()

import openai
from openai import OpenAI
# replace with your OpenAI API key. THIS IS CONFIDENTIAL AND SHOULD NOT BE SHARED PUBLICLY
# #create an OpenAI client with the provided API key
from Data import disorders, disorders_and_DSM5Symptoms, probabilities_calculation_list, response_identifier_list, \
    symptom_index_number

# this reads your .env file and sets environment variables
openai.api_key = ###client = openai

client = OpenAI(api_key=openai.api_key)


# Functions in functions that make up the logic
def clear_incrementation_and_state():
    total_probabilities = 0
    probabilities_calculation_list.clear()
    disorders_and_DSM5Symptoms.clear()
    symptom_index_number.clear()


def print_blank_statement(num_times):
    for i in range(num_times):
        print()


def print_list_in_commas(list_one):
    message = ""
    for item in list_one:
        message += str(item) + ", "

    return message


def increment_DSM_symptoms(disorder_name, second_most_likely_disorder, returning_other_disorder):
    if not returning_other_disorder:
        disorder_number = 1
        for disorder in disorders:
            if disorder_name == disorder["name"]:
                for symptom in disorder["DSM-5 Symptoms"]:
                    disorder = "Symptom " + str(disorder_number) + ": " + symptom
                    print(disorder)
                    disorder_number += 1
        return disorder_number




    else:
        disorder_number = 1
        for disorder in disorders:
            if second_most_likely_disorder == disorder["name"]:
                for symptom in disorder["DSM-5 Symptoms"]:
                    next_most_likely_disorder_symptoms = "Symptom " + str(disorder_number) + ": " + symptom
                    disorder_number += 1

        return next_most_likely_disorder_symptoms


# Main functions make up logic file


def Detect_with_GPT(description, disorder):
    # create an OpenAI client with the provided API key

    GeneralInfo = Get_General_info(disorder)
    DSM_Symptoms = List_DSM_Symptoms(disorder)
    promptOne = (
                "You are an AI tasked with using the initial user input to help diagnose disorders. For the disorder, " + disorder + ", the DSM symptoms, " + DSM_Symptoms + ", and the user description, " + description + ", you must look at the description and DSM symptoms and analyze them in context to help determine whether the user has or does not have a certain disorder. Then, on a scale of 1-100, you ABSOULTEY MUST give me a rating of the likelihood of having the disorder, " + disorder + ", based on the DSM-symptoms, " + DSM_Symptoms + ", with no explanation. Only include the numeric integer rating in your response and nothing else. If you cannot determine what the disorder possibly could be or if the input seems to be bogus, please put 0 as your rating. For reference, here is some general info about" + disorder + ": " + GeneralInfo + " Please keep in mind that there is ONE excetpion to the no-integer in this response rule. If the input that the user inputs into description seems bogus, nonsensical, some random string of letter/numbers/words, something completely irrelevant to what I ask, which is to describe symptoms of a certain disorder, so if they only mention other things completely IRRELEVANT basically, then you MUST say 'bogus' and ONLY 'bogus' as response one.")

    responseOne = client.chat.completions.create(
        model="chatgpt-4o-latest",
        messages=[{"role": "user", "content": promptOne},
                  {"role": "system", "content": description}]
    )

    if responseOne.choices[0].message.content.strip().lower() == 'bogus':
        print(
            "Your response doesn’t seem to be genuine or relevant. Please provide an honest and thoughtful description so I can assist you better.")
        return "BOGUS", "BOGUS"

    response_identifier_list.append(int(responseOne.choices[0].message.content.strip()))

    promptTwo = (
                str(responseOne) + " is the rating out of 1-100 that you gave of the likelihood of having " + disorder + ". Based on the response that the computer, which was a rating on a scale from one to 100 of the likelihood of having the disorder, " + disorder + ", you must now explain why the client has that rating based on what they said and the characteristics of the disorder shown by these following symptoms:" + DSM_Symptoms)

    responseTwo = client.chat.completions.create(
        model="chatgpt-4o-latest",
        messages=[{"role": "user", "content": promptTwo},
                  {"role": "system", "content": description}]
    )
    response_identifier_list.append(responseTwo)

    return responseOne.choices[0].message.content.strip(), responseTwo.choices[0].message.content.strip()


def chat_with_gpt(prompt, DSM_list, General_Info, highest_probability_disorder, second_most_likely_disorder,
                  DSM_list_second_most_likely_disorder, responseOne, responseTwo,
                  description):  # function to interact with the GPT model

    SYSTEM_PROMPT = (
            "You are Cerebot, a direct, pragmatic AI assistant developed by a clinical research team. "
            "You give clear, intelligent, and medically relevant responses.  "
            "If the user seems like they are depressed, chatGPT will provide them the help that they need and will mention the following suicide hotline for them to call: 988  "
            "You only provide information that is evidence-based or logically reasoned. "
            "If the user describes symptoms, you give a focused prognosis and suggest next steps. "
            "You do not hallucinate. You admit when you don’t know."
            "You do not use emojis or casual language. You do not use any formatting other than plain text. Please make it absolutely clear that the diagnosis made on this program may not be an accurate diagnosis of a disorder, and that you should consult a mental health professional for an accurate diagnosis of a disorder"
            + DSM_list
            + "According to the calculations, the user seems to have" + highest_probability_disorder +
            "Here is some general info about " + highest_probability_disorder + ", including treatments, information about the disorder, and whatnot: " +
            General_Info + ". Please use this to help the user better understand their disorder and what they can do about it. Just to let you know, " + str(
        responseOne) + " is the rating, out of one hundred, that the other AI gave based on the likelihood of the individual having " + highest_probability_disorder + ". " +
            " '" + str(responseTwo) + "'  is the reason why, according to the AI, the user deserved the rating"
                                      "Oh, and for the most important information of all the client entered this in their description. Please use this description to best suggest what the client should do next: " +
            description +
            "Understands your mental health context better than a generic AI."

            "Also, please take into account that although " + highest_probability_disorder + " is, according to the calculations, the disorder that this individual is most likely to have, " + second_most_likely_disorder + "is the disorder that this individual is the second-most likely to have, so please take this into account and consider the fact that the individual could also have" + second_most_likely_disorder + ". For reference, this is the DSM list of symptoms for the disorder that the user is second-most likely to have: " + DSM_list_second_most_likely_disorder + ". If you believe that the individual could have" + second_most_likely_disorder + ", please ask if they have any of those symptoms as well."


                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 "Tracks user's progress over time."


                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 "Asks the right questions at the right time."


                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 "Offers personalized tips or exercises tailored specifically to your OCD experience."

    )

    response = client.chat.completions.create(
        model="chatgpt-4o-latest",  # the gpt that we use
        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                  {"role": "user", "content": prompt}]  # the message that we send to the gpt
    )
    return response.choices[0].message.content.strip()  # the response from the gpt


def run_main_chatbot(DSM_list, General_Info, highest_probability_disorder, next_most_likely_disorder,
                     next_most_likely_disorder_symptoms, responseOne, responseTwo, description):
    while True:
        user_input = input("You: ")  # input from the user
        if any(keyword in user_input.lower() for keyword in
               ["exit", "quit", "bye", "stop"]):  # if the user wants to exit
            break
        response = chat_with_gpt(user_input, DSM_list, General_Info, highest_probability_disorder,
                                 next_most_likely_disorder, next_most_likely_disorder_symptoms, responseOne,
                                 responseTwo, description)  # get the response from the gpt
        print("Chatbot: ", response)  # print the response from the gpt
        print(" ")

    print("Thank you for using Cerebot!")  # exit message!

    while True:
        again = input("Would you like to run this chatbot again? (yes/no)")

        if again.strip().lower() == "yes":
            return True


        elif again.strip().lower() == "no":
            return False


        else:
            print("please enter either yes or no.")


def check_all_disorders(description):
    description = description.lower()
    symptom_list = ""

    for disorder in disorders:
        responseOne, responseTwo = Detect_with_GPT(description, disorder["name"])
        # print(responseOne) #delete later
        # print(responseTwo) #delete later

        if responseOne == "BOGUS" and responseTwo == "BOGUS":
            return 0, False, False

        try:
            if int(responseOne) >= 1:
                probabilities_calculation_list.append(disorder["name"])
                probabilities_calculation_list.append(int(responseOne))


        except ValueError:
            continue

        max_val = max(x for x in response_identifier_list if isinstance(x, int))

        i = response_identifier_list.index(max_val)

        max_val_explanation = response_identifier_list[i + 1]

    if len(probabilities_calculation_list) == 0:
        print(
            'No disorders found in the input. Please try and use certain precise keywords, such as "fear of public speaking" or "socially anxious" to get a better response')

    return len(probabilities_calculation_list), max_val, max_val_explanation


def calculate_probability_percentage():
    # Calculates probability percentages
    total_probabilities = 0
    for item in probabilities_calculation_list:
        if type(item) == int:
            total_probabilities += item
    for index, item in enumerate(probabilities_calculation_list):
        if type(item) == int:
            probability_percent = round((item / total_probabilities) * 100)
            print("Your chances of having " + probabilities_calculation_list[index - 1] + " is " + str(
                probability_percent) + "%.")

    max_val = max(x for x in probabilities_calculation_list if isinstance(x, int))
    i = probabilities_calculation_list.index(max_val)
    most_likely_disorder = probabilities_calculation_list[i - 1]
    filtered = [x for x in probabilities_calculation_list if isinstance(x, int)]
    unique_sorted = sorted(set(filtered), reverse=True)
    if len(unique_sorted) >= 2:
        next_most_likely_disorder_number = unique_sorted[1]
        index = probabilities_calculation_list.index(next_most_likely_disorder_number)
        next_most_likely_disorder = probabilities_calculation_list[index - 1]
    else:
        next_most_likely_disorder = None

    if next_most_likely_disorder == None:
        return most_likely_disorder, "There is no second-most likely disorder."


    else:
        return most_likely_disorder, next_most_likely_disorder


def check_with_DSM():
    if all(not isinstance(x, int) for x in probabilities_calculation_list):
        print(
            "We are sorry, but we are unable to diagnose your disorder at this time. Please enter your description of your symptoms again and try and be more specific so we can pinpoint what it is.")
        clear_incrementation_and_state()
        return False, True, 0, ""
    max_val = max(x for x in probabilities_calculation_list if isinstance(x, int))
    i = probabilities_calculation_list.index(max_val)
    most_likely_disorder = probabilities_calculation_list[i - 1]
    print("It appears that according to our calculations, you have the highest chance of having " +
          probabilities_calculation_list[i - 1])
    print_blank_statement(3)
    print(
        "We will now list official symptoms using the DSM-5. If you have any of these symptoms, please indicate that using the words yes or no and either indicate the number of the symptom that you have")
    print_blank_statement(3)
    placeholder = None
    disorder_length = increment_DSM_symptoms(most_likely_disorder, placeholder, False)
    # print("The disorder length is" + str(disorder_length))
    answer = ""
    while True:
        answer = input("Do you have any of these symptoms? (yes/no): ")
        if answer.strip().lower() == "yes":
            while True:
                try:
                    second_answer = input("What symptom number do you have? If you are done typing symptoms, say done ")
                    if int(second_answer) >= disorder_length or int(second_answer) < 1:
                        print("Sorry, but your number is too high/low. Please enter the disorder number properly.")


                    else:
                        symptom_index_number.append(int(second_answer))




                except ValueError:
                    if second_answer.strip().lower() == "done":
                        break


                    else:
                        print("Please enter a number or 'done'. Try again.")

        if second_answer.strip().lower() == "done":
            break


        elif answer.strip().lower() == "no":
            del probabilities_calculation_list[i]
            del probabilities_calculation_list[i - 1]
            return False, False, 0, most_likely_disorder


        else:
            print("Please enter yes or no.")

    print(
        "I'm sorry you're experiencing these symptoms. Please talk to to this AI where you can discuss your symptoms.")
    return True, False, 1, most_likely_disorder


def close_program():
    while True:
        again = input("Would you like to enter symptoms again? (yes/no): ").strip().lower()
        if again.strip().lower() == 'no':
            print("Thank you for using Cerebot. Take care!")
            return again


        elif again.strip().lower() == 'yes':  # resets everything
            clear_incrementation_and_state()
            return again


        else:
            print("Please enter either yes or no!")


def List_DSM_Symptoms(highest_probability_disorder):
    DSM_message = "These are the DSM-5 Symptoms that the user has:"
    for disorder in disorders:
        if disorder["name"] == highest_probability_disorder:
            for symptom in disorder["DSM-5 Symptoms"]:
                if any(symptom == disorder["DSM-5 Symptoms"][item - 1] for item in symptom_index_number):
                    DSM_message += symptom + ", "
    return DSM_message


def Get_General_info(highest_probability_disorder):
    for disorder in disorders:
        if highest_probability_disorder.strip().lower() == disorder["name"].strip().lower():
            return disorder["General Info"]



