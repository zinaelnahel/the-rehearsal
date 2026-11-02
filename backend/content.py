"""Curated multilingual demo content. All sample situations are fictional."""
LANGUAGES = {'English': 'en', 'German': 'de', 'Spanish': 'es'}
NO_CORRECTION = {
 'English':'The scripted demo identified no specific correction for this turn. This is not a live language assessment.',
 'German':'Die skriptbasierte Demo hat für diesen Beitrag keine konkrete Korrektur erkannt. Dies ist keine Live-Sprachbewertung.',
 'Spanish':'La demostración con guion no ha detectado una corrección concreta para este turno. No es una evaluación lingüística en vivo.'
}
LEVELS = ('Everyday', 'B1', 'B2')

CONTENT = {
 'apartment': {
  'English': {
   'opening': 'Hello, welcome to the viewing. What would you like to know about the apartment?',
   'goals': ['Ask about the monthly rent', 'Ask about availability', 'Ask whether pets are allowed'],
   'starters': ['How much is the monthly rent?', 'When is the apartment available?', 'Are pets allowed?'],
   'patterns': [r'rent|price|cost', r'availab|when|move in|date', r'pet|dog|cat'],
   'vocabulary': 'Rent · deposit · bills · availability · pets'},
  'German': {
   'opening': 'Guten Tag, willkommen zur Besichtigung. Was möchten Sie über die Wohnung wissen?',
   'goals': ['Nach der monatlichen Miete fragen', 'Nach der Verfügbarkeit fragen', 'Fragen, ob Haustiere erlaubt sind'],
   'starters': ['Wie hoch ist die monatliche Miete?', 'Ab wann ist die Wohnung verfügbar?', 'Sind Haustiere erlaubt?'],
   'patterns': [r'miete|preis|kostet|kosten', r'verfug|wann|einzieh|datum|frei', r'haustier|hund|katze'],
   'vocabulary': 'Miete · Kaution · Nebenkosten · Verfügbarkeit · Haustiere'},
  'Spanish': {
   'opening': 'Hola, bienvenido a la visita. ¿Qué te gustaría saber del piso?',
   'goals': ['Preguntar por el alquiler mensual', 'Preguntar por la disponibilidad', 'Preguntar si se admiten mascotas'],
   'starters': ['¿Cuánto cuesta el alquiler al mes?', '¿Cuándo está disponible el piso?', '¿Se admiten mascotas?'],
   'patterns': [r'alquiler|precio|cuesta|renta', r'disponib|cuando|fecha|entrar', r'mascota|perro|gato'],
   'vocabulary': 'Alquiler · fianza · gastos · disponibilidad · mascotas'}},
 'interview': {
  'English': {
   'opening': 'Hello, thank you for coming. Could you tell me about your relevant experience?',
   'goals': ['Describe your relevant experience', 'Ask about working hours', 'Ask about the salary'],
   'starters': ['I have experience in customer service.', 'What are the working hours?', 'What is the salary?'],
   'patterns': [r'experience|worked|customer|years', r'hours|schedule|shift', r'salary|pay|wage'],
   'vocabulary': 'Experience · responsibilities · working hours · salary'},
  'German': {
   'opening': 'Guten Tag, danke, dass Sie gekommen sind. Erzählen Sie mir bitte von Ihrer Berufserfahrung.',
   'goals': ['Die relevante Berufserfahrung beschreiben', 'Nach den Arbeitszeiten fragen', 'Nach dem Gehalt fragen'],
   'starters': ['Ich habe Erfahrung im Kundenservice.', 'Wie sind die Arbeitszeiten?', 'Wie hoch ist das Gehalt?'],
   'patterns': [r'erfahrung|gearbeitet|kunden|jahre', r'arbeitszeit|stunden|schicht', r'gehalt|lohn|bezahlt'],
   'vocabulary': 'Berufserfahrung · Aufgaben · Arbeitszeiten · Gehalt'},
  'Spanish': {
   'opening': 'Hola, gracias por venir. ¿Puedes contarme un poco sobre tu experiencia?',
   'goals': ['Describir tu experiencia relevante', 'Preguntar por el horario de trabajo', 'Preguntar por el salario'],
   'starters': ['Tengo experiencia en atención al cliente.', '¿Cuál es el horario de trabajo?', '¿Cuál es el salario?'],
   'patterns': [r'experiencia|trabajado|trabaje|anos|cliente', r'horario|horas|jornada', r'salario|sueldo|pagan'],
   'vocabulary': 'Experiencia · responsabilidades · horario · sueldo'}},
 'course': {
  'English': {
   'opening': 'Hello, welcome to the school. What would you like to know about the course?',
   'goals': ['Ask about the class schedule', 'Ask about the course price', 'Ask about cancellation'],
   'starters': ['When are the classes?', 'How much does the course cost?', 'What is the cancellation policy?'],
   'patterns': [r'schedule|when|class|time|days', r'price|cost|pay|fee', r'cancel|refund'],
   'vocabulary': 'Enrolment · timetable · fee · materials · cancellation'},
  'German': {
   'opening': 'Guten Tag, willkommen in der Schule. Was möchten Sie über den Kurs wissen?',
   'goals': ['Nach den Kurszeiten fragen', 'Nach dem Kurspreis fragen', 'Nach der Stornierung fragen'],
   'starters': ['Wann findet der Unterricht statt?', 'Wie viel kostet der Kurs?', 'Welche Stornierungsbedingungen gelten?'],
   'patterns': [r'kurszeit|wann|unterricht|uhr|tage|stundenplan', r'preis|kostet|kosten|gebuhr|bezahlen', r'storn|kundig|ruckerstatt'],
   'vocabulary': 'Anmeldung · Stundenplan · Kursgebühr · Materialien · Stornierung'},
  'Spanish': {
   'opening': 'Hola, bienvenido a la escuela. ¿En qué puedo ayudarte?',
   'goals': ['Preguntar por el horario de las clases', 'Preguntar por el precio del curso', 'Preguntar por la cancelación'],
   'starters': ['¿Cuál es el horario de las clases?', '¿Cuánto cuesta el curso?', '¿Cuál es la política de cancelación?'],
   'patterns': [r'horario|dias|clase|hora', r'precio|cuesta|coste|pagar', r'cancel|devolucion|reembolso'],
   'vocabulary': 'Matrícula · horario · precio · materiales · cancelación'}},
 'difficult': {
  'English': {
   'opening': 'Hi, thanks for making time to talk. What would you like us to discuss?',
   'goals': ['Explain your concern without blame', 'Ask for the other person’s perspective', 'Propose a concrete next step'],
   'starters': ['I feel concerned when plans change at short notice.', 'How do you see the situation?', 'Could we agree on a next step?'],
   'patterns': [r'i feel|i am concerned|i find|i noticed|i need', r'your (view|perspective)|how do you|what do you think', r'could we|shall we|next step|agree|suggest|propose'],
   'vocabulary': 'Concern · perspective · boundary · compromise · next step'},
  'German': {
   'opening': 'Hallo, danke, dass du dir Zeit nimmst. Worüber möchtest du sprechen?',
   'goals': ['Das eigene Anliegen ohne Vorwürfe erklären', 'Nach der Sichtweise der anderen Person fragen', 'Einen konkreten nächsten Schritt vorschlagen'],
   'starters': ['Ich fühle mich verunsichert, wenn sich Pläne kurzfristig ändern.', 'Wie siehst du die Situation?', 'Können wir einen nächsten Schritt vereinbaren?'],
   'patterns': [r'ich fuhle|ich bin besorgt|ich finde|ich brauche|mir ist', r'wie siehst|deine (sicht|meinung)|was denkst', r'konnen wir|nachsten schritt|vereinbar|vorschlag|schlage'],
   'vocabulary': 'Anliegen · Sichtweise · Grenze · Kompromiss · nächster Schritt'},
  'Spanish': {
   'opening': 'Hola, gracias por dedicar tiempo a hablar. ¿De qué te gustaría hablar?',
   'goals': ['Explicar tu preocupación sin culpar', 'Preguntar por el punto de vista de la otra persona', 'Proponer un próximo paso concreto'],
   'starters': ['Me preocupa que los planes cambien a última hora.', '¿Cómo ves la situación?', '¿Podemos acordar un próximo paso?'],
   'patterns': [r'me preocupa|me siento|yo necesito|he notado', r'como ves|tu (opinion|punto de vista)|que piensas', r'podemos|proximo paso|acord|propongo'],
   'vocabulary': 'Preocupación · punto de vista · límite · acuerdo · próximo paso'}}
}

COMMON = {
 'English': {
  'grounded': 'Let’s check the document; the original passage is below. If a detail is absent, it is not specified. What else would you like to ask?',
  'continue': 'Thank you for explaining. What would you like to discuss next?',
  'retry': 'Let’s rehearse that moment again. What would you like to say or ask?',
  'suggestion': 'Try this as a clear, considerate way to move the conversation forward. This is a practice suggestion, not a grammar correction.',
  'punctuation': 'Written Spanish uses an opening question mark as well as a closing one.',
  'interested': 'Use estar interesado/a to express interest.',
  'translation': 'Demo phrase only: “I would like to know…” → {phrase}. Free-text translation requires live mode.',
  'note': 'Scripted demo: keyword-based progress is approximate; edited goals need live mode for automatic assessment. Hints used: {count}.',
  'clarify': 'What still needs to be clarified about this goal: {goal}?',
  'prompt': 'Could you explain that a little more?',
  'terms': 'Useful words: '},
 'German': {
  'grounded': 'Schauen wir in das Dokument; die Originalstelle steht unten. Fehlt eine Angabe, ist sie nicht angegeben. Was möchten Sie noch fragen?',
  'continue': 'Danke für die Erklärung. Worüber möchten Sie als Nächstes sprechen?',
  'retry': 'Üben wir diesen Moment noch einmal. Was möchten Sie sagen oder fragen?',
  'suggestion': 'Versuchen Sie diese Formulierung, um das Gespräch klar und respektvoll weiterzuführen. Das ist ein Übungsvorschlag, keine Grammatikkorrektur.',
  'punctuation': 'Im geschriebenen Spanisch stehen Fragezeichen am Anfang und am Ende einer Frage.',
  'interested': 'Verwenden Sie estar interesado/a, um Interesse auszudrücken.',
  'translation': 'Nur ein Demo-Beispiel: „I would like to know…“ → {phrase}. Freie Übersetzungen benötigen den Live-Modus.',
  'note': 'Skriptbasierte Demo: Die Erkennung durch Schlüsselwörter ist ungenau. Bearbeitete Ziele benötigen den Live-Modus zur Auswertung. Verwendete Hilfen: {count}.',
  'clarify': 'Was muss zu diesem Ziel noch geklärt werden: {goal}?',
  'prompt': 'Könnten Sie das etwas genauer erklären?',
  'terms': 'Nützliche Wörter: '},
 'Spanish': {
  'grounded': 'Podemos consultar el documento; el fragmento original aparece abajo. Si el detalle no aparece, no está especificado. ¿Qué más te gustaría preguntar?',
  'continue': 'Gracias por contármelo. ¿De qué te gustaría hablar ahora?',
  'retry': 'Vamos a ensayar ese momento otra vez. ¿Qué te gustaría decir o preguntar?',
  'suggestion': 'Prueba esta expresión para continuar la conversación de forma clara y respetuosa. Es una sugerencia de práctica, no una corrección gramatical.',
  'punctuation': 'En español escrito se usa un signo de apertura y otro de cierre en las preguntas.',
  'interested': 'Usa estar interesado/a para expresar interés.',
  'translation': 'Solo una frase de demostración: «I would like to know…» → {phrase}. La traducción libre requiere el modo en vivo.',
  'note': 'Demostración con guion: el progreso por palabras clave es aproximado; los objetivos editados necesitan el modo en vivo para evaluarse. Ayudas usadas: {count}.',
  'clarify': '¿Qué falta aclarar sobre este objetivo: {goal}?',
  'prompt': '¿Podrías explicarlo un poco más?',
  'terms': 'Palabras útiles: '}
}

TRANSLATIONS = {'English':'I would like to know…','German':'Ich würde gerne wissen…','Spanish':'Me gustaría saber…'}

def pack(session, feedback=False):
 setup=session['setup']
 from backend.context import BREAKUP
 from backend.family_boundary import FAMILY_BOUNDARY
 language=setup['feedback_language'] if feedback else setup['language']
 return BREAKUP[language] if session.get('breakup') else FAMILY_BOUNDARY[language] if session.get('family_boundary') else CONTENT[setup['scenario']][language]

def goal_index(session, text):
 """Goals are in the feedback language; matching patterns are in the spoken language."""
 goals=pack(session,feedback=True)['goals']
 return goals.index(text) if text in goals else None
