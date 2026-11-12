"""Authored interview phrases express questions, never invented qualifications."""

INTERVIEW_PHRASES = {
    'English': ('May I tell you about my background?', 'Is remote work possible for this role?', 'What is the salary range?'),
    'German': ('Darf ich Ihnen meinen Hintergrund vorstellen?', 'Ist bei dieser Stelle Remote-Arbeit möglich?', 'In welchem Bereich liegt das Gehalt?'),
    'Spanish': ('¿Puedo hablarle de mi trayectoria?', '¿Es posible trabajar en remoto en este puesto?', '¿Cuál es el rango salarial?'),
}


def phrase_choices(session):
    """An empty tuple leaves non-interview phrase generation unchanged."""
    if session['setup']['scenario'] == 'interview':
        return INTERVIEW_PHRASES[session['setup']['language']]
    return ()


def bind_phrases(phrases, choices):
    """Enforce the allowlist even for legacy/internal model adapters."""
    if not choices:
        return phrases
    selected = list(dict.fromkeys(phrase for phrase in phrases if phrase in choices))
    return (selected + [phrase for phrase in choices if phrase not in selected])[:3]
