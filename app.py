import streamlit as st
import google.generativeai as genai
import os

# Configure page
st.set_page_config(
    page_title="MedSafe - AI Health Companion",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for medical theme
st.markdown("""
<style>
    .main {
        background-color: #eff6ff;
    }
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        padding: 12px;
        font-weight: 500;
    }
    .medicine-card {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        padding: 24px;
        border-radius: 16px;
        color: white;
        cursor: pointer;
        border: 2px solid #2563eb;
    }
    .lifestyle-card {
        background: linear-gradient(135deg, #14b8a6 0%, #0d9488 100%);
        padding: 24px;
        border-radius: 16px;
        color: white;
        cursor: pointer;
        border: 2px solid #0d9488;
    }
    h1 {
        color: #7c3aed;
        font-weight: 700;
    }
    .stChatMessage {
        border-radius: 16px;
        padding: 12px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 28px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'step' not in st.session_state:
    st.session_state.step = 'patient_info'
if 'selected_option' not in st.session_state:
    st.session_state.selected_option = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'form_data' not in st.session_state:
    st.session_state.form_data = {
        'symptoms': '',
        'symptom_duration': 1,
        'symptom_unit': 'days',
        'meals_per_day': 0,
        'water_intake': 0,
        'last_meal': '',
        'additional_info': '',
        'exercise_frequency': 'never',
        'sleep_hours': 7,
        'stress_level': 'moderate',
        'smoking_status': 'non-smoker',
        'alcohol_consumption': 'none'
    }

# Gemini API configuration
IDENTITY = """<Role>
Medi-Safe, created by Siddharth Satija, is an empathetic AI health companion that helps individuals who feel unwell or overwhelmed by confusing online health information. It listens calmly, simplifies verified facts, and helps users make safe, confident, and informed decisions. Medi-Safe combines emotional reassurance with practical, educational guidance—something often missing from diagnostic-focused AI tools.
</Role>

<Goal>
The goal is to support users with clarity, comfort, and confidence by offering two evidence-based guidance paths:
1) **Drug Information (OTC Education Only)** – Offers clear, safe, and easy-to-understand explanations about common over-the-counter medicines, their usage awareness, and safety reminders.  
2) **Lifestyle Assistance** – Provides personalized, science-backed recommendations for hydration, sleep, stress management, and nutrition to support faster recovery.  
Medi-Safe never diagnoses or prescribes—it educates, reassures, and empowers users to make informed choices about their well-being.
</Goal>

<Rules>
1. Start every conversation with an empathetic, warm, and respectful greeting that builds trust.  
2. Detect the emotional tone of the user's input (e.g., worry, fatigue, frustration) and adapt the tone—patient, calm, and supportive.  
3. Gather core details naturally: symptoms, duration, meals, hydration, last meal, and any allergies or medical history.  
4. Confirm collected data once before providing information to ensure accuracy and clarity.  
5. Present two choices: **Drug Information** and **Lifestyle Guidance**—explain their purpose clearly.  
6. **If Drug Information is chosen:**  
   - Provide only **OTC (over-the-counter)** education; never recommend or prescribe medication.  
   - Explain what the medicine does, how it helps, and its common real-world uses.  
   - All dosage and timing details must come exclusively from the internal `get_dosage` tool linked to a vetted `dosage_facts` table.  
   - Never invent, guess, or hallucinate dosage numbers.  
   - Always include safety guidelines, dosage intervals, and "When to seek care."  
7. **Safety Gate:** Before showing any dosing info, verify user's **age (must be 18+), allergies, pregnancy, chronic conditions, and current medications.**  
8. If safety inputs are missing or conflicting, politely request clarification and pause dosage guidance.  
9. **If Lifestyle Guidance is chosen:**  
   - Ask about exercise frequency, sleep hours, stress level, hydration, smoking, and alcohol consumption.  
   - Offer small, actionable lifestyle tips (e.g., "try 7–9 hours of sleep," "drink 2–3 L water," "do light stretching").  
   - Explain *why* each habit helps and what users can expect from following it.  
10. Always include a "When to seek care" section.  
11. Clearly display a medical disclaimer in every session: "This information is for educational purposes and is not medical advice."  
12. Detect red-flag symptoms (chest pain, severe vomiting, confusion, shortness of breath, persistent fever, self-harm). Immediately respond with:  
    "⚠️ Your symptoms sound serious — please seek urgent medical care or contact emergency services."  
13. Keep all responses short, friendly, and well-structured (3–6 lines or bullets).  
14. Never diagnose, prescribe, or override a medical professional.  
15. Store user data only for the session; never collect or save identifiable information.  
16. Avoid repetition or filler text—every response should add new value.  
17. Validate emotions: "It's okay to feel this way; you're taking the right steps."  
18. Use small, calm emojis 🌿💊💧😊 sparingly to make tone friendly yet professional.  
19. End every session with positivity and reassurance: "You're doing a great job taking care of yourself. Rest well and stay hydrated."  
20. If the user indicates being under 18, immediately show:  
    "This service is for adults (18+) only. Please seek guidance from a parent, guardian, or healthcare professional."  
</Rules>

<Knowledge>
Medi-Safe is designed to handle mild-to-moderate wellness concerns such as fever, fatigue, cold, headache, mild stomach upset, dehydration, or stress.  
It can explain over-the-counter medication categories—antipyretics (acetaminophen, ibuprofen), antacids, oral rehydration salts (ORS)—and general use guidance.  

All dosage data must be retrieved **only** from the verified internal `dosage_facts` table via the `get_dosage` tool.  
If missing or incomplete, Medi-Safe clearly says it cannot provide dosage information and advises reading product labels or consulting a pharmacist or doctor.  
No brand names, prescription medicines, or treatment plans should ever be provided.  

For lifestyle guidance, Medi-Safe offers simple, science-based suggestions:
- Hydrate (2–3 L/day depending on needs)  
- Sleep 7–9 hours nightly  
- Eat balanced meals, limit caffeine, and reduce screen time  
- Light exercise or stretching daily  
- Stress-relief techniques (breathing, journaling, brief outdoor breaks)  

All advice should include *why* it helps and *what to expect*, e.g., "Better sleep and hydration can reduce fatigue in 2–3 days."  

Health knowledge must be drawn from reputable sources (Mayo Clinic, WebMD, CDC, NHS, WHO).  
Medi-Safe fully complies with Google Gemini API and data-safety standards:  
- Never diagnose, treat, or prescribe.  
- Never delay medical care.  
- Never collect or store personally identifiable information.  
- Be transparent about data handling and allow users to clear sessions anytime.  
</Knowledge>"""

def get_gemini_response(user_message, patient_context):
    """Get response from Gemini API"""
    try:
        # Configure Gemini
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            return "⚠️ API key not configured. Please add your GEMINI_API_KEY to Streamlit secrets."
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        # Build full prompt with identity and context
        full_prompt = f"{IDENTITY}\n\n{patient_context}\n\nUser: {user_message}"
        
        # Generate response
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"I'm sorry, I'm having trouble connecting right now. Error: {str(e)}"

def build_patient_context():
    """Build patient context from form data"""
    data = st.session_state.form_data
    context = "\n<PatientContext>\n"
    
    if data['symptoms']:
        context += f"Symptoms: {data['symptoms']}\n"
    context += f"Duration: {data['symptom_duration']} {data['symptom_unit']}\n"
    context += f"Meals per day: {data['meals_per_day']}\n"
    context += f"Water intake: {data['water_intake']} liters/day\n"
    
    if data['last_meal']:
        context += f"Last meal: {data['last_meal']}\n"
    if data['additional_info']:
        context += f"Additional info: {data['additional_info']}\n"
    
    if st.session_state.selected_option:
        context += f"\nGuidance Type Selected: {st.session_state.selected_option}\n"
        
        if st.session_state.selected_option == 'Lifestyle Guidance':
            context += f"Exercise: {data['exercise_frequency']}\n"
            context += f"Sleep: {data['sleep_hours']} hours\n"
            context += f"Stress: {data['stress_level']}\n"
            context += f"Smoking: {data['smoking_status']}\n"
            context += f"Alcohol: {data['alcohol_consumption']}\n"
    
    context += "</PatientContext>\n"
    return context

# Navigation functions
def go_to_chatbot():
    st.session_state.step = 'chatbot'
    # Initialize chat with greeting
    if not st.session_state.chat_history:
        if st.session_state.selected_option == 'Medicine Information':
            greeting = "Hello! 🌿 I'm Medi-Safe, your empathetic health companion. I'm here to help you understand your medicine better. Please share any questions about your medications, dosage, or concerns."
        else:
            greeting = "Hello! 💚 I'm Medi-Safe, and I'm here to help you build healthier lifestyle habits. Let's talk about your wellness journey together."
        st.session_state.chat_history.append({"role": "assistant", "content": greeting})

def go_back():
    if st.session_state.step == 'chatbot':
        if st.session_state.selected_option == 'Medicine Information':
            st.session_state.step = 'patient_info'
        else:
            st.session_state.step = 'lifestyle'
        st.session_state.chat_history = []
    elif st.session_state.step == 'lifestyle':
        st.session_state.step = 'patient_info'

# Main App
st.title("🏥 MedSafe")
st.caption("Created by Siddharth Satija")

# PATIENT INFO FORM
if st.session_state.step == 'patient_info':
    st.markdown("### Patient Information Form")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.session_state.form_data['symptoms'] = st.text_area(
            "What symptoms are you experiencing? *",
            value=st.session_state.form_data['symptoms'],
            placeholder="e.g., headache, fever, cough, fatigue...",
            height=120
        )
    
    with col2:
        st.write("**Since when have you been experiencing these symptoms?**")
        col_a, col_b = st.columns([2, 1])
        with col_a:
            st.session_state.form_data['symptom_duration'] = st.number_input(
                "Duration",
                min_value=0,
                value=st.session_state.form_data['symptom_duration'],
                label_visibility="collapsed"
            )
        with col_b:
            st.session_state.form_data['symptom_unit'] = st.selectbox(
                "Unit",
                ['hours', 'days', 'weeks', 'months'],
                index=['hours', 'days', 'weeks', 'months'].index(st.session_state.form_data['symptom_unit']),
                label_visibility="collapsed"
            )
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write("**Meals per day**")
        st.session_state.form_data['meals_per_day'] = st.number_input(
            "Meals",
            min_value=0,
            max_value=10,
            value=st.session_state.form_data['meals_per_day'],
            label_visibility="collapsed"
        )
        
        # Color feedback for meals
        meals = st.session_state.form_data['meals_per_day']
        if meals == 0:
            st.markdown("🔴 **0 meals - Please eat something!**")
        elif meals == 1:
            st.markdown("🟠 **1 meal - Try to eat more**")
        elif meals == 2:
            st.markdown("🟡 **2 meals - Good**")
        else:
            st.markdown("🟢 **3+ meals - Excellent!**")
    
    with col2:
        st.write("**Daily water intake (liters)**")
        st.session_state.form_data['water_intake'] = st.slider(
            "Water",
            min_value=0,
            max_value=10,
            value=st.session_state.form_data['water_intake'],
            label_visibility="collapsed"
        )
        st.markdown(f"💧 **{st.session_state.form_data['water_intake']} L per day**")
    
    with col3:
        st.session_state.form_data['last_meal'] = st.text_input(
            "What was your last meal?",
            value=st.session_state.form_data['last_meal'],
            placeholder="e.g., rice and chicken"
        )
    
    st.session_state.form_data['additional_info'] = st.text_area(
        "Any additional information?",
        value=st.session_state.form_data['additional_info'],
        placeholder="e.g., existing conditions, allergies...",
        height=80
    )
    
    st.markdown("---")
    st.markdown("### Select Guidance Type")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💊 Medicine Information", use_container_width=True, type="primary" if st.session_state.selected_option == 'Medicine Information' else "secondary"):
            st.session_state.selected_option = 'Medicine Information'
            go_to_chatbot()
            st.rerun()
        st.caption("Get OTC education and medication guidance")
    
    with col2:
        if st.button("💚 Lifestyle Guidance", use_container_width=True, type="primary" if st.session_state.selected_option == 'Lifestyle Guidance' else "secondary"):
            st.session_state.selected_option = 'Lifestyle Guidance'
            st.session_state.step = 'lifestyle'
            st.rerun()
        st.caption("Get personalized health recommendations")

# LIFESTYLE FORM
elif st.session_state.step == 'lifestyle':
    col1, col2 = st.columns([1, 8])
    with col1:
        if st.button("⬅️ Back"):
            go_back()
            st.rerun()
    with col2:
        st.markdown("### 💚 Lifestyle Guidance Questionnaire")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.session_state.form_data['exercise_frequency'] = st.selectbox(
            "Exercise Frequency",
            ['never', 'rarely', 'sometimes', 'regularly', 'daily'],
            index=['never', 'rarely', 'sometimes', 'regularly', 'daily'].index(st.session_state.form_data['exercise_frequency'])
        )
        
        st.session_state.form_data['sleep_hours'] = st.slider(
            "Average Sleep Hours",
            min_value=0,
            max_value=24,
            value=st.session_state.form_data['sleep_hours']
        )
    
    with col2:
        st.session_state.form_data['stress_level'] = st.selectbox(
            "Current Stress Level",
            ['low', 'moderate', 'high', 'very-high'],
            index=['low', 'moderate', 'high', 'very-high'].index(st.session_state.form_data['stress_level'])
        )
        
        st.session_state.form_data['smoking_status'] = st.selectbox(
            "Smoking Status",
            ['non-smoker', 'former-smoker', 'occasional', 'regular'],
            index=['non-smoker', 'former-smoker', 'occasional', 'regular'].index(st.session_state.form_data['smoking_status'])
        )
    
    with col3:
        st.session_state.form_data['alcohol_consumption'] = st.selectbox(
            "Alcohol Consumption",
            ['none', 'occasional', 'moderate', 'regular', 'frequent'],
            index=['none', 'occasional', 'moderate', 'regular', 'frequent'].index(st.session_state.form_data['alcohol_consumption'])
        )
    
    st.markdown("---")
    col1, col2, col3 = st.columns([3, 1, 1])
    with col2:
        if st.button("⬅️ Back", use_container_width=True):
            go_back()
            st.rerun()
    with col3:
        if st.button("Continue to Chat →", use_container_width=True, type="primary"):
            go_to_chatbot()
            st.rerun()

# CHATBOT
elif st.session_state.step == 'chatbot':
    col1, col2 = st.columns([1, 8])
    with col1:
        if st.button("⬅️ Back"):
            go_back()
            st.rerun()
    with col2:
        if st.session_state.selected_option == 'Medicine Information':
            st.markdown("### 💊 Medicine Assistant")
        else:
            st.markdown("### 💚 Lifestyle Coach")
    
    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Type your message..."):
        # Add user message
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                context = build_patient_context()
                response = get_gemini_response(prompt, context)
                st.markdown(response)
                st.session_state.chat_history.append({"role": "assistant", "content": response})
    
    # Disclaimer
    st.markdown("---")
    st.caption("⚠️ This information is for educational purposes and is not medical advice.")

# Footer
st.markdown("---")
st.caption("MedSafe - Your empathetic AI health companion | Created by Siddharth Satija")
