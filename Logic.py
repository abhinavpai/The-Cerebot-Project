def Cerebot():


   import Functions
   number_matches = 0
   DSM_Symptoms_identified = False
   Symptoms_ran_out = False
   again = False
   import openai
   from openai import OpenAI








   while again == False:
       while DSM_Symptoms_identified == False:
           while number_matches == 0:
               description = input("To get started, please give me a detailed description of the symptoms you currently face: ").strip().lower()
               number_matches, responseOne, responseTwo = Functions.check_all_disorders(description)
           highest_probability_disorder, next_most_likely_disorder = Functions.calculate_probability_percentage()
           DSM_Symptoms_identified, Symptoms_ran_out, number_matches, highest_probability_disorder = Functions.check_with_DSM()
           while DSM_Symptoms_identified == False and Symptoms_ran_out == False:
               DSM_Symptoms_identified, Symptoms_ran_out, number_matches, highest_probability_disorder = Functions.check_with_DSM()


       DSM_list = Functions.List_DSM_Symptoms(highest_probability_disorder)
       next_most_likely_disorder_symptoms = Functions.increment_DSM_symptoms(highest_probability_disorder, next_most_likely_disorder, True)
       General_Info = Functions.Get_General_info(highest_probability_disorder)
       again = Functions.run_main_chatbot(DSM_list, General_Info, highest_probability_disorder, next_most_likely_disorder, next_most_likely_disorder_symptoms, responseOne, responseTwo, description)
       if again:
           print("Redirecting you back to beginning . . .")
           again = False
           DSM_Symptoms_identified = False
           number_matches = 0
           continue


       elif not again:
           print("Thank you for using cerebot!")
           break


#This is the main function, that's the culmination of basically ALL my code
Cerebot()


#ALL OF THIS IS FOR THE CHATBOT AI THAT ANALYZES SYMPTOMS AND TELLS USER WHAT TO DO
